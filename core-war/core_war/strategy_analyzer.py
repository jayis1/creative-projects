"""
Strategy analyzer for Core War warriors.

Analyzes warrior Redcode source to classify strategies, identify
vulnerabilities, and provide insights about warrior behavior.

Strategy classifications:
  - Bomber: Drops DAT bombs throughout core
  - Replicator/Paper: Copies itself to multiple locations
  - Scanner: Scans core for enemy code and attacks
  - Imp: Self-replicating forward-copier
  - Vampire: Steals enemy processes via JMP
  - One-shot: Attempts a quick kill then dies
  - Silk: Fast replicator that spreads quickly
  - Hybrid: Combines multiple strategies
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode
from core_war.parser import ParsedWarrior, RedcodeParser


class StrategyType(Enum):
    """Classification of warrior strategies."""

    BOMBER = "Bomber"
    REPLICATOR = "Replicator"
    SCANNER = "Scanner"
    IMP = "Imp"
    VAMPIRE = "Vampire"
    ONE_SHOT = "One-Shot"
    SILK = "Silk"
    STONE = "Stone"
    HYBRID = "Hybrid"
    UNKNOWN = "Unknown"

    @classmethod
    def from_str(cls, name: str) -> "StrategyType":
        """Parse a strategy type from string."""
        for st in cls:
            if st.value.lower() == name.lower():
                return st
        return cls.UNKNOWN


@dataclass
class OpcodeFrequency:
    """Frequency analysis of opcodes in a warrior."""

    counts: Dict[str, int] = field(default_factory=dict)
    total: int = 0

    def add(self, opcode: Opcode) -> None:
        """Record an opcode occurrence."""
        name = opcode.name
        self.counts[name] = self.counts.get(name, 0) + 1
        self.total += 1

    def percentage(self, opcode_name: str) -> float:
        """Get the percentage of a specific opcode."""
        if self.total == 0:
            return 0.0
        return 100.0 * self.counts.get(opcode_name, 0) / self.total

    def most_common(self, n: int = 5) -> List[Tuple[str, int]]:
        """Get the n most common opcodes."""
        return Counter(self.counts).most_common(n)


@dataclass
class Vulnerability:
    """A potential vulnerability in a warrior."""

    severity: str  # "critical", "high", "medium", "low", "info"
    description: str
    location: Optional[int] = None  # instruction index
    recommendation: str = ""


@dataclass
class AnalysisResult:
    """Complete analysis result for a warrior."""

    name: str
    strategy: StrategyType = StrategyType.UNKNOWN
    secondary_strategy: Optional[StrategyType] = None
    opcode_freq: OpcodeFrequency = field(default_factory=OpcodeFrequency)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    instruction_count: int = 0
    has_spl: bool = False
    has_jmp: bool = False
    has_scanning: bool = False
    has_bombing: bool = False
    has_replication: bool = False
    process_estimate: int = 1
    self_modifying: bool = False
    uses_indirect: bool = False
    uses_predec: bool = False
    uses_postinc: bool = False
    start_offset: int = 0
    estimated_aggressiveness: int = 0  # 0-10 scale
    estimated_resilience: int = 0  # 0-10 scale
    summary: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "strategy": self.strategy.value,
            "secondary_strategy": self.secondary_strategy.value if self.secondary_strategy else None,
            "instruction_count": self.instruction_count,
            "has_spl": self.has_spl,
            "has_jmp": self.has_jmp,
            "has_scanning": self.has_scanning,
            "has_bombing": self.has_bombing,
            "has_replication": self.has_replication,
            "process_estimate": self.process_estimate,
            "self_modifying": self.self_modifying,
            "uses_indirect": self.uses_indirect,
            "uses_predec": self.uses_predec,
            "uses_postinc": self.uses_postinc,
            "start_offset": self.start_offset,
            "estimated_aggressiveness": self.estimated_aggressiveness,
            "estimated_resilience": self.estimated_resilience,
            "opcode_frequency": dict(self.opcode_freq.counts),
            "vulnerabilities": [
                {
                    "severity": v.severity,
                    "description": v.description,
                    "location": v.location,
                    "recommendation": v.recommendation,
                }
                for v in self.vulnerabilities
            ],
            "summary": self.summary,
        }


class StrategyAnalyzer:
    """
    Analyzes warrior Redcode to classify strategy and find vulnerabilities.

    Usage::

        analyzer = StrategyAnalyzer()
        result = analyzer.analyze(warrior)
        print(f"Strategy: {result.strategy.value}")
        print(f"Aggressiveness: {result.estimated_aggressiveness}/10")
    """

    # Opcodes that indicate bombing
    BOMB_OPS = {Opcode.DAT}
    # Opcodes that indicate scanning
    SCAN_OPS = {Opcode.SEQ, Opcode.SNE, Opcode.SLT, Opcode.CMP, Opcode.JMZ, Opcode.JMN}
    # Opcodes that indicate replication
    REPLICATE_OPS = {Opcode.MOV, Opcode.SPL}

    def analyze(self, warrior: ParsedWarrior) -> AnalysisResult:
        """
        Analyze a parsed warrior and return a detailed analysis.

        Args:
            warrior: A ParsedWarrior instance.

        Returns:
            AnalysisResult with strategy classification, vulnerabilities,
            and statistics.
        """
        result = AnalysisResult(
            name=warrior.name,
            instruction_count=len(warrior.instructions),
            start_offset=warrior.start_offset,
        )

        # Analyze opcodes
        for instr in warrior.instructions:
            result.opcode_freq.add(instr.opcode)

            if instr.opcode == Opcode.SPL:
                result.has_spl = True
            if instr.opcode in (Opcode.JMP, Opcode.JMZ, Opcode.JMN, Opcode.DJN):
                result.has_jmp = True
            if instr.opcode in self.SCAN_OPS:
                result.has_scanning = True
            if instr.opcode == Opcode.DAT and instr is not warrior.instructions[warrior.start_offset]:
                # DAT instructions that aren't the entry point could be bombs
                pass

            # Check addressing modes
            if instr.a_mode in (AddressMode.INDIRECT_B, AddressMode.INDIRECT_A):
                result.uses_indirect = True
            if instr.a_mode in (AddressMode.PREDEC_B, AddressMode.PREDEC_A):
                result.uses_predec = True
            if instr.a_mode in (AddressMode.POSTINC_B, AddressMode.POSTINC_A):
                result.uses_postinc = True
            if instr.b_mode in (AddressMode.INDIRECT_B, AddressMode.INDIRECT_A):
                result.uses_indirect = True
            if instr.b_mode in (AddressMode.PREDEC_B, AddressMode.PREDEC_A):
                result.uses_predec = True
            if instr.b_mode in (AddressMode.POSTINC_B, AddressMode.POSTINC_A):
                result.uses_postinc = True

        # Detect self-modification (instruction references itself or nearby)
        result.self_modifying = self._detect_self_modification(warrior)

        # Detect bombing (MOV that copies DAT instructions)
        result.has_bombing = self._detect_bombing(warrior)

        # Detect replication (SPL + MOV patterns)
        result.has_replication = self._detect_replication(warrior)

        # Estimate process count
        result.process_estimate = self._estimate_processes(warrior)

        # Classify strategy
        result.strategy, result.secondary_strategy = self._classify_strategy(warrior, result)

        # Find vulnerabilities
        result.vulnerabilities = self._find_vulnerabilities(warrior, result)

        # Estimate aggressiveness and resilience
        result.estimated_aggressiveness = self._estimate_aggressiveness(warrior, result)
        result.estimated_resilience = self._estimate_resilience(warrior, result)

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def analyze_source(self, source: str, name: str = "Unknown") -> AnalysisResult:
        """Parse and analyze warrior source from a string."""
        parser = RedcodeParser()
        warrior = parser.parse(source, name)
        return self.analyze(warrior)

    def _detect_self_modification(self, warrior: ParsedWarrior) -> bool:
        """Detect if the warrior modifies its own code."""
        for i, instr in enumerate(warrior.instructions):
            if instr.opcode in (Opcode.MOV, Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD):
                # Check if B-operand references near the warrior itself
                # In Redcode, operands are relative to the current instruction
                b_target = i + instr.b_value
                if 0 <= b_target < len(warrior.instructions):
                    return True
        return False

    def _detect_bombing(self, warrior: ParsedWarrior) -> bool:
        """Detect if the warrior drops DAT bombs."""
        has_dat = any(instr.opcode == Opcode.DAT for instr in warrior.instructions)
        has_mov = any(instr.opcode == Opcode.MOV for instr in warrior.instructions)
        return has_dat and has_mov

    def _detect_replication(self, warrior: ParsedWarrior) -> bool:
        """Detect if the warrior replicates itself."""
        spl_count = sum(1 for instr in warrior.instructions if instr.opcode == Opcode.SPL)
        mov_count = sum(1 for instr in warrior.instructions if instr.opcode == Opcode.MOV)
        return spl_count > 0 and mov_count >= 1

    def _estimate_processes(self, warrior: ParsedWarrior) -> int:
        """Estimate the maximum number of processes the warrior might create."""
        spl_count = sum(1 for instr in warrior.instructions if instr.opcode == Opcode.SPL)
        if spl_count == 0:
            return 1
        # Each SPL can potentially double processes
        # Rough estimate: 2^spl_count, capped at 1000
        return min(2 ** spl_count, 1000)

    def _classify_strategy(
        self, warrior: ParsedWarrior, result: AnalysisResult
    ) -> Tuple[StrategyType, Optional[StrategyType]]:
        """Classify the warrior's primary and secondary strategies."""
        strategies: List[Tuple[StrategyType, int]] = []

        # Check for Imp (simple MOV 0, 1 pattern)
        if self._is_imp(warrior):
            strategies.append((StrategyType.IMP, 100))

        # Check for Bomber
        if result.has_bombing and not result.has_replication:
            score = 50
            if result.uses_indirect:
                score += 20
            strategies.append((StrategyType.BOMBER, score))

        # Check for Stone (compact bomber, typically 3-5 instructions)
        if result.has_bombing and len(warrior.instructions) <= 5:
            strategies.append((StrategyType.STONE, 60))

        # Check for Scanner
        if result.has_scanning:
            score = 60
            if result.has_bombing:
                score += 20
            strategies.append((StrategyType.SCANNER, score))

        # Check for Replicator/Paper
        if result.has_replication:
            score = 55
            spl_count = sum(1 for instr in warrior.instructions if instr.opcode == Opcode.SPL)
            if spl_count >= 2:
                score += 20
            strategies.append((StrategyType.REPLICATOR, score))

        # Check for Silk (fast replicator with SPL + MOV in tight loop)
        if result.has_replication and len(warrior.instructions) <= 4:
            strategies.append((StrategyType.SILK, 65))

        # Check for One-Shot (short warrior with no loop)
        if len(warrior.instructions) <= 4 and not result.has_spl:
            has_loop = any(
                instr.opcode in (Opcode.JMP, Opcode.JMZ, Opcode.JMN, Opcode.DJN)
                and instr.a_value <= 0
                for instr in warrior.instructions
            )
            if not has_loop:
                strategies.append((StrategyType.ONE_SHOT, 40))

        # Check for Vampire (uses JMP to redirect enemy processes)
        jmp_count = sum(1 for instr in warrior.instructions if instr.opcode == Opcode.JMP)
        if jmp_count >= 2 and result.uses_indirect:
            strategies.append((StrategyType.VAMPIRE, 45))

        if not strategies:
            return StrategyType.UNKNOWN, None

        # Sort by score, pick primary and secondary
        strategies.sort(key=lambda x: -x[1])
        primary = strategies[0][0]
        secondary = strategies[1][0] if len(strategies) > 1 else None

        # If primary is STONE and secondary is BOMBER, they're the same family
        if primary == StrategyType.STONE and secondary == StrategyType.BOMBER:
            secondary = None

        return primary, secondary

    def _is_imp(self, warrior: ParsedWarrior) -> bool:
        """Check if the warrior is an imp (MOV 0, 1 pattern)."""
        for instr in warrior.instructions:
            if (
                instr.opcode == Opcode.MOV
                and instr.a_value == 0
                and instr.b_value == 1
                and instr.a_mode == AddressMode.DIRECT
                and instr.b_mode == AddressMode.DIRECT
            ):
                return True
        return False

    def _find_vulnerabilities(
        self, warrior: ParsedWarrior, result: AnalysisResult
    ) -> List[Vulnerability]:
        """Identify potential vulnerabilities in the warrior."""
        vulns: List[Vulnerability] = []

        # Check for no DAT protection (no way to kill enemies)
        if not result.has_bombing and not result.has_scanning:
            vulns.append(Vulnerability(
                severity="medium",
                description="Warrior has no offensive capability (no bombing or scanning)",
                recommendation="Add DAT bombing or scanning to attack enemies",
            ))

        # Check for single process (no SPL)
        if not result.has_spl:
            vulns.append(Vulnerability(
                severity="low",
                description="Single-process warrior — vulnerable to single DAT hit",
                recommendation="Add SPL to create multiple processes for redundancy",
            ))

        # Check for very short warriors
        if len(warrior.instructions) < 3:
            vulns.append(Vulnerability(
                severity="low",
                description="Very short warrior — may be easily identified and countered",
                recommendation="Consider adding decoy instructions or self-repair code",
            ))

        # Check for self-modifying code without protection
        if result.self_modifying and not result.has_spl:
            vulns.append(Vulnerability(
                severity="medium",
                description="Self-modifying code without process redundancy — "
                           "if the code is corrupted, the warrior dies",
                recommendation="Add SPL to create backup processes",
            ))

        # Check for large warriors (easy to scan)
        if len(warrior.instructions) > 20:
            vulns.append(Vulnerability(
                severity="low",
                description="Large warrior footprint — easier for scanners to detect",
                recommendation="Minimize instruction count to reduce scan visibility",
            ))

        # Check for no entry point offset
        if warrior.start_offset == 0 and len(warrior.instructions) > 1:
            vulns.append(Vulnerability(
                severity="info",
                description="Entry point at first instruction — predictable start location",
                recommendation="Use ORG to offset the entry point",
            ))

        # Check for unconditional JMP loops (can be trapped)
        for i, instr in enumerate(warrior.instructions):
            if instr.opcode == Opcode.JMP and instr.a_value == 0:
                # JMP 0 = infinite loop, fine for survival but not offensive
                if not result.has_bombing and not result.has_scanning:
                    vulns.append(Vulnerability(
                        severity="medium",
                        description=f"Instruction {i}: JMP 0 infinite loop with no offense",
                        location=i,
                        recommendation="Add offensive capability or the warrior will only draw",
                    ))
                break

        return vulns

    def _estimate_aggressiveness(self, warrior: ParsedWarrior, result: AnalysisResult) -> int:
        """Estimate aggressiveness on a 0-10 scale."""
        score = 0

        if result.has_bombing:
            score += 3
        if result.has_scanning:
            score += 3
        if result.uses_indirect:
            score += 1  # Indirect addressing allows more sophisticated attacks
        if result.uses_postinc or result.uses_predec:
            score += 1  # Auto-increment allows sweeping attacks

        # Count offensive opcodes
        offensive_count = sum(
            1 for instr in warrior.instructions
            if instr.opcode in (Opcode.MOV, Opcode.DAT)
        )
        score += min(offensive_count, 3)

        if result.strategy == StrategyType.ONE_SHOT:
            score += 2  # One-shots are aggressive by nature

        return min(score, 10)

    def _estimate_resilience(self, warrior: ParsedWarrior, result: AnalysisResult) -> int:
        """Estimate resilience on a 0-10 scale."""
        score = 0

        if result.has_spl:
            score += 3
        if result.has_replication:
            score += 3
        if result.process_estimate > 4:
            score += 2
        if result.self_modifying:
            score += 1  # Self-repair capability

        # Short warriors are harder to hit
        if len(warrior.instructions) <= 5:
            score += 2
        elif len(warrior.instructions) <= 10:
            score += 1

        # Imps are very resilient
        if result.strategy == StrategyType.IMP:
            score += 2

        return min(score, 10)

    def _generate_summary(self, result: AnalysisResult) -> str:
        """Generate a human-readable summary of the analysis."""
        parts = [f"{result.name}: {result.strategy.value}"]

        if result.secondary_strategy:
            parts.append(f"with {result.secondary_strategy.value} elements")

        parts.append(f"({result.instruction_count} instructions)")
        parts.append(f"aggression={result.estimated_aggressiveness}/10")
        parts.append(f"resilience={result.estimated_resilience}/10")

        if result.vulnerabilities:
            critical = sum(1 for v in result.vulnerabilities if v.severity == "critical")
            high = sum(1 for v in result.vulnerabilities if v.severity == "high")
            medium = sum(1 for v in result.vulnerabilities if v.severity == "medium")
            if critical or high or medium:
                parts.append(f"({len(result.vulnerabilities)} vulnerabilities)")

        return " ".join(parts)

    def compare(self, warrior1: ParsedWarrior, warrior2: ParsedWarrior) -> dict:
        """
        Compare two warriors and return a comparison analysis.

        Returns:
            Dictionary with comparison metrics.
        """
        r1 = self.analyze(warrior1)
        r2 = self.analyze(warrior2)

        return {
            "warrior1": r1.to_dict(),
            "warrior2": r2.to_dict(),
            "aggressiveness_diff": r1.estimated_aggressiveness - r2.estimated_aggressiveness,
            "resilience_diff": r1.estimated_resilience - r2.estimated_resilience,
            "process_advantage": (
                warrior1.name if r1.process_estimate > r2.process_estimate
                else warrior2.name if r2.process_estimate > r1.process_estimate
                else "tie"
            ),
            "size_advantage": (
                warrior1.name if r1.instruction_count < r2.instruction_count
                else warrior2.name if r2.instruction_count < r1.instruction_count
                else "tie"
            ),
            "predicted_winner": self._predict_winner(r1, r2),
        }

    def _predict_winner(self, r1: AnalysisResult, r2: AnalysisResult) -> str:
        """Predict the likely winner based on analysis (heuristic)."""
        score1 = r1.estimated_aggressiveness + r1.estimated_resilience
        score2 = r2.estimated_aggressiveness + r2.estimated_resilience

        if abs(score1 - score2) <= 2:
            return "too close to call"
        return r1.name if score1 > score2 else r2.name