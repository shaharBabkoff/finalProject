# face_types.py
from enum import Enum, auto


class FaceType(Enum):
    RECTANGLE = auto()
    RIGHT_TRI = auto()
    OBTUSE_TRI = auto()
    OPEN_SLAB = auto()


# dcel.py
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


# slab_partition.py
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
from typing import List, Tuple, Iterable, Optional, Dict, Set

from dcel import DCEL, Face, HalfEdge, Vertex
from face_types import FaceType


def slab_partition(dcel: DCEL, debug: bool = False) -> None:
    """Main slab partition algorithm - Stage 3 of Bern-Eppstein"""
    if debug:
        print("Starting slab partition...")
        dcel.validate_integrity()

    add_vertical_cuts(dcel, debug)

    if debug:
        print("Vertical cuts completed, adding horizontal cuts...")
        dcel.validate_integrity()

    add_horizontal_cuts(dcel, debug)

    if debug:
        print("Horizontal cuts completed, classifying faces...")
        dcel.validate_integrity()

    # Classify and split faces
    pending: List[Face] = [f for f in dcel.faces if f is not dcel.outer_face]
    iteration = 0

    while pending:
        iteration += 1
        if debug:
            print(f"Classification iteration {iteration}, {len(pending)} faces pending")

        f = pending.pop()
        f.ftype = classify_face(f, debug)

        if f.ftype is FaceType.OPEN_SLAB:
            if debug:
                print(f"Splitting open slab face {f.id}")
            f1, f2 = split_open_slab(dcel, f)
            pending.extend([f1, f2])

    if debug:
        print("Slab partition completed successfully")


def add_vertical_cuts(dcel: DCEL, debug: bool = False) -> None:
    """Add vertical cuts through all vertex x-coordinates"""
    # Get all unique x-coordinates
    xs = sorted({v.x for v in dcel.vertices})
    total_v = 0

    if debug:
        print(f"Adding vertical cuts at x-coordinates: {[float(x) for x in xs]}")

    for x0 in xs:
        hits: List[Vertex] = []

        # Find all intersections with vertical line x = x0
        for he in list(dcel.half_edges):  # Copy list to avoid modification during iteration
            if he.face is dcel.outer_face:
                continue

            x1, x2 = he.origin.x, he.twin.origin.x

            # Check if edge crosses vertical line
            if min(x1, x2) < x0 < max(x1, x2):
                # Calculate intersection point
                t = (x0 - x1) / (x2 - x1)
                y0 = he.origin.y + t * (he.twin.origin.y - he.origin.y)
                new_vertex = dcel.split_edge(he, x0, y0)
                hits.append(new_vertex)
                if debug:
                    print(f"  Split edge at ({float(x0)}, {float(y0)})")
            elif x1 == x0:
                # Vertex lies exactly on vertical line
                hits.append(he.origin)

        # Sort hits by y-coordinate
        hits.sort(key=lambda v: v.y)

        # Connect consecutive pairs of hits
        i = 0
        while i + 1 < len(hits):
            v_low, v_up = hits[i], hits[i + 1]
            face = _common_face(v_low, v_up)

            if face is None:
                i += 1
                continue

            if _edge_exists(face, v_low, v_up, vertical=True):
                i += 2
                continue

            add_diagonal(dcel, face, v_low, v_up)
            total_v += 1
            if debug:
                print(f"  Added vertical diagonal between {v_low} and {v_up}")
            i += 2

    if debug:
        print(f"Total vertical diagonals added: {total_v}")


def add_horizontal_cuts(dcel: DCEL, debug: bool = False) -> None:
    """Add horizontal cuts using gather-then-apply approach"""
    total_h = 0

    # Process each non-outer face
    for face in [f for f in dcel.faces if f is not dcel.outer_face]:
        if debug:
            print(f"Processing face {face.id} for horizontal cuts")

        hits_by_y: Dict[Fraction, List[Vertex]] = defaultdict(list)

        # Gather all vertices that lie on vertical segments of this face
        face_edges = list(iterate_half_edges(face.outer))

        for he in face_edges:
            if not _is_vertical(he):
                continue

            # Get y-range of this vertical segment
            y_min, y_max = sorted([he.origin.y, he.twin.origin.y])

            if debug:
                print(f"  Vertical edge from {he.origin} to {he.twin.origin}")

            # Check all vertices of this face
            for he_v in face_edges:
                vy = he_v.origin.y
                vx = he_v.origin.x

                # Check if vertex lies on this vertical segment
                if y_min <= vy <= y_max and abs(vx - he.origin.x) < 1e-9:
                    if he_v.origin not in hits_by_y[vy]:
                        hits_by_y[vy].append(he_v.origin)
                        if debug:
                            print(f"    Added vertex {he_v.origin} at y={float(vy)}")

        # Connect successive hits at each y-level
        for y, verts in hits_by_y.items():
            if len(verts) < 2:
                continue

            # Sort vertices by x-coordinate
            verts.sort(key=lambda v: v.x)

            if debug:
                print(f"  Connecting {len(verts)} vertices at y={float(y)}")

            # Connect pairs of vertices
            for i in range(0, len(verts) - 1, 2):
                if i + 1 >= len(verts):
                    break

                v_left, v_right = verts[i], verts[i + 1]

                if _edge_exists(face, v_left, v_right, vertical=False):
                    if debug:
                        print(f"    Edge already exists between {v_left} and {v_right}")
                    continue

                add_diagonal(dcel, face, v_left, v_right)
                total_h += 1
                if debug:
                    print(f"    Added horizontal diagonal between {v_left} and {v_right}")

    if debug:
        print(f"Total horizontal diagonals added: {total_h}")


