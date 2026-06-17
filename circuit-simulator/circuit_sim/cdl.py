"""Circuit Description Language (CDL) parser for declarative circuit construction."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .core import Signal, Wire
from .circuit import Circuit


class CDLParseError(Exception):
    """Error encountered while parsing CDL."""
    pass


def parse_cdl(source: str) -> Circuit:
    """
    Parse a CDL description and return a Circuit.
    
    CDL syntax:
    
        circuit <name>;
        
        wire <name> [initial=LOW|HIGH|UNDEFINED];
        bus <name> <width> [initial=LOW|HIGH|UNDEFINED];
        
        gate <type> <name> <input1> <input2> ... -> <output>;
        sequential <type> <name> <input1> <input2> ... -> <output1> <output2>;
        clock <name> <output> period=<ns> [duty=<fraction>];
        
        # Composite builders
        half_adder <prefix> <a> <b> -> <sum> <carry>;
        full_adder <prefix> <a> <b> <cin> -> <sum> <cout>;
        ripple_adder <prefix> bus:<bus_a> bus:<bus_b> bus:<sum_bus>;
        mux2 <prefix> <a> <b> <sel> -> <out>;
        
        # Stimulus
        set <wire> LOW|HIGH at <time_ns>;
        setbus <bus> <value> at <time_ns>;
    
    Lines starting with # are comments. Empty lines are ignored.
    """
    lines = source.strip().split('\n')
    circuit: Optional[Circuit] = None
    stimuli: List[Tuple[int, str, Signal]] = []
    bus_stimuli: List[Tuple[int, str, int]] = []
    
    for line_num, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        # Remove inline comments
        if '#' in line:
            line = line[:line.index('#')].strip()
        if not line:
            continue
        
        tokens = line.rstrip(';').split()
        if not tokens:
            continue
        
        try:
            cmd = tokens[0].lower()
            
            if cmd == 'circuit':
                if circuit is not None:
                    raise CDLParseError(f"Line {line_num}: circuit already defined")
                circuit = Circuit(tokens[1])
            
            elif cmd == 'wire':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                name = tokens[1]
                initial = Signal.UNDEFINED
                for t in tokens[2:]:
                    if t.startswith('initial='):
                        val = t.split('=')[1].upper()
                        initial = Signal[val]
                circuit.add_wire(name, initial)
            
            elif cmd == 'bus':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                name = tokens[1]
                width = int(tokens[2])
                initial = Signal.LOW
                for t in tokens[3:]:
                    if t.startswith('initial='):
                        val = t.split('=')[1].upper()
                        initial = Signal[val]
                circuit.add_bus(name, width, initial)
            
            elif cmd == 'gate':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                gate_type = tokens[1].lower()
                name = tokens[2]
                # Find -> separator
                arrow_idx = tokens.index('->')
                input_names = tokens[3:arrow_idx]
                output_name = tokens[arrow_idx + 1]
                
                input_wires = [circuit.wire(n) for n in input_names]
                output_wire = circuit.wire(output_name)
                
                gate_map = {
                    'and': circuit.add_and,
                    'or': circuit.add_or,
                    'not': circuit.add_not,
                    'xor': circuit.add_xor,
                    'nand': circuit.add_nand,
                    'nor': circuit.add_nor,
                    'xnor': circuit.add_xnor,
                    'buffer': circuit.add_buffer,
                }
                
                if gate_type in gate_map:
                    if gate_type == 'not' or gate_type == 'buffer':
                        gate_map[gate_type](name, input_wires[0], output_wire)
                    else:
                        gate_map[gate_type](name, input_wires[0], input_wires[1], output_wire)
                elif gate_type == 'tristate':
                    circuit.add_tristate(name, input_wires[0], input_wires[1], output_wire)
                else:
                    raise CDLParseError(f"Line {line_num}: unknown gate type {gate_type!r}")
            
            elif cmd == 'sequential':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                seq_type = tokens[1].lower()
                name = tokens[2]
                arrow_idx = tokens.index('->')
                input_names = tokens[3:arrow_idx]
                output_names = tokens[arrow_idx + 1:]
                
                input_wires = [circuit.wire(n) for n in input_names]
                output_wires = [circuit.wire(n) for n in output_names]
                
                if seq_type == 'sr_latch':
                    circuit.add_sr_latch(name, input_wires[0], input_wires[1],
                                         output_wires[0], output_wires[1])
                elif seq_type == 'd_latch':
                    circuit.add_d_latch(name, input_wires[0], input_wires[1],
                                        output_wires[0], output_wires[1])
                elif seq_type == 'd_flipflop':
                    circuit.add_d_flipflop(name, input_wires[0], input_wires[1],
                                           output_wires[0], output_wires[1])
                elif seq_type == 'jk_flipflop':
                    circuit.add_jk_flipflop(name, input_wires[0], input_wires[1],
                                            input_wires[2], output_wires[0], output_wires[1])
                elif seq_type == 't_flipflop':
                    circuit.add_t_flipflop(name, input_wires[0], input_wires[1],
                                           output_wires[0], output_wires[1])
                else:
                    raise CDLParseError(f"Line {line_num}: unknown sequential type {seq_type!r}")
            
            elif cmd == 'clock':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                name = tokens[1]
                output_name = tokens[2]
                period = 20
                duty = 0.5
                for t in tokens[3:]:
                    if t.startswith('period='):
                        period = int(t.split('=')[1])
                    elif t.startswith('duty='):
                        duty = float(t.split('=')[1])
                circuit.add_clock(name, circuit.wire(output_name), period, duty)
            
            elif cmd == 'half_adder':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                prefix = tokens[1]
                arrow_idx = tokens.index('->')
                input_names = tokens[2:arrow_idx]
                output_names = tokens[arrow_idx + 1:]
                circuit.build_half_adder(prefix,
                    circuit.wire(input_names[0]), circuit.wire(input_names[1]),
                    circuit.wire(output_names[0]), circuit.wire(output_names[1]))
            
            elif cmd == 'full_adder':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                prefix = tokens[1]
                arrow_idx = tokens.index('->')
                input_names = tokens[2:arrow_idx]
                output_names = tokens[arrow_idx + 1:]
                circuit.build_full_adder(prefix,
                    circuit.wire(input_names[0]), circuit.wire(input_names[1]),
                    circuit.wire(input_names[2]),
                    circuit.wire(output_names[0]), circuit.wire(output_names[1]))
            
            elif cmd == 'mux2':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                prefix = tokens[1]
                arrow_idx = tokens.index('->')
                input_names = tokens[2:arrow_idx]
                output_name = tokens[arrow_idx + 1]
                circuit.build_mux2(prefix,
                    circuit.wire(input_names[0]), circuit.wire(input_names[1]),
                    circuit.wire(input_names[2]), circuit.wire(output_name))
            
            elif cmd == 'ripple_adder':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                prefix = tokens[1]
                # Parse bus references: bus:<name>
                bus_refs = tokens[2:]
                bus_names = []
                for ref in bus_refs:
                    if ref.startswith('bus:'):
                        bus_names.append(ref[4:])
                    else:
                        raise CDLParseError(f"Line {line_num}: ripple_adder requires bus references (bus:<name>)")
                if len(bus_names) != 3:
                    raise CDLParseError(f"Line {line_num}: ripple_adder requires 3 bus references (bus:a bus:b bus:sum)")
                bus_a = circuit.bus(bus_names[0])
                bus_b = circuit.bus(bus_names[1])
                sum_bus = circuit.bus(bus_names[2])
                circuit.build_ripple_carry_adder(prefix, bus_a, bus_b, sum_bus)
            
            elif cmd == 'set':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                wire_name = tokens[1]
                value = Signal[tokens[2].upper()]
                time_ns = int(tokens[4])  # 'at' is tokens[3]
                stimuli.append((time_ns, wire_name, value))
            
            elif cmd == 'setbus':
                if circuit is None:
                    raise CDLParseError(f"Line {line_num}: no circuit defined")
                bus_name = tokens[1]
                value = int(tokens[2])
                time_ns = int(tokens[4])
                bus_stimuli.append((time_ns, bus_name, value))
            
            else:
                raise CDLParseError(f"Line {line_num}: unknown command {cmd!r}")
        
        except (IndexError, ValueError, KeyError) as e:
            raise CDLParseError(f"Line {line_num}: syntax error — {e}") from e
    
    if circuit is None:
        raise CDLParseError("No circuit definition found")
    
    # Attach stimuli to the circuit for later use
    circuit._stimuli = stimuli
    circuit._bus_stimuli = bus_stimuli
    
    return circuit