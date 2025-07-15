from fractions import Fraction
from typing import List, Optional, Tuple
from src.be_alg.face_types import FaceType


class Vertex:
    __slots__ = ("x", "y", "incident")

    def __init__(self, x: Fraction, y: Fraction):
        self.x: Fraction = x
        self.y: Fraction = y
        self.incident: Optional["HalfEdge"] = None

    # נוח להדפסה
    def __repr__(self):
        return f"V({float(self.x):.2f},{float(self.y):.2f})"


class HalfEdge:
    __slots__ = ("origin", "twin", "next", "prev", "face")

    def __init__(self):
        self.origin: Optional[Vertex] = None
        self.twin: Optional["HalfEdge"] = None
        self.next: Optional["HalfEdge"] = None
        self.prev: Optional["HalfEdge"] = None
        self.face: Optional["Face"] = None

    def __repr__(self):
        return f"E({self.origin}→{self.twin.origin})"


class Face:
    __slots__ = ("outer", "ftype")

    def __init__(self):
        self.outer: Optional[HalfEdge] = None
        self.ftype: Optional[FaceType] = None   # ← ימולא אחרי classify_face


class DCEL:
    """ DCEL מינימלי: מספיק ל-slab partition + triangulation """

    def __init__(self, points: List[Tuple[Fraction, Fraction]]):
        self.vertices: List[Vertex] = [Vertex(x, y) for x, y in points]
        self.half_edges: List[HalfEdge] = []
        self.faces: List[Face] = []
        self.outer_face: Optional[Face] = None

    # ---------- בנייה ראשונית מהגבול (ללא אילוצים) ----------
    @classmethod
    def from_polygon(cls, boundary_indices: List[int],
                     points: List[Tuple[Fraction, Fraction]]):
        """
        boundary_indices – רצף אינדקסים CCW (ללא חזרה על הראשון).
        """
        dcel = cls(points)
        n = len(boundary_indices)

        # יוצרים n זוגות half-edges
        edges_fwd = [HalfEdge() for _ in range(n)]
        edges_rev = [HalfEdge() for _ in range(n)]

        # יוצרים שתי פאות: פנים + אינסוף
        inner = Face()
        outer = Face()
        dcel.outer_face = outer
        for i in range(n):
            v_origin = dcel.vertices[boundary_indices[i]]
            v_dest = dcel.vertices[boundary_indices[(i + 1) % n]]

            e = edges_fwd[i]
            te = edges_rev[i]

            # קישור בסיסי
            e.origin = v_origin
            te.origin = v_dest
            e.twin = te
            te.twin = e

            # שרשראות next/prev לפאה הפנימית
            e.next = edges_fwd[(i + 1) % n]
            e.prev = edges_fwd[(i - 1) % n]
            e.face = inner

            # לפאה החיצונית – הסדר הפוך
            te.next = edges_rev[(i - 1) % n]
            te.prev = edges_rev[(i + 1) % n]
            te.face = outer

            # שמים מצביע incident כלשהו
            if v_origin.incident is None:
                v_origin.incident = e
            if v_dest.incident is None:
                v_dest.incident = te

        inner.outer = edges_fwd[0]
        outer.outer = edges_rev[0]

        # רישום ברשימות
        dcel.half_edges.extend(edges_fwd + edges_rev)
        dcel.faces.extend([inner, outer])
        return dcel

    def split_edge(self, he: HalfEdge, x: Fraction, y: Fraction) -> Vertex:
        """Split directed edge `he` (A→B) at (x,y). Return vertex M."""
        A = he.origin
        B = he.twin.origin
        F_left = he.face
        F_right = he.twin.face

        # 0. create new vertex
        M = Vertex(x, y)
        self.vertices.append(M)

        # 1. create new half-edges
        he_mb = HalfEdge()  # M → B     (left face)
        he_am = HalfEdge()  # M → A     (right face)
        self.half_edges.extend([he_mb, he_am])

        he_mb.origin = M
        he_am.origin = M
        he_mb.twin = he.twin  # M→B  ⟷  B→M
        he.twin.twin = he_mb
        he_am.twin = he  # M→A  ⟷  A→M
        he.twin = he_am

        # ---- helper to splice (edge_prev, edge_next, new_edge) ----
        def _splice(prev_edge: HalfEdge, next_edge: Optional[HalfEdge],
                    new_edge: HalfEdge):
            new_edge.prev = prev_edge
            if next_edge is None:
                # טבעת בת 2-קשתות: prev_edge ↔ new_edge
                prev_edge.next = new_edge
                new_edge.next = prev_edge
                prev_edge.prev = new_edge
            else:
                new_edge.next = next_edge
                prev_edge.next = new_edge
                next_edge.prev = new_edge

        # 2a. LEFT face ring  (A→M→B→…)
        he_mb.face = F_left
        _splice(he, he.next, he_mb)
        he.face = F_left  # remains

        # 2b. RIGHT face ring (B→M→A→…)
        he_am.face = F_right
        _splice(he.twin, he.twin.next, he_am)
        he.twin.face = F_right  # remains

        # 3. incident pointer
        M.incident = he_am

        return M