def classify_face(face: Face, debug: bool = False) -> FaceType:
    """Classify face according to Lemma 5"""
    edges = list(iterate_half_edges(face.outer))
    vert = [e for e in edges if _is_vertical(e)]
    horz = [e for e in edges if _is_horizontal(e)]

    if debug:
        print(f"Classifying face {face.id}: {len(edges)} edges, {len(vert)} vertical, {len(horz)} horizontal")

    # Rectangle: 4 edges, 2 vertical, 2 horizontal
    if len(edges) == 4 and len(vert) == 2 and len(horz) == 2:
        if debug:
            print(f"  Face {face.id} classified as RECTANGLE")
        return FaceType.RECTANGLE

    # Right triangle: 3 edges, 1 vertical, 1 horizontal
    if len(edges) == 3 and len(vert) == 1 and len(horz) == 1:
        if debug:
            print(f"  Face {face.id} classified as RIGHT_TRI")
        return FaceType.RIGHT_TRI

    # Check for overlapping vertical segments (obtuse triangle vs open slab)
    if len(vert) == 2:
        y1 = sorted([vert[0].origin.y, vert[0].twin.origin.y])
        y2 = sorted([vert[1].origin.y, vert[1].twin.origin.y])

        # Check if vertical segments overlap
        if max(y1[0], y2[0]) <= min(y1[1], y2[1]):
            if debug:
                print(f"  Face {face.id} classified as OBTUSE_TRI (overlapping verticals)")
            return FaceType.OBTUSE_TRI
        else:
            if debug:
                print(f"  Face {face.id} classified as OPEN_SLAB (non-overlapping verticals)")
            return FaceType.OPEN_SLAB

    # Default classification
    if debug:
        print(f"  Face {face.id} classified as OBTUSE_TRI (default)")
    return FaceType.OBTUSE_TRI


def split_open_slab(dcel: DCEL, face: Face) -> Tuple[Face, Face]:
    """Split open slab face into two obtuse triangles"""
    # Find the two vertical edges
    verts = [e for e in iterate_half_edges(face.outer) if _is_vertical(e)]
    verts.sort(key=lambda e: e.origin.x)  # Sort by x-coordinate

    left_e, right_e = verts[0], verts[1]

    # Find appropriate vertices for diagonal
    v_left_top = left_e.origin if left_e.origin.y > left_e.twin.origin.y else left_e.twin.origin
    v_right_bot = right_e.origin if right_e.origin.y < right_e.twin.origin.y else right_e.twin.origin

    return add_diagonal(dcel, face, v_left_top, v_right_bot)


def iterate_half_edges(start: HalfEdge) -> Iterable[HalfEdge]:
    """Iterate through half-edges of a face boundary"""
    if start is None:
        return

    he = start
    first = True
    while he and (first or he is not start):
        first = False
        yield he
        he = he.next

    if he is None:
        raise RuntimeError("Broken face boundary ring")


def _faces_incident(v: Vertex) -> Set[Face]:
    """Get all faces incident to a vertex"""
    faces = set()
    if not v.incident:
        return faces

    he = v.incident
    first = True
    while he and (first or he is not v.incident):
        first = False
        if he.face:
            faces.add(he.face)
        he = he.twin.next if he.twin else None
        if he is None:
            break

    return faces


def _common_face(v1: Vertex, v2: Vertex) -> Optional[Face]:
    """Find common face of two vertices"""
    faces1 = _faces_incident(v1)
    for f in _faces_incident(v2):
        if f in faces1 and f.outer is not None:
            return f
    return None


def _is_vertical(e: HalfEdge) -> bool:
    """Check if edge is vertical"""
    return abs(e.origin.x - e.twin.origin.x) < 1e-9


def _is_horizontal(e: HalfEdge) -> bool:
    """Check if edge is horizontal"""
    return abs(e.origin.y - e.twin.origin.y) < 1e-9


