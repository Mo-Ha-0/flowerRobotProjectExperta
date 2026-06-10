"""
run.py — نقطة التشغيل (المرحلة 6: A*)

يُشغّل محرك Experta مع استراتيجية A* (افتراضياً)
أو DFS (بالمعامل --dfs) ويطبع مسار الحل + شجرة البحث + الانتهاكات.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import FlowerExhibitionKE
from initial_state import PAVILIONS_SIMPLE, PAVILIONS


def bouquets_summary(bouquets: list) -> str:
    if not bouquets:
        return "empty"
    from collections import Counter

    c = Counter(bouquets)
    return ", ".join(f"{k[0]}/{k[1]}x{v}" for k, v in c.items())


def main():
    use_astar = "--dfs" not in sys.argv
    pavs = PAVILIONS_SIMPLE
    for arg in sys.argv[1:]:
        if arg == "--full":
            pavs = PAVILIONS

    engine = FlowerExhibitionKE(max_depth=10, use_astar=use_astar)
    engine.reset()
    engine.declare_facts(pavs)

    engine.run()

    # ── رأس التقرير ──────────────────────────────────────────
    strategy_name = "A* (F(n)=g+h)" if use_astar else "DFS (depth)"
    print("\n" + "█" * 65)
    print(f"  Search strategy: {strategy_name}")
    print(f"  Max depth: {engine.max_depth}")
    print("█" * 65)

    # ── Goal summary ──────────────────────────────────────────
    if engine.solution is None:
        print("\n  ✗ No goal state found within current depth limit")

    # ── Search tree ──────────────────────────────────────────
    print("\n" + "═" * 65)
    print("  Search tree")
    print("═" * 65)

    by_depth: dict[int, list] = {}
    for n in engine.all_nodes:
        by_depth.setdefault(n["depth"], []).append(n)

    for depth in sorted(by_depth):
        print(f"\n  ── depth {depth}  ({len(by_depth[depth])} nodes) ──")
        for n in by_depth[depth][:8]:
            bq_str = bouquets_summary(n.get("bouquets", []))
            print(
                f"    {n['action']:30s}  ({n['rx']},{n['ry']})"
                f"  cost={n['cost']}  [{bq_str}]"
            )
        if len(by_depth[depth]) > 8:
            print(f"    ... and {len(by_depth[depth]) - 8} more nodes")

    print(f"\n  Total nodes generated : {len(engine.all_nodes)}")
    print(f"  Visited states        : {len(engine.visited)}")

    # ── Violations log ───────────────────────────────────────
    if engine.violations_log:
        print(f"\n  Constraint violations: {len(engine.violations_log)}")
        for v in engine.violations_log:
            print(f"    • {v['rule']}: {v['detail']}")
    else:
        print(f"\n  Constraint violations: 0")


if __name__ == "__main__":
    main()
