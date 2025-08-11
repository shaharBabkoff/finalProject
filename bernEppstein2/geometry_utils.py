from fractions import Fraction
from typing import Tuple, List, Literal, Dict
import math
from cgshop2025_pyutils.geometry import Point, FieldNumber, Polygon, Segment, VerificationGeometryHelper


def build_polygon_from_indices(index_list: list[int],
                               coordinates: list[tuple[float, float]]) -> Polygon:
    """
    Build a CGAL `Polygon` from CCW indices.

    Parameters
    ----------
    index_list   : boundary indices in CCW order (first index *not* repeated)
    coordinates  : global list [(x,y), …]  (floats or already CGAL Points)

    Returns
    -------
    poly : cgshop2025_pyutils.geometry._bindings.Polygon
           – guaranteed CCW and simple
    """
    # --- 0. bounds & duplicates checks (optional but recommended) ----------
    if any(i < 0 or i >= len(coordinates) for i in index_list):
        raise IndexError("boundary index out of range")
    if len(set(index_list)) != len(index_list):
        raise ValueError("boundary indices contain duplicates")

    # --- 1. build list of CGAL Points --------------------------------------
    pts = []
    for idx in index_list:
        xy = coordinates[idx]
        if isinstance(xy, Point):          # already an exact CGAL point
            pts.append(xy)
        else:                              # plain tuple
            x_val, y_val = xy
            pts.append(Point(FieldNumber(x_val), FieldNumber(y_val)))

    poly = Polygon(pts)
    print(poly)
    # --- 2. enforce CCW orientation ----------------------------------------
    if poly.area() < FieldNumber(0):       # CGAL: positive area ⇒ CCW
        pts.reverse()
        poly = Polygon(pts)

    # --- 3. sanity‑check: simple polygon -----------------------------------
    if not poly.is_simple():
        raise ValueError("Boundary indices do not form a simple (non‑self‑intersecting) polygon")

    return poly
def make_vertical_grid(poly: Polygon) -> Tuple[list[Segment], list[tuple[float, float]]]:
    """Return the maximal vertical slices through every boundary vertex.

    Parameters
    ----------
    poly : CGAL Polygon            (outer boundary only)

    Returns
    -------
    v_segments : list[Segment]               # closed vertical segments S_i
    steiner_pts: list[(float,float)]         # interior Steiner points on S_i
    """
    boundary_pts = poly.boundary()   # list[Point] in CCW order
    n            = len(boundary_pts)

    v_segments:  list[Segment] = []
    steiner_pts: list[tuple[float, float]] = []

    def as_tuple(p: Point) -> tuple[float, float]:
        return float(p.x()), float(p.y())

    # ------------------------------------------------------------------
    # iterate over every boundary vertex v
    # ------------------------------------------------------------------
    for v in boundary_pts:
        x_fnum = v.x()                       # exact x
        x_val  = float(x_fnum)              # numeric x (for comparisons)

        up_hits:   list[Point] = []
        down_hits: list[Point] = []

        # ---- loop over each boundary edge ----------------------------
        for i in range(n):
            a, b = boundary_pts[i], boundary_pts[(i + 1) % n]

            # skip edges incident to v (they *touch* v already)
            if a == v or b == v:
                continue

            ax, ay = float(a.x()), float(a.y())
            bx, by = float(b.x()), float(b.y())

            # vertical edge → ignore
            if ax == bx:
                continue

            # does the vertical line x = x_val intersect the x‑range of (a,b)?
            if not (min(ax, bx) <= x_val <= max(ax, bx)):
                continue

            t = (x_val - ax) / (bx - ax)     # param on edge (a→b)

            # ------------------------------------------------------------------
            # OLD CODE:
            #     if t <= 0.0 or t >= 1.0: continue      # skipped *all* endpoint hits
            # ------------------------------------------------------------------
            # NEW: allow endpoint hits **unless** that endpoint is exactly v
            #      ⇒ we still ignore the two edges adjacent to v, but we *keep*
            #        intersections that land on *other* vertices.
            # ------------------------------------------------------------------
            if (t <= 0.0 or t >= 1.0):
                # intersection is an endpoint -> keep only if this endpoint is
                # **not** the original vertex v
                hit_pt = a if t <= 0.0 else b
                if hit_pt == v:
                    continue  # skip self‑hit
                # else: treat it like a normal interior hit (falls through)

            y_int = ay + t * (by - ay)
            p_int = Point(x_fnum, FieldNumber(y_int))

            if y_int > float(v.y()):
                up_hits.append(p_int)
            elif y_int < float(v.y()):
                down_hits.append(p_int)
            # equal y → p_int *is* v; impossible because incident edges skipped

        # If no proper hit was found in one direction, the next vertex with the
        # same x lies on the boundary (convex/reflex cases) – find it explicitly
        if not up_hits:
            up_hits = [p for p in boundary_pts if float(p.x()) == x_val and float(p.y()) > float(v.y())]
        if not down_hits:
            down_hits = [p for p in boundary_pts if float(p.x()) == x_val and float(p.y()) < float(v.y())]

        # choose nearest hits
        up_point   = min(up_hits,   key=lambda p: float(p.y())) if up_hits else v
        down_point = max(down_hits, key=lambda p: float(p.y())) if down_hits else v

        # ignore zero‑length slices (happens for isolated reflex vert.)
        if up_point == down_point:
            continue

        seg = Segment(down_point, up_point)
        v_segments.append(seg)

        # collect interior Steiner pts
        if down_point != v:
            steiner_pts.append(as_tuple(down_point))
        if up_point != v:
            steiner_pts.append(as_tuple(up_point))

    return v_segments, steiner_pts





