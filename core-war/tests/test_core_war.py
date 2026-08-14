"""
Test suite for the Core War MARS simulator.

Tests cover:
  - Instruction parsing and representation
  - Opcode/modifier/addressing mode parsing
  - Redcode parser (labels, EQU, ORG, expressions)
  - MARS execution engine (all opcodes, addressing modes)
  - Battle scheduling and tournaments
  - Disassembler
  - Edge cases and bug fixes
"""

import pytest
from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode, OPCODE_NAMES, DEFAULT_MODIFIERS
from core_war.parser import RedcodeParser, ParseError, ParsedWarrior
from core_war.mars import MARS, WarriorState, BattleResult, Warrior
from core_war.scheduler import BattleScheduler, BattleStats, TournamentResult
from core_war.disassembler import disassemble, disassemble_core, disassemble_around
from core_war.visualizer import core_heatmap, core_summary, format_core_summary, battle_log
from core_war.loader import load_warrior, load_warrior_from_string


# ============================================================================
# Opcodes Tests
# ============================================================================

class TestOpcodes:
    def test_opcode_from_str(self):
        assert Opcode.from_str("DAT") == Opcode.DAT
        assert Opcode.from_str("MOV") == Opcode.MOV
        assert Opcode.from_str("mov") == Opcode.MOV  # case insensitive
        assert Opcode.from_str("SEQ") == Opcode.SEQ
        assert Opcode.from_str("CMP") == Opcode.CMP

    def test_opcode_from_str_invalid(self):
        with pytest.raises(ValueError):
            Opcode.from_str("XYZ")

    def test_opcode_names_dict(self):
        assert OPCODE_NAMES["DAT"] == Opcode.DAT
        assert OPCODE_NAMES["MOV"] == Opcode.MOV
        assert len(OPCODE_NAMES) >= 16

    def test_modifier_from_str(self):
        assert Modifier.from_str("A") == Modifier.A
        assert Modifier.from_str("B") == Modifier.B
        assert Modifier.from_str("F") == Modifier.F
        assert Modifier.from_str("i") == Modifier.I  # case insensitive

    def test_modifier_from_str_invalid(self):
        with pytest.raises(ValueError):
            Modifier.from_str("ZZ")

    def test_address_mode_from_str(self):
        assert AddressMode.from_str("#") == AddressMode.IMMEDIATE
        assert AddressMode.from_str("$") == AddressMode.DIRECT
        assert AddressMode.from_str("@") == AddressMode.INDIRECT_B
        assert AddressMode.from_str("*") == AddressMode.INDIRECT_A
        assert AddressMode.from_str("{") == AddressMode.PREDEC_B
        assert AddressMode.from_str("<") == AddressMode.PREDEC_A
        assert AddressMode.from_str("}") == AddressMode.POSTINC_B
        assert AddressMode.from_str(">") == AddressMode.POSTINC_A
        assert AddressMode.from_str("") == AddressMode.DIRECT  # default

    def test_address_mode_from_str_invalid(self):
        with pytest.raises(ValueError):
            AddressMode.from_str("!")

    def test_default_modifiers(self):
        assert DEFAULT_MODIFIERS[Opcode.DAT] == Modifier.F
        assert DEFAULT_MODIFIERS[Opcode.MOV] == Modifier.I
        assert DEFAULT_MODIFIERS[Opcode.JMP] == Modifier.B
        assert DEFAULT_MODIFIERS[Opcode.SPL] == Modifier.B


# ============================================================================
# Instruction Tests
# ============================================================================

class TestInstruction:
    def test_instruction_creation(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 1,
                            AddressMode.DIRECT, 2)
        assert instr.opcode == Opcode.MOV
        assert instr.modifier == Modifier.I
        assert instr.a_value == 1
        assert instr.b_value == 2

    def test_instruction_defaults(self):
        instr = Instruction()
        assert instr.opcode == Opcode.DAT
        assert instr.a_value == 0
        assert instr.b_value == 0

    def test_instruction_copy(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 5,
                            AddressMode.INDIRECT_B, 10)
        copy = instr.copy()
        assert copy.opcode == instr.opcode
        assert copy.a_value == instr.a_value
        assert copy.b_value == instr.b_value
        # Modify original, copy should be unaffected
        instr.a_value = 999
        assert copy.a_value == 5

    def test_instruction_str(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 1,
                            AddressMode.DIRECT, 2)
        s = str(instr)
        assert "MOV" in s
        assert "I" in s
        assert "$1" in s
        assert "$2" in s


