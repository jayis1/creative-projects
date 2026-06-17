"""Preset circuits: common patterns pre-built for convenience."""

from __future__ import annotations
from typing import Optional
from .core import Signal
from .circuit import Circuit


def build_sr_latch_circuit(name: str = "sr_latch") -> Circuit:
    """Build a circuit with an SR latch and test inputs."""
    circ = Circuit(name)
    s = circ.add_wire("s", Signal.LOW)
    r = circ.add_wire("r", Signal.LOW)
    q = circ.add_wire("q", Signal.LOW)
    qbar = circ.add_wire("qbar", Signal.HIGH)
    circ.add_sr_latch("latch", s, r, q, qbar)
    return circ


def build_d_flipflop_counter(name: str = "counter", width: int = 4) -> Circuit:
    """
    Build an N-bit ripple counter using T flip-flops.
    Each stage toggles on the falling edge of the previous stage.
    """
    if width < 1:
        raise ValueError("Counter width must be >= 1")

    circ = Circuit(name)
    clk = circ.add_wire("clk", Signal.LOW)
    circ.add_clock("sys_clk", clk, period_ns=20)

    prev_q = clk
    for i in range(width):
        t = circ.add_wire(f"t{i}", Signal.HIGH)  # Always toggle
        q = circ.add_wire(f"q{i}", Signal.LOW)
        qbar = circ.add_wire(f"q{i}bar", Signal.HIGH)
        circ.add_t_flipflop(f"tff{i}", t, prev_q, q, qbar)
        prev_q = q

    return circ


def build_alu_1bit(name: str = "alu_1bit") -> Circuit:
    """
    Build a 1-bit ALU that supports AND, OR, XOR, and ADD operations.
    Control signals: op[0], op[1] select the operation:
      00 = AND, 01 = OR, 10 = XOR, 11 = ADD
    """
    circ = Circuit(name)
    a = circ.add_wire("a", Signal.LOW)
    b = circ.add_wire("b", Signal.LOW)
    op0 = circ.add_wire("op0", Signal.LOW)
    op1 = circ.add_wire("op1", Signal.LOW)
    cin = circ.add_wire("cin", Signal.LOW)
    result = circ.add_wire("result")
    cout = circ.add_wire("cout")

    # Compute all operations in parallel
    and_out = circ.add_wire("and_out")
    or_out = circ.add_wire("or_out")
    xor_out = circ.add_wire("xor_out")
    add_sum = circ.add_wire("add_sum")
    add_cout_wire = circ.add_wire("add_cout")

    circ.add_and("alu_and", a, b, and_out)
    circ.add_or("alu_or", a, b, or_out)
    circ.add_xor("alu_xor", a, b, xor_out)
    circ.build_full_adder("alu_add", a, b, cin, add_sum, add_cout_wire)

    # 4-to-1 MUX for result selection
    # MUX: op1 op0 -> select
    # 00 = AND, 01 = OR, 10 = XOR, 11 = ADD (sum)
    not_op0 = circ.add_wire("not_op0")
    not_op1 = circ.add_wire("not_op1")
    m0_en = circ.add_wire("m0_en")  # op1=0, op0=0 -> AND
    m1_en = circ.add_wire("m1_en")  # op1=0, op0=1 -> OR
    m2_en = circ.add_wire("m2_en")  # op1=1, op0=0 -> XOR
    m3_en = circ.add_wire("m3_en")  # op1=1, op0=1 -> ADD

    circ.add_not("not_op0", op0, not_op0)
    circ.add_not("not_op1", op1, not_op1)
    circ.add_and("m0_dec", not_op1, not_op0, m0_en)
    circ.add_and("m1_dec", not_op1, op0, m1_en)
    circ.add_and("m2_dec", op1, not_op0, m2_en)
    circ.add_and("m3_dec", op1, op0, m3_en)

    # Tri-state buffers for MUX output
    ts0_out = circ.add_wire("ts0_out")
    ts1_out = circ.add_wire("ts1_out")
    ts2_out = circ.add_wire("ts2_out")
    ts3_out = circ.add_wire("ts3_out")

    circ.add_tristate("ts0", and_out, m0_en, ts0_out)
    circ.add_tristate("ts1", or_out, m1_en, ts1_out)
    circ.add_tristate("ts2", xor_out, m2_en, ts2_out)
    circ.add_tristate("ts3", add_sum, m3_en, ts3_out)

    # Combine tri-state outputs with a pull-down resistor (OR-like behavior)
    # Since only one tri-state is active at a time, we can use a multi-input OR
    circ.add_multi_gate("result_mux", [ts0_out, ts1_out, ts2_out, ts3_out], result, "or", delay_ns=2)

    # Carry out only for ADD operation
    circ.add_and("cout_gate", add_cout_wire, m3_en, cout)

    return circ


def build_register(name: str = "register", width: int = 4) -> Circuit:
    """
    Build an N-bit register using D flip-flops with a common clock.
    Supports load enable and reset.
    """
    if width < 1:
        raise ValueError("Register width must be >= 1")

    circ = Circuit(name)
    clk = circ.add_wire("clk", Signal.LOW)
    circ.add_clock("sys_clk", clk, period_ns=20)
    load = circ.add_wire("load", Signal.LOW)
    rst = circ.add_wire("rst", Signal.LOW)

    for i in range(width):
        d_in = circ.add_wire(f"d_in{i}", Signal.LOW)
        d_actual = circ.add_wire(f"d_actual{i}")
        q = circ.add_wire(f"q{i}", Signal.LOW)
        qbar = circ.add_wire(f"q{i}bar", Signal.HIGH)

        # MUX: if load=1, take d_in; if load=0, hold current q
        not_load = circ.add_wire(f"not_load{i}")
        hold_val = circ.add_wire(f"hold{i}")
        new_val = circ.add_wire(f"new{i}")

        circ.add_not(f"not_load{i}", load, not_load)
        circ.add_and(f"hold_and{i}", q, not_load, hold_val)
        circ.add_and(f"new_and{i}", d_in, load, new_val)
        circ.add_or(f"mux_or{i}", hold_val, new_val, d_actual)

        circ.add_d_flipflop(f"dff{i}", d_actual, clk, q, qbar, reset=rst)

    return circ


def build_ring_oscillator(name: str = "ring_osc", num_stages: int = 5) -> Circuit:
    """
    Build a ring oscillator with an odd number of inverter stages.
    The output oscillates based on the total propagation delay.
    """
    if num_stages % 2 == 0:
        raise ValueError("Ring oscillator requires odd number of stages")
    if num_stages < 3:
        raise ValueError("Ring oscillator requires at least 3 stages")

    circ = Circuit(name)
    wires = []
    for i in range(num_stages):
        w = circ.add_wire(f"stage{i}", Signal.HIGH if i == 0 else Signal.UNDEFINED)
        wires.append(w)

    for i in range(num_stages):
        input_wire = wires[i]
        output_wire = wires[(i + 1) % num_stages]
        circ.add_not(f"inv{i}", input_wire, output_wire, delay_ns=2)

    return circ


def build_priority_encoder(name: str = "priority_encoder_4bit") -> Circuit:
    """
    Build a 4-bit priority encoder.
    Inputs: d3, d2, d1, d0 (active HIGH)
    Outputs: y1, y0 (binary encoded position of highest priority)
             valid (at least one input active)
    """
    circ = Circuit(name)
    d3 = circ.add_wire("d3", Signal.LOW)
    d2 = circ.add_wire("d2", Signal.LOW)
    d1 = circ.add_wire("d1", Signal.LOW)
    d0 = circ.add_wire("d0", Signal.LOW)
    y1 = circ.add_wire("y1")
    y0 = circ.add_wire("y0")
    valid = circ.add_wire("valid")

    not_d3 = circ.add_wire("not_d3")
    not_d2 = circ.add_wire("not_d2")
    not_d3_d2 = circ.add_wire("not_d3_d2")

    # y1 = d3 OR (NOT d3 AND d2) = d3 OR d2 (simplified, but we implement properly)
    circ.add_not("not3", d3, not_d3)
    circ.add_not("not2", d2, not_d2)
    circ.add_and("not_d3_d2_gate", not_d3, d2, not_d3_d2)
    circ.add_or("y1_gate", d3, not_d3_d2, y1)

    # y0 = d3 OR (NOT d3 AND NOT d2 AND d1)
    not_d3_not_d2 = circ.add_wire("not_d3_not_d2")
    not_d3_not_d2_d1 = circ.add_wire("not_d3_not_d2_d1")
    circ.add_and("not_d3_not_d2_gate", not_d3, not_d2, not_d3_not_d2)
    circ.add_and("not_d3_not_d2_d1_gate", not_d3_not_d2, d1, not_d3_not_d2_d1)
    circ.add_or("y0_gate", d3, not_d3_not_d2_d1, y0)

    # valid = d3 OR d2 OR d1 OR d0
    circ.add_multi_gate("valid_gate", [d3, d2, d1, d0], valid, "or")

    return circ