def make_horizontal_grid(poly: Polygon, v_segments: list[Segment]) -> Tuple[list[Segment], list[tuple[float, float]]]:
    """Return the maximal horizontal slices through every slab vertex.

    Parameters
    ----------
    poly : CGAL Polygon            (outer boundary only)
    v_segments : list[Segment]     (vertical segments from previous step)

    Returns
    -------
    h_segments : list[Segment]               # closed horizontal segments
    steiner_pts: list[(float,float)]         # interior Steiner points on horizontal segments
    """
    boundary_pts = poly.boundary()  # list[Point] in CCW order
    n = len(boundary_pts)

    # Collect all "slab vertices" = boundary vertices + Steiner points from vertical segments
    slab_vertices = list(boundary_pts)
    for seg in v_segments:
        # Add endpoints of vertical segments that aren't already boundary points
        src = seg.source()
        tgt = seg.target()
        if src not in boundary_pts:
            slab_vertices.append(src)
        if tgt not in boundary_pts:
            slab_vertices.append(tgt)

    h_segments: list[Segment] = []
    steiner_pts: list[tuple[float, float]] = []

    def as_tuple(p: Point) -> tuple[float, float]:
        return float(p.x()), float(p.y())

    # ------------------------------------------------------------------
    # iterate over every slab vertex v
    # ------------------------------------------------------------------
    for v in slab_vertices:
        y_fnum = v.y()  # exact y
        y_val = float(y_fnum)  # numeric y (for comparisons)

        left_hits: list[Point] = []
        right_hits: list[Point] = []

        # Note: We don't intersect with boundary edges directly.
        # The horizontal segments should only extend to vertical segments or slab vertices.
        # equal x → p_int *is* v; impossible because incident edges skipped

        # ---- loop over each vertical segment -------------------------
        for seg in v_segments:
            src_x, src_y = float(seg.source().x()), float(seg.source().y())
            tgt_x, tgt_y = float(seg.target().x()), float(seg.target().y())

            # vertical segments should have same x coordinate
            seg_x = src_x  # = tgt_x

            # does the horizontal line y = y_val intersect this vertical segment?
            if not (min(src_y, tgt_y) <= y_val <= max(src_y, tgt_y)):
                continue

            # intersection point
            p_int = Point(FieldNumber(seg_x), y_fnum)

            # skip if this intersection is exactly v
            if p_int == v:
                continue

            if seg_x > float(v.x()):
                right_hits.append(p_int)
            elif seg_x < float(v.x()):
                left_hits.append(p_int)

        # If no hit was found in one direction, find the nearest slab vertex
        # with the same y coordinate (this handles boundary cases)
        if not left_hits:
            left_hits = [p for p in slab_vertices if float(p.y()) == y_val and float(p.x()) < float(v.x())]
        if not right_hits:
            right_hits = [p for p in slab_vertices if float(p.y()) == y_val and float(p.x()) > float(v.x())]

        # choose the FARTHEST hits (last possible vertical segment)
        # For left: we want the leftmost point (minimum x)
        # For right: we want the rightmost point (maximum x)
        left_point = min(left_hits, key=lambda p: float(p.x())) if left_hits else v
        right_point = max(right_hits, key=lambda p: float(p.x())) if right_hits else v

        # ignore zero‑length slices
        if left_point == right_point:
            continue

        seg = Segment(left_point, right_point)
        h_segments.append(seg)

        # collect interior Steiner pts
        if left_point != v:
            steiner_pts.append(as_tuple(left_point))
        if right_point != v:
            steiner_pts.append(as_tuple(right_point))

    return h_segments, steiner_pts

