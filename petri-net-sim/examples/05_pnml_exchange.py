"""Example: PNML export/import round-trip."""

from petri.presets import mutual_exclusion
from petri.pnml import to_pnml, from_pnml, validate_pnml

net = mutual_exclusion()

print("=== PNML Export/Import ===")
print(f"Original net: {net}")
print()

# Export to PNML
pnml = to_pnml(net)
print("--- PNML (first 500 chars) ---")
print(pnml[:500])
print("...")
print()

# Validate
issues = validate_pnml(pnml)
print(f"Validation issues: {len(issues)}")
for issue in issues:
    print(f"  - {issue}")
print()

# Import back
imported = from_pnml(pnml)
print(f"Imported net: {imported}")
print(f"  Places match: {len(imported.places) == len(net.places)}")
print(f"  Transitions match: {len(imported.transitions) == len(net.transitions)}")
print()

# Save to file
with open("/tmp/mutex.pnml", "w") as f:
    f.write(pnml)
print("Saved to /tmp/mutex.pnml")