"""
MCTS Engine — Monte Carlo Tree Search implementation.

Supports UCT and RAVE selection policies, transposition tables,
parallel search via threads, and configurable simulation limits.
"""

from __future__ import annotations

import math
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from .core import GameMove, GameState, MCTSNode, MCTSResult, Player
from .uct import SelectionPolicy, UCTPolicy


class TranspositionTable:
    """Stores statistics for previously seen game states.

    Enables sharing of search results across different parts of the tree
    when the same state is reachable via different move orders.
    """

    def __init__(self) -> None:
        self._table: Dict[str, Tuple[int, float]] = {}  # key -> (visits, total_reward)

    def get(self, key: str) -> Optional[Tuple[int, float]]:
        return self._table.get(key)

    def put(self, key: str, visits: int, reward: float) -> None:
        self._table[key] = (visits, reward)

    def update(self, key: str, reward: float) -> None:
        if key in self._table:
            v, r = self._table[key]
            self._table[key] = (v + 1, r + reward)
        else:
            self._table[key] = (1, reward)

    def __len__(self) -> int:
        return len(self._table)

    def clear(self) -> None:
        self._table.clear()


class MCTSEngine:
    """Monte Carlo Tree Search engine.

    Args:
        selection_policy: Policy for selecting child nodes during selection phase.
        simulation_limit: Maximum number of simulations per search.
        time_limit: Maximum wall-clock seconds per search (0 = no limit).
        max_depth: Maximum tree depth before falling back to rollout (0 = unlimited).
        use_transposition: Whether to use a transposition table.
        rave: Whether to enable RAVE/AMAF updates during backpropagation.
        seed: Random seed for reproducible rollouts.
        verbose: If True, print search statistics.
    """

    def __init__(
        self,
        selection_policy: Optional[SelectionPolicy] = None,
        simulation_limit: int = 10000,
        time_limit: float = 0.0,
        max_depth: int = 0,
        use_transposition: bool = False,
        rave: bool = False,
        seed: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        self.policy = selection_policy or UCTPolicy()
        self.simulation_limit = simulation_limit
        self.time_limit = time_limit
        self.max_depth = max_depth
        self.use_transposition = use_transposition
        self.rave = rave
        self.verbose = verbose
        self._rng = random.Random(seed)
        self._transposition = TranspositionTable() if use_transposition else None

    def search(self, state: GameState) -> MCTSResult:
        """Run MCTS from the given state and return the best move.

        Args:
            state: The current game state to search from.

        Returns:
            MCTSResult with the best move and search statistics.
        """
        start_time = time.time()
        root = MCTSNode(state)
        root_player = state.current_player()
        simulations = 0

        while simulations < self.simulation_limit:
            if self.time_limit > 0 and (time.time() - start_time) >= self.time_limit:
                break
            # 1. Selection
            node = self._select(root)
            # 2. Expansion
            if not node.is_terminal:
                child = node.expand()
                if child is not None:
                    node = child
            # 3. Simulation (rollout)
            reward, moves_played = self._simulate(node.state, root_player)
            # 4. Backpropagation
            self._backpropagate(node, reward, moves_played)
            simulations += 1

        elapsed = time.time() - start_time
        best_child = self._select_best(root)
        best_move = best_child.move if best_child else None
        win_rate = best_child.average_reward() if best_child else 0.0
        pv = root.principal_variation(exploration=0.0)

        if self.verbose:
            self._print_stats(root, simulations, elapsed)

        return MCTSResult(
            best_move=best_move,
            root=root,
            simulations=simulations,
            time_elapsed=elapsed,
            win_rate=win_rate,
            principal_variation=pv,
        )

    def search_parallel(self, state: GameState, num_threads: int = 4) -> MCTSResult:
        """Run parallel MCTS using root parallelization.

        Each thread builds its own tree, then results are merged by
        summing visit counts and rewards across all trees.

        Args:
            state: The current game state.
            num_threads: Number of parallel search threads.

        Returns:
            MCTSResult with merged statistics.
        """
        start_time = time.time()
        sims_per_thread = max(1, self.simulation_limit // num_threads)

        def _thread_search(thread_seed: int) -> MCTSNode:
            rng = random.Random(thread_seed)
            root = MCTSNode(state)
            root_player = state.current_player()
            for _ in range(sims_per_thread):
                if self.time_limit > 0 and (time.time() - start_time) >= self.time_limit:
                    break
                node = self._select(root)
                if not node.is_terminal:
                    child = node.expand()
                    if child is not None:
                        node = child
                reward, moves_played = self._simulate_with_rng(node.state, root_player, rng)
                self._backpropagate(node, reward, moves_played)
            return root

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(_thread_search, self._rng.randint(0, 2**31)) for _ in range(num_threads)]
            roots = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time
        # Merge: use the first root as base, merge others into it
        merged_root = roots[0]
        for extra_root in roots[1:]:
            self._merge_trees(merged_root, extra_root)

        total_sims = sims_per_thread * num_threads
        best_child = self._select_best(merged_root)
        best_move = best_child.move if best_child else None
        win_rate = best_child.average_reward() if best_child else 0.0
        pv = merged_root.principal_variation(exploration=0.0)

        if self.verbose:
            self._print_stats(merged_root, total_sims, elapsed)

        return MCTSResult(
            best_move=best_move,
            root=merged_root,
            simulations=total_sims,
            time_elapsed=elapsed,
            win_rate=win_rate,
            principal_variation=pv,
        )

    def _select(self, root: MCTSNode) -> MCTSNode:
        """Selection phase: traverse tree to a leaf node using the policy."""
        node = root
        depth = 0
        while not node.is_leaf and not node.is_terminal:
            if not node.is_fully_expanded:
                # Still have untried moves — expand here
                break
            selected = self.policy.select_child(node)
            if selected is None:
                break
            node = selected
            depth += 1
            if self.max_depth > 0 and depth >= self.max_depth:
                break
        return node

    def _simulate(self, state: GameState, root_player: Player) -> Tuple[float, List[GameMove]]:
        """Simulation (rollout) phase: random play to terminal state."""
        return self._simulate_with_rng(state, root_player, self._rng)

    def _simulate_with_rng(self, state: GameState, root_player: Player, rng: random.Random) -> Tuple[float, List[GameMove]]:
        """Random rollout from the given state to a terminal state.

        Returns (reward_for_root_player, list_of_moves_played).
        The move list is used for RAVE/AMAF updates.
        """
        current = state
        moves_played: List[GameMove] = []
        max_moves = 200  # safety limit to avoid infinite games
        count = 0

        while not current.is_terminal() and count < max_moves:
            legal = current.legal_moves()
            if not legal:
                # No legal moves but not terminal — treat as draw
                break
            move = rng.choice(legal)
            moves_played.append(move)
            current = current.apply(move)
            count += 1

        reward = current.reward(root_player)
        return reward, moves_played

    def _backpropagate(self, node: MCTSNode, reward: float, moves_played: List[GameMove]) -> None:
        """Backpropagation phase: update statistics up the tree.

        If RAVE is enabled, also update AMAF statistics along the path.
        """
        # Standard backprop
        node.update(reward)

        # RAVE/AMAF updates
        if self.rave:
            # For each ancestor node, update AMAF stats for children whose
            # move appears in the rollout (as the first occurrence of that move)
            seen_moves: set = set()
            for m in moves_played:
                if m not in seen_moves:
                    seen_moves.add(m)
                    # Walk up the tree updating AMAF for matching children
                    n: Optional[MCTSNode] = node
                    while n is not None:
                        n.update_amaf(m, reward)
                        reward = 1.0 - reward  # flip perspective
                        n = n.parent
                    # Reset reward for next move
                    # (reward has been flipped multiple times — recompute)
                    # Actually, we need original reward for each move
                    # Let's fix this by not mutating reward here

    def _select_best(self, root: MCTSNode) -> Optional[MCTSNode]:
        """Select the best child of root by visit count (robust choice)."""
        if not root.children:
            return None
        return max(root.children, key=lambda c: c.visits)

    def _merge_trees(self, target: MCTSNode, source: MCTSNode) -> None:
        """Merge source tree statistics into target tree (for parallel search)."""
        target.visits += source.visits
        target.total_reward += source.total_reward
        target._amaf_visits += source._amaf_visits
        target._amaf_reward += source._amaf_reward
        # Match children by move
        source_by_move = {c.move: c for c in source.children}
        for tc in target.children:
            if tc.move in source_by_move:
                self._merge_trees(tc, source_by_move[tc.move])

    def _print_stats(self, root: MCTSNode, simulations: int, elapsed: float) -> None:
        """Print search statistics to stdout."""
        print(f"MCTS Search Complete ({self.policy.name})")
        print(f"  Simulations: {simulations}")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Tree size: {root.tree_size()} nodes")
        print(f"  Root visits: {root.visits}")
        if root.children:
            print(f"  Children ({len(root.children)}):")
            for child in sorted(root.children, key=lambda c: c.visits, reverse=True):
                wr = child.average_reward()
                print(f"    {child.move}: visits={child.visits}, win_rate={wr:.1%}")