import json
import hashlib
import copy
from typing import Callable


def state_hash(rx: int, ry: int,
               bouquets: list, pavilions: list) -> str:
    bq_key = tuple(sorted(bouquets))
    pav_key = tuple(
        (p["id"],
         tuple(sorted((c, v[0] - v[1]) for c, v in p["needs"].items())))
        for p in sorted(pavilions, key=lambda p: p["id"])
    )
    raw = json.dumps({"rx": rx, "ry": ry, "bq": bq_key, "pav": pav_key},
                     sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def build_pavilions(pavilions_raw: list) -> list:
    result = []
    for pav in pavilions_raw:
        result.append({
            "id":          pav["id"],
            "flower_type": pav["flower_type"],
            "x":           pav["x"],
            "y":           pav["y"],
            "needs":       {color: [qty, 0] for color, qty in pav["needs"].items()},
        })
    return result


def compute_max_load(pavilions_raw: list) -> int:
    return max(
        sum(qty for qty in pav["needs"].values())
        for pav in pavilions_raw
    )


def clone_pavilions(pavilions: list) -> list:
    """نسخة عميقة من قائمة الأجنحة — كل عقدة تحتاج نسختها المستقلة"""
    return copy.deepcopy(pavilions)


_counter = [0]  # عداد عام لتوليد معرّفات فريدة للعقد


def reset_counter():
    """إعادة العداد إلى الصفر (يُستدعى عند إنشاء محرك جديد)"""
    _counter[0] = 0


def make_node_id(parent_id: str, action: str) -> str:
    """
    توليد معرّف فريد لعقدة جديدة.
    مثال: parent="root", action="move_right" → "root→move_right#1"
    """
    _counter[0] += 1
    return f"{parent_id}→{action}#{_counter[0]}"


def is_goal(bouquets: list, pavilions: list) -> bool:
    """
    التحقق من الحالة الهدف:
      1. الروبوت لا يحمل أي باقات (bouquets فارغة)
      2. جميع الأجنحة استلمت احتياجاتها كاملة (needs[color][0] <= needs[color][1])
    """
    if bouquets:
        return False
    for pav in pavilions:
        for need_qty, fulfilled_qty in pav["needs"].values():
            if fulfilled_qty < need_qty:
                return False
    return True


def reconstruct_path(all_nodes: list, goal_id: str) -> list:
    """
    إعادة بناء مسار الحل من العقدة الهدف وصولاً إلى الجذر.
    تعيد قائمة بالعقد بالترتيب من الجذر ← الهدف.
    """
    node_map = {n["id"]: n for n in all_nodes}
    path = []
    current = goal_id
    while current is not None:
        node = node_map.get(current)
        if node is None:
            break
        path.append(node)
        parent = node.get("parent")
        if parent is None or parent == current:
            break
        current = parent
    path.reverse()
    return path
