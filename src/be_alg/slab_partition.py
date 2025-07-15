# ------------------------------------------------------------
#  src/be_alg/slab_partition.py
#  Bern–Eppstein 1991 — Stage 3 : Slab Partition
# ------------------------------------------------------------
from __future__ import annotations

from fractions import Fraction
from typing import List, Tuple, Iterable, Optional
from collections import Counter
from be_alg.dcel import DCEL, Face, HalfEdge, Vertex
from be_alg.face_types import FaceType
from be_alg.viz_utils import show_slab_partition



# ------------------------------------------------------------
#  3-A : vertical slab lines  –  FINAL FIX
# ------------------------------------------------------------
# ------------------------------------------------------------------
#  3-A : Vertical slab lines  (FINAL VERSION)
# ------------------------------------------------------------------
def add_vertical_cuts(dcel: DCEL) -> None:
    """
    לכל ערך x שקיים בקודקודי המצולע:
        • מאתרים את כל נקודות-החיתוך (קודקודים קיימים / סטיינר חדשים)
          שבהן הקו x = const פוגש צלעות פנימיות של המצולע.
        • ממיינים לפי y ומחברים כל זוג עוקב (תחתון-עליון) באלכסון
          אנכי, אבל *רק אם* הם באותה פאה ועדיין לא מחוברים בקו אנכי.
    """
    xs = sorted({v.x for v in dcel.vertices})

    for x0 in xs:
        # 1. אסוף / צור כל Hit על הקו האנכי הזה
        hits: list[Vertex] = []
        for he in list(dcel.half_edges):
            if he.face is dcel.outer_face:                # דלג על החוץ
                continue

            x1, x2 = he.origin.x, he.twin.origin.x
            if min(x1, x2) < x0 < max(x1, x2):           # חוצה צלע
                t  = (x0 - x1) / (x2 - x1)
                y0 = he.origin.y + t * (he.twin.origin.y - he.origin.y)
                hits.append(dcel.split_edge(he, x0, y0))
            elif x1 == x0:                               # פוגע בקודקוד קיים
                hits.append(he.origin)

        if len(hits) < 2:
            continue

        # 2. מיין לפי y וחבר זוגות
        hits.sort(key=lambda v: v.y)
        i = 0
        while i + 1 < len(hits):
            v_low, v_up = hits[i], hits[i + 1]

            # 2a. חייבים להיות באותה פאה פנימית
            face = _common_face(v_low, v_up)
            if face is None:
                i += 1          # לא באותה פאה → עבור לקודקוד הבא
                continue

            # 2b. אם כבר מחוברים בקו אנכי קיים, דלג
            edge_from_low = _find_edge_from_vertex_in_face(v_low, face)
            if (_is_vertical(edge_from_low) and
                (edge_from_low.origin is v_up or edge_from_low.twin.origin is v_up)):
                i += 2
                continue

            # 2c. מוסיף אלכסון אנכי חדש
            add_diagonal(dcel, face, v_low, v_up)
            i += 2


# ------------------------------------------------------------
#  סביב הקודקוד – קבע אילו פאות צמודות אליו
# ------------------------------------------------------------
def _faces_incident(v: Vertex) -> set[Face]:
    faces, visited = set(), set()
    he0 = v.incident
    he  = he0
    while he and he not in visited:
        visited.add(he)
        if he.face is not None:
            faces.add(he.face)
        he = he.twin.next
    return faces


def _common_face(v1: Vertex, v2: Vertex) -> Optional[Face]:
    faces1 = _faces_incident(v1)
    for f in _faces_incident(v2):
        if f in faces1 and f.outer is not None:   # מתעלמים מהפאה החיצונית
            return f
    return None


def _is_vertical(e: HalfEdge) -> bool:
    return e.origin.x == e.twin.origin.x


# ------------------------------------------------------------
# helper – add one vertical diagonal  (קצר ובטוח)
# ------------------------------------------------------------
def _add_vertical_diagonal(dcel: DCEL, v_low: Vertex, v_up: Vertex) -> None:
    face = _find_edge_from_vertex_in_face(v_low, v_low.incident.face).face
    add_diagonal(dcel, face, v_low, v_up)

# ------------------------------------------------------------
#  3-B  :  horizontal slab lines  –  FINAL
# ------------------------------------------------------------
def add_horizontal_cuts(dcel: DCEL) -> None:
    """
    לכל קודקוד (מקורי או סטיינר) בפאות הפנימיות:
        • יורה קרן אופקית ימינה עד למפגש הראשון עם קטע אנכי
          השייך *לאותה* פאה.
        • מחלק את הקטע האנכי בנקודת הפגישה.
    """
    made = 0
    # סורקים ישירות את רשימת הקודקודים – כך לא מפספסים גם קודקודים
    # שנוצרו ע״י split_edge ואינם origin של half-edge בפאה הנוכחית.
    for v in dcel.vertices:
        if v.incident is None:
            continue
        f = v.incident.face
        if f is None or f is dcel.outer_face:
            continue            # קודקוד על גבול חיצוני – לא חותכים

        target = _first_vertical_hit_to_right(f, v.x, v.y)
        if target:
            dcel.split_edge(target, target.origin.x, v.y)
            made += 1
    # אפשר להדפיס/לוג אם רוצים:  print("horizontal cuts:", made)


