"""
rules/load_unload_rules.py — قواعد التحميل والتفريغ (المرحلة 3)

قاعدة التحميل (load_rule):
  - الروبوت في المستودع + فارغ +存在 احتياجات متبقية
  - يولّد كل خيارات التحميل الممكنة (خيار أ: نفس اللون، خيار ب: نفس النوع)
  - لكل خيار: يُعلن عقدة جديدة (تكلفة +1)

قاعدة التفريغ (unload_rule):
  - الروبوت في جناح + يحمل باقات مناسبة
  - يُسلّم كل ما يمكن تسليمه دفعة واحدة
  - يُعلن عقدة جديدة (تكلفة +1)
"""

from collections import Counter, defaultdict
from itertools import product
from experta import Rule, MATCH, TEST

from facts import SearchNode, WarehouseFact
from utils import state_hash, clone_pavilions, make_node_id


# ══════════════════════════════════════════════════════════════
# دوال مساعدة للتحميل
# ══════════════════════════════════════════════════════════════

def _build_remaining(pavilions: list) -> tuple:
    """
    تبني خريطتي الاحتياجات المتبقية:
      by_type  : {نوع_الورد : {لون : الكمية_المتبقية}}
      by_color : {اللون     : {نوع_الورد : الكمية_المتبقية}}

    مثال للجناح p1 (جوري) يحتاج red:2, pink:1:
      by_type  = {"rose": {"red": 2, "pink": 1}}
      by_color = {"red": {"rose": 2}, "pink": {"rose": 1}}
    """
    by_type  = defaultdict(dict)
    by_color = defaultdict(dict)
    for pav in pavilions:
        ft = pav["flower_type"]
        for color, (req, done) in pav["needs"].items():
            rem = req - done          # ما تبقّى من هذا اللون
            if rem > 0:
                by_type[ft][color]  = by_type[ft].get(color, 0)  + rem
                by_color[color][ft] = by_color[color].get(ft, 0) + rem
    return dict(by_type), dict(by_color)


def is_valid_load(bouquets: list) -> bool:
    """
    تتحقق من合法性 التحميل حسب القيدين:
      - خيار أ: كل الباقات من نفس اللون (بأنواع مختلفة مسموحة)
      - خيار ب: كل الباقات من نفس النوع (بألوان مختلفة مسموحة)
      - ممنوع: نوعان مختلفان + لونان مختلفان معاً
    """
    if not bouquets:
        return False
    types  = {bt for bt, bc in bouquets}
    colors = {bc for bt, bc in bouquets}
    return len(types) == 1 or len(colors) == 1


def generate_load_options(pavilions: list, max_load: int) -> list:
    """
    تولّد جميع خيارات التحميل الممكنة مع مراعاة:
      - خيار أ: نفس اللون + أنواع مختلفة
      - خيار ب: نفس النوع + ألوان مختلفة
      - max_load: عدد الباقات ≤ الحمولة القصوى
      - الفائدة: كل باقة محمولة مطلوبة من جناح ما
    """
    by_type, by_color = _build_remaining(pavilions)
    seen    = set()
    options = []

    def _add(bq: list):
        """تضيف خيار تحميل إذا كان صحيحاً وغير مكرر"""
        if not bq:
            return
        if len(bq) > max_load:
            return
        if not is_valid_load(bq):
            return
        key = tuple(sorted(bq))
        if key not in seen:
            seen.add(key)
            options.append(list(key))

    def _expand_limited(items: list) -> list:
        """
        تولّد كل التراكيب الممكنة ضمن الحمولة القصوى.
        items: [(flower_type, color, remaining_qty), ...]
        """
        ranges = [range(qty + 1) for _, _, qty in items]
        for counts in product(*ranges):
            if not any(counts) or sum(counts) > max_load:
                continue
            bq = []
            for (ft, color, _qty), count in zip(items, counts):
                bq.extend([(ft, color)] * count)
            _add(bq)

    # ── خيار ب: نفس النوع (نوع ورد واحد + ألوان مختلفة) ──────
    for ft, color_needs in by_type.items():
        if not color_needs:
            continue
        _expand_limited([
            (ft, color, qty)
            for color, qty in color_needs.items()
        ])

    # ── خيار أ: نفس اللون (لون واحد + أنواع مختلفة) ──────────
    for color, type_needs in by_color.items():
        if len(type_needs) < 2:
            continue          # يحتاج نوعين مختلفين على الأقل
        _expand_limited([
            (ft, color, qty)
            for ft, qty in type_needs.items()
        ])

    return options


