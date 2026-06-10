"""
engine.py — نظام الخبير الرئيسي

يجمع جميع Mixins القواعد عبر الوراثة المتعددة:
  - MoveRulesMixin       : قواعد الحركة (المرحلة 2)
  - LoadUnloadRulesMixin : قواعد التحميل والتفريغ (المرحلة 3) — لاحقاً
  - ConstraintRulesMixin : قواعد منع انتهاك القيود (المرحلة 4) — لاحقاً
  - GoalRulesMixin       : قواعد الهدف والطباعة (المرحلة 5) — لاحقاً
"""

from experta import KnowledgeEngine

from facts import GridFact, WarehouseFact, SearchNode
from initial_state import GRID, WAREHOUSE, ROBOT_START
from utils import build_pavilions, compute_max_load, reset_counter, state_hash
from rules import (
    MoveRulesMixin,
    LoadUnloadRulesMixin,
    ConstraintRulesMixin,
    GoalRulesMixin,
)
from strategy import AStarStrategy


class FlowerExhibitionKE(
    MoveRulesMixin,           # قواعد الحركة (المرحلة 2)
    LoadUnloadRulesMixin,     # قواعد التحميل والتفريغ (المرحلة 3)
    ConstraintRulesMixin,     # قواعد منع انتهاك القيود (المرحلة 4)
    GoalRulesMixin,           # قواعد اكتشاف الهدف وطباعة المسار (المرحلة 5)
    KnowledgeEngine,          # محرك Experta الأساسي — يجب أن يكون الأخير
):
    """
    نظام الخبير — معرض الورود الذكي.

    السمات (attributes):
      max_depth  : int  — حد عمق البحث
      visited    : set  — مجموعة هاشات الحالات المزارة (لمنع التكرار)
    """

    def __init__(self, max_depth: int = 30, use_astar: bool = True):
        super().__init__()
        # استبدال الإستراتيجية الافتراضية (DepthStrategy) بـ AStarStrategy
        if use_astar:
            self.strategy = AStarStrategy(WAREHOUSE["x"], WAREHOUSE["y"])
        self.use_astar      = use_astar  # للطباعة التوضيحية
        self.max_depth      = max_depth   # حد عمق البحث
        self.visited        = set()       # حالات سبق زيارتها
        self.all_nodes      = []          # جميع العقد المولَّدة (للطباعة)
        self.violations_log = []          # سجل انتهاكات القيود
        self.solution       = None        # معلومات مسار الحل (تملؤه goal_rule)
        reset_counter()                   # إعادة عداد معرّفات العقد

    def declare_facts(self, pavilions_raw: list):
        """
        تُعلن الحقائق الأولية في ذاكرة العمل:
          - GridFact       : أبعاد الشبكة
          - WarehouseFact  : موقع المستودع
          - SearchNode     : العقدة الجذر (الحالة الابتدائية)

        pavilions_raw : بيانات الأجنحة الخام من initial_state.py
        """

        # تحويل بيانات الأجنحة من صيغة NeedItem إلى صيغة dict
        pavilions = build_pavilions(pavilions_raw)

        # حساب الحمولة القصوى (أكبر مجموع باقات في جناح واحد)
        max_load = compute_max_load(pavilions_raw)

        # موقع الروبوت الابتدائي
        rx, ry = ROBOT_START["x"], ROBOT_START["y"]

        # ── إعلان الحقائق الثابتة (البيئة) ──────────────────
        self.declare(GridFact(width=GRID["width"], height=GRID["height"]))
        self.declare(WarehouseFact(x=WAREHOUSE["x"], y=WAREHOUSE["y"]))

        # ── تسجيل الحالة الجذر في visited ──────────────────
        # نضيف هاش الحالة الابتدائية لمنع توليدها مجدداً
        root_hash = state_hash(rx, ry, [], pavilions)
        self.visited.add(root_hash)

        # ── إعلان العقدة الجذر ──────────────────────────────
        # هذه العقدة ستنشّط قواعد الحركة فور إعلانها
        root = SearchNode(
            node_id="root", parent_id="root", action="start",
            robot_x=rx, robot_y=ry, bouquets=[], pavilions=pavilions,
            max_load=max_load, cost=0, depth=0,
        )
        self.all_nodes.append({
            "id"      : "root",
            "parent"  : "root",
            "action"  : "start",
            "rx"      : rx,
            "ry"      : ry,
            "cost"    : 0,
            "depth"   : 0,
            "bouquets": [],
        })
        self.declare(root)
