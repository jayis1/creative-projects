"""
Genetic algorithm for evolving Core War warriors.

Uses mutation, crossover, and fitness-based selection to evolve
warriors over generations. Fitness is determined by battle performance
against a set of opponent warriors.

This is a significant feature that enables automated warrior design
through evolutionary computation.
"""

from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode, OPCODE_NAMES, ADDRESS_MODE_SYMBOLS
from core_war.parser import RedcodeParser, ParsedWarrior
from core_war.scheduler import BattleScheduler, BattleStats
from core_war.loader import load_warrior_from_string

logger = logging.getLogger("core_war.mutator")


# All opcodes that can appear in generated warriors
_MUTATABLE_OPCODES = [
    Opcode.DAT, Opcode.MOV, Opcode.ADD, Opcode.SUB, Opcode.MUL,
    Opcode.DIV, Opcode.MOD, Opcode.JMP, Opcode.JMZ, Opcode.JMN,
    Opcode.DJN, Opcode.SPL, Opcode.CMP, Opcode.SNE, Opcode.SLT, Opcode.NOP,
]

# All modifiers
_MUTATABLE_MODIFIERS = list(Modifier)

# All addressing modes
_MUTATABLE_MODES = list(AddressMode)


@dataclass
class Individual:
    """
    A single warrior in the genetic population.

    Each individual has a genome (list of Instructions), a fitness score,
    and metadata about its lineage.
    """

    name: str
    genome: List[Instruction]
    fitness: float = 0.0
    battles_won: int = 0
    battles_lost: int = 0
    battles_drawn: int = 0
    generation: int = 0
    parent_names: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        """Fraction of battles won."""
        total = self.battles_won + self.battles_lost + self.battles_drawn
        if total == 0:
            return 0.0
        return self.battles_won / total

    def to_source(self) -> str:
        """Convert the genome to Redcode source text."""
        lines = [f"; {self.name} (gen {self.generation}, fitness={self.fitness:.1f})"]
        lines.append(f"        ORG     start")
        lines.append("")
        for i, instr in enumerate(self.genome):
            label = "start   " if i == 0 else "        "
            a_sym = ADDRESS_MODE_SYMBOLS.get(instr.a_mode, "$")
            b_sym = ADDRESS_MODE_SYMBOLS.get(instr.b_mode, "$")
            lines.append(f"{label}{instr.opcode.name}.{instr.modifier.name} "
                        f"{a_sym}{instr.a_value}, {b_sym}{instr.b_value}")
        return "\n".join(lines)

    def to_parsed(self) -> ParsedWarrior:
        """Parse the genome's source into a ParsedWarrior."""
        source = self.to_source()
        return load_warrior_from_string(source, self.name)


@dataclass
class PopulationStats:
    """Statistics for a generation of the genetic algorithm."""

    generation: int
    population_size: int
    best_fitness: float
    avg_fitness: float
    worst_fitness: float
    best_individual: str
    diversity: float  # 0-1, how diverse the population is
    total_battles: int = 0


