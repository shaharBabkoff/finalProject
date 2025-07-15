from __future__ import annotations
from fractions import Fraction
import matplotlib
matplotlib.use("TkAgg")         # חייב לבוא לפני import pyplot
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from be_alg.dcel import DCEL, HalfEdge
#from cgshop2025_pyutils.io.instance import read_instance   # רק אם רוצים show_problem


# ------------------------------------------------------------
#  A.  ציור ה-DCEL לאחר add_vertical_cuts + add_horizontal_cuts
# ------------------------------------------------------------
def show_slab_partition(dcel: DCEL, title: str = "Slab partition"):
    """
    מצייר את כל חצי-הקשתות:
        אנכיות  – כתום
        אופקיות – כחול
        אלכסוניות (גבול / אלכסון open-slab) – אפור
    """
    fig, ax = plt.subplots(figsize=(7, 7))

    def col(e: HalfEdge) -> str:
        if e.origin.x == e.twin.origin.x:
            return "darkorange"   # vertical
        if e.origin.y == e.twin.origin.y:
            return "royalblue"    # horizontal
        return "lightgray"        # everything else

    # מציירים רק half-edges "קדמיים" (כדי לא להכפיל קווים)
    for he in dcel.half_edges:
        if id(he) > id(he.twin):
            continue
        x1, y1 = float(he.origin.x), float(he.origin.y)
        x2, y2 = float(he.twin.origin.x), float(he.twin.origin.y)
        ax.plot([x1, x2], [y1, y2], color=col(he), linewidth=1)

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    plt.show()


# ------------------------------------------------------------
#  B.  ציור ה-בעיה בלבד  (points + boundary + constraints)
#      – שימושי להשוואה חזותית
# ------------------------------------------------------------
def show_problem(instance):
    fig, ax = plt.subplots()
    ax.scatter(instance.points_x, instance.points_y, color="black")

    # boundary
    for i in range(len(instance.region_boundary)):
        a = instance.region_boundary[i]
        b = instance.region_boundary[(i + 1) % len(instance.region_boundary)]
        ax.plot([instance.points_x[a], instance.points_x[b]],
                [instance.points_y[a], instance.points_y[b]],
                color="blue", linewidth=1.5)

    # constraints
    for c in instance.additional_constraints:
        ax.plot([instance.points_x[c[0]], instance.points_x[c[1]]],
                [instance.points_y[c[0]], instance.points_y[c[1]]],
                color="red")
    ax.set_aspect("equal")
    ax.set_title(instance.instance_uid)
    plt.show()


# ------------------------------------------------------------
#  C.  הדגמה מהירה – להריץ `python -m be_alg.viz_utils`
# ------------------------------------------------------------
if __name__ == "__main__":
    # מצולע דוגמה קטן
    pts = pts = [(0,0),(7,0),(7,3),(5,5),(3,5),(1,4),(0,2)]
    dcel = DCEL.from_polygon(boundary_indices=list(range(len(pts))),
                             points=pts)

    # חיתוך אנכי-אופקי
    from be_alg.slab_partition import slab_partition
    slab_partition(dcel)

    show_slab_partition(dcel, "Vertical + Horizontal cuts")