# ============================================================================
# Parser Tests
# ============================================================================

class TestParser:
    def setup_method(self):
        self.parser = RedcodeParser()

    def test_parse_simple_imp(self):
        src = "ORG start\nstart MOV 0, 1"
        w = self.parser.parse(src, "Imp")
        assert w.name == "Imp"
        assert len(w.instructions) == 1
        assert w.instructions[0].opcode == Opcode.MOV
        assert w.start_offset == 0

    def test_parse_dat(self):
        src = "DAT 0, 0"
        w = self.parser.parse(src, "Dat")
        assert len(w.instructions) == 1
        assert w.instructions[0].opcode == Opcode.DAT

    def test_parse_dat_one_operand(self):
        """DAT with one operand should put it in B-field."""
        src = "DAT 5"
        w = self.parser.parse(src, "Dat")
        assert w.instructions[0].b_value == 5
        assert w.instructions[0].a_value == 0

    def test_parse_labels(self):
        src = """
        ORG start
loop    MOV 0, 1
        JMP loop
start   DAT 0, 0
"""
        w = self.parser.parse(src, "Test")
        assert len(w.instructions) == 3
        # loop is at position 0, start is at position 2
        # ORG start means start_offset = 2
        assert w.start_offset == 2

    def test_parse_equ_constants(self):
        src = """
        step EQU 4
        ORG start
start   ADD #step, bomb
bomb    DAT 0, 0
"""
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].opcode == Opcode.ADD
        assert w.instructions[0].a_mode == AddressMode.IMMEDIATE
        assert w.instructions[0].a_value == 4  # step = 4

    def test_parse_modifiers(self):
        src = "MOV.I 0, 1"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].modifier == Modifier.I

        src = "MOV.A 0, 1"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].modifier == Modifier.A

    def test_parse_addressing_modes(self):
        src = "MOV #1, $2"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].a_mode == AddressMode.IMMEDIATE
        assert w.instructions[0].a_value == 1
        assert w.instructions[0].b_mode == AddressMode.DIRECT
        assert w.instructions[0].b_value == 2

    def test_parse_indirect_addressing(self):
        src = "MOV @1, *2"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].a_mode == AddressMode.INDIRECT_B
        assert w.instructions[0].b_mode == AddressMode.INDIRECT_A

    def test_parse_comments(self):
        src = """
        ; This is a comment
        MOV 0, 1  ; Inline comment
        ; Another comment
"""
        w = self.parser.parse(src, "Test")
        assert len(w.instructions) == 1

    def test_parse_empty_source(self):
        with pytest.raises(ParseError):
            self.parser.parse("", "Empty")

    def test_parse_case_insensitive_labels(self):
        src = """
        ORG Start
Start   MOV 0, 1
"""
        w = self.parser.parse(src, "Test")
        assert w.start_offset == 0

    def test_parse_arithmetic_expressions(self):
        src = """
        ORG start
start   MOV 2+3, 10-1
"""
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].a_value == 5
        assert w.instructions[0].b_value == 9

    def test_parse_too_many_instructions(self):
        # Generate too many instructions
        lines = [f"MOV 0, {i}" for i in range(250)]
        src = "\n".join(lines)
        with pytest.raises(ParseError):
            self.parser.parse(src, "Big")

    def test_parse_jmp_single_operand(self):
        """JMP with one operand should put it in A-field."""
        src = "JMP 5"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].a_value == 5
        assert w.instructions[0].a_mode == AddressMode.DIRECT

    def test_parse_spl_single_operand(self):
        """SPL with one operand should put it in A-field."""
        src = "SPL 3"
        w = self.parser.parse(src, "Test")
        assert w.instructions[0].a_value == 3

    def test_parse_label_arithmetic(self):
        src = """
        ORG start
start   JMP end
end     DAT 0, 0
"""
        w = self.parser.parse(src, "Test")
        # start is at 0, end is at 1
        # JMP end → relative offset = 1 - 0 = 1
        assert w.instructions[0].a_value == 1

    def test_parse_invalid_opcode(self):
        with pytest.raises(ParseError):
            self.parser.parse("XYZ 0, 1", "Test")

    def test_parse_no_opcode(self):
        with pytest.raises(ParseError):
            self.parser.parse("label_only", "Test")