# ══════════════════════════════════════════════════════════════
# دوال مساعدة للتفريغ
# ══════════════════════════════════════════════════════════════

def find_pavilion_at(rx: int, ry: int, pavilions: list):
    """تُعيد الجناح الموجود في الموقع (rx, ry) أو None إن لم يوجد"""
    for pav in pavilions:
        if pav["x"] == rx and pav["y"] == ry:
            return pav
    return None


def compute_unload(bouquets: list, pav: dict) -> tuple:
    """
    تحسب ما يمكن تسليمه لهذا الجناح في زيارة واحدة.

    لكل لون من ألوان الجناح:
      - إذا كان الروبوت يحمل ≥ ما تبقّى → يسلّم الكمية المتبقية
      - الباقي يبقى مع الروبوت

    تُعيد:
      to_remove    : list[tuple] — الباقات التي تُحذف من الروبوت
      updated_pav  : dict — بيانات الجناح المحدَّثة (أو None)
    """
    ft      = pav["flower_type"]
    # كم باقة من هذا النوع يحملها الروبوت لكل لون
    carried = Counter(bc for bt, bc in bouquets if bt == ft)

    if not carried:
        return [], None

    to_remove     = []
    updated_needs = {c: [v[0], v[1]] for c, v in pav["needs"].items()}
    delivered_any = False

    for color, count in carried.items():
        if color not in updated_needs:
            continue
        req, done = updated_needs[color]
        remaining = req - done
        if remaining > 0 and count >= remaining:
            # يسلّم بالضبط الكمية المتبقية
            to_remove.extend([(ft, color)] * remaining)
            updated_needs[color][1] = req   # اكتمل
            delivered_any = True

    if not delivered_any:
        return [], None

    updated_pav = {
        "id":          pav["id"],
        "flower_type": pav["flower_type"],
        "x":           pav["x"],
        "y":           pav["y"],
        "needs":       updated_needs,
    }
    return to_remove, updated_pav


def can_unload_at(rx: int, ry: int, bouquets: list, pavilions: list) -> bool:
    """True إذا كان يمكن تفريغ شيء في هذا الموقع"""
    pav = find_pavilion_at(rx, ry, pavilions)
    if pav is None:
        return False
    to_remove, _ = compute_unload(bouquets, pav)
    return len(to_remove) > 0


def _apply_unload(bouquets: list, to_remove: list,
                  pavilions: list, updated_pav: dict) -> tuple:
    """
    تطبّق التفريغ وتُعيد:
      new_bouquets  : الباقات المتبقية مع الروبوت
      new_pavilions : قائمة الأجنحة المحدَّثة
    """
    new_bq = list(bouquets)
    for item in to_remove:
        new_bq.remove(item)

    new_pavs = []
    for p in pavilions:
        if p["id"] == updated_pav["id"]:
            new_pavs.append(updated_pav)
        else:
            new_pavs.append({
                "id":          p["id"],
                "flower_type": p["flower_type"],
                "x":           p["x"],
                "y":           p["y"],
                "needs":       {c: [v[0], v[1]] for c, v in p["needs"].items()},
            })
    return new_bq, new_pavs


# ══════════════════════════════════════════════════════════════
# الـ Mixin
# ══════════════════════════════════════════════════════════════