def _first_vertical_hit_to_right(face: Face,
                                 x0: Fraction, y0: Fraction
                                 ) -> Optional[HalfEdge]:
    """
    מחזירה את חצי-הקשת האנכית הקרובה ביותר מימין (x > x0)
    כך שהגובה y0 נמצא בתחומה.  אם אין – מחזירה None.
    """
    best_dx: Optional[Fraction] = None
    best_he: Optional[HalfEdge] = None

    for he in iterate_half_edges(face.outer):
        if not _is_vertical(he):
            continue

        x_vert = he.origin.x                          # כי אנכי: x קבוע
        if x_vert <= x0:                              # כולל  ==  (על הקו עצמו)
            continue

        y_min = min(he.origin.y, he.twin.origin.y)
        y_max = max(he.origin.y, he.twin.origin.y)
        if not (y_min <= y0 <= y_max):
            continue                                  # לא מגיע לגובה y0

        dx = x_vert - x0
        if best_dx is None or dx < best_dx:
            best_dx, best_he = dx, he

    return best_he



def _first_vertical_hit_to_right(face: Face,
                                 x0: Fraction, y0: Fraction) -> Optional[HalfEdge]:
    """Return the closest vertical half-edge to the right at height y0."""
    best_dx: Optional[Fraction] = None
    best_he: Optional[HalfEdge] = None
    for he in iterate_half_edges(face.outer):
        if he.origin.x == he.twin.origin.x:         # vertical
            x_vert = he.origin.x
            if x_vert > x0:
                y_min = min(he.origin.y, he.twin.origin.y)
                y_max = max(he.origin.y, he.twin.origin.y)
                if y_min <= y0 <= y_max:
                    dx = x_vert - x0
                    if best_dx is None or dx < best_dx:
                        best_dx, best_he = dx, he
    return best_he

# ------------------------------------------------------------
#  3-C  :  classify faces  (Lemma 5)
# ------------------------------------------------------------
def classify_face(face: Face) -> FaceType:
    edges = list(iterate_half_edges(face.outer))
    vert  = [e for e in edges if _is_vertical(e)]
    horz  = [e for e in edges if _is_horizontal(e)]

    if len(edges) == 4 and len(vert) == 2 and len(horz) == 2:
        return FaceType.RECTANGLE
    if len(edges) == 3 and len(vert) == 1 and len(horz) == 1:
        return FaceType.RIGHT_TRI
    if len(vert) == 2:
        y1 = sorted([vert[0].origin.y, vert[0].twin.origin.y])
        y2 = sorted([vert[1].origin.y, vert[1].twin.origin.y])
        if max(y1[0], y2[0]) <= min(y1[1], y2[1]):
            return FaceType.OBTUSE_TRI        # overlap → obtuse triangle
        return FaceType.OPEN_SLAB
    return FaceType.OBTUSE_TRI                # default safe

# ------------------------------------------------------------
#  3-D  :  split remaining OPEN_SLAB faces
# ------------------------------------------------------------
def split_open_slab(dcel: DCEL, face: Face) -> Tuple[Face, Face]:
    vert_edges = sorted([e for e in iterate_half_edges(face.outer) if _is_vertical(e)],
                        key=lambda e: e.origin.x)
    left_e, right_e = vert_edges[0], vert_edges[1]

    v_left_top  = left_e.origin  if left_e.origin.y  > left_e.twin.origin.y  else left_e.twin.origin
    v_right_bot = right_e.origin if right_e.origin.y < right_e.twin.origin.y else right_e.twin.origin

    return add_diagonal(dcel, face, v_left_top, v_right_bot)

# ------------------------------------------------------------
#  main Stage-3 driver
# ------------------------------------------------------------
def slab_partition(dcel: DCEL) -> None:
    add_vertical_cuts(dcel)
    add_horizontal_cuts(dcel)

    pending: List[Face] = [f for f in dcel.faces if f is not dcel.outer_face]
    while pending:
        f = pending.pop()
        f.ftype = classify_face(f)
        if f.ftype is FaceType.OPEN_SLAB:
            f1, f2 = split_open_slab(dcel, f)
            pending.extend([f1, f2])

