"""PNML (Petri Net Markup Language) import and export.

PNML is the ISO/IEC 15909-2 standard interchange format for Petri nets.
This module supports a useful subset: P/T nets with places, transitions,
arcs, initial markings, and capacity constraints.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from .net import PetriNet, Place, Transition


def to_pnml(net: PetriNet) -> str:
    """Export a Petri net as PNML (XML) string.

    Produces a valid PNML document conforming to the P/T net exchange format.
    """
    root = ET.Element("pnml")
    net_el = ET.SubElement(root, "net", attrib={"id": net.name, "type": "P/T net"})

    # Places
    for p in net.places.values():
        place_el = ET.SubElement(net_el, "place", attrib={"id": p.name})
        name_el = ET.SubElement(place_el, "name")
        ET.SubElement(name_el, "text").text = p.name
        ET.SubElement(place_el, "initialMarking").text = str(p.initial)
        if p.capacity is not None:
            ET.SubElement(place_el, "capacity").text = str(p.capacity)

    # Transitions
    for t in net.transitions.values():
        trans_el = ET.SubElement(net_el, "transition", attrib={"id": t.name})
        name_el = ET.SubElement(trans_el, "name")
        ET.SubElement(name_el, "text").text = t.name
        if t.label:
            ET.SubElement(trans_el, "label").text = t.label

    # Arcs
    arc_id = 0
    seen = set()
    for t_name in net.transitions:
        for arc in net.input_arcs(t_name):
            key = (arc.source, arc.target)
            if key in seen:
                continue
            seen.add(key)
            arc_el = ET.SubElement(net_el, "arc", attrib={
                "id": f"a{arc_id}",
                "source": arc.source,
                "target": arc.target,
            })
            if arc.weight > 1:
                ET.SubElement(arc_el, "inscription").text = str(arc.weight)
            arc_id += 1
        for arc in net.output_arcs(t_name):
            key = (arc.source, arc.target)
            if key in seen:
                continue
            seen.add(key)
            arc_el = ET.SubElement(net_el, "arc", attrib={
                "id": f"a{arc_id}",
                "source": arc.source,
                "target": arc.target,
            })
            if arc.weight > 1:
                ET.SubElement(arc_el, "inscription").text = str(arc.weight)
            arc_id += 1

    # Pretty print
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def from_pnml(pnml_str: str) -> PetriNet:
    """Parse a PNML string and return a PetriNet.

    Supports the P/T net subset: places, transitions, arcs, initial markings.
    """
    root = ET.fromstring(pnml_str)
    net_el = root.find("net")
    if net_el is None:
        raise ValueError("Invalid PNML: no <net> element")

    net_name = net_el.get("id", "imported")
    net = PetriNet(name=net_name)

    # Parse places
    for place_el in net_el.findall("place"):
        p_id = place_el.get("id", "")
        initial = 0
        capacity = None

        im_el = place_el.find("initialMarking")
        if im_el is not None and im_el.text:
            initial = int(im_el.text.strip())

        cap_el = place_el.find("capacity")
        if cap_el is not None and cap_el.text:
            capacity = int(cap_el.text.strip())

        net.add_place(Place(p_id, initial=initial, capacity=capacity))

    # Parse transitions
    for trans_el in net_el.findall("transition"):
        t_id = trans_el.get("id", "")
        label = ""
        label_el = trans_el.find("label")
        if label_el is not None and label_el.text:
            label = label_el.text
        net.add_transition(Transition(t_id, label=label))

    # Parse arcs
    for arc_el in net_el.findall("arc"):
        source = arc_el.get("source", "")
        target = arc_el.get("target", "")
        weight = 1
        inscr_el = arc_el.find("inscription")
        if inscr_el is not None and inscr_el.text:
            weight = int(inscr_el.text.strip())

        # Only add if both endpoints exist
        if source in net.places or source in net.transitions:
            try:
                net.add_arc(source, target, weight=weight)
            except (ValueError, KeyError):
                pass  # skip invalid arcs

    return net


def validate_pnml(pnml_str: str) -> list[str]:
    """Validate a PNML string and return a list of issues (empty = valid)."""
    issues: list[str] = []
    try:
        root = ET.fromstring(pnml_str)
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    net_el = root.find("net")
    if net_el is None:
        return ["Missing <net> element"]

    place_ids = set()
    for p in net_el.findall("place"):
        pid = p.get("id")
        if not pid:
            issues.append("Place without id")
        else:
            place_ids.add(pid)
        im = p.find("initialMarking")
        if im is not None and im.text:
            try:
                int(im.text.strip())
            except ValueError:
                issues.append(f"Place '{pid}': invalid initialMarking '{im.text}'")

    trans_ids = set()
    for t in net_el.findall("transition"):
        tid = t.get("id")
        if not tid:
            issues.append("Transition without id")
        else:
            trans_ids.add(tid)

    for a in net_el.findall("arc"):
        src = a.get("source", "")
        tgt = a.get("target", "")
        if src not in place_ids and src not in trans_ids:
            issues.append(f"Arc {src}->{tgt}: source not found")
        if tgt not in place_ids and tgt not in trans_ids:
            issues.append(f"Arc {src}->{tgt}: target not found")
        inscr = a.find("inscription")
        if inscr is not None and inscr.text:
            try:
                w = int(inscr.text.strip())
                if w < 1:
                    issues.append(f"Arc {src}->{tgt}: weight must be >= 1")
            except ValueError:
                issues.append(f"Arc {src}->{tgt}: invalid weight '{inscr.text}'")

    return issues