class WarriorMutator:
    """
    Mutates warrior genomes to create variations.

    Mutation operations:
    - Point mutation: Change a single instruction field
    - Instruction swap: Swap two instructions
    - Insertion: Insert a new random instruction
    - Deletion: Remove an instruction
    - Duplication: Duplicate an instruction
    """

    def __init__(self, mutation_rate: float = 0.15, rng: Optional[random.Random] = None):
        """
        Args:
            mutation_rate: Probability of each instruction being mutated (0-1).
            rng: Optional random number generator for reproducibility.
        """
        if not 0 <= mutation_rate <= 1:
            raise ValueError(f"mutation_rate must be 0-1, got {mutation_rate}")
        self.mutation_rate = mutation_rate
        self.rng = rng or random.Random()

    def mutate(self, individual: Individual) -> Individual:
        """Apply mutations to an individual and return the mutated copy."""
        # Deep copy the genome
        new_genome = [instr.copy() for instr in individual.genome]
        mutations: List[str] = []

        for i, instr in enumerate(new_genome):
            if self.rng.random() < self.mutation_rate:
                mutation_type = self.rng.choice(["opcode", "modifier", "a_mode",
                                                   "a_value", "b_mode", "b_value"])
                old_val = getattr(instr, mutation_type)
                new_val = self._random_field_value(mutation_type)
                setattr(instr, mutation_type, new_val)
                mutations.append(f"instr[{i}].{mutation_type}: {old_val}→{new_val}")

        # Structural mutations (less frequent)
        if self.rng.random() < self.mutation_rate * 0.3 and len(new_genome) > 2:
            # Deletion
            idx = self.rng.randint(0, len(new_genome) - 1)
            new_genome.pop(idx)
            mutations.append(f"deleted instruction at {idx}")

        if self.rng.random() < self.mutation_rate * 0.2 and len(new_genome) < 20:
            # Insertion
            idx = self.rng.randint(0, len(new_genome))
            new_genome.insert(idx, self._random_instruction())
            mutations.append(f"inserted random instruction at {idx}")

        if self.rng.random() < self.mutation_rate * 0.15 and len(new_genome) >= 2:
            # Swap
            i, j = self.rng.sample(range(len(new_genome)), 2)
            new_genome[i], new_genome[j] = new_genome[j], new_genome[i]
            mutations.append(f"swapped instructions {i} and {j}")

        # Ensure at least 1 instruction
        if not new_genome:
            new_genome = [self._random_instruction()]

        return Individual(
            name=self._generate_name(individual),
            genome=new_genome,
            generation=individual.generation + 1,
            parent_names=[individual.name],
            mutations=mutations,
        )

    def crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """
        Create a child by combining genomes from two parents.

        Uses single-point crossover: take the first N instructions from
        parent1 and the rest from parent2.
        """
        # Choose crossover point
        max_len = max(len(parent1.genome), len(parent2.genome))
        if max_len <= 1:
            cross_point = 1
        else:
            cross_point = self.rng.randint(1, max_len)

        # Combine genomes
        genome = [instr.copy() for instr in parent1.genome[:cross_point]]
        genome += [instr.copy() for instr in parent2.genome[cross_point:]]

        # Ensure at least 1 instruction
        if not genome:
            genome = [self._random_instruction()]

        return Individual(
            name=self._generate_name(parent1, parent2),
            genome=genome,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_names=[parent1.name, parent2.name],
            mutations=[],
        )

    def _random_field_value(self, field_name: str):
        """Generate a random value for a given instruction field."""
        if field_name == "opcode":
            return self.rng.choice(_MUTATABLE_OPCODES)
        elif field_name == "modifier":
            return self.rng.choice(_MUTATABLE_MODIFIERS)
        elif field_name in ("a_mode", "b_mode"):
            return self.rng.choice(_MUTATABLE_MODES)
        elif field_name in ("a_value", "b_value"):
            return self.rng.randint(0, 20)
        return 0

    def _random_instruction(self) -> Instruction:
        """Generate a completely random instruction."""
        return Instruction(
            opcode=self.rng.choice(_MUTATABLE_OPCODES),
            modifier=self.rng.choice(_MUTATABLE_MODIFIERS),
            a_mode=self.rng.choice(_MUTATABLE_MODES),
            a_value=self.rng.randint(0, 20),
            b_mode=self.rng.choice(_MUTATABLE_MODES),
            b_value=self.rng.randint(0, 20),
        )

    def _generate_name(self, *parents: Individual) -> str:
        """Generate a unique name for a child based on parent names."""
        suffix = "".join(self.rng.choices(string.ascii_lowercase + string.digits, k=4))
        if len(parents) == 1:
            return f"{parents[0].name[:8]}_{suffix}"
        return f"{parents[0].name[:4]}{parents[1].name[:4]}_{suffix}"


class GeneticEvolver:
    """
    Evolves a population of warriors using genetic algorithms.

    Workflow:
    1. Initialize population (random or seed warriors)
    2. Evaluate fitness (battle against opponents)
    3. Select survivors (tournament selection)
    4. Create children (crossover + mutation)
    5. Repeat for N generations

    Usage::

        evolver = GeneticEvolver(
            population_size=20,
            generations=10,
            opponents=[load_warrior("warriors/dwarf.red")],
        )
        best = evolver.evolve()
        print(f"Best warrior: {best.name} (fitness={best.fitness:.1f})")
    """

    def __init__(
        self,
        population_size: int = 20,
        generations: int = 10,
        opponents: Optional[List[ParsedWarrior]] = None,
        core_size: int = 8000,
        max_cycles: int = 10000,
        rounds_per_battle: int = 3,
        mutation_rate: float = 0.15,
        elite_fraction: float = 0.2,
        seed: Optional[int] = None,
    ):
        """
        Args:
            population_size: Number of individuals in each generation.
            generations: Number of generations to evolve.
            opponents: Warriors to battle against for fitness evaluation.
            core_size: Core size for battles.
            max_cycles: Max cycles per battle.
            rounds_per_battle: Rounds per battle for fitness evaluation.
            mutation_rate: Probability of mutation.
            elite_fraction: Fraction of top individuals preserved (elitism).
            seed: Random seed for reproducibility.
        """
        if population_size < 2:
            raise ValueError("population_size must be at least 2")
        if generations < 1:
            raise ValueError("generations must be at least 1")
        if not 0 <= elite_fraction <= 1:
            raise ValueError("elite_fraction must be 0-1")

        self.population_size = population_size
        self.generations = generations
        self.opponents = opponents or []
        self.core_size = core_size
        self.max_cycles = max_cycles
        self.rounds_per_battle = rounds_per_battle
        self.mutation_rate = mutation_rate
        self.elite_fraction = elite_fraction
        self.rng = random.Random(seed)

        self.mutator = WarriorMutator(mutation_rate=mutation_rate, rng=self.rng)
        self.history: List[PopulationStats] = []
        self.best_ever: Optional[Individual] = None

    def evolve(
        self,
        seed_warriors: Optional[List[ParsedWarrior]] = None,
        on_generation: Optional[Callable[[int, PopulationStats], None]] = None,
    ) -> Individual:
        """
        Run the genetic algorithm and return the best individual.

        Args:
            seed_warriors: Optional initial warriors to seed the population.
            on_generation: Optional callback called after each generation.

        Returns:
            The best individual found across all generations.
        """
        # Initialize population
        population = self._initialize_population(seed_warriors)

        for gen in range(self.generations):
            # Evaluate fitness
            self._evaluate_fitness(population)

            # Record statistics
            stats = self._compute_stats(population, gen)
            self.history.append(stats)

            # Track best ever
            best_in_gen = max(population, key=lambda ind: ind.fitness)
            if self.best_ever is None or best_in_gen.fitness > self.best_ever.fitness:
                self.best_ever = Individual(
                    name=best_in_gen.name,
                    genome=[instr.copy() for instr in best_in_gen.genome],
                    fitness=best_in_gen.fitness,
                    battles_won=best_in_gen.battles_won,
                    battles_lost=best_in_gen.battles_lost,
                    battles_drawn=best_in_gen.battles_drawn,
                    generation=best_in_gen.generation,
                    parent_names=list(best_in_gen.parent_names),
                )

            logger.info(
                "Generation %d: best=%.1f, avg=%.1f, best_individual=%s",
                gen, stats.best_fitness, stats.avg_fitness, stats.best_individual,
            )

            if on_generation:
                on_generation(gen, stats)

            # Don't evolve on the last generation
            if gen == self.generations - 1:
                break

            # Selection + reproduction
            population = self._reproduce(population)

        return self.best_ever  # type: ignore

    def _initialize_population(
        self, seed_warriors: Optional[List[ParsedWarrior]] = None
    ) -> List[Individual]:
        """Initialize the population with seed warriors and random individuals."""
        population: List[Individual] = []

        # Add seed warriors
        if seed_warriors:
            for i, w in enumerate(seed_warriors[:self.population_size]):
                # Create a genome from the warrior's instructions
                genome = [instr.copy() for instr in w.instructions]
                population.append(Individual(
                    name=f"seed_{w.name}_{i}",
                    genome=genome,
                    generation=0,
                ))

        # Fill remaining with random individuals
        while len(population) < self.population_size:
            genome_len = self.rng.randint(3, 10)
            genome = [self.mutator._random_instruction() for _ in range(genome_len)]
            population.append(Individual(
                name=f"rand_{len(population)}",
                genome=genome,
                generation=0,
            ))

        return population

    def _evaluate_fitness(self, population: List[Individual]) -> None:
        """Evaluate fitness by battling each individual against opponents."""
        if not self.opponents:
            # No opponents — fitness based on instruction count (shorter = better)
            for ind in population:
                ind.fitness = max(0, 20 - len(ind.genome))
            return

        for ind in population:
            try:
                parsed = ind.to_parsed()
            except Exception:
                # Invalid warrior — lowest fitness
                ind.fitness = 0
                ind.battles_lost = len(self.opponents)
                continue

            total_score = 0
            ind.battles_won = 0
            ind.battles_lost = 0
            ind.battles_drawn = 0

            for opponent in self.opponents:
                try:
                    scheduler = BattleScheduler(
                        core_size=self.core_size,
                        max_cycles=self.max_cycles,
                        rounds=self.rounds_per_battle,
                        seed=self.rng.randint(0, 2**31 - 1),
                    )
                    stats = scheduler.run_battle([parsed, opponent])
                    ind_stats = stats.get(parsed.name, BattleStats(name=parsed.name))
                    total_score += ind_stats.score
                    ind.battles_won += ind_stats.wins
                    ind.battles_lost += ind_stats.losses
                    ind.battles_drawn += ind_stats.draws
                except Exception as e:
                    logger.debug("Battle failed for %s: %s", ind.name, e)
                    ind.battles_lost += 1

            ind.fitness = total_score

    def _compute_stats(self, population: List[Individual], generation: int) -> PopulationStats:
        """Compute statistics for the current population."""
        fitnesses = [ind.fitness for ind in population]
        best = max(population, key=lambda ind: ind.fitness)

        # Compute diversity (fraction of unique genomes)
        unique = set()
        for ind in population:
            # Hash the genome
            genome_hash = tuple(
                (instr.opcode, instr.modifier, instr.a_value, instr.b_value)
                for instr in ind.genome
            )
            unique.add(genome_hash)
        diversity = len(unique) / len(population) if population else 0

        return PopulationStats(
            generation=generation,
            population_size=len(population),
            best_fitness=max(fitnesses) if fitnesses else 0,
            avg_fitness=sum(fitnesses) / len(fitnesses) if fitnesses else 0,
            worst_fitness=min(fitnesses) if fitnesses else 0,
            best_individual=best.name,
            diversity=diversity,
            total_battles=sum(ind.battles_won + ind.battles_lost + ind.battles_drawn
                             for ind in population),
        )

    def _reproduce(self, population: List[Individual]) -> List[Individual]:
        """Create the next generation via selection, crossover, and mutation."""
        # Sort by fitness (descending)
        sorted_pop = sorted(population, key=lambda ind: -ind.fitness)

        # Elite preservation
        elite_count = max(1, int(self.elite_fraction * self.population_size))
        elites = [Individual(
            name=ind.name,
            genome=[instr.copy() for instr in ind.genome],
            fitness=ind.fitness,
            battles_won=ind.battles_won,
            battles_lost=ind.battles_lost,
            battles_drawn=ind.battles_drawn,
            generation=ind.generation,
        ) for ind in sorted_pop[:elite_count]]

        # Create children to fill the rest
        children: List[Individual] = []
        while len(elites) + len(children) < self.population_size:
            # Tournament selection (pick 2 from random 3)
            tournament_size = min(3, len(sorted_pop))
            candidates = self.rng.sample(sorted_pop, tournament_size)
            candidates.sort(key=lambda ind: -ind.fitness)
            parent1 = candidates[0]
            parent2 = candidates[1] if len(candidates) > 1 else candidates[0]

            # Crossover
            child = self.mutator.crossover(parent1, parent2)

            # Mutate
            if self.rng.random() < self.mutation_rate:
                child = self.mutator.mutate(child)

            children.append(child)

        return elites + children

    def get_history(self) -> List[PopulationStats]:
        """Get the evolution history (statistics per generation)."""
        return self.history

    def save_best(self, path: str) -> None:
        """Save the best warrior found to a .red file."""
        if not self.best_ever:
            raise RuntimeError("No best individual — run evolve() first")
        source = self.best_ever.to_source()
        with open(path, "w") as f:
            f.write(source)
        logger.info("Saved best warrior to %s", path)