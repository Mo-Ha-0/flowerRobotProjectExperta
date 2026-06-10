"""
rules/move_rules.py — قواعد الحركة (المرحلة 2)

يحتوي على 4 قواعد لتحريك الروبوت:
  - move_right : X+1
  - move_left  : X-1
  - move_up    : Y-1
  - move_down  : Y+1

تكلفة كل حركة = 1

آلية العمل لكل قاعدة:
  ① تطابق عقدة SearchNode حالية + GridFact
  ② TEST يتحقق أن الموقع الجديد ضمن حدود الشبكة
  ③ عند الإطلاق: نتحقق من عدم تكرار الحالة وعدم تجاوز العمق
  ④ نُعلن SearchNode جديدة (الحالة التالية)
"""

from experta import Rule, MATCH, TEST

from facts import SearchNode, GridFact
from utils import state_hash, clone_pavilions, make_node_id


class MoveRulesMixin:
    """
    Mixin يُضاف إلى FlowerExhibitionKE ليمنحه قواعد الحركة الأربع.
    """

    # ── دالة مساعدة مشتركة للقواعد الأربع ────────────────────
    def _try_move(self, node_id: str, rx: int, ry: int,
                  new_rx: int, new_ry: int,
                  bouquets: list, pavilions: list,
                  max_load: int, cost: int, depth: int,
                  action: str):
        """
        تتحقق من صحة الحركة وتُعلن العقدة الجديدة.
        جميع القواعد الأربع تستدعي هذه الدالة لتجنب تكرار الكود.

        المتغيرات:
          node_id : معرّف العقدة الحالية (الأم)
          rx, ry  : موقع الروبوت الحالي
          new_rx, new_ry : الموقع الجديد بعد الحركة
          bouquets, pavilions : الحالة الحالية (تنتقل كما هي للعقدة الجديدة)
          max_load, cost, depth : بيانات التكلفة والعمق
          action  : اسم العملية (move_right, move_left, ...)
        """

        # التحقق من عدم تكرار الحالة الجديدة
        new_hash = state_hash(new_rx, new_ry, bouquets, pavilions)
        if new_hash in self.visited:
            return  # هذه الحالة زُرناها سابقاً → نتجاهلها

        # التحقق من عدم تجاوز حد العمق
        if depth + 1 > self.max_depth:
            return

        # تسجيل الحالة كمزارة
        self.visited.add(new_hash)

        # توليد معرّف فريد للعقدة الجديدة
        new_id = make_node_id(node_id, action)

        # نسخ الأجنحة (كل عقدة تحتاج نسختها المستقلة)
        new_pavs = clone_pavilions(pavilions)

        # إنشاء العقدة الجديدة
        new_node = SearchNode(
            node_id   = new_id,
            parent_id = node_id,
            action    = action,
            robot_x   = new_rx,
            robot_y   = new_ry,
            bouquets  = list(bouquets),
            pavilions = new_pavs,
            max_load  = max_load,
            cost      = cost + 1,   # كل حركة تكلف 1
            depth     = depth + 1,
        )

        # تسجيل العقدة في قائمة جميع العقد (للطباعة لاحقاً)
        self.all_nodes.append({
            "id"      : new_id,
            "parent"  : node_id,
            "action"  : action,
            "rx"      : new_rx,
            "ry"      : new_ry,
            "cost"    : cost + 1,
            "depth"   : depth + 1,
            "bouquets": list(bouquets),
        })

        # إعلان العقدة الجديدة — Experta سيُضيفها لذاكرة العمل
        # وهذا سيُشغّل القواعد تلقائياً عليها (توسّع في العمق)
        self.declare(new_node)

    # ════════════════════════════════════════════════════════════
    # القاعدة 1: move_right  →  X += 1
    # ════════════════════════════════════════════════════════════
    # الشرط: الموقع الجديد (rx+1) <= عرض الشبكة (gw)
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            robot_x   = MATCH.rx,
            robot_y   = MATCH.ry,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            max_load  = MATCH.ml,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        GridFact(width=MATCH.gw, height=MATCH.gh),
        TEST(lambda rx, gw: rx + 1 <= gw),  # ضمن الحدود اليمنى
    )
    def move_right(self, nid, rx, ry, bq, pavs, ml, cost, depth, gw, gh):
        """حركة لليمين: X يزيد بمقدار 1"""
        self._try_move(nid, rx, ry, rx + 1, ry,
                       bq, pavs, ml, cost, depth, "move_right")

    # ════════════════════════════════════════════════════════════
    # القاعدة 2: move_left  →  X -= 1
    # ════════════════════════════════════════════════════════════
    # الشرط: الموقع الجديد (rx-1) >= 1
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            robot_x   = MATCH.rx,
            robot_y   = MATCH.ry,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            max_load  = MATCH.ml,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        GridFact(width=MATCH.gw, height=MATCH.gh),
        TEST(lambda rx: rx - 1 >= 1),  # ضمن الحدود اليسرى
    )
    def move_left(self, nid, rx, ry, bq, pavs, ml, cost, depth, gw, gh):
        """حركة لليسار: X ينقص بمقدار 1"""
        self._try_move(nid, rx, ry, rx - 1, ry,
                       bq, pavs, ml, cost, depth, "move_left")

    # ════════════════════════════════════════════════════════════
    # القاعدة 3: move_up  →  Y -= 1
    # ════════════════════════════════════════════════════════════
    # الشرط: الموقع الجديد (ry-1) >= 1
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            robot_x   = MATCH.rx,
            robot_y   = MATCH.ry,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            max_load  = MATCH.ml,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        GridFact(width=MATCH.gw, height=MATCH.gh),
        TEST(lambda ry: ry - 1 >= 1),  # ضمن الحدود العليا
    )
    def move_up(self, nid, rx, ry, bq, pavs, ml, cost, depth, gw, gh):
        """حركة للأعلى: Y ينقص بمقدار 1"""
        self._try_move(nid, rx, ry, rx, ry - 1,
                       bq, pavs, ml, cost, depth, "move_up")

    # ════════════════════════════════════════════════════════════
    # القاعدة 4: move_down  →  Y += 1
    # ════════════════════════════════════════════════════════════
    # الشرط: الموقع الجديد (ry+1) <= ارتفاع الشبكة (gh)
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            robot_x   = MATCH.rx,
            robot_y   = MATCH.ry,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            max_load  = MATCH.ml,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        GridFact(width=MATCH.gw, height=MATCH.gh),
        TEST(lambda ry, gh: ry + 1 <= gh),  # ضمن الحدود السفلى
    )
    def move_down(self, nid, rx, ry, bq, pavs, ml, cost, depth, gw, gh):
        """حركة لأسفل: Y يزيد بمقدار 1"""
        self._try_move(nid, rx, ry, rx, ry + 1,
                       bq, pavs, ml, cost, depth, "move_down")
