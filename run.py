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
        return "فارغ"
    from collections import Counter

    c = Counter(bouquets)
    return ", ".join(f"{k[0]}/{k[1]}×{v}" for k, v in c.items())


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
    strategy_name = "A* (F(n)=g+h)" if use_astar else "DFS (عمق)"
    print("\n" + "█" * 65)
    print(f"  استراتيجية البحث: {strategy_name}")
    print(f"  العمق الأقصى: {engine.max_depth}")
    print("█" * 65)

    # ── ملخص الهدف ───────────────────────────────────────────
    if engine.solution is None:
        print("\n  ✗ لم يتم العثور على حالة هدف ضمن حد العمق الحالي")

    # ── شجرة البحث ───────────────────────────────────────────
    print("\n" + "═" * 65)
    print("  شجرة البحث")
    print("═" * 65)

    by_depth: dict[int, list] = {}
    for n in engine.all_nodes:
        by_depth.setdefault(n["depth"], []).append(n)

    for depth in sorted(by_depth):
        print(f"\n  ── العمق {depth}  ({len(by_depth[depth])} عقدة) ──")
        for n in by_depth[depth][:8]:  # حد 8 عقد لكل عمق للاختصار
            bq_str = bouquets_summary(n.get("bouquets", []))
            print(
                f"    {n['action']:30s}  ({n['rx']},{n['ry']})"
                f"  cost={n['cost']}  [{bq_str}]"
            )
        if len(by_depth[depth]) > 8:
            print(f"    ... و {len(by_depth[depth]) - 8} عقدة أخرى")

    print(f"\n  إجمالي العقد المولَّدة : {len(engine.all_nodes)}")
    print(f"  الحالات المزارة       : {len(engine.visited)}")

    # ── سجل الانتهاكات ───────────────────────────────────────
    if engine.violations_log:
        print(f"\n  انتهاكات القيود: {len(engine.violations_log)}")
        for v in engine.violations_log:
            print(f"    • {v['rule']}: {v['detail']}")
    else:
        print(f"\n  انتهاكات القيود: 0")


if __name__ == "__main__":
    main()
