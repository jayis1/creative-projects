#!/usr/bin/env python3
"""Pause-time analysis example.

Shows how to build a pause-time histogram and generate a detailed
comparison report with percentile breakdowns.
"""

from gc_sim.simulator import GCSimulator
from gc_sim.collectors import available_collectors
from gc_sim.reporting import (
    PauseHistogram,
    CollectorReport,
    format_comparison_report,
    analyse_from_sims,
)


def main():
    # Run multiple collections to build up pause-time data
    sims = {}
    for collector in available_collectors():
        sim = GCSimulator(heap_size=512, collector=collector)
        sim.scenario_churn(n_short=80, n_long=5, obj_size=4)
        # Run 5 collections to get varied pause times
        for _ in range(5):
            sim.collect()
        sims[collector] = sim

    # Generate reports
    reports = analyse_from_sims(sims)

    # Print detailed comparison
    print(format_comparison_report(reports, include_histogram=True))

    # Show histogram for a single collector
    print("\n")
    print("=" * 60)
    print("Detailed histogram for generational collector")
    print("=" * 60)
    gen_report = next(r for r in reports if r.collector == "generational")
    if gen_report.histogram:
        print(gen_report.histogram.render_ascii())


if __name__ == "__main__":
    main()