FaceType = Literal["RECTANGLE", "RIGHT_TRI", "OBTUSE_TRI", "SLAB"]


def _angle_is_obtuse(a: Point, b: Point, c: Point) -> bool:
    """Return True iff angle ∠abc is > 90° (exact arithmetic)."""
    abx, aby = float(a.x()) - float(b.x()), float(a.y()) - float(b.y())
    cbx, cby = float(c.x()) - float(b.x()), float(c.y()) - float(b.y())
    # dot‑product < 0  ⇒ obtuse
    return abx * cbx + aby * cby < 0.0


def _classify_simple_face(vertices: List[Point]) -> FaceType:
    """Given a bounded face (no holes), decide which of the 4 categories."""
    m = len(vertices)
    if m == 3:                        # triangle
        # check if any angle is obtuse
        if any(
            _angle_is_obtuse(vertices[(i - 1) % 3],
                             vertices[i],
                             vertices[(i + 1) % 3])
            for i in range(3)
        ):
            return "OBTUSE_TRI"
        else:
            # right or acute → but paper only puts ‘right’ here
            return "RIGHT_TRI"

    if m == 4:                        # quadrilateral
        # count how many horizontal / vertical edges
        dirs = []
        for i in range(4):
            p, q = vertices[i], vertices[(i + 1) % 4]
            if float(p.x()) == float(q.x()):
                dirs.append("V")
            elif float(p.y()) == float(q.y()):
                dirs.append("H")
        if len(dirs) == 4:            # two V, two H  → rectangle
            return "RECTANGLE"

    # anything else is a “slab” (4+ vertices, exactly two V edges)
    return "SLAB"


FaceType = Literal["RECTANGLE", "RIGHT_TRI", "OBTUSE_TRI", "SLAB"]


# ---------------------------------------------------------------------------
#  Helper – classify one bounded face according to Lemma 5
# ---------------------------------------------------------------------------
def _classify_face(face_pts: List[Point], poly: Polygon) -> FaceType:
    """
    Parameters
    ----------
    face_pts : list[Point]  -- CCW cycle returned by CGAL
    poly     : original polygon (outer boundary only)

    Returns a string in {"RECTANGLE","RIGHT_TRI","OBTUSE_TRI","SLAB"}.
    """
    n = len(face_pts)

    # convenience lambdas --------------------------------------------------
    def is_vertical(a: Point, b: Point) -> bool:
        return a.x() == b.x()

    def is_horizontal(a: Point, b: Point) -> bool:
        return a.y() == b.y()

    def on_boundary(a: Point, b: Point) -> bool:
        # CGAL equality is exact; we can compare coordinates
        boundary = poly.boundary()
        m = len(boundary)
        for i in range(m):
            p, q = boundary[i], boundary[(i + 1) % m]
            if (a == p and b == q) or (a == q and b == p):
                return True
        return False

    # count edge properties ------------------------------------------------
    vert_cnt = hori_cnt = bound_cnt = 0
    for i in range(n):
        p = face_pts[i]
        q = face_pts[(i + 1) % n]
        if is_vertical(p, q):
            vert_cnt += 1
        elif is_horizontal(p, q):
            hori_cnt += 1
        if on_boundary(p, q):
            bound_cnt += 1

    # 1. rectangle (axis aligned, no boundary edges)
    if n == 4 and vert_cnt == 2 and hori_cnt == 2 and bound_cnt == 0:
        return "RECTANGLE"

    # 2 & 3. triangles ------------------------------------------------------
    if n == 3:
        if bound_cnt == 2:
            return "OBTUSE_TRI"
        return "RIGHT_TRI"          # 1 or 0 boundary edges

    # 4. everything else is a slab
    return "SLAB"

FaceType = Literal["RECTANGLE", "RIGHT_TRI", "OBTUSE_TRI", "SLAB"]


# --- tiny helpers ----------------------------------------------------------
def _pt_tup(p: Point | Tuple[float, float]) -> Tuple[float, float]:
    return (float(p.x()), float(p.y())) if isinstance(p, Point) else p


def _sort_ccw_around(a: Tuple[float, float], neigh: List[Tuple[float, float]]):
    ax, ay = a
    return sorted(
        neigh,
        key=lambda p: math.atan2(p[1] - ay, p[0] - ax)
    )


# --- main routine ----------------------------------------------------------
def extract_faces_of_grid(
    poly: Polygon,
    v_segments: List[Segment],
    h_segments: List[Segment],
    global_points: List[Tuple[float, float]],
) -> List[Dict]:
    """
    Find all bounded faces of  (boundary ∪ v_segments ∪ h_segments).

    It works entirely in Python (floating‑point *is* OK here because
    every vertex comes from exact construction):
       • boundary vertices are integer
       • Steiner vertices are rational combinations of those integers
    """

    # ------------------------------------------------------------------ #
    # 1. Build the *undirected* adjacency map of the grid
    # ------------------------------------------------------------------ #
    adj: Dict[Tuple[float, float], List[Tuple[float, float]]] = {}

    def _add_edge(p: Tuple[float, float], q: Tuple[float, float]):
        if p == q:
            return
        adj.setdefault(p, []).append(q)
        adj.setdefault(q, []).append(p)

    #  boundary ----------------------------------------------------------
    B = poly.boundary()
    for i in range(len(B)):
        _add_edge(_pt_tup(B[i]), _pt_tup(B[(i + 1) % len(B)]))

    #  grid segments -----------------------------------------------------
    for seg in v_segments + h_segments:
        _add_edge(_pt_tup(seg.source()), _pt_tup(seg.target()))

    #  sort neighbours CCW around each vertex (needed for face walk)
    for v, nbrs in adj.items():
        adj[v] = _sort_ccw_around(v, nbrs)

    # ------------------------------------------------------------------ #
    # 2. Walk every edge in CCW order exactly once -> bounded faces
    # ------------------------------------------------------------------ #
    used_directed: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    faces: List[List[Tuple[float, float]]] = []

    for v in adj:
        for w in adj[v]:
            if (v, w) in used_directed:          # edge already on some face
                continue

            face = [v]
            prev, curr = v, w
            while True:
                used_directed.add((prev, curr))
                nbrs = adj[curr]
                # take next neighbour CCW after 'prev'
                idx = (nbrs.index(prev) - 1) % len(nbrs)   # -1 ⇒ CCW
                nxt = nbrs[idx]

                if curr == v and nxt == w:  # closed the loop
                    break
                face.append(curr)
                prev, curr = curr, nxt

            # reject the outer (unbounded) face – it contains all boundary pts
            if all(_pt_tup(b) in face for b in B):
                continue
            faces.append(face)

    # ------------------------------------------------------------------ #
    # 3. Classify each face (Lemma 5)
    # ------------------------------------------------------------------ #
    from geometry_utils import _classify_face  # you already wrote this

    regions: List[Dict] = []
    for face in faces:
        # convert to CGAL Points for classification
        face_pts = [Point(FieldNumber(x), FieldNumber(y)) for x, y in face]
        ftype    = _classify_face(face_pts, poly)

        # map to global_points list
        idx_list = []
        for pt in face:
            if pt not in global_points:
                global_points.append(pt)
            idx_list.append(global_points.index(pt))

        regions.append({"type": ftype, "indices": idx_list})

    return regions
def split_slab_diag(
    slab_idx: List[int],               # exactly four vertex indices, CCW order
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Split a *slab* (two vertical edges, top & bottom possibly tilted)
    into two triangles by inserting the safe diagonal (v1 ➜ v3).

    Parameters
    ----------
    slab_idx : list[int]
        CCW indices of the four slab corners ::
            v0 ---- v1              v0 = left‑bottom
             |      |               v1 = left‑top
             |      |               v2 = right‑top
            v3 ---- v2              v3 = right‑bottom

    Returns
    -------
    triA, triB : Tuple[int,int,int]
        Two index‑triples whose union is the slab
        (both oriented CCW, hence positive area).
    """
    if len(slab_idx) != 4:
        raise ValueError("slab_idx must contain *exactly* four indices")

    # unpack for clarity
    v0, v1, v2, v3 = slab_idx

    # Insert diagonal (v1 → v3).  For a vertical slab this is always inside;
    # no geometric test required.
    #
    # CCW orientation:
    #   Triangle A : v0‑v1‑v3
    #   Triangle B : v1‑v2‑v3
    tri_A = (v0, v1, v3)
    tri_B = (v1, v2, v3)

    return tri_A, tri_B


def _to_exact_repr(val: float | int) -> str | int:
    """Return an int if val is integral, otherwise an exact rational string."""
    if float(val).is_integer():
        return int(round(val))  # e.g. 2.0 -> 2
    frac = Fraction(str(val)).limit_denominator()
    return f"{frac.numerator}/{frac.denominator}"  # e.g. 0.666… -> '2/3'