from experta import Fact, Field


class GridFact(Fact):
    """أبعاد شبكة المعرض"""
    width  = Field(int, mandatory=True)
    height = Field(int, mandatory=True)


class WarehouseFact(Fact):
    """موقع المستودع المركزي"""
    x = Field(int, mandatory=True)
    y = Field(int, mandatory=True)


class PavilionFact(Fact):
    """جناح في المعرض (للحالة الابتدائية فقط)"""
    pavilion_id = Field(str, mandatory=True)
    flower_type = Field(str, mandatory=True)
    x           = Field(int, mandatory=True)
    y           = Field(int, mandatory=True)
    needs       = Field(list, mandatory=True)


class SearchNode(Fact):
    """
    عقدة في شجرة البحث — الحالة الكاملة للنظام.
    تمثل موقع الروبوت + ما يحمله + حالة كل جناح.
    """
    node_id   = Field(str,  mandatory=True)
    parent_id = Field(str,  mandatory=True)
    action    = Field(str,  mandatory=True)
    robot_x   = Field(int,  mandatory=True)
    robot_y   = Field(int,  mandatory=True)
    bouquets  = Field(list, mandatory=True)
    pavilions = Field(list, mandatory=True)
    max_load  = Field(int,  mandatory=True)
    cost      = Field(int,  mandatory=True)
    depth     = Field(int,  mandatory=True)


class GoalFound(Fact):
    """
    تُعلَن عندما يكتشف goal_rule الحالةَ الهدف.
    تُشغّل print_path_rule لطباعة مسار الحل.
    """
    node_id = Field(str, mandatory=True)
    cost    = Field(int, mandatory=True)
    depth   = Field(int, mandatory=True)


class SearchDone(Fact):
    """
    تُعلَن من run.py بعد انتهاء engine.run().
    تُشغّل print_tree_rule لطباعة شجرة البحث.
    """
    total_nodes = Field(int, mandatory=True)
