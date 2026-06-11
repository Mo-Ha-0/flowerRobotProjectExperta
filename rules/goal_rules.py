"""
rules/goal_rules.py — قواعد الهدف وطباعة المسار (المرحلة 5)

قاعدتان:
  1. goal_rule     : تكتشف الحالة الهدف (salience=5)
     - الروبوت فارغ + كل الأجنحة استوفيت احتياجاتها
     - تخزّن مسار الحل وتُعلن GoalFound
  2. print_path_rule : تطبع مسار الحل (salience=1)
     - تُشغّل على GoalFound → تطبع المسار ← halt()
"""

from collections import Counter
from experta import Rule, MATCH, TEST

from facts import SearchNode, GoalFound
from utils import is_goal, reconstruct_path


def bouquets_summary(bouquets: list) -> str:
    if not bouquets:
        return "empty"
    c = Counter(bouquets)
    return ", ".join(f"{k[0]}/{k[1]}x{v}" for k, v in c.items())


class GoalRulesMixin:
    """
    قواعد اكتشاف الهدف وطباعة مسار الحل.
    سَلَّم (salience):
      - goal_rule      : 5   ← قبل التوسّع (0) لكن بعد القيود (10)
      - print_path_rule: 1   ← بعد الهدف لكن قبل التوسّع
    """

    # ════════════════════════════════════════════════════════
    # قاعدة اكتشاف الهدف (goal_rule)
    # ════════════════════════════════════════════════════════
    #
    # الشروط:
    #   ① bouquets == []  (الروبوت فارغ)
    #   ② جميع pavilion needs محقّقة (fulfilled_qty >= need_qty)
    #
    # التأثير:
    #   - يحفظ مسار الحل في self.solution
    #   - يُعلن GoalFound ← يُشغّل print_path_rule
    # ════════════════════════════════════════════════════════
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        TEST(lambda bq, pavs: is_goal(bq, pavs)),
        salience=5,
    )
    def goal_rule(self, nid, bq, pavs, cost, depth):
        if self.solution is not None:
            return

        path = reconstruct_path(self.all_nodes, nid)
        self.solution = {
            "node_id": nid,
            "cost"   : cost,
            "depth"  : depth,
            "path"   : path,
        }
        self.declare(GoalFound(node_id=nid, cost=cost, depth=depth))

    # ════════════════════════════════════════════════════════
    # قاعدة طباعة مسار الحل (print_path_rule)
    # ════════════════════════════════════════════════════════
    #
    # تُشغّل على GoalFound وتطبع المسار ثم توقف المحرك.
    # ════════════════════════════════════════════════════════
    @Rule(
        GoalFound(node_id=MATCH.nid, cost=MATCH.cost, depth=MATCH.depth),
        salience=1,
    )
    def print_path_rule(self, nid, cost, depth):
        print("\n" + "\u2550" * 65)
        print("  ★ Goal found! cost={}  depth={}".format(cost, depth))
        print("\u2550" * 65)
        print("  Solution path — operation sequence")
        print("\u2550" * 65)

        path = self.solution.get("path", [])
        for i, node in enumerate(path):
            bq_str = bouquets_summary(node.get("bouquets", []))
            icon = "\u2605" if i == 0 else ("\u25BC" if "unload" in node.get("action", "") else ("\u25B2" if "load" in node.get("action", "") else "\u2193"))
            print("  {} {:<30s}  ({},{})  cost={:>2d}  [{}]".format(
                icon,
                node.get("action", "?"),
                node.get("rx", 0),
                node.get("ry", 0),
                node.get("cost", 0),
                bq_str,
            ))

        print("\n  ✓ All pavilions received their full needs")

        self.halt()