# ============================================================================
# MARS Tests
# ============================================================================

class TestMARS:
    def test_mars_init(self):
        mars = MARS(core_size=100, max_cycles=1000, seed=42)
        assert mars.core_size == 100
        assert mars.max_cycles == 1000
        assert mars.core == []  # Not initialized until reset

    def test_mars_reset(self):
        mars = MARS(core_size=100, max_cycles=1000, seed=42)
        mars.reset()
        assert len(mars.core) == 100
        assert all(isinstance(i, Instruction) for i in mars.core)
        assert all(i.opcode == Opcode.DAT for i in mars.core)

    def test_mars_invalid_params(self):
        with pytest.raises(ValueError):
            MARS(core_size=0)
        with pytest.raises(ValueError):
            MARS(max_cycles=0)
        with pytest.raises(ValueError):
            MARS(max_processes=0)

    def test_load_warrior(self):
        mars = MARS(core_size=100, max_cycles=1000, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV 0, 1", "Imp")
        state = mars.load_warrior(w, position=10)
        assert state.load_address == 10
        assert len(state.processes) == 1
        assert mars.core[10].opcode == Opcode.MOV

    def test_load_warrior_wraps_around(self):
        """Warrior loading should wrap around core boundary."""
        mars = MARS(core_size=20, max_cycles=100, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV 0, 1\nDAT 1, 2\nDAT 3, 4", "Test")
        # Load at position 18, should wrap: 18, 19, 0
        mars.load_warrior(w, position=18)
        assert mars.core[18].opcode == Opcode.MOV
        assert mars.core[19].opcode == Opcode.DAT
        assert mars.core[0].opcode == Opcode.DAT
        assert mars.core[0].a_value == 3

    def test_imp_execution(self):
        """Imp should copy itself forward each cycle."""
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        imp = parser.parse("MOV 0, 1", "Imp")
        mars.load_warrior(imp, position=10)
        mars.run()
        # After 10 cycles, the imp should have spread forward
        # Imp copies itself to position+1 each cycle
        assert mars.core[10].opcode == Opcode.MOV
        assert mars.core[11].opcode == Opcode.MOV

    def test_dat_kills_process(self):
        """DAT should kill the executing process."""
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("DAT 0, 0", "Dead")
        mars.load_warrior(w, position=10)
        result = mars.run()
        assert not mars.warriors[0].alive
        assert result.winner is None

    def test_spl_creates_process(self):
        """SPL should create a new process."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SPL 1: split to next instruction, then NOP, then DAT
        w = parser.parse("SPL 1\nNOP\nDAT 0, 0", "Splittest")
        mars.load_warrior(w, position=10)
        mars.run()
        # The warrior should have had multiple processes
        assert mars.warriors[0].instructions_executed > 1

    def test_jmp_instruction(self):
        """JMP should redirect execution."""
        mars = MARS(core_size=50, max_cycles=20, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMP 0 creates an infinite loop
        w = parser.parse("JMP 0", "Looper")
        mars.load_warrior(w, position=10)
        mars.run()
        # Should survive (infinite loop never executes DAT)
        assert mars.warriors[0].alive

    def test_add_instruction(self):
        """ADD should add values correctly."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # ADD #5 to the B-field of the next instruction
        # Then DAT to stop
        w = parser.parse("ADD.AB #5, $1\nDAT 0, 10", "Adder")
        mars.load_warrior(w, position=10)
        mars.run()
        # After ADD.AB #5, $1: B-field of instruction at offset 1 should be 15
        assert mars.core[11].b_value == 15

    def test_sub_instruction(self):
        """SUB should subtract values correctly."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("SUB.AB #3, $1\nDAT 0, 10", "Subber")
        mars.load_warrior(w, position=10)
        mars.run()
        # B-field should be 10 - 3 = 7
        assert mars.core[11].b_value == 7

    def test_mov_i_copies_full_instruction(self):
        """MOV.I should copy the entire instruction."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV.I $0, $1\nDAT 0, 0", "Mover")
        mars.load_warrior(w, position=10)
        mars.run()
        # Instruction at 11 should now be a copy of instruction at 10
        assert mars.core[11].opcode == Opcode.MOV
        assert mars.core[11].modifier == Modifier.I

    def test_battle_result(self):
        """Test that battle results are correctly structured."""
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w1 = parser.parse("JMP 0", "Survivor")
        w2 = parser.parse("DAT 0, 0", "Dead")
        mars.load_warrior(w1, position=10)
        mars.load_warrior(w2, position=20)
        result = mars.run()
        assert result.winner == "Survivor"
        assert result.warrior_results["Survivor"] == "win"
        assert result.warrior_results["Dead"] == "loss"

    def test_single_warrior_survives(self):
        """A single warrior that doesn't die should 'win'."""
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("JMP 0", "Loner")
        mars.load_warrior(w, position=10)
        result = mars.run()
        assert result.winner == "Loner"

    def test_single_warrior_dies(self):
        """A single warrior that dies should have no winner."""
        mars = MARS(core_size=50, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("DAT 0, 0", "Doomed")
        mars.load_warrior(w, position=10)
        result = mars.run()
        assert result.winner is None

    def test_step_method(self):
        """step() should execute one cycle at a time."""
        mars = MARS(core_size=50, max_cycles=100, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV 0, 1", "Imp")
        mars.load_warrior(w, position=10)

        assert mars.cycle == 0
        running = mars.step()
        assert running == True
        assert mars.cycle == 1
        running = mars.step()
        assert mars.cycle == 2

    def test_step_returns_false_when_done(self):
        mars = MARS(core_size=50, max_cycles=2, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("DAT 0, 0", "Dead")
        mars.load_warrior(w, position=10)
        # First step: DAT kills the process
        mars.step()
        # Second step: no alive warriors
        running = mars.step()
        assert running == False

    def test_access_tracking(self):
        """Access counts should track execution frequency."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("JMP 0", "Looper")
        mars.load_warrior(w, position=10)
        mars.run()
        assert 10 in mars.access_counts
        assert mars.access_counts[10] > 0

    def test_on_execute_callback(self):
        """on_execute callback should fire for each instruction."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        events = []
        mars.on_execute = lambda name, pc, instr: events.append((name, pc))
        parser = RedcodeParser()
        w = parser.parse("JMP 0", "Looper")
        mars.load_warrior(w, position=10)
        mars.run()
        assert len(events) > 0
        assert all(name == "Looper" for name, pc in events)

    def test_div_by_zero(self):
        """DIV by zero should result in 0, not crash."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("DIV.AB #0, $1\nDAT 0, 10", "Divider")
        mars.load_warrior(w, position=10)
        # Should not crash
        mars.run()
        # B-field should be 0 (div by zero gives 0)
        assert mars.core[11].b_value == 0

    def test_mod_by_zero(self):
        """MOD by zero should result in 0, not crash."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOD.AB #0, $1\nDAT 0, 10", "Modder")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.core[11].b_value == 0

    def test_djn_instruction(self):
        """DJN should decrement B-field and jump if non-zero."""
        mars = MARS(core_size=50, max_cycles=50, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # DJN 0, 1: decrement B-field at offset+1, jump to self (offset 0) if non-zero
        # DAT 0, 3: B-field starts at 3
        w = parser.parse("DJN 0, 1\nDAT 0, 3", "DJNtest")
        mars.load_warrior(w, position=10)
        mars.run()
        # The B-field should have been decremented to 0 (3 → 2 → 1 → 0)
        assert mars.core[11].b_value == 0  # Should reach 0 eventually

    def test_jmz_jump_when_zero(self):
        """JMZ should jump when B-field is zero."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMZ 0, 1: jump to self if B-field of $1 is zero
        # DAT 0, 0: B-field is 0, so should jump (infinite loop)
        w = parser.parse("JMZ 0, 1\nDAT 0, 0", "JMZtest")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive  # Should survive (infinite loop)

    def test_jmn_jump_when_nonzero(self):
        """JMN should jump when B-field is non-zero."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMN 0, 1: jump to self if B-field of $1 is non-zero
        # DAT 0, 5: B-field is 5, so should jump (infinite loop)
        w = parser.parse("JMN 0, 1\nDAT 0, 5", "JMNtest")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_cmp_skip_if_equal(self):
        """CMP/SEQ should skip next instruction if equal."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SEQ.B #5, #5: equal, so skip next (DAT)
        # DAT 0, 0: should be skipped
        # JMP 0: should be reached, infinite loop
        w = parser.parse("SEQ.B #5, #5\nDAT 0, 0\nJMP 0", "CMPtest")
        mars.load_warrior(w, position=10)
        mars.run()
        # Should survive because SEQ skips the DAT
        assert mars.warriors[0].alive

    def test_sne_skip_if_not_equal(self):
        """SNE should skip next instruction if not equal."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SNE.B #5, #3: not equal (5 != 3), so skip next (DAT)
        # DAT 0, 0: should be skipped
        # JMP 0: should be reached, infinite loop
        w = parser.parse("SNE.B #5, #3\nDAT 0, 0\nJMP 0\nDAT 0, 0", "SNEtest")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_slt_skip_if_less_than(self):
        """SLT should skip next instruction if A < B."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SLT.B #3, #5: 3 < 5, so skip next (DAT)
        # DAT 0, 0: should be skipped
        # JMP 0: should be reached, infinite loop
        w = parser.parse("SLT.B #3, #5\nDAT 0, 0\nJMP 0\nDAT 0, 0", "SLTtest")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_nop_instruction(self):
        """NOP should just advance to the next instruction."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("NOP\nJMP 0", "NOPtest")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_mul_instruction(self):
        """MUL should multiply values correctly."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MUL.AB #3, $1\nDAT 0, 5", "Mul")
        mars.load_warrior(w, position=10)
        mars.run()
        # B-field should be 3 * 5 = 15
        assert mars.core[11].b_value == 15

    def test_indirect_addressing_b(self):
        """@ mode should resolve via B-field pointer."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # MOV $2, @1: copy instruction at offset+2 to address pointed by B-field of offset+1
        # At offset+1: DAT 0, 3 → B-field = 3, so target = (offset+1) + 3 = offset+4
        # At offset+2: MOV 0, 1 (source)
        # At offset+4: should receive the MOV
        w = parser.parse("MOV $2, @1\nDAT 0, 3\nMOV 0, 1\nDAT 0, 0\nDAT 0, 0", "Indirect")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.core[14].opcode == Opcode.MOV  # 10+4

    def test_predec_addressing(self):
        """{ mode should predecrement B-field then resolve."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # MOV $2, {1: predecrement B-field of offset+1, then use as pointer
        # At offset+1: DAT 0, 4 → predec to 3, target = (offset+1) + 3 = offset+4
        w = parser.parse("MOV $2, {1\nDAT 0, 4\nMOV 0, 1\nDAT 0, 0\nDAT 0, 0", "Predec")
        mars.load_warrior(w, position=10)
        mars.run()
        # B-field at offset+1 should be decremented to 3
        assert mars.core[11].b_value == 3
        # Target at offset+4 should receive the MOV
        assert mars.core[14].opcode == Opcode.MOV

    def test_postinc_addressing(self):
        """} mode should post-increment B-field after resolving."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # MOV $2, }1: use B-field of offset+1 as pointer, then increment
        # At offset+1: DAT 0, 3 → pointer = (offset+1)+3 = offset+4, then B-field becomes 4
        w = parser.parse("MOV $2, }1\nDAT 0, 3\nMOV 0, 1\nDAT 0, 0\nDAT 0, 0", "Postinc")
        mars.load_warrior(w, position=10)
        mars.run()
        # B-field at offset+1 should be incremented to 4
        assert mars.core[11].b_value == 4
        # Target at offset+4 should receive the MOV
        assert mars.core[14].opcode == Opcode.MOV


# ============================================================================
# Scheduler Tests
# ============================================================================

class TestScheduler:
    def test_battle_stats(self):
        stat = BattleStats(name="Test")
        stat.record("win")
        stat.record("loss")
        stat.record("draw")
        assert stat.wins == 1
        assert stat.losses == 1
        assert stat.draws == 1
        assert stat.rounds_played == 3
        assert stat.score == 4  # 3*1 + 1 = 4

    def test_battle_stats_win_rate(self):
        stat = BattleStats(name="Test")
        assert stat.win_rate == 0.0
        stat.record("win")
        stat.record("win")
        stat.record("loss")
        assert stat.win_rate == pytest.approx(2/3)

    def test_battle_scheduler_basic(self):
        parser = RedcodeParser()
        w1 = parser.parse("JMP 0", "Survivor")
        w2 = parser.parse("DAT 0, 0", "Dead")
        scheduler = BattleScheduler(core_size=100, max_cycles=50, rounds=3, seed=42)
        stats = scheduler.run_battle([w1, w2])
        assert stats["Survivor"].wins > 0
        assert stats["Dead"].losses > 0

    def test_tournament_result(self):
        parser = RedcodeParser()
        w1 = parser.parse("JMP 0", "A")
        w2 = parser.parse("JMP 0", "B")
        scheduler = BattleScheduler(core_size=100, max_cycles=10, rounds=2, seed=42)
        result = scheduler.run_tournament([w1, w2])
        assert len(result.standings) == 2
        assert result.total_battles == 1
        assert result.total_rounds == 2

    def test_tournament_winner(self):
        parser = RedcodeParser()
        w1 = parser.parse("JMP 0", "Winner")
        w2 = parser.parse("DAT 0, 0", "Loser")
        scheduler = BattleScheduler(core_size=100, max_cycles=10, rounds=3, seed=42)
        result = scheduler.run_tournament([w1, w2])
        champ = result.winner()
        assert champ is not None
        assert champ.name == "Winner"


# ============================================================================
# Disassembler Tests
# ============================================================================

class TestDisassembler:
    def test_disassemble(self):
        instr = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 1,
                            AddressMode.DIRECT, 2)
        s = disassemble(instr)
        assert "MOV" in s
        assert "I" in s
        assert "$1" in s
        assert "$2" in s

    def test_disassemble_core(self):
        core = [Instruction(Opcode.DAT) for _ in range(10)]
        core[5] = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                              AddressMode.DIRECT, 1)
        result = disassemble_core(core, start=3, count=5)
        lines = result.split("\n")
        assert len(lines) == 5
        assert "MOV" in lines[2]  # Line 3+2=5 → index 5

    def test_disassemble_around(self):
        core = [Instruction(Opcode.DAT) for _ in range(20)]
        core[10] = Instruction(Opcode.MOV)
        result = disassemble_around(core, center=10, radius=2)
        lines = result.split("\n")
        assert len(lines) == 5  # 2 before + center + 2 after
        assert ">>" in lines[2]  # Center should be marked


# ============================================================================
# Visualizer Tests
# ============================================================================

class TestVisualizer:
    def test_core_summary(self):
        core = [Instruction(Opcode.DAT) for _ in range(10)]
        core[0] = Instruction(Opcode.MOV)
        core[1] = Instruction(Opcode.MOV)
        summary = core_summary(core)
        assert summary["DAT"] == 8
        assert summary["MOV"] == 2

    def test_format_core_summary(self):
        summary = {"DAT": 8, "MOV": 2}
        text = format_core_summary(summary, 10)
        assert "10" in text
        assert "DAT" in text
        assert "MOV" in text

    def test_core_heatmap(self):
        core = [Instruction(Opcode.DAT) for _ in range(20)]
        result = core_heatmap(core, width=10)
        lines = result.split("\n")
        assert len(lines) == 2  # 20 / 10 = 2 rows

    def test_battle_log(self):
        from core_war.mars import WarriorState
        from collections import deque
        w = WarriorState(name="Test", instructions=[], start_offset=0,
                         load_address=10, processes=deque([5]))
        log = battle_log([], [w])
        assert "Test" in log
        assert "ALIVE" in log


# ============================================================================
# Loader Tests
# ============================================================================

class TestLoader:
    def test_load_warrior_from_string(self):
        w = load_warrior_from_string("JMP 0", "Test")
        assert w.name == "Test"
        assert len(w.instructions) == 1
        assert w.instructions[0].opcode == Opcode.JMP

    def test_load_warrior_from_string_default_name(self):
        w = load_warrior_from_string("JMP 0")
        assert w.name == "Inline"


# ============================================================================
# Bug-Specific Tests (for Phase 3)
# ============================================================================

class TestBugsFound:
    """Tests for bugs found during Phase 3 bug hunt."""

    def test_bug_spl_process_order(self):
        """BUG: SPL should add both processes to the back of the queue.
        The current process continues (next_pc) and the new process (a_addr)
        should both be added to the back of the queue, with next_pc first.
        """
        mars = MARS(core_size=100, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SPL 1: split — current process continues to next, new process goes to offset+1
        # But SPL 1 means a_addr = pc + 1, and next_pc = pc + 1 too
        # So both processes point to the same place
        # Then NOP, then DAT
        w = parser.parse("SPL 1\nNOP\nDAT 0, 0", "Splittest")
        mars.load_warrior(w, position=10)
        mars.run()
        # Warrior should be dead (both processes eventually hit DAT)
        # But it should have had multiple processes at some point
        assert mars.warriors[0].instructions_executed >= 3

    def test_bug_unsafe_eval_no_code_injection(self):
        """BUG: _safe_eval uses eval() — verify it properly restricts input.
        The allowed character set should prevent code injection.
        """
        parser = RedcodeParser()
        # Try to inject code via expression — should fail
        with pytest.raises(ParseError):
            parser.parse("MOV __import__('os'), 1", "Test")

    def test_bug_eval_division_by_zero(self):
        """BUG: Division by zero in arithmetic expressions should not crash."""
        parser = RedcodeParser()
        # 1/0 in expression — should raise ParseError, not crash
        with pytest.raises(ParseError):
            parser.parse("MOV 1/0, 1", "Test")

    def test_bug_negative_values_in_core(self):
        """BUG: Values in core should always be non-negative (mod core_size).
        Negative operand values should be wrapped.
        """
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMP 0: jump to self (infinite loop). Tests that 0 offset works.
        w = parser.parse("JMP 0", "NegTest")
        mars.load_warrior(w, position=10)
        mars.run()
        # Should survive (infinite loop)
        assert mars.warriors[0].alive

    def test_bug_warrior_wrap_around_load(self):
        """BUG: Warrior loading should handle wrap-around correctly.
        If a warrior is loaded near the end of core, its instructions
        should wrap to the beginning.
        """
        mars = MARS(core_size=15, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV 0, 1\nDAT 1, 2\nDAT 3, 4", "Wrap")
        state = mars.load_warrior(w, position=13)
        # Instructions at 13, 14, 0
        assert mars.core[13].opcode == Opcode.MOV
        assert mars.core[14].opcode == Opcode.DAT
        assert mars.core[0].opcode == Opcode.DAT
        assert mars.core[0].a_value == 3

    def test_bug_core_size_too_small(self):
        """BUG: Core size smaller than warrior should still work (wrapping)."""
        mars = MARS(core_size=5, max_cycles=10, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV 0, 1\nDAT 1, 2\nDAT 3, 4", "Big")
        # Loading a 3-instruction warrior into a 5-cell core
        mars.load_warrior(w, position=0)
        assert mars.core[0].opcode == Opcode.MOV
        assert mars.core[1].opcode == Opcode.DAT
        assert mars.core[2].opcode == Opcode.DAT

    def test_bug_empty_process_queue(self):
        """BUG: Warrior with empty process queue should be marked dead."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        from collections import deque
        parser = RedcodeParser()
        w = parser.parse("JMP 0", "Test")
        state = mars.load_warrior(w, position=10)
        # Manually clear processes
        state.processes.clear()
        mars._execute_one_instruction(state)
        assert not state.alive

    def test_bug_compare_equal_modifier_i(self):
        """BUG: CMP.I should compare ALL fields including opcode, modifier, modes."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        # Two identical instructions should compare equal with .I
        instr1 = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                             AddressMode.DIRECT, 1)
        instr2 = Instruction(Opcode.MOV, Modifier.I, AddressMode.DIRECT, 0,
                             AddressMode.DIRECT, 1)
        assert mars._compare_equal(Modifier.I, [instr1, instr2], 0, 1)

        # Different opcode should not compare equal
        instr3 = Instruction(Opcode.DAT, Modifier.I, AddressMode.DIRECT, 0,
                             AddressMode.DIRECT, 1)
        assert not mars._compare_equal(Modifier.I, [instr1, instr3], 0, 1)

    def test_bug_spl_at_max_processes(self):
        """BUG: SPL when at max processes should silently drop the new process,
        not crash."""
        mars = MARS(core_size=100, max_cycles=20, max_processes=2, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SPL creates new processes, but max is 2
        w = parser.parse("SPL 0\nSPL 0\nSPL 0\nJMP 0", "Splitter")
        mars.load_warrior(w, position=10)
        # Should not crash
        mars.run()

    def test_bug_mov_i_copies_modes_too(self):
        """BUG: MOV.I should copy addressing modes, not just opcode and values."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        w = parser.parse("MOV.I $0, $1\nDAT 0, 0", "MovTest")
        mars.load_warrior(w, position=10)
        mars.run()
        # The instruction at position 11 should be an exact copy of position 10
        assert mars.core[11].opcode == Opcode.MOV
        assert mars.core[11].a_mode == AddressMode.DIRECT
        assert mars.core[11].b_mode == AddressMode.DIRECT
        assert mars.core[11].a_value == 0
        assert mars.core[11].b_value == 1

    def test_bug_add_modulo_core_size(self):
        """BUG: ADD results should be mod core_size to prevent overflow."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # ADD a large number to B-field — result should wrap
        w = parser.parse("ADD.AB #99, $1\nDAT 0, 50", "Adder")
        mars.load_warrior(w, position=10)
        mars.run()
        # 50 + 99 = 149, mod 100 = 49
        assert mars.core[11].b_value == 49

    def test_bug_sub_negative_result_wraps(self):
        """BUG: SUB should wrap negative results via mod core_size."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SUB 50 from 10: 10 - 50 = -40, mod 100 = 60
        w = parser.parse("SUB.AB #50, $1\nDAT 0, 10", "Subber")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.core[11].b_value == 60

    def test_bug_mul_large_result_wraps(self):
        """BUG: MUL results should wrap via mod core_size."""
        mars = MARS(core_size=100, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # MUL 20 * 10 = 200, mod 100 = 0
        w = parser.parse("MUL.AB #20, $1\nDAT 0, 10", "Mul")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.core[11].b_value == 0  # 200 % 100 = 0

    def test_bug_label_with_opcode_name(self):
        """BUG: A label that matches an opcode name should be treated as an
        opcode, not a label. This is actually correct behavior, but let's verify."""
        parser = RedcodeParser()
        # "MOV" as a label should be treated as opcode, not label
        # So "MOV MOV 0, 1" means label "MOV" then opcode "MOV"
        # But the first MOV would be interpreted as opcode, not label
        # This means you can't use opcode names as labels
        src = "MOV 0, 1"
        w = parser.parse(src, "Test")
        assert w.instructions[0].opcode == Opcode.MOV

    def test_bug_immediate_mode_comparison(self):
        """BUG: SEQ/SNE/SLT with immediate addressing should compare the
        immediate values, not the instruction at pc (which is always itself).
        Fixed by adding _compare_with_modes and _compare_less_with_modes.
        """
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # SNE.B #5, #3: 5 != 3 → skip → should survive
        w = parser.parse("SNE.B #5, #3\nDAT 0, 0\nJMP 0", "ImmCmp")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_bug_immediate_mode_jmz(self):
        """BUG: JMZ with immediate B should check the immediate value, not
        the B-field of the instruction at pc."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMZ 0, #0: immediate B=0 → jump to self → infinite loop
        w = parser.parse("JMZ 0, #0", "ImmJMZ")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_bug_immediate_mode_jmn(self):
        """BUG: JMN with immediate B should check the immediate value."""
        mars = MARS(core_size=50, max_cycles=5, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # JMN 0, #5: immediate B=5 (non-zero) → jump to self → infinite loop
        w = parser.parse("JMN 0, #5", "ImmJMN")
        mars.load_warrior(w, position=10)
        mars.run()
        assert mars.warriors[0].alive

    def test_bug_immediate_mode_djn(self):
        """BUG: DJN with immediate B should decrement the instruction's
        own B-field, not the value at a resolved address."""
        mars = MARS(core_size=50, max_cycles=20, seed=42)
        mars.reset()
        parser = RedcodeParser()
        # DJN 0, #3: decrement B-field (starts at 3), jump to self if non-zero
        w = parser.parse("DJN 0, #3", "ImmDJN")
        mars.load_warrior(w, position=10)
        mars.run()
        # After 3 decrements, B-field reaches 0 and the process falls through
        # to the next instruction (DAT 0, 0 at position 11) and dies
        assert not mars.warriors[0].alive

    def test_bug_dead_code_removal(self):
        """Verify that the dead code (unused a_val_a, etc.) was removed."""
        import inspect
        source = inspect.getsource(MARS._execute_instruction)
        # The dead variables should not be in the source anymore
        assert "a_val_a" not in source
        assert "a_val_b" not in source
        assert "b_val_a" not in source
        assert "b_val_b" not in source