def _edge_exists(face: Face, v1: Vertex, v2: Vertex, *, vertical: bool) -> bool:
    """
    Check if edge exists between v1 and v2 in the given face.
    Only considers edges with the specified orientation (vertical/horizontal).
    """
    for he in iterate_half_edges(face.outer):
        # Check orientation constraint
        if vertical and not _is_vertical(he):
            continue
        if not vertical and not _is_horizontal(he):
            continue

        # Check if this edge connects v1 and v2 (in either direction)
        if ((he.origin is v1 and he.twin.origin is v2) or
                (he.origin is v2 and he.twin.origin is v1)):
            return True

    return False


def add_diagonal(dcel: DCEL, face: Face, v1: Vertex, v2: Vertex) -> Tuple[Face, Face]:
    """Add diagonal between two vertices in a face, splitting it into two faces"""
    # Find edges from vertices in this face
    h1 = _edge_from_v_in_face(v1, face)
    h2 = _edge_from_v_in_face(v2, face)
    h1_prev, h2_prev = h1.prev, h2.prev

    # Create new half-edges for the diagonal
    e1 = HalfEdge(dcel._get_next_edge_id())  # v1 → v2
    e2 = HalfEdge(dcel._get_next_edge_id())  # v2 → v1

    e1.origin, e2.origin = v1, v2
    e1.twin, e2.twin = e2, e1
    dcel.half_edges.extend([e1, e2])

    # Update next/prev pointers
    e1.prev, e1.next = h1_prev, h2
    h1_prev.next, h2.prev = e1, e1

    e2.prev, e2.next = h2_prev, h1
    h2_prev.next, h1.prev = e2, e2

    # Create new face
    new_face = Face(dcel._get_next_face_id())
    dcel.faces.append(new_face)

    def paint(start: HalfEdge, f: Face):
        """Assign face to all edges in boundary starting from 'start'"""
        he = start
        while True:
            he.face = f
            he = he.next
            if he is start:
                break

    # Assign faces to the two boundary components
    paint(e1, new_face)
    paint(e2, face)

    # Set outer boundary pointers
    new_face.outer = e1
    if face.outer in {h1, h2}:
        face.outer = e2

    return face, new_face


def _edge_from_v_in_face(v: Vertex, face: Face) -> HalfEdge:
    """Find a half-edge starting from vertex v in the given face"""
    if not v.incident:
        raise ValueError(f"Vertex {v} has no incident edges")

    he = v.incident
    first = True
    while he and (first or he is not v.incident):
        first = False
        if he.face is face:
            return he
        he = he.twin.next if he.twin else None
        if he is None:
            break

    raise ValueError(f"Vertex {v} not incident to face {face.id}")


# viz_utils.py
from __future__ import annotations
from fractions import Fraction
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

from dcel import DCEL, HalfEdge
from face_types import FaceType


def show_slab_partition(dcel: DCEL, title: str = "Slab partition") -> None:
    """Visualize DCEL with color-coding for different edge types"""
    fig, ax = plt.subplots(figsize=(10, 8))

    def style(e: HalfEdge) -> tuple[str, float]:
        if abs(e.origin.x - e.twin.origin.x) < 1e-9:  # vertical
            return "darkorange", 2.5
        if abs(e.origin.y - e.twin.origin.y) < 1e-9:  # horizontal
            return "limegreen", 2.5
        return "lightgray", 1.5  # boundary / diagonal

    # Draw edges (avoid drawing each edge twice)
    drawn_edges = set()
    for he in dcel.half_edges:
        edge_key = tuple(sorted([id(he), id(he.twin)]))
        if edge_key in drawn_edges:
            continue
        drawn_edges.add(edge_key)

        c, lw = style(he)
        xs = [float(he.origin.x), float(he.twin.origin.x)]
        ys = [float(he.origin.y), float(he.twin.origin.y)]
        ax.plot(xs, ys, color=c, linewidth=lw)

    # Draw vertices
    for v in dcel.vertices:
        ax.plot(float(v.x), float(v.y), 'ko', markersize=4)

    # Add face type annotations
    for face in dcel.faces:
        if face is dcel.outer_face or not hasattr(face, 'ftype') or face.ftype is None:
            continue

        # Calculate face centroid for label placement
        vertices = dcel.get_face_vertices(face)
        if vertices:
            cx = sum(float(v.x) for v in vertices) / len(vertices)
            cy = sum(float(v.y) for v in vertices) / len(vertices)

            type_name = face.ftype.name
            ax.text(cx, cy, type_name, ha='center', va='center',
                    fontsize=8, bbox=dict(boxstyle="round,pad=0.3",
                                          facecolor="white", alpha=0.7))

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


