"""Tests for colored Petri nets."""

import pytest
from petri.colored import (
    ColoredPetriNet, ColoredPlace, ColoredTransition,
    ColorSet, ArcInscription, INT, STRING, BOOL, UNIT,
)


class TestColorSet:
    def test_int_colorset(self):
        assert INT.contains(42)
        assert INT.contains(0)
        assert not INT.contains("hello")

    def test_string_colorset(self):
        assert STRING.contains("hello")
        assert not STRING.contains(42)

    def test_bool_colorset(self):
        assert BOOL.contains(True)
        assert BOOL.contains(False)
        assert not BOOL.contains(1)  # 1 is not True/False in bool values

    def test_custom_values(self):
        cs = ColorSet("colors", values=["red", "green", "blue"])
        assert cs.contains("red")
        assert not cs.contains("yellow")

    def test_unit(self):
        assert UNIT.contains(())


class TestColoredPlace:
    def test_basic(self):
        p = ColoredPlace("p1", color_set=INT, initial=[1, 2, 3])
        assert p.name == "p1"
        assert len(p.initial) == 3

    def test_invalid_initial(self):
        with pytest.raises(ValueError):
            ColoredPlace("p1", color_set=INT, initial=["not_an_int"])

    def test_capacity_exceeded(self):
        with pytest.raises(ValueError):
            ColoredPlace("p1", color_set=INT, initial=[1, 2, 3], capacity=2)


class TestColoredPetriNet:
    def test_simple_firing(self):
        """Simple colored net: one place -> one transition -> one place."""
        cpn = ColoredPetriNet("simple")
        cpn.add_place(ColoredPlace("in", color_set=UNIT, initial=[()]))
        cpn.add_place(ColoredPlace("out", color_set=UNIT))
        cpn.add_transition(ColoredTransition("t"))
        cpn.add_arc("in", "t", ArcInscription.unit(), direction="in")
        cpn.add_arc("out", "t", ArcInscription.unit(), direction="out")

        marking = cpn.initial_marking()
        assert cpn.is_enabled("t", marking)
        new_marking = cpn.fire("t", marking)
        assert len(new_marking["in"]) == 0
        assert len(new_marking["out"]) == 1

    def test_identity_arc(self):
        """Identity arc passes through a token's value."""
        cpn = ColoredPetriNet("identity")
        cpn.add_place(ColoredPlace("in", color_set=INT, initial=[42]))
        cpn.add_place(ColoredPlace("out", color_set=INT))
        cpn.add_transition(ColoredTransition("t"))
        cpn.add_arc("in", "t", ArcInscription.identity("x"), direction="in")
        cpn.add_arc("out", "t", ArcInscription.identity("x"), direction="out")

        marking = cpn.initial_marking()
        new_marking = cpn.fire("t", marking)
        assert 42 in new_marking["out"]

    def test_transform_arc(self):
        """Transform arc modifies token value on the output side."""
        cpn = ColoredPetriNet("transform")
        cpn.add_place(ColoredPlace("in", color_set=INT, initial=[5]))
        cpn.add_place(ColoredPlace("out", color_set=INT))
        cpn.add_transition(ColoredTransition("double"))
        # Input arc: consume the token (identity, binds variable x)
        cpn.add_arc("in", "double", ArcInscription.identity("x"), direction="in")
        # Output arc: produce transformed value
        cpn.add_arc("out", "double", ArcInscription.transform(lambda x: x * 2, "x"), direction="out")

        marking = cpn.initial_marking()
        new_marking = cpn.fire("double", marking)
        assert 10 in new_marking["out"]

    def test_guard(self):
        """Guard prevents firing when condition is not met."""
        cpn = ColoredPetriNet("guarded")
        cpn.add_place(ColoredPlace("in", color_set=INT, initial=[3]))
        cpn.add_place(ColoredPlace("out", color_set=INT))
        cpn.add_transition(ColoredTransition("check", guard=lambda b: b.get("x", 0) > 5))
        cpn.add_arc("in", "check", ArcInscription.identity("x"), direction="in")
        cpn.add_arc("out", "check", ArcInscription.identity("x"), direction="out")

        marking = cpn.initial_marking()
        # Token is 3, guard requires > 5, so not enabled
        assert not cpn.is_enabled("check", marking)

        # Now with a token > 5
        marking["in"] = [10]
        assert cpn.is_enabled("check", marking)

    def test_constant_produce(self):
        """Constant arc inscription produces a fixed value."""
        cpn = ColoredPetriNet("constant")
        cpn.add_place(ColoredPlace("trigger", color_set=UNIT, initial=[()]))
        cpn.add_place(ColoredPlace("output", color_set=STRING))
        cpn.add_transition(ColoredTransition("emit"))
        cpn.add_arc("trigger", "emit", ArcInscription.unit(), direction="in")
        cpn.add_arc("output", "emit", ArcInscription.constant("hello"), direction="out")

        marking = cpn.initial_marking()
        new_marking = cpn.fire("emit", marking)
        assert "hello" in new_marking["output"]

    def test_not_enabled_empty_place(self):
        """Transition not enabled when input place is empty."""
        cpn = ColoredPetriNet("empty")
        cpn.add_place(ColoredPlace("in", color_set=INT, initial=[]))
        cpn.add_place(ColoredPlace("out", color_set=INT))
        cpn.add_transition(ColoredTransition("t"))
        cpn.add_arc("in", "t", ArcInscription.identity("x"), direction="in")
        cpn.add_arc("out", "t", ArcInscription.identity("x"), direction="out")

        marking = cpn.initial_marking()
        assert not cpn.is_enabled("t", marking)

    def test_duplicate_place_raises(self):
        cpn = ColoredPetriNet("test")
        cpn.add_place(ColoredPlace("p1"))
        with pytest.raises(ValueError):
            cpn.add_place(ColoredPlace("p1"))

    def test_repr(self):
        cpn = ColoredPetriNet("test")
        cpn.add_place(ColoredPlace("p1"))
        cpn.add_transition(ColoredTransition("t1"))
        r = repr(cpn)
        assert "ColoredPetriNet" in r
        assert "1" in r  # 1 place, 1 transition