# ------------------------------------------------------------
#  helper utilities
# ------------------------------------------------------------
def iterate_half_edges(start: HalfEdge) -> Iterable[HalfEdge]:
    """Yield the half-edges in the boundary loop; abort if ring is broken."""
    he = start
    first = True
    visited = set()
    while he and (first or he is not start):
        if he in visited:          # self-loop → שבירה
            raise RuntimeError("broken ring (cycle) while iterating face")
        visited.add(he)

        first = False
        yield he
        he = he.next              # ←  he.next might be None
    if he is None:
        raise RuntimeError("broken ring (next is None)")


def _is_vertical(e: HalfEdge)   -> bool: return e.origin.x == e.twin.origin.x
def _is_horizontal(e: HalfEdge) -> bool: return e.origin.y == e.twin.origin.y

# ---- generic diagonal (used by split_open_slab) ----
# ==== תיקון add_diagonal (רק 4 שורות מודגשות) ====
# be_alg/slab_partition.py  -------------------------------------
# be_alg/slab_partition.py  -------------------------------------
def add_diagonal(dcel: DCEL, face: Face,
                 v1: Vertex, v2: Vertex) -> Tuple[Face, Face]:
    """
    Insert diagonal (v1,v2) inside 'face' and split it into two faces.
    Returns (face_left, face_right)  – the two faces that now share the
    new diagonal (in arbitrary order).
    """

    # -- 0.  locate boundary edges that start at v1 , v2  inside 'face'
    h1 = _find_edge_from_vertex_in_face(v1, face)   # v1 → …  in F
    h2 = _find_edge_from_vertex_in_face(v2, face)   # v2 → …  in F

    # save their current predecessors BEFORE we touch anything
    h1_prev = h1.prev
    h2_prev = h2.prev

    # -- 1.  create the two half-edges of the new diagonal
    e1, e2 = HalfEdge(), HalfEdge()     # e1 : v1→v2 ,  e2 : v2→v1
    e1.origin, e2.origin = v1, v2
    e1.twin,   e2.twin   = e2, e1
    dcel.half_edges.extend([e1, e2])

    # -- 2.  splice e1 between h1_prev ↔ h2
    e1.prev = h1_prev
    e1.next = h2
    h1_prev.next = e1
    h2.prev = e1

    # -- 3.  splice e2 between h2_prev ↔ h1
    e2.prev = h2_prev
    e2.next = h1
    h2_prev.next = e2
    h1.prev = e2

    # -- 4.  build the new face  (all half-edges reachable from e1)
    new_face = Face()
    dcel.faces.append(new_face)

    # flood-fill two rings → assign 'face' / 'new_face'
    def paint(start: HalfEdge, f: Face):
        he = start
        while True:
            he.face = f
            he = he.next
            if he is start:
                break

    paint(e1, new_face)   # ring #1
    paint(e2, face)       # ring #2   (shrunk original face)

    new_face.outer = e1
    if face.outer in {h1, h2}:          # outer pointer might cross to other ring
        face.outer = e2

    # (optionally) set incident pointer of the vertices
    if v1.incident is None or v1.incident.face is face:
        v1.incident = e1
    if v2.incident is None or v2.incident.face is face:
        v2.incident = e2

    return face, new_face

    # נהל שתי טבעות: אחת שמתחילה ב-e1, ואחת ב-e2
    def flood_fill(start: HalfEdge, f: Face):
        he = start
        while True:
            he.face = f
            he = he.next
            if he is start:
                break

    flood_fill(e1, new_face)   # הטבעת החדשה
    flood_fill(e2, face)       # הטבעת שנותרה ב-face הישן

    # קבע outer כלשהו לפאות
    new_face.outer = e1
    if face.outer in {h1, h2}:
        face.outer = e2        # outer של הפאה המקורית אולי השתנה

    return face, new_face


# ------------------------------------------------------------
#  clean  _find_edge_from_vertex_in_face
# ------------------------------------------------------------
def _find_edge_from_vertex_in_face(v: Vertex, f: Face) -> HalfEdge:
    """
    Return a half-edge whose origin is v and whose face is f.
    Raise ValueError if none exists.
    """
    he0 = v.incident
    if he0 is None:
        raise ValueError("vertex has no incident edge")

    he = he0
    first = True
    while first or he is not he0:
        first = False
        if he.face is f:
            return he
        he = he.twin.next
        if he is None:
            raise ValueError("broken DCEL (next is None)")
    raise ValueError("vertex not incident to given face")

# ------------------------------------------------------------
#  demo / debug
# ------------------------------------------------------------
if __name__ == "__main__":
    from fractions import Fraction
    pts = [(0,0),(7,0),(7,3),(5,5),(3,5),(1,4),(0,2)]
    pts = [(Fraction(x), Fraction(y)) for x,y in pts]

    d = DCEL.from_polygon(list(range(len(pts))), pts)
    slab_partition(d)          # לא אמור לזרוק שגיאה
    show_slab_partition(d)     # אמור להציג רשת סדורה
