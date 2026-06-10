"""
strategy.py — استراتيجية A* الذكية (المرحلة 6)

تطبّق مبدأ F(n) = g(n) + h(n) لترتيب أولويات العقد في جدول الأعمال (agenda):

  - القواعد ذات salience > 0 (القيود، الهدف، الطباعة) تُعطى أولوية مطلقة
    عبر مفتاح سالب كبير (-salience × 10000).
  - قواعد التوسّع (salience == 0) تُرتَّب حسب f(n) حيث:
      • g(n) = التكلفة الفعلية حتى العقدة
      • h(n) = التكلفة التقديرية المتبقية (مانهاتن لأقرب نقطة عمل)

الدالة التقديرية h(n) مقبولة (admissible):
  - h(n) ≤ التكلفة الحقيقية المتبقية دائماً
  - لأن المسافة لمانهاتن ≤ أي مسار حقيقي
"""

from functools import lru_cache

from experta import strategies


class AStarStrategy(strategies.Strategy):
    """
    استراتيجية A* — ترتيب العقد حسب f(n) = g(n) + h(n).

    آلية عمل agenda (قائمة مرتبة تصاعدياً، ويُسحب العنصر الأيمن أولاً):
      - القواعد الخاصة (salience>0): مفتاح = (salience × 10000,)
        ← قيمة كبيرة ← تُسحب أولاً
        الترتيب: قيد(10) > هدف(5) > طباعة(1)
      - قواعد التوسّع  (salience=0): مفتاح = (-(cost + h),)
        ← قيمة أصغر ← تُسحب لاحقاً
        الترتيب: f الأصغر ← يُسحب أولاً (لأن -f الأكبر)

    المعاملات:
      warehouse_x, warehouse_y : موقع المستودع (للحساب التقديري)
    """

    def __init__(self, warehouse_x: int, warehouse_y: int):
        self.warehouse_x = warehouse_x
        self.warehouse_y = warehouse_y

    # ══════════════════════════════════════════════════════════
    @lru_cache(maxsize=None)
    def get_key(self, activation) -> tuple:
        """
        تُعيد مفتاح الترتيب للـ activation:
          - salience>0 : (salience × 10000,)  ← أولوية عالية
          - salience=0 : (-(cost + h),)       ← أولوية حسب f(n)
        """
        # ── القواعد الخاصة (salience>0) ──
        if activation.rule.salience > 0:
            return (activation.rule.salience * 10000,)

        # ── قواعد التوسّع: ابحث عن SearchNode واحسب f(n) ──
        for fact in activation.facts:
            if type(fact).__name__ == "SearchNode":
                cost = fact["cost"]
                rx   = fact["robot_x"]
                ry   = fact["robot_y"]
                bq   = fact["bouquets"]
                pavs = fact["pavilions"]
                h = self._heuristic(rx, ry, bq, pavs)
                return (-(cost + h), activation.rule.__name__)

        return (0,)

    # ══════════════════════════════════════════════════════════
    def _heuristic(self, rx: int, ry: int,
                   bouquets: list, pavilions: list) -> int:
        """
        دالة الكلفة التقديرية h(n) — مقبولة (admissible):
          • إذا لم يبقَ شيء → 0
          • إذا كان الروبوت فارغاً → مسافة مانهاتن إلى المستودع
          • وإلّا → مسافة مانهاتن إلى أقرب جناح ما زال يحتاج
        """
        remaining = sum(
            max(0, req - done)
            for p in pavilions
            for req, done in p["needs"].values()
        )
        if remaining == 0:
            return 0

        if not bouquets:
            return abs(rx - self.warehouse_x) + abs(ry - self.warehouse_y)

        return min(
            (abs(rx - p["x"]) + abs(ry - p["y"]))
            for p in pavilions
            if any(done < req for req, done in p["needs"].values())
        )

    # ══════════════════════════════════════════════════════════
    def _update_agenda(self, agenda, added, removed):
        """
        تُحدّث قائمة التنشيطات عند إضافة أو إزالة الحقائق.
        التنفيذ مطابق تماماً لـ DepthStrategy._update_agenda
        لكنه يستخدم get_key المعدّلة أعلاه.
        """
        import bisect

        for act in removed:
            act.key = self.get_key(act)
            idx = bisect.bisect_left(agenda.activations, act)
            for offset in (0, 1, -1):
                try:
                    if agenda.activations[idx + offset] == act:
                        del agenda.activations[idx + offset]
                        break
                except IndexError:
                    continue

        for act in added:
            act.key = self.get_key(act)
            bisect.insort(agenda.activations, act)
