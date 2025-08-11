from fractions import Fraction
from typing import List, Optional, Tuple
from face_types import FaceType


class Vertex:
    __slots__ = ("x", "y", "incident", "id")

    def __init__(self, x: Fraction, y: Fraction, vertex_id: int = None):
        self.x: Fraction = x
        self.y: Fraction = y
        self.incident: Optional["HalfEdge"] = None
        self.id = vertex_id

    def __repr__(self):
        return f"V({float(self.x):.2f},{float(self.y):.2f})"

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if not isinstance(other, Vertex):
            return False
        return self.x == other.x and self.y == other.y


class HalfEdge:
    __slots__ = ("origin", "twin", "next", "prev", "face", "id")

    def __init__(self, edge_id: int = None):
        self.origin: Optional[Vertex] = None
        self.twin: Optional["HalfEdge"] = None
        self.next: Optional["HalfEdge"] = None
        self.prev: Optional["HalfEdge"] = None
        self.face: Optional["Face"] = None
        self.id = edge_id

    def __repr__(self):
        if self.origin and self.twin and self.twin.origin:
            return f"E({self.origin}→{self.twin.origin})"
        return f"E(id={self.id})"


class Face:
    __slots__ = ("outer", "ftype", "id")

    def __init__(self, face_id: int = None):
        self.outer: Optional[HalfEdge] = None
        self.ftype: Optional[FaceType] = None
        self.id = face_id


class DCEL:
    """ Enhanced DCEL for Bern-Eppstein slab partition """

    def __init__(self, points: List[Tuple[Fraction, Fraction]]):
        self.vertices: List[Vertex] = [Vertex(x, y, i) for i, (x, y) in enumerate(points)]
        self.half_edges: List[HalfEdge] = []
        self.faces: List[Face] = []
        self.outer_face: Optional[Face] = None
        self._next_edge_id = 0
        self._next_face_id = 0

    def _get_next_edge_id(self):
        self._next_edge_id += 1
        return self._next_edge_id

    def _get_next_face_id(self):
        self._next_face_id += 1
        return self._next_face_id

    @classmethod
    def from_polygon(cls, boundary_indices: List[int],
                     points: List[Tuple[Fraction, Fraction]]):
        """
        Create DCEL from polygon boundary.
        boundary_indices – sequence of vertex indices in CCW order (no repetition).
        """
        dcel = cls(points)
        n = len(boundary_indices)

        # Create n pairs of half-edges
        edges_fwd = [HalfEdge(dcel._get_next_edge_id()) for _ in range(n)]
        edges_rev = [HalfEdge(dcel._get_next_edge_id()) for _ in range(n)]

        # Create two faces: inner + outer
        inner = Face(dcel._get_next_face_id())
        outer = Face(dcel._get_next_face_id())
        dcel.outer_face = outer

        for i in range(n):
            v_origin = dcel.vertices[boundary_indices[i]]
            v_dest = dcel.vertices[boundary_indices[(i + 1) % n]]

            e = edges_fwd[i]
            te = edges_rev[i]

            # Basic linking
            e.origin = v_origin
            te.origin = v_dest
            e.twin = te
            te.twin = e

            # Next/prev chains for inner face
            e.next = edges_fwd[(i + 1) % n]
            e.prev = edges_fwd[(i - 1) % n]
            e.face = inner

            # For outer face – reverse order
            te.next = edges_rev[(i - 1) % n]
            te.prev = edges_rev[(i + 1) % n]
            te.face = outer

            # Set incident pointer
            if v_origin.incident is None:
                v_origin.incident = e
            if v_dest.incident is None:
                v_dest.incident = te

        inner.outer = edges_fwd[0]
        outer.outer = edges_rev[0]

        # Register in lists
        dcel.half_edges.extend(edges_fwd + edges_rev)
        dcel.faces.extend([inner, outer])
        return dcel

    def split_edge(self, he: HalfEdge, x: Fraction, y: Fraction) -> Vertex:
        """Split directed edge `he` (A→B) at (x,y). Return vertex M."""
        A = he.origin
        B = he.twin.origin
        F_left = he.face
        F_right = he.twin.face

        # Create new vertex
        M = Vertex(x, y, len(self.vertices))
        self.vertices.append(M)

        # Create new half-edges
        he_mb = HalfEdge(self._get_next_edge_id())  # M → B (left face)
        he_am = HalfEdge(self._get_next_edge_id())  # M → A (right face)
        self.half_edges.extend([he_mb, he_am])

        he_mb.origin = M
        he_am.origin = M
        he_mb.twin = he.twin  # M→B  ⟷  B→M
        he.twin.twin = he_mb
        he_am.twin = he  # M→A  ⟷  A→M
        he.twin = he_am

        # Helper to splice (edge_prev, edge_next, new_edge)
        def _splice(prev_edge: HalfEdge, next_edge: Optional[HalfEdge],
                    new_edge: HalfEdge):
            new_edge.prev = prev_edge
            if next_edge is None:
                # Ring of 2 edges: prev_edge ↔ new_edge
                prev_edge.next = new_edge
                new_edge.next = prev_edge
                prev_edge.prev = new_edge
            else:
                new_edge.next = next_edge
                prev_edge.next = new_edge
                next_edge.prev = new_edge

        # LEFT face ring (A→M→B→…)
        he_mb.face = F_left
        _splice(he, he.next, he_mb)
        he.face = F_left  # remains

        # RIGHT face ring (B→M→A→…)
        he_am.face = F_right
        _splice(he.twin, he.twin.next, he_am)
        he.twin.face = F_right  # remains

        # Incident pointer
        M.incident = he_am

        return M

    def validate_integrity(self):
        """Validate DCEL integrity"""
        errors = []

        # Check half-edge twin relationships
        for edge in self.half_edges:
            if edge.twin is None:
                errors.append(f"Edge {edge.id} missing twin")
            elif edge.twin.twin != edge:
                errors.append(f"Edge {edge.id} twin relationship broken")

        # Check next/prev consistency
        for edge in self.half_edges:
            if edge.next is None:
                errors.append(f"Edge {edge.id} missing next pointer")
            elif edge.next.prev != edge:
                errors.append(f"Edge {edge.id} next/prev relationship broken")

        # Check vertex incident edges
        for vertex in self.vertices:
            if vertex.incident is None:
                errors.append(f"Vertex {vertex.id} missing incident edge")
            elif vertex.incident.origin != vertex:
                errors.append(f"Vertex {vertex.id} incident edge origin mismatch")

        if errors:
            raise ValueError(f"DCEL integrity violations: {errors}")

    def get_face_vertices(self, face: Face) -> List[Vertex]:
        """Get vertices of a face in order"""
        if not face.outer:
            return []

        vertices = []
        start = face.outer
        current = start
        while True:
            vertices.append(current.origin)
            current = current.next
            if current == start:
                break
        return vertices
