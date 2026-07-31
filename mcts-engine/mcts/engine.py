"""
MCTS Engine — Monte Carlo Tree Search implementation.

Supports UCT and RAVE selection policies, transposition tables,
parallel search via threads, tree reuse between moves, custom rollout
policies, progressive bias, and configurable simulation limits.
"""

from __future__ import annotations

import math
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple

from .core import GameMove, GameState, MCTSNode, MCTSResult, Player
from .uct import SelectionPolicy, UCTPolicy


# Type alias for a rollout policy function.
# Takes (state, rng) and returns a move, or None to fall back to random.
RolloutPolicy = Callable[[GameState, random.Random], Optional[GameMove]]


class TranspositionTable:
    """Stores statistics for previously seen game states.

    Enables sharing of search results across different parts of the tree
    when the same state is reachable via different move orders.
    """

    def __init__(self, max_size: int = 100000) -> None:
        self._table: Dict[str, Tuple[int, float]] = {}  # key -> (visits, total_reward)
        self._max_size = max_size

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


class SearchStats:
    """Collects statistics about MCTS search performance over time.

    Useful for analyzing search efficiency and convergence.
    """

    def __init__(self) -> None:
        self.total_simulations: int = 0
        self.total_time: float = 0.0
        self.total_tree_nodes: int = 0
        self.searches: int = 0
        self._win_rates: List[float] = []

    def record(self, result: MCTSResult) -> None:
        self.total_simulations += result.simulations
        self.total_time += result.time_elapsed
        self.total_tree_nodes += result.root.tree_size()
        self.searches += 1
        self._win_rates.append(result.win_rate)

    def summary(self) -> str:
        avg_sims = self.total_simulations / max(1, self.searches)
        avg_time = self.total_time / max(1, self.searches)
        avg_nodes = self.total_tree_nodes / max(1, self.searches)
        avg_wr = sum(self._win_rates) / max(1, len(self._win_rates))
        return (
            f"SearchStats: {self.searches} searches, "
            f"avg {avg_sims:.0f} sims, avg {avg_time:.3f}s, "
            f"avg {avg_nodes:.0f} nodes, avg win_rate={avg_wr:.1%}"
        )

    def __repr__(self) -> str:
        return self.summary()


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
        rollout_policy: Custom policy for the simulation/rollout phase.
            Takes (state, rng) and returns a move, or None for random fallback.
        progressive_bias: Weight for progressive bias heuristic (0 = disabled).
            Adds a prior based on a heuristic evaluation of each child.
        heuristic_fn: Heuristic evaluation function for progressive bias.
            Takes a GameState and returns a float in [0, 1] for the current player.
        tree_reuse: If True, reuse the subtree from the previous search for the
            next search when the game state is a descendant of the previous root.
        rollout_limit: Maximum number of moves in a rollout before declaring a draw.
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
        rollout_policy: Optional[RolloutPolicy] = None,
        progressive_bias: float = 0.0,
        heuristic_fn: Optional[Callable[[GameState], float]] = None,
        tree_reuse: bool = False,
        rollout_limit: int = 200,
    ) -> None:
        self.policy = selection_policy or UCTPolicy()
        self.simulation_limit = simulation_limit
        self.time_limit = time_limit
        self.max_depth = max_depth
        self.use_transposition = use_transposition
        self.rave = rave
        self.verbose = verbose
        self.rollout_policy = rollout_policy
        self.progressive_bias = progressive_bias
        self.heuristic_fn = heuristic_fn
        self.tree_reuse = tree_reuse
        self.rollout_limit = rollout_limit
        self._rng = random.Random(seed)
        self._transposition = TranspositionTable() if use_transposition else None
        self._last_root: Optional[MCTSNode] = None
        self._last_state_key: Optional[str] = None
        self.stats = SearchStats()

    def search(self, state: GameState) -> MCTSResult:
        """Run MCTS from the given state and return the best move.

        Args:
            state: The current game state to search from.

        Returns:
            MCTSResult with the best move and search statistics.
        """
        start_time = time.time()
        root_player = state.current_player()

        # Tree reuse: check if current state is a descendant of the previous root
        root: MCTSNode
        if self.tree_reuse and self._last_root is not None:
            root = self._reuse_tree(state) or MCTSNode(state)
        else:
            root = MCTSNode(state)

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
                    # Apply progressive bias prior if enabled
                    if self.progressive_bias > 0 and self.heuristic_fn:
                        self._apply_progressive_bias(child)
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

        # Save root for tree reuse
        if self.tree_reuse:
            self._last_root = root
            self._last_state_key = state.hash_key()

        # Record stats
        result = MCTSResult(
            best_move=best_move,
            root=root,
            simulations=simulations,
            time_elapsed=elapsed,
            win_rate=win_rate,
            principal_variation=pv,
        )
        self.stats.record(result)

        if self.verbose:
            self._print_stats(root, simulations, elapsed)

        return result

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
        if num_threads <= 1:
            return self.search(state)

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
                        if self.progressive_bias > 0 and self.heuristic_fn:
                            self._apply_progressive_bias(child)
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

        result = MCTSResult(
            best_move=best_move,
            root=merged_root,
            simulations=total_sims,
            time_elapsed=elapsed,
            win_rate=win_rate,
            principal_variation=pv,
        )
        self.stats.record(result)

        if self.verbose:
            self._print_stats(merged_root, total_sims, elapsed)

        return result

    def _reuse_tree(self, state: GameState) -> Optional[MCTSNode]:
        """Try to reuse subtree from previous search.

        Walks the previous tree to find the node matching the current state.
        Returns the reused subtree root, or None if not found.
        """
        if self._last_root is None:
            return None
        # Try to find the current state in the previous tree
        # by following the principal variation or breadth-first search
        target_key = state.hash_key()

        # BFS through the previous tree
        from collections import deque
        queue = deque([self._last_root])
        while queue:
            node = queue.popleft()
            if node.state.hash_key() == target_key:
                # Detach from parent so it becomes a new root
                node.parent = None
                return node
            queue.extend(node.children)
        return None

    def _select(self, root: MCTSNode) -> MCTSNode:
        """Selection phase: traverse tree to a leaf node using the policy.

        Follows the selection policy to choose children until reaching a node
        that is terminal, has untried moves, or reaches max depth.
        """
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

        Uses the custom rollout policy if provided, falling back to random
        when the policy returns None or an illegal move.

        Returns (reward_for_root_player, list_of_moves_played).
        The move list is used for RAVE/AMAF updates.
        """
        current = state
        moves_played: List[GameMove] = []
        count = 0

        while not current.is_terminal() and count < self.rollout_limit:
            legal = current.legal_moves()
            if not legal:
                # No legal moves but not terminal — treat as draw
                break

            move: Optional[GameMove] = None
            if self.rollout_policy is not None:
                try:
                    move = self.rollout_policy(current, rng)
                except Exception:
                    move = None
                # Validate the move is legal
                if move is not None and move not in legal:
                    move = None

            if move is None:
                move = rng.choice(legal)

            moves_played.append(move)
            current = current.apply(move)
            count += 1

        reward = current.reward(root_player)
        return reward, moves_played

    def _backpropagate(self, node: MCTSNode, reward: float, moves_played: List[GameMove]) -> None:
        """Backpropagation phase: update statistics up the tree.

        Standard backpropagation flips the reward perspective at each level
        (zero-sum alternation). If RAVE is enabled, also updates AMAF
        statistics along the path.

        Args:
            node: The leaf node where simulation ended.
            reward: The reward from the terminal state (for root player).
            moves_played: Moves played during the rollout (for RAVE).
        """
        # Standard backprop with perspective alternation
        node.update(reward)

        # RAVE/AMAF updates
        # For each unique move in the rollout, update AMAF stats for matching
        # children along the entire tree path from leaf to root.
        if self.rave and moves_played:
            # Track first occurrence of each move (AMAF = "all moves as first")
            seen_moves: set = set()
            # The reward alternates perspective as we go up the tree.
            # The leaf node's player just made a move, so the node represents
            # the state AFTER that move. The reward is from root player's perspective.
            # When we update a child at a node where it's player P's turn,
            # the relevant reward is from P's perspective.
            # node.update() already flipped correctly, so we walk up and flip
            # the same way for AMAF.
            for m in moves_played:
                if m in seen_moves:
                    continue
                seen_moves.add(m)
                # Walk from leaf to root, updating AMAF for children matching move m
                # Reward perspective flips at each level (same as standard backprop)
                amaf_reward = reward
                n: Optional[MCTSNode] = node
                while n is not None:
                    n.update_amaf(m, amaf_reward)
                    amaf_reward = 1.0 - amaf_reward  # flip perspective
                    n = n.parent

    def _apply_progressive_bias(self, child: MCTSNode) -> None:
        """Apply progressive bias prior to a newly created child node.

        Adds virtual visits and rewards based on a heuristic evaluation,
        which biases the UCB1 formula toward heuristically good moves
        early in the search. The influence decays as real visits accumulate.
        """
        if self.heuristic_fn is None:
            return
        try:
            h = self.heuristic_fn(child.state)
        except Exception:
            return
        # Add virtual visits proportional to the bias weight
        virtual_visits = max(1, int(self.progressive_bias * 10))
        child.visits += virtual_visits
        child.total_reward += h * virtual_visits

    def _select_best(self, root: MCTSNode) -> Optional[MCTSNode]:
        """Select the best child of root by visit count (robust choice).

        Visit count is the most robust metric for MCTS move selection,
        as it correlates with the move's actual value under the search policy.
        Ties are broken by average reward.
        """
        if not root.children:
            return None
        return max(root.children, key=lambda c: (c.visits, c.average_reward()))

    def _merge_trees(self, target: MCTSNode, source: MCTSNode) -> None:
        """Merge source tree statistics into target tree (for parallel search).

        Sums visit counts, rewards, and AMAF statistics recursively.
        Children are matched by their move.
        """
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
        print(f"  Sims/sec: {simulations/elapsed:.0f}" if elapsed > 0 else "  Sims/sec: N/A")
        print(f"  Tree size: {root.tree_size()} nodes")
        print(f"  Root visits: {root.visits}")
        if root.children:
            print(f"  Children ({len(root.children)}):")
            for child in sorted(root.children, key=lambda c: c.visits, reverse=True):
                wr = child.average_reward()
                rave_str = ""
                if child._amaf_visits > 0:
                    amaf_avg = child._amaf_reward / child._amaf_visits
                    rave_str = f", amaf={amaf_avg:.2f}({child._amaf_visits})"
                print(f"    {child.move}: visits={child.visits}, win_rate={wr:.1%}{rave_str}")

    def reset(self) -> None:
        """Reset engine state, clearing tree reuse and transposition table."""
        self._last_root = None
        self._last_state_key = None
        if self._transposition:
            self._transposition.clear()
        self.stats = SearchStats()