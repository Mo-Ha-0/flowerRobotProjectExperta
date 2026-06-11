GRID        = {"width": 5, "height": 5}
WAREHOUSE   = {"x": 3, "y": 2}
ROBOT_START = {"x": 3, "y": 1}

PAVILIONS = [
    {
        "id": "p1", "flower_type": "rose",
        "x": 2, "y": 4,
        "needs": {"red": 2, "pink": 1, "white": 1},
    },
    {
        "id": "p2", "flower_type": "tulip",
        "x": 4, "y": 3,
        "needs": {"red": 3, "yellow": 1},
    },
    {
        "id": "p3", "flower_type": "orchid",
        "x": 4, "y": 5,
        "needs": {"purple": 2, "pink": 1},
    },
    {
        "id": "p4", "flower_type": "goliat",
        "x": 5, "y": 2,
        "needs": {"gold": 2, "light_pink": 2},
    },
]

PAVILIONS_SIMPLE = [
    {
        "id": "p1", "flower_type": "rose",
        "x": 3, "y": 3,
        "needs": {"red": 2},
    },
]