class LoadUnloadRulesMixin:
    """
    قواعد التحميل والتفريغ — تُدمج في FlowerExhibitionKE.
    """

    # ════════════════════════════════════════════════════════
    # قاعدة التحميل (load_rule)
    # ════════════════════════════════════════════════════════
    #
    # شروط الإطلاق (كلها في TEST):
    #   ① الروبوت في موقع المستودع (rx == wx, ry == wy)
    #   ② الروبوت فارغ (bouquets == [])
    #   ③ لا تزال هناك احتياجات لم تُسلّم
    #
    # التأثير:
    #   لكل خيار تحميل صحيح ← نُعلن عقدة جديدة
    #   التكلفة +1  |  العمق +1
    # ════════════════════════════════════════════════════════
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
        WarehouseFact(x=MATCH.wx, y=MATCH.wy),
        TEST(lambda rx, ry, wx, wy: rx == wx and ry == wy),   # ① في المستودع
        TEST(lambda bq: len(bq) == 0),                         # ② فارغ
        TEST(lambda pavs: any(                                  # ③ needs remain
            v[0] > v[1]
            for p in pavs
            for v in p["needs"].values()
        )),
    )
    def load_rule(self, nid, rx, ry, bq, pavs, ml, cost, depth, wx, wy):
        """
        تُولّد كل خيارات التحميل الممكنة وتُعلن عقدة لكل خيار.
        """
        # توليد جميع الخيارات الصالحة
        options = generate_load_options(pavs, ml)

        for opt_bq in options:
            # التحقق من عدم تجاوز العمق
            if depth + 1 > self.max_depth:
                break

            # التحقق من عدم تكرار الحالة
            h = state_hash(rx, ry, opt_bq, pavs)
            if h in self.visited:
                continue
            self.visited.add(h)

            # إنشاء معرّف للعقدة الجديدة
            new_id = make_node_id(nid, "load")

            # تحديد اسم العملية: خيار أ (نفس اللون) أم ب (نفس النوع)
            types_loaded  = {bt for bt, bc in opt_bq}
            colors_loaded = {bc for bt, bc in opt_bq}
            if len(types_loaded) == 1:
                label = f"load_B({next(iter(types_loaded))})"     # خيار ب: نوع واحد
            else:
                label = f"load_A({next(iter(colors_loaded))})"    # خيار أ: لون واحد

            # إنشاء وإعلان العقدة الجديدة
            new_node = SearchNode(
                node_id   = new_id,
                parent_id = nid,
                action    = label,
                robot_x   = rx,
                robot_y   = ry,
                bouquets  = opt_bq,
                pavilions = clone_pavilions(pavs),
                max_load  = ml,
                cost      = cost + 1,
                depth     = depth + 1,
            )
            self.all_nodes.append({
                "id"      : new_id,
                "parent"  : nid,
                "action"  : label,
                "rx"      : rx,
                "ry"      : ry,
                "cost"    : cost + 1,
                "depth"   : depth + 1,
                "bouquets": opt_bq,
            })
            self.declare(new_node)

    # ════════════════════════════════════════════════════════
    # قاعدة التفريغ (unload_rule)
    # ════════════════════════════════════════════════════════
    #
    # شروط الإطلاق:
    #   ① الروبوت يحمل باقات (bouquets != [])
    #   ② الروبوت في موقع جناح
    #   ③ يمكن تسليم شيء (count >= remaining for some color)
    #
    # التأثير:
    #   نسلّم كل الألوان القابلة دفعة واحدة
    #   التكلفة +1  |  العمق +1
    # ════════════════════════════════════════════════════════
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
        TEST(lambda bq: len(bq) > 0),                                    # ① يحمل
        TEST(lambda rx, ry, bq, pavs: can_unload_at(rx, ry, bq, pavs)),  # ②③
    )
    def unload_rule(self, nid, rx, ry, bq, pavs, ml, cost, depth):
        """
        تُسلّم ما يمكن تسليمه في هذا الجناح وتُعلن عقدة جديدة.
        """
        if depth + 1 > self.max_depth:
            return

        # البحث عن الجناح في هذا الموقع
        pav = find_pavilion_at(rx, ry, pavs)

        # حساب ما يمكن تسليمه
        to_remove, updated_pav = compute_unload(bq, pav)

        # تطبيق التفريغ
        new_bq, new_pavs = _apply_unload(bq, to_remove, pavs, updated_pav)

        # التحقق من عدم التكرار
        h = state_hash(rx, ry, new_bq, new_pavs)
        if h in self.visited:
            return
        self.visited.add(h)

        # إنشاء معرّف للعقدة الجديدة
        new_id = make_node_id(nid, "unload")

        # تحديد اسم العملية (الألوان التي تم تسليمها)
        colors_done = sorted({bc for _, bc in to_remove})
        action_label = f"unload@{pav['id']}[{','.join(colors_done)}]"

        # إنشاء وإعلان العقدة الجديدة
        new_node = SearchNode(
            node_id   = new_id,
            parent_id = nid,
            action    = action_label,
            robot_x   = rx,
            robot_y   = ry,
            bouquets  = new_bq,
            pavilions = new_pavs,
            max_load  = ml,
            cost      = cost + 1,
            depth     = depth + 1,
        )
        self.all_nodes.append({
            "id"      : new_id,
            "parent"  : nid,
            "action"  : action_label,
            "rx"      : rx,
            "ry"      : ry,
            "cost"    : cost + 1,
            "depth"   : depth + 1,
            "bouquets": new_bq,
        })
        self.declare(new_node)
