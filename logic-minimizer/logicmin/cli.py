"""
Command-line interface for logicmin.

Subcommands
-----------
* ``minimize``  — exact Quine–McCluskey minimization
* ``espresso``  — heuristic Espresso minimization
* ``multi``     — multi-output minimization from a PLA file
* ``factor``    — factorize a SOP expression
* ``truth``     — show the truth table of a function
* ``verify``    — verify a minimized expression against the original function
* ``info``      — show prime implicants and chart info
* ``pos``       — product-of-sums minimization
* ``kmap``      — render Karnaugh map
* ``benchmark`` — benchmark QM vs Espresso
* ``config``    — show or save configuration
* ``bdd``       — build a ROBDD and show stats / SOP
* ``sensitivity`` — sensitivity analysis for each variable
* ``unate``     — classify variables as positive/negative/binate
* ``dc-optimize`` — optimize don't-care assignment
* ``batch``     — batch minimize multiple functions from a PLA file
* ``html``      — generate HTML visualization (truth table / K-map / report)
* ``export``    — serialize a function or result to JSON
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from .boolean import BooleanFunction, TruthTable, var_names
from .quine_mccluskey import QuineMcCluskey
from .espresso import Espresso
from .multi_output import MultiOutputMinimizer
from .factorizer import Factorizer
from .parser import parse_truth_table, parse_minterms, parse_sop, parse_pla


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logicmin",
        description="Boolean logic minimization toolkit (Quine–McCluskey + Espresso + Petrick + BDD + Analysis)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # minimize
    p = sub.add_parser("minimize", help="Exact QM minimization")
    p.add_argument("--minterms", "-m", type=str, default="",
                   help="Minterm list: '4 8 10 d: 9 14'")
    p.add_argument("--nvars", "-n", type=int, required=True,
                   help="Number of input variables")
    p.add_argument("--sop", "-s", type=str, default="",
                   help="SOP expression to minimize (e.g. AB'C+AC)")
    p.add_argument("--tt", "-t", type=str, default="",
                   help="Truth table file or inline (- for stdin)")
    p.add_argument("--no-petrick", action="store_true",
                   help="Use greedy cover instead of Petrick's method")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--show-primes", action="store_true",
                   help="List all prime implicants")

    # espresso
    p = sub.add_parser("espresso", help="Heuristic Espresso minimization")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--max-iter", type=int, default=50)
    p.add_argument("--json", action="store_true")

    # multi
    p = sub.add_parser("multi", help="Multi-output minimization from PLA")
    p.add_argument("pla_file", type=str, help="PLA file path (or - for stdin)")
    p.add_argument("--no-petrick", action="store_true")

    # factor
    p = sub.add_parser("factor", help="Factorize a SOP expression")
    p.add_argument("sop", type=str, help="SOP expression")

    # truth
    p = sub.add_parser("truth", help="Show truth table")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")

    # verify
    p = sub.add_parser("verify", help="Verify SOP against minterms")
    p.add_argument("--minterms", "-m", type=str, required=True)
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, required=True,
                   help="SOP expression to verify")

    # info
    p = sub.add_parser("info", help="Show prime implicants and chart")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")

    # pos
    p = sub.add_parser("pos", help="Product-of-sums minimization")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--no-petrick", action="store_true")

    # kmap
    p = sub.add_parser("kmap", help="Render Karnaugh map")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--cover", action="store_true",
                   help="Highlight the minimized cover in the K-map")

    # benchmark
    p = sub.add_parser("benchmark", help="Benchmark QM vs Espresso")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--trials", "-t", type=int, default=5)
    p.add_argument("--seed", type=int, default=None)

    # config
    p = sub.add_parser("config", help="Show or save configuration")
    p.add_argument("--save", type=str, default="",
                   help="Save default config to file")
    p.add_argument("--load", type=str, default="",
                   help="Load and display config from file")

    # bdd
    p = sub.add_parser("bdd", help="Build a ROBDD and show stats / SOP")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--render", action="store_true", help="Render BDD as ASCII")
    p.add_argument("--count", action="store_true", help="Count satisfying assignments")

    # sensitivity
    p = sub.add_parser("sensitivity", help="Sensitivity analysis for each variable")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")

    # unate
    p = sub.add_parser("unate", help="Classify variables as positive/negative/binate")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")

    # dc-optimize
    p = sub.add_parser("dc-optimize", help="Optimize don't-care assignment")
    p.add_argument("--minterms", "-m", type=str, required=True)
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--minimizer", type=str, default="qm", choices=["qm", "espresso"])

    # batch
    p = sub.add_parser("batch", help="Batch minimize from a PLA file")
    p.add_argument("pla_file", type=str, help="PLA file path")
    p.add_argument("--minimizer", type=str, default="qm", choices=["qm", "espresso", "pos"])
    p.add_argument("--json", action="store_true")

    # html
    p = sub.add_parser("html", help="Generate HTML visualization")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--output", "-o", type=str, default="",
                   help="Output HTML file (default: stdout)")
    p.add_argument("--mode", type=str, default="report",
                   choices=["truth", "kmap", "report"],
                   help="What to generate: truth table, K-map, or full report")

    # export
    p = sub.add_parser("export", help="Serialize a function or result to JSON")
    p.add_argument("--minterms", "-m", type=str, default="")
    p.add_argument("--nvars", "-n", type=int, required=True)
    p.add_argument("--sop", "-s", type=str, default="")
    p.add_argument("--result", action="store_true",
                   help="Also minimize and export the result")

    # version
    p = sub.add_parser("version", help="Show version info")

    return parser


def _load_function(args: argparse.Namespace) -> BooleanFunction:
    if getattr(args, "sop", "") and args.sop:
        return parse_sop(args.sop)
    if getattr(args, "minterms", "") and args.minterms:
        return parse_minterms(args.minterms, args.nvars)
    if getattr(args, "tt", "") and args.tt:
        if args.tt == "-":
            text = sys.stdin.read()
        else:
            with open(args.tt) as fh:
                text = fh.read()
        return parse_truth_table(text)
    raise ValueError("must provide --minterms, --sop, or --tt")


def _cmd_minimize(args: argparse.Namespace) -> int:
    func = _load_function(args)
    qm = QuineMcCluskey(args.nvars, use_petrick=not args.no_petrick)
    result = qm.minimize(func)
    if args.json:
        import json
        print(json.dumps({
            "sop": result.sop,
            "n_terms": result.n_terms,
            "n_literals": result.n_literals,
            "minterms_covered": result.minterms_covered,
            "prime_implicants": [p.cube for p in result.prime_implicants],
            "essential_implicants": [p.cube for p in result.essential_implicants],
            "method": result.method,
        }, indent=2))
    else:
        print(f"Minimized SOP: {result.sop}")
        print(f"  Terms:       {result.n_terms}")
        print(f"  Literals:    {result.n_literals}")
        print(f"  Primes:      {len(result.prime_implicants)}")
        print(f"  Essentials:  {len(result.essential_implicants)}")
        if args.show_primes:
            names = var_names(args.nvars)
            print("  Prime implicants:")
            for p in result.prime_implicants:
                print(f"    {p.cube}  =  {p.sop_term(names)}")
    return 0


def _cmd_espresso(args: argparse.Namespace) -> int:
    func = _load_function(args)
    esp = Espresso(args.nvars, max_iter=args.max_iter)
    result = esp.minimize(func)
    if args.json:
        import json
        print(json.dumps({
            "sop": result.sop,
            "n_terms": result.n_terms,
            "n_literals": result.n_literals,
            "method": result.method,
        }, indent=2))
    else:
        print(f"Espresso SOP: {result.sop}")
        print(f"  Terms:    {result.n_terms}")
        print(f"  Literals: {result.n_literals}")
    return 0


def _cmd_multi(args: argparse.Namespace) -> int:
    if args.pla_file == "-":
        text = sys.stdin.read()
    else:
        with open(args.pla_file) as fh:
            text = fh.read()
    functions = parse_pla(text)
    if not functions:
        print("No functions found in PLA")
        return 1
    nvars = functions[0].n_vars
    mom = MultiOutputMinimizer(nvars, use_petrick=not args.no_petrick)
    result = mom.minimize(functions)
    print(f"Multi-output minimization: {len(functions)} outputs, {nvars} vars")
    print(f"  Total terms:    {result.total_terms}")
    print(f"  Total literals: {result.total_literals}")
    for i, (func, sop) in enumerate(zip(functions, result.sop)):
        print(f"  {func.name}: {sop}")
    shared = [s for s in result.shared_implicants if len(s.outputs) > 1]
    if shared:
        print(f"  Shared implicants ({len(shared)}):")
        names = var_names(nvars)
        for s in shared:
            print(f"    {s.implicant.sop_term(names)}  → outputs {sorted(s.outputs)}")
    return 0


def _cmd_factor(args: argparse.Namespace) -> int:
    from .boolean import BooleanFunction
    func = BooleanFunction.from_sop(args.sop)
    fact = Factorizer(n_vars=func.n_vars)
    ff = fact.factorize_sop(args.sop)
    print(f"Factored: {ff.to_string(func.var_names)}")
    print(f"  Literals: {ff.literal_count()}")
    return 0


def _cmd_truth(args: argparse.Namespace) -> int:
    func = _load_function(args)
    tt = func.truth_table()
    print(tt.render_ascii())
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    func_orig = parse_minterms(args.minterms, args.nvars)
    func_check = parse_sop(args.sop, args.nvars)
    mismatch = False
    for m in range(1 << args.nvars):
        if m in func_orig.dontcare:
            continue
        a = 1 if m in func_orig.minterms else 0
        b = 1 if m in func_check.minterms else 0
        if a != b:
            print(f"MISMATCH at minterm {m}: expected {a}, got {b}")
            mismatch = True
    if mismatch:
        print("Verification FAILED")
        return 1
    print("Verification PASSED")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    func = _load_function(args)
    qm = QuineMcCluskey(args.nvars)
    result = qm.minimize(func)
    names = var_names(args.nvars)
    print(f"Function: {func.name}")
    print(f"  Vars:      {args.nvars} ({', '.join(names)})")
    print(f"  Minterms:  {sorted(func.minterms)}")
    print(f"  Dontcare:  {sorted(func.dontcare)}")
    print(f"  Primes ({len(result.prime_implicants)}):")
    for p in result.prime_implicants:
        covers = [m for m in p.minterms if m in func.minterms]
        tag = " (essential)" if p in result.essential_implicants else ""
        print(f"    {p.cube} = {p.sop_term(names)}  covers {covers}{tag}")
    print(f"  Result:    {result.sop}")
    return 0


def _cmd_pos(args: argparse.Namespace) -> int:
    from .pos import POSMinimizer
    func = _load_function(args)
    pm = POSMinimizer(args.nvars, use_petrick=not args.no_petrick)
    result = pm.minimize(func)
    print(f"Minimized POS: {result.pos}")
    print(f"  Clauses:     {result.n_clauses}")
    print(f"  Literals:    {result.n_literals}")
    print(f"  Dual SOP:    {result.dual_sop}")
    return 0


def _cmd_kmap(args: argparse.Namespace) -> int:
    from .kmap import KarnaughMap
    func = _load_function(args)
    km = KarnaughMap(func)
    if args.cover:
        qm = QuineMcCluskey(args.nvars)
        r = qm.minimize(func)
        print(km.render_with_coverage(r.sop_cubes))
        print(f"\nCover: {r.sop}")
    else:
        print(km.render())
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    from .benchmark import Benchmark
    bench = Benchmark(args.nvars, n_trials=args.trials, seed=args.seed)
    all_results = bench.run_trials()
    print(f"Benchmark: {args.nvars} vars, {args.trials} trials")
    print()
    for i, results in enumerate(all_results):
        print(f"--- Trial {i + 1} ---")
        print(Benchmark.format_results(results))
        print()
    from collections import defaultdict
    methods = defaultdict(list)
    for results in all_results:
        for r in results:
            methods[r.method].append(r)
    print("--- Summary (avg) ---")
    for method, rs in methods.items():
        avg_lits = sum(r.n_literals for r in rs) / len(rs)
        avg_time = sum(r.elapsed_ms for r in rs) / len(rs)
        print(f"  {method:<20} avg_lits={avg_lits:.1f}  avg_time={avg_time:.2f}ms")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    from .config import Config
    if args.save:
        cfg = Config()
        cfg.save(args.save)
        print(f"Saved default config to {args.save}")
        return 0
    if args.load:
        cfg = Config.from_file(args.load)
        print(cfg.to_json())
        return 0
    cfg = Config()
    print(cfg.to_json())
    return 0


def _cmd_bdd(args: argparse.Namespace) -> int:
    from .bdd import BDDManager
    func = _load_function(args)
    mgr = BDDManager(args.nvars)
    root = mgr.from_function(func)
    n_nodes = mgr.node_count(root)
    print(f"BDD: {args.nvars} vars, {n_nodes} nodes")
    if args.count:
        count = mgr.count_satisfying(root)
        print(f"  Satisfying assignments: {count}")
    if args.render:
        print()
        print(mgr.render_ascii(root))
    sop_cubes = mgr.to_sop(root)
    names = var_names(args.nvars)
    from .boolean import Implicant
    sop_str = " + ".join(Implicant(c).sop_term(names) for c in sop_cubes) if sop_cubes else "0"
    print(f"  SOP from BDD: {sop_str}")
    return 0


def _cmd_sensitivity(args: argparse.Namespace) -> int:
    from .analysis import all_sensitivities, boolean_difference
    func = _load_function(args)
    names = var_names(args.nvars)
    sens = all_sensitivities(func)
    print(f"Sensitivity analysis for {func.name} ({args.nvars} vars):")
    for i, name in enumerate(names):
        print(f"  {name}: {sens[i]:.4f}")
    print()
    print("Boolean differences:")
    for i, name in enumerate(names):
        if args.nvars > 1:
            diff = boolean_difference(func, i)
            print(f"  ∂f/∂{name}: minterms={sorted(diff.minterms)}")
    return 0


def _cmd_unate(args: argparse.Namespace) -> int:
    from .analysis import unate_profile
    func = _load_function(args)
    names = var_names(args.nvars)
    profile = unate_profile(func)
    print(f"Unate classification for {func.name} ({args.nvars} vars):")
    for i, name in enumerate(names):
        cls = profile[i]
        print(f"  {name}: {cls}")
    return 0


def _cmd_dc_optimize(args: argparse.Namespace) -> int:
    from .dc_optimize import assign_dontcares
    func = parse_minterms(args.minterms, args.nvars)
    result = assign_dontcares(func, minimizer=args.minimizer)
    print(f"Don't-care optimization ({args.minimizer}):")
    print(f"  Original SOP:  {result.original_sop}  (cost={result.original_cost})")
    print(f"  Optimized SOP: {result.optimized_sop} (cost={result.optimized_cost})")
    print(f"  Improvement:   {result.improvement} literals")
    if result.assignment:
        print(f"  Assignment:")
        for dc, val in sorted(result.assignment.items()):
            print(f"    minterm {dc} → {val}")
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    from .batch import BatchProcessor, batch_from_pla_file, batch_summary, batch_to_json
    entries = batch_from_pla_file(args.pla_file, minimizer=args.minimizer)
    summary = batch_summary(entries)
    if args.json:
        print(batch_to_json(entries))
    else:
        print(f"Batch: {summary.n_functions} functions, minimizer={args.minimizer}")
        print(f"  {'Name':<15} {'Vars':>4} {'Method':>15} {'Terms':>6} {'Lits':>5} {'Time(ms)':>10} {'OK':>4}")
        print("  " + "-" * 65)
        for e in entries:
            ok = "✓" if e.correct else "✗"
            print(f"  {e.name:<15} {e.n_vars:>4} {e.method:>15} {e.n_terms:>6} {e.n_literals:>5} {e.elapsed_ms:>10.2f} {ok:>4}")
        print()
        print(f"  Total: {summary.total_terms} terms, {summary.total_literals} literals, {summary.total_time_ms:.1f}ms")
        print(f"  All correct: {'Yes' if summary.all_correct else 'NO'}")
    return 0


def _cmd_html(args: argparse.Namespace) -> int:
    from .htmlviz import truth_table_html, kmap_html, full_report_html
    func = _load_function(args)
    if args.mode == "truth":
        html = truth_table_html(func)
    elif args.mode == "kmap":
        html = kmap_html(func)
    else:  # report
        qm = QuineMcCluskey(args.nvars)
        result = qm.minimize(func)
        html = full_report_html(func, result)
    if args.output:
        with open(args.output, "w") as fh:
            fh.write(html)
        print(f"HTML written to {args.output}")
    else:
        print(html)
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    func = _load_function(args)
    if args.result:
        from .serialize import result_to_json
        qm = QuineMcCluskey(args.nvars)
        result = qm.minimize(func)
        print(result_to_json(result))
    else:
        from .serialize import function_to_json
        print(function_to_json(func))
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    from . import __version__
    print(f"logicmin v{__version__}")
    print("Boolean logic minimization toolkit")
    print("  Quine-McCluskey, Petrick, Espresso, BDD, Analysis, PLA, HTML viz")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "minimize": _cmd_minimize,
        "espresso": _cmd_espresso,
        "multi": _cmd_multi,
        "factor": _cmd_factor,
        "truth": _cmd_truth,
        "verify": _cmd_verify,
        "info": _cmd_info,
        "pos": _cmd_pos,
        "kmap": _cmd_kmap,
        "benchmark": _cmd_benchmark,
        "config": _cmd_config,
        "bdd": _cmd_bdd,
        "sensitivity": _cmd_sensitivity,
        "unate": _cmd_unate,
        "dc-optimize": _cmd_dc_optimize,
        "batch": _cmd_batch,
        "html": _cmd_html,
        "export": _cmd_export,
        "version": _cmd_version,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    try:
        return handler(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())