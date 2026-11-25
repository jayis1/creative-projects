## Known Issues (Resolved)

- Rendering previously trusted externally constructed `CoveragePlan` coordinates and could leak an `IndexError` for an out-of-grid cell. Rendering now validates every route coordinate and rejects malformed plans with a clear `ValueError`; regression coverage includes both bounds and blocked-cell violations.
