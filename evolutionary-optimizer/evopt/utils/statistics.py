"""Statistics tracking for evolutionary algorithms."""

from __future__ import annotations

from typing import Dict, Any, List
import json


class Statistics:
    """Collects and summarizes per-generation statistics."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def update(self, stats: Dict[str, Any]) -> None:
        """Record a generation's statistics."""
        self.records.append(dict(stats))

    @property
    def num_generations(self) -> int:
        return len(self.records)

    def best_fitness_history(self) -> List[float]:
        return [r["best_fitness"] for r in self.records if r.get("best_fitness") is not None]

    def avg_fitness_history(self) -> List[float]:
        return [r["avg_fitness"] for r in self.records if r.get("avg_fitness") is not None]

    def diversity_history(self) -> List[float]:
        return [r["diversity"] for r in self.records if r.get("diversity") is not None]

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict with best/avg/std of recorded metrics."""
        best_hist = self.best_fitness_history()
        if not best_hist:
            return {"generations": 0}
        return {
            "generations": len(self.records),
            "best_fitness_overall": min(best_hist) if best_hist else None,
            "worst_best_fitness": max(best_hist) if best_hist else None,
            "final_best_fitness": best_hist[-1],
            "final_avg_fitness": self.avg_fitness_history()[-1] if self.avg_fitness_history() else None,
            "final_diversity": self.diversity_history()[-1] if self.diversity_history() else None,
            "improvement": best_hist[0] - best_hist[-1] if len(best_hist) >= 2 else 0,
        }

    def to_json(self) -> str:
        return json.dumps(self.records, indent=2, default=str)

    def to_csv(self) -> str:
        if not self.records:
            return ""
        keys = list(self.records[0].keys())
        lines = [",".join(keys)]
        for r in self.records:
            lines.append(",".join(str(r.get(k, "")) for k in keys))
        return "\n".join(lines)