"""
Test suite for new Core War modules (v3.0 additions).

Tests cover:
  - Configuration management (BattleConfig)
  - Strategy analyzer
  - Battle recording and replay
  - Genetic evolution
  - CLI interface
  - Enhanced Instruction class
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from core_war.config import BattleConfig, load_config
from core_war.strategy_analyzer import (
    StrategyAnalyzer, StrategyType, AnalysisResult, Vulnerability,
)
from core_war.replay import (
    BattleRecorder, BattleReplay, BattleRecording, CycleSnapshot,
)
from core_war.mutator import (
    GeneticEvolver, WarriorMutator, Individual, PopulationStats,
)
from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode
from core_war.parser import RedcodeParser, ParsedWarrior
from core_war.mars import MARS
from core_war.loader import load_warrior_from_string


# ============================================================================
# Config Tests
# ============================================================================

class TestConfig:
    """Tests for BattleConfig."""

    def test_default_config(self):
        config = BattleConfig()
        assert config.core_size == 8000
        assert config.max_cycles == 80000
        assert config.rounds == 10
        assert config.warriors == []
        assert config.log_level == "INFO"

    def test_custom_config(self):
        config = BattleConfig(core_size=1000, max_cycles=5000, rounds=5, seed=42)
        assert config.core_size == 1000
        assert config.max_cycles == 5000
        assert config.seed == 42

    def test_config_validation_positive(self):
        with pytest.raises(ValueError, match="core_size must be positive"):
            BattleConfig(core_size=0)
        with pytest.raises(ValueError, match="max_cycles must be positive"):
            BattleConfig(max_cycles=-1)
        with pytest.raises(ValueError, match="rounds must be positive"):
            BattleConfig(rounds=0)

    def test_config_validation_log_level(self):
        with pytest.raises(ValueError, match="Invalid log_level"):
            BattleConfig(log_level="VERBOSE")

    def test_config_validation_output_format(self):
        with pytest.raises(ValueError, match="Invalid output_format"):
            BattleConfig(output_format="xml")

    def test_config_to_dict(self):
        config = BattleConfig(core_size=100)
        d = config.to_dict()
        assert d["core_size"] == 100
        assert "warriors" in d
        assert "log_level" in d

    def test_config_to_json(self):
        config = BattleConfig(core_size=100, rounds=5)
        j = config.to_json()
        data = json.loads(j)
        assert data["core_size"] == 100
        assert data["rounds"] == 5

    def test_config_from_dict(self):
        data = {"core_size": 200, "max_cycles": 1000, "rounds": 3, "unknown_key": "ignored"}
        config = BattleConfig.from_dict(data)
        assert config.core_size == 200
        assert config.rounds == 3

    def test_config_save_load_json(self, tmp_path):
        path = tmp_path / "config.json"
        config = BattleConfig(core_size=500, max_cycles=10000, seed=99)
        config.save(str(path))
        assert path.exists()
        loaded = BattleConfig.from_file(str(path))
        assert loaded.core_size == 500
        assert loaded.seed == 99

    def test_config_save_load_yaml(self, tmp_path):
        path = tmp_path / "config.yaml"
        config = BattleConfig(core_size=500, rounds=7)
        config.save(str(path))
        assert path.exists()
        loaded = BattleConfig.from_file(str(path))
        assert loaded.core_size == 500
        assert loaded.rounds == 7

    def test_config_create_template(self, tmp_path):
        path = tmp_path / "template.yaml"
        BattleConfig.create_template(str(path))
        assert path.exists()
        content = path.read_text()
        assert "core_size" in content
        assert "warriors" in content

    def test_config_unsupported_format(self, tmp_path):
        path = tmp_path / "config.txt"
        config = BattleConfig()
        with pytest.raises(ValueError, match="Unsupported config format"):
            config.save(str(path))

    def test_config_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            BattleConfig.from_file("/nonexistent/config.json")

    def test_load_config_function(self, tmp_path):
        path = tmp_path / "config.json"
        BattleConfig(core_size=42).save(str(path))
        config = load_config(str(path))
        assert config.core_size == 42

    def test_config_unreasonably_large_core(self):
        with pytest.raises(ValueError, match="unreasonably large"):
            BattleConfig(core_size=2_000_000)

    def test_config_to_yaml(self):
        config = BattleConfig(core_size=100)
        yaml_str = config.to_yaml()
        assert "core_size: 100" in yaml_str


# ============================================================================
# Strategy Analyzer Tests
# ============================================================================

class TestStrategyAnalyzer:
    """Tests for the strategy analyzer."""

    def setup_method(self):
        self.analyzer = StrategyAnalyzer()
        self.parser = RedcodeParser()

    def test_analyze_imp(self):
        w = self.parser.parse("MOV 0, 1", "Imp")
        result = self.analyzer.analyze(w)
        assert result.strategy == StrategyType.IMP
        assert result.instruction_count == 1
        assert result.estimated_resilience > 0

    def test_analyze_bomber(self):
        w = self.parser.parse(
            "ADD #4, bomb\nMOV bomb, @bomb\nJMP 0\nbomb DAT 0, 0", "Bomber"
        )
        result = self.analyzer.analyze(w)
        assert result.strategy == StrategyType.BOMBER
        assert result.has_bombing == True
        assert result.estimated_aggressiveness > 0

    def test_analyze_scanner(self):
        src = """
        ORG scan
scan    ADD step, ptr
ptr     JMZ scan, 100
        MOV bomb, @ptr
        JMP scan
step    DAT 10, 10
bomb    DAT 0, 0
"""
        w = self.parser.parse(src, "Scanner")
        result = self.analyzer.analyze(w)
        assert result.has_scanning == True
        assert result.estimated_aggressiveness > 5

    def test_analyze_replicator(self):
        src = """
        ORG copy
copy    SPL @copy
        MOV copy, <copy
        JMP copy
"""
        w = self.parser.parse(src, "Replicator")
        result = self.analyzer.analyze(w)
        assert result.has_replication == True
        assert result.has_spl == True
        assert result.process_estimate > 1

    def test_analyze_vulnerabilities(self):
        w = self.parser.parse("JMP 0", "Looper")
        result = self.analyzer.analyze(w)
        assert len(result.vulnerabilities) > 0
        # Should have "no offensive capability" vulnerability
        vulns = [v for v in result.vulnerabilities if "offensive" in v.description]
        assert len(vulns) > 0

    def test_analyze_aggressiveness_scale(self):
        # Pure imp should have low aggressiveness
        imp = self.parser.parse("MOV 0, 1", "Imp")
        imp_result = self.analyzer.analyze(imp)
        assert imp_result.estimated_aggressiveness <= 3

        # Scanner should have higher aggressiveness
        scanner = self.parser.parse(
            "ADD 1, ptr\nJMZ 0, 2\nMOV 3, @ptr\nJMP 0\nptr DAT 0, 0", "Scanner"
        )
        scanner_result = self.analyzer.analyze(scanner)
        assert scanner_result.estimated_aggressiveness > imp_result.estimated_aggressiveness

    def test_analyze_resilience_scale(self):
        # Single process should have lower resilience than multi-process
        single = self.parser.parse("JMP 0", "Single")
        multi = self.parser.parse("SPL 1\nJMP 0", "Multi")
        single_r = self.analyzer.analyze(single)
        multi_r = self.analyzer.analyze(multi)
        assert multi_r.estimated_resilience > single_r.estimated_resilience

    def test_analyze_to_dict(self):
        w = self.parser.parse("MOV 0, 1", "Imp")
        result = self.analyzer.analyze(w)
        d = result.to_dict()
        assert d["name"] == "Imp"
        assert d["strategy"] == "Imp"
        assert "opcode_frequency" in d
        assert "vulnerabilities" in d

    def test_analyze_source(self):
        result = self.analyzer.analyze_source("MOV 0, 1", "InlineImp")
        assert result.strategy == StrategyType.IMP
        assert result.name == "InlineImp"

    def test_compare_warriors(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        w2 = self.parser.parse("DAT 0, 0", "Dead")
        comparison = self.analyzer.compare(w1, w2)
        assert "warrior1" in comparison
        assert "warrior2" in comparison
        assert "predicted_winner" in comparison
        # Imp has resilience but no aggression; Dead has neither
        # The prediction is heuristic, just check it's a valid result
        assert comparison["predicted_winner"] in ("Imp", "too close to call")

    def test_strategy_type_from_str(self):
        assert StrategyType.from_str("Bomber") == StrategyType.BOMBER
        assert StrategyType.from_str("bomber") == StrategyType.BOMBER
        assert StrategyType.from_str("Unknown") == StrategyType.UNKNOWN
        assert StrategyType.from_str("NonExistent") == StrategyType.UNKNOWN

    def test_opcode_frequency(self):
        from core_war.strategy_analyzer import OpcodeFrequency
        freq = OpcodeFrequency()
        freq.add(Opcode.MOV)
        freq.add(Opcode.MOV)
        freq.add(Opcode.DAT)
        assert freq.counts["MOV"] == 2
        assert freq.counts["DAT"] == 1
        assert freq.total == 3
        assert freq.percentage("MOV") == pytest.approx(200.0/3)
        assert freq.most_common(1)[0] == ("MOV", 2)

    def test_uses_indirect_detection(self):
        w = self.parser.parse("MOV @1, $2", "Indirect")
        result = self.analyzer.analyze(w)
        assert result.uses_indirect == True

    def test_uses_postinc_detection(self):
        w = self.parser.parse("MOV }1, $2", "PostInc")
        result = self.analyzer.analyze(w)
        assert result.uses_postinc == True

    def test_uses_predec_detection(self):
        w = self.parser.parse("MOV {1, $2", "PreDec")
        result = self.analyzer.analyze(w)
        assert result.uses_predec == True

    def test_self_modifying_detection(self):
        w = self.parser.parse("ADD #4, $1\nDAT 0, 0", "Modifier")
        result = self.analyzer.analyze(w)
        assert result.self_modifying == True

    def test_process_estimate(self):
        w = self.parser.parse("SPL 1\nSPL 1\nJMP 0", "Splitter")
        result = self.analyzer.analyze(w)
        assert result.process_estimate >= 2

    def test_summary_generation(self):
        w = self.parser.parse("MOV 0, 1", "Imp")
        result = self.analyzer.analyze(w)
        assert "Imp" in result.summary
        assert "Imp" in result.summary


# ============================================================================
# Replay Tests
# ============================================================================

class TestReplay:
    """Tests for battle recording and replay."""

    def setup_method(self):
        self.parser = RedcodeParser()

    def test_record_battle(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        w2 = self.parser.parse("JMP 0", "Looper")
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        recorder = BattleRecorder(max_snapshots=100)
        recording = recorder.record(mars, [w1, w2])
        assert len(recording.snapshots) > 0
        assert recording.core_size == 50
        assert "Imp" in recording.warrior_loads
        assert "Looper" in recording.warrior_loads

    def test_recording_save_load(self, tmp_path):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        w2 = self.parser.parse("JMP 0", "Looper")
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1, w2])

        path = tmp_path / "battle.json"
        recording.save(str(path))
        assert path.exists()

        loaded = BattleRecording.from_file(str(path))
        assert loaded.core_size == 50
        assert len(loaded.snapshots) == len(recording.snapshots)
        assert "Imp" in loaded.warrior_loads

    def test_replay_play(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        w2 = self.parser.parse("JMP 0", "Looper")
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1, w2])

        replay = BattleReplay(recording)
        cycles_seen = 0
        for snapshot in replay.play():
            assert isinstance(snapshot, CycleSnapshot)
            assert snapshot.cycle >= 0
            cycles_seen += 1
        assert cycles_seen > 0

    def test_replay_get_core_at(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1])

        replay = BattleReplay(recording)
        # Get core state at cycle 0
        core0 = replay.get_core_at(0)
        assert len(core0) == 50
        # Get core state at last cycle
        core_last = replay.get_core_at(len(recording.snapshots) - 1)
        assert len(core_last) == 50

    def test_replay_summary(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1])
        replay = BattleReplay(recording)
        summary = replay.summary()
        assert "Battle Recording Summary" in summary
        assert "Core size: 50" in summary

    def test_replay_total_cycles(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1])
        replay = BattleReplay(recording)
        assert replay.total_cycles() == len(recording.snapshots)

    def test_recording_to_dict_to_json(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1])
        d = recording.to_dict()
        assert "core_size" in d
        assert "snapshots" in d
        j = recording.to_json()
        assert json.loads(j)["core_size"] == 50

    def test_recording_max_snapshots(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=100, seed=42)
        recorder = BattleRecorder(max_snapshots=5)
        recording = recorder.record(mars, [w1])
        assert len(recording.snapshots) <= 5

    def test_recording_from_dict(self):
        w1 = self.parser.parse("MOV 0, 1", "Imp")
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        recorder = BattleRecorder()
        recording = recorder.record(mars, [w1])
        d = recording.to_dict()
        loaded = BattleRecording.from_dict(d)
        assert loaded.core_size == recording.core_size
        assert len(loaded.snapshots) == len(recording.snapshots)


# ============================================================================
# Genetic Evolver Tests
# ============================================================================

class TestMutator:
    """Tests for warrior mutation and genetic evolution."""

    def test_mutator_init(self):
        mutator = WarriorMutator(mutation_rate=0.2)
        assert mutator.mutation_rate == 0.2

    def test_mutator_invalid_rate(self):
        with pytest.raises(ValueError, match="mutation_rate must be 0-1"):
            WarriorMutator(mutation_rate=1.5)

    def test_mutate_individual(self):
        import random
        rng = random.Random(42)
        mutator = WarriorMutator(mutation_rate=0.5, rng=rng)
        genome = [Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                               AddressMode.DIRECT, 1)]
        ind = Individual(name="test", genome=genome, generation=0)
        mutated = mutator.mutate(ind)
        assert mutated.generation == 1
        assert mutated.parent_names == ["test"]
        # With 50% mutation rate on 1 instruction, it may or may not mutate
        assert len(mutated.genome) >= 1

    def test_crossover(self):
        import random
        rng = random.Random(42)
        mutator = WarriorMutator(rng=rng)
        genome1 = [Instruction(Opcode.MOV), Instruction(Opcode.JMP), Instruction(Opcode.DAT)]
        genome2 = [Instruction(Opcode.ADD), Instruction(Opcode.SUB), Instruction(Opcode.MUL)]
        parent1 = Individual(name="p1", genome=genome1, generation=0)
        parent2 = Individual(name="p2", genome=genome2, generation=0)
        child = mutator.crossover(parent1, parent2)
        assert len(child.genome) >= 1
        assert child.parent_names == ["p1", "p2"]
        assert child.generation == 1

    def test_individual_to_source(self):
        genome = [Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                               AddressMode.DIRECT, 1)]
        ind = Individual(name="TestWarrior", genome=genome, generation=5)
        source = ind.to_source()
        assert "TestWarrior" in source
        assert "MOV.I" in source

    def test_individual_to_parsed(self):
        genome = [Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                               AddressMode.DIRECT, 1)]
        ind = Individual(name="TestWarrior", genome=genome, generation=0)
        parsed = ind.to_parsed()
        assert parsed.name == "TestWarrior"
        assert len(parsed.instructions) >= 1

    def test_individual_win_rate(self):
        ind = Individual(name="test", genome=[Instruction()])
        ind.battles_won = 3
        ind.battles_lost = 1
        ind.battles_drawn = 1
        assert ind.win_rate == pytest.approx(3/5)

    def test_individual_win_rate_zero(self):
        ind = Individual(name="test", genome=[Instruction()])
        assert ind.win_rate == 0.0


class TestGeneticEvolver:
    """Tests for the genetic evolver."""

    def test_evolver_init(self):
        evolver = GeneticEvolver(population_size=10, generations=5, seed=42)
        assert evolver.population_size == 10
        assert evolver.generations == 5

    def test_evolver_invalid_params(self):
        with pytest.raises(ValueError, match="population_size"):
            GeneticEvolver(population_size=1)
        with pytest.raises(ValueError, match="generations"):
            GeneticEvolver(generations=0)
        with pytest.raises(ValueError, match="elite_fraction"):
            GeneticEvolver(elite_fraction=1.5)

    def test_evolver_evolve_no_opponents(self):
        """Evolution without opponents should still run (fitness by size)."""
        evolver = GeneticEvolver(
            population_size=5,
            generations=3,
            core_size=50,
            max_cycles=50,
            seed=42,
        )
        best = evolver.evolve()
        assert best is not None
        assert best.fitness >= 0
        assert len(best.genome) >= 1

    def test_evolver_evolve_with_opponents(self):
        parser = RedcodeParser()
        opponent = parser.parse("JMP 0", "Survivor")
        evolver = GeneticEvolver(
            population_size=4,
            generations=2,
            opponents=[opponent],
            core_size=50,
            max_cycles=50,
            rounds_per_battle=1,
            seed=42,
        )
        best = evolver.evolve()
        assert best is not None
        assert best.fitness >= 0
        assert len(evolver.history) == 2

    def test_evolver_history(self):
        evolver = GeneticEvolver(
            population_size=4,
            generations=3,
            core_size=50,
            max_cycles=20,
            seed=42,
        )
        evolver.evolve()
        assert len(evolver.history) == 3
        assert all(isinstance(s, PopulationStats) for s in evolver.history)

    def test_evolver_save_best(self, tmp_path):
        evolver = GeneticEvolver(
            population_size=4,
            generations=1,
            core_size=50,
            max_cycles=20,
            seed=42,
        )
        evolver.evolve()
        path = tmp_path / "best.red"
        evolver.save_best(str(path))
        assert path.exists()
        content = path.read_text()
        assert "ORG" in content

    def test_evolver_save_best_without_evolve(self):
        evolver = GeneticEvolver(population_size=4, generations=1)
        with pytest.raises(RuntimeError, match="No best individual"):
            evolver.save_best("/tmp/test.red")

    def test_evolver_with_seeds(self):
        parser = RedcodeParser()
        seed = parser.parse("MOV 0, 1", "Imp")
        evolver = GeneticEvolver(
            population_size=4,
            generations=2,
            core_size=50,
            max_cycles=20,
            seed=42,
        )
        best = evolver.evolve(seed_warriors=[seed])
        assert best is not None

    def test_population_stats(self):
        stats = PopulationStats(
            generation=0,
            population_size=10,
            best_fitness=30.0,
            avg_fitness=15.0,
            worst_fitness=0.0,
            best_individual="test",
            diversity=0.8,
        )
        assert stats.generation == 0
        assert stats.best_fitness == 30.0


# ============================================================================
# Enhanced Instruction Tests
# ============================================================================

class TestEnhancedInstruction:
    """Tests for enhanced Instruction class."""

    def test_is_dat_zero(self):
        instr = Instruction(Opcode.DAT, Modifier.F, AddressMode.DIRECT, 0,
                            AddressMode.DIRECT, 0)
        assert instr.is_dat_zero() == True

        instr2 = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                              AddressMode.DIRECT, 1)
        assert instr2.is_dat_zero() == False

    def test_pack(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 5,
                            AddressMode.INDIRECT_B, 10)
        packed = instr.pack()
        assert packed == (int(Opcode.MOV), int(Modifier.I),
                          int(AddressMode.DIRECT), 5,
                          int(AddressMode.INDIRECT_B), 10)
        assert len(packed) == 6

    def test_copy_independence(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 5,
                            AddressMode.DIRECT, 10)
        copy = instr.copy()
        copy.a_value = 999
        assert instr.a_value == 5  # Original unchanged


# ============================================================================
# CLI Integration Tests
# ============================================================================

class TestCLI:
    """Integration tests for the CLI."""

    def test_cli_analyze(self, tmp_path):
        """Test the analyze command via subprocess."""
        import subprocess
        import sys

        # Create a warrior file
        warrior_file = tmp_path / "test.red"
        warrior_file.write_text("MOV 0, 1\n")

        result = subprocess.run(
            [sys.executable, "-m", "core_war.cli",
             "--core-size", "100", "--max-cycles", "50",
             "analyze", str(warrior_file)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "WARRIOR ANALYSIS" in result.stdout

    def test_cli_validate(self, tmp_path):
        import subprocess
        import sys

        warrior_file = tmp_path / "test.red"
        warrior_file.write_text("MOV 0, 1\n")

        result = subprocess.run(
            [sys.executable, "-m", "core_war.cli",
             "validate", str(warrior_file)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "valid" in result.stdout

    def test_cli_config(self, tmp_path):
        import subprocess
        import sys

        config_file = tmp_path / "config.yaml"
        result = subprocess.run(
            [sys.executable, "-m", "core_war.cli",
             "config", str(config_file)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert config_file.exists()

    def test_cli_version(self):
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "core_war.cli", "--version"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "3.0.0" in result.stdout