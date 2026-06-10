"""
rules/constraint_rules.py — قواعد منع انتهاك القيود (المرحلة 4)

أربع قواعد (salience=10 > salience=0 لقواعد التوسيع):

  1. overload_violation      — تجاوز الحمولة القصوى → سحب العقدة
  2. invalid_load_violation  — تحميل نوعين بلونين مختلفين → سحب العقدة
  3. wrong_type_violation    — روبوت في جناح بغير نوعه → تسجيل فقط
  4. out_of_bounds_violation — موقع خارج الشبكة → سحب العقدة

آلية العمل:
  - القواعد 1، 2، 4 تَسحب العقدة المنتهِكة (retract) لأن الحالة مستحيلة
  - القاعدة 3 تُسجّل تحذيراً فقط — الروبوت قد يعبر الجناح دون تفريغ
"""

from experta import Rule, MATCH, TEST, AS

from facts import SearchNode, GridFact


# ══════════════════════════════════════════════════════════════
# دوال مساعدة للتحقق من القيود
# ══════════════════════════════════════════════════════════════

def _is_overloaded(bouquets: list, max_load: int) -> bool:
    """True إذا تجاوز عدد الباقات الحمولة القصوى"""
    return len(bouquets) > max_load


def _is_invalid_combination(bouquets: list) -> bool:
    """
    True إذا الحمولة تجمع نوعَين مختلفَين بلونَين مختلفَين —
    هذا هو القيد الممنوع صراحةً (خيار أ ولا خيار ب).
    """
    if len(bouquets) < 2:
        return False
    types  = {bt for bt, bc in bouquets}
    colors = {bc for bt, bc in bouquets}
    return len(types) > 1 and len(colors) > 1


def _wrong_type_at_pavilion(rx: int, ry: int,
                             bouquets: list, pavilions: list) -> bool:
    """
    True إذا:
      - الروبوت في موقع جناح
      - يحمل باقات
      - كل الباقات من نوع مختلف عن نوع هذا الجناح
    (لا يمكن تفريغ أي شيء — زيارة بلا فائدة)
    """
    if not bouquets:
        return False
    pav = next((p for p in pavilions if p["x"] == rx and p["y"] == ry), None)
    if pav is None:
        return False
    ft = pav["flower_type"]
    return all(bt != ft for bt, bc in bouquets)


def _is_out_of_bounds(rx: int, ry: int, gw: int, gh: int) -> bool:
    """True إذا موقع الروبوت خارج حدود الشبكة"""
    return not (1 <= rx <= gw and 1 <= ry <= gh)


# ══════════════════════════════════════════════════════════════
# الـ Mixin
# ══════════════════════════════════════════════════════════════

class ConstraintRulesMixin:
    """
    قواعد القيود — تُدمج في FlowerExhibitionKE.
    salience=10 يضمن انطلاقها قبل قواعد التوسيع (salience=0).
    """

    # ════════════════════════════════════════════════════════
    # القاعدة 1: overload_violation
    # ════════════════════════════════════════════════════════
    # الانتهاك: عدد الباقات > max_load
    # الإجراء : سحب العقدة + تسجيل الانتهاك
    @Rule(
        AS.node << SearchNode(
            node_id  = MATCH.nid,
            robot_x  = MATCH.rx,
            robot_y  = MATCH.ry,
            bouquets = MATCH.bq,
            max_load = MATCH.ml,
            cost     = MATCH.cost,
            depth    = MATCH.depth,
        ),
        TEST(lambda bq, ml: _is_overloaded(bq, ml)),
        salience = 10,
    )
    def overload_violation(self, node, nid, rx, ry, bq, ml, cost, depth):
        """تجاوز الحمولة القصوى — سحب العقدة المنتهكة"""
        self.violations_log.append({
            "rule"    : "overload_violation",
            "node_id" : nid,
            "position": (rx, ry),
            "bouquets": list(bq),
            "max_load": ml,
            "carried" : len(bq),
            "detail"  : f"carries {len(bq)} bouquets, max_load={ml}",
        })
        self.retract(node)  # إزالة العقدة من ذاكرة العمل

    # ════════════════════════════════════════════════════════
    # القاعدة 2: invalid_load_violation
    # ════════════════════════════════════════════════════════
    # الانتهاك: نوعان مختلفان + لونان مختلفان معاً
    # الإجراء : سحب العقدة + تسجيل الانتهاك
    @Rule(
        AS.node << SearchNode(
            node_id  = MATCH.nid,
            robot_x  = MATCH.rx,
            robot_y  = MATCH.ry,
            bouquets = MATCH.bq,
            cost     = MATCH.cost,
            depth    = MATCH.depth,
        ),
        TEST(lambda bq: _is_invalid_combination(bq)),
        salience = 10,
    )
    def invalid_load_violation(self, node, nid, rx, ry, bq, cost, depth):
        """تحميل غير قانوني (نوعان مختلفان + لونان مختلفان)"""
        types  = {bt for bt, bc in bq}
        colors = {bc for bt, bc in bq}
        self.violations_log.append({
            "rule"    : "invalid_load_violation",
            "node_id" : nid,
            "position": (rx, ry),
            "bouquets": list(bq),
            "types"   : types,
            "colors"  : colors,
            "detail"  : f"types={types} AND colors={colors} together — forbidden",
        })
        self.retract(node)

    # ════════════════════════════════════════════════════════
    # القاعدة 3: wrong_type_violation
    # ════════════════════════════════════════════════════════
    # الانتهاك: روبوت في جناح ويحمل فقط نوعاً مختلفاً
    # الإجراء : تسجيل تحذير فقط (بدون سحب)
    #   — قد يكون الروبوت عابراً في طريقه إلى جناح آخر
    @Rule(
        SearchNode(
            node_id   = MATCH.nid,
            robot_x   = MATCH.rx,
            robot_y   = MATCH.ry,
            bouquets  = MATCH.bq,
            pavilions = MATCH.pavs,
            cost      = MATCH.cost,
            depth     = MATCH.depth,
        ),
        TEST(lambda bq: len(bq) > 0),
        TEST(lambda rx, ry, bq, pavs: _wrong_type_at_pavilion(rx, ry, bq, pavs)),
        salience = 10,
    )
    def wrong_type_violation(self, nid, rx, ry, bq, pavs, cost, depth):
        """الروبوت في جناح لكن يحمل نوعاً لا يناسبه — تحذير فقط"""
        pav = next((p for p in pavs if p["x"] == rx and p["y"] == ry), None)
        pav_type   = pav["flower_type"] if pav else "?"
        carried    = {bt for bt, bc in bq}
        self.violations_log.append({
            "rule"          : "wrong_type_violation",
            "node_id"       : nid,
            "position"      : (rx, ry),
            "bouquets"      : list(bq),
            "pav_type"      : pav_type,
            "carried_types" : carried,
            "detail"        : f"at pavilion '{pav_type}' but carrying {carried}",
        })
        # لا retract — الروبوت يمر فقط

    # ════════════════════════════════════════════════════════
    # القاعدة 4: out_of_bounds_violation
    # ════════════════════════════════════════════════════════
    # الانتهاك: موقع الروبوت خارج الشبكة
    # الإجراء : سحب العقدة + تسجيل الانتهاك
    @Rule(
        AS.node << SearchNode(
            node_id = MATCH.nid,
            robot_x = MATCH.rx,
            robot_y = MATCH.ry,
            cost    = MATCH.cost,
            depth   = MATCH.depth,
        ),
        GridFact(width=MATCH.gw, height=MATCH.gh),
        TEST(lambda rx, ry, gw, gh: _is_out_of_bounds(rx, ry, gw, gh)),
        salience = 10,
    )
    def out_of_bounds_violation(self, node, nid, rx, ry, gw, gh, cost, depth):
        """موقع خارج الشبكة — سحب العقدة"""
        self.violations_log.append({
            "rule"    : "out_of_bounds_violation",
            "node_id" : nid,
            "position": (rx, ry),
            "grid"    : (gw, gh),
            "detail"  : f"({rx},{ry}) out of grid {gw}x{gh}",
        })
        self.retract(node)
