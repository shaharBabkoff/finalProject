from fractions import Fraction
from typing import Tuple, List, Literal, Dict
import math
from cgshop2025_pyutils.geometry import Point, FieldNumber, Polygon, Segment
EPS_INSIDE = 1e-9
EPS = 1e-10
FaceType = Literal["RECTANGLE", "RIGHT_TRI", "OBTUSE_TRI", "SLAB"]


def build_polygon_from_indices(index_list: list[int],
                               coordinates: list[tuple[float, float]]) -> Polygon:

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


def _q(v: float, eps: float) -> int:
    return int(round(v / eps))


def feq(a: float, b: float, eps: float) -> bool:
    return abs(a - b) <= eps


def _uniq_by_y(pts: List[Point], EPS: float) -> List[Point]:
    """Deduplicate by y (snapped) and keep first occurrence."""
    seen = set()
    out: List[Point] = []
    for p in pts:
        ky = _q(float(p.y()), EPS)
        if ky not in seen:
            seen.add(ky)
            out.append(p)
    return out


def _as_tuple(p: Point) -> tuple[float, float]:
    return float(p.x()), float(p.y())


def _merge_collinear_segments_vertical(segs: List[Segment], EPS: float) -> List[Segment]:
    """
    Merge overlapping vertical segments that share (snapped) x.
    Assumes general position; keeps closed intervals.
    """
    buckets = {}
    for s in segs:
        x = float(s.source().x())
        y1 = float(s.source().y())
        y2 = float(s.target().y())
        if y2 < y1:
            y1, y2 = y2, y1
            src, tgt = s.target(), s.source()
        else:
            src, tgt = s.source(), s.target()
        key = _q(x, EPS)
        buckets.setdefault(key, []).append((x, y1, y2, src, tgt))

    out: List[Segment] = []
    for key, items in buckets.items():
        items.sort(key=lambda t: t[1])  # by y1
        cur_x, cur_y1, cur_y2, cur_src, cur_tgt = items[0]
        for (x, y1, y2, src, tgt) in items[1:]:
            if feq(x, cur_x, EPS) and y1 <= cur_y2 + EPS:  # overlap / touch
                # extend
                if y2 > cur_y2:
                    cur_y2 = y2
                    cur_tgt = tgt if float(tgt.y()) >= cur_y2 - EPS else cur_tgt
            else:
                out.append(Segment(cur_src, cur_tgt))
                cur_x, cur_y1, cur_y2, cur_src, cur_tgt = x, y1, y2, src, tgt
        out.append(Segment(cur_src, cur_tgt))
    return out


def make_vertical_grid(poly: Polygon, *, EPS: float = 1e-12) -> Tuple[List[Segment], List[tuple[float, float]]]:
    """Return maximal vertical slices through every boundary vertex (outer boundary only)."""
    boundary_pts: List[Point] = poly.boundary()  # CCW
    n = len(boundary_pts)

    v_segments: List[Segment] = []
    steiner_pts: List[tuple[float, float]] = []

    boundary_xy = {(_q(float(p.x()), EPS), _q(float(p.y()), EPS)) for p in boundary_pts}

    for v in boundary_pts:
        x_fnum = v.x()                # exact x
        xv = float(x_fnum)
        yv = float(v.y())

        up_hits:   List[Point] = []
        down_hits: List[Point] = []

        for i in range(n):
            a = boundary_pts[i]
            b = boundary_pts[(i + 1) % n]

            # skip edges incident to v (they touch v)
            if a == v or b == v:
                continue

            ax, ay = float(a.x()), float(a.y())
            bx, by = float(b.x()), float(b.y())

            # vertical boundary edge -> ignore here (handled later via walls)
            if feq(ax, bx, EPS):
                continue

            # x-range overlap?
            if not (min(ax, bx) - EPS <= xv <= max(ax, bx) + EPS):
                continue

            denom = (bx - ax)
            if abs(denom) <= EPS:
                continue
            t = (xv - ax) / denom

            # accept interior or endpoint hits (unless that endpoint is v)
            if t < -EPS or t > 1 + EPS:
                continue

            # clamp tiny overshoots
            tt = min(1.0, max(0.0, t))
            y_int = ay + tt * (by - ay)
            p_int = Point(x_fnum, FieldNumber(y_int))

            # if it lands exactly on a or b which equals v, skip
            if (tt <= EPS and a == v) or (tt >= 1.0 - EPS and b == v):
                continue

            if y_int > yv + EPS:
                up_hits.append(p_int)
            elif y_int < yv - EPS:
                down_hits.append(p_int)
            # equal y → would be v (incident edges were skipped)

        # dedup same-Y double hits at vertices
        up_hits   = _uniq_by_y(up_hits, EPS)
        down_hits = _uniq_by_y(down_hits, EPS)

        # If no hit in a direction, try to find boundary vertex collinear above/below v
        if not up_hits:
            up_hits = [p for p in boundary_pts
                       if feq(float(p.x()), xv, EPS) and float(p.y()) > yv + EPS]
        if not down_hits:
            down_hits = [p for p in boundary_pts
                         if feq(float(p.x()), xv, EPS) and float(p.y()) < yv - EPS]

        # choose nearest above / below
        up_point   = min(up_hits,   key=lambda p: float(p.y())) if up_hits else v
        down_point = max(down_hits, key=lambda p: float(p.y())) if down_hits else v

        if up_point == down_point:
            continue

        # keep only if inside
        if not _segment_axis_aligned_is_inside(poly, down_point, up_point):
            continue

        seg = Segment(down_point, up_point)
        v_segments.append(seg)  # (only once)

        # Steiner points = interior points only (not original boundary vertices)
        dp = _as_tuple(down_point); up = _as_tuple(up_point); vv = _as_tuple(v)
        if dp != vv and (_q(dp[0], EPS), _q(dp[1], EPS)) not in boundary_xy:
            steiner_pts.append(dp)
        if up != vv and (_q(up[0], EPS), _q(up[1], EPS)) not in boundary_xy:
            steiner_pts.append(up)

    # Merge overlapping verticals on same x
    v_segments = _merge_collinear_segments_vertical(v_segments, EPS)
    return v_segments, steiner_pts


def _poly_boundary_xy(poly: Polygon) -> list[tuple[float, float]]:
    return [(float(p.x()), float(p.y())) for p in poly.boundary()]


def _point_in_polygon_half_open(px: float, py: float,
                                boundary_xy: list[tuple[float, float]],
                                eps: float = EPS_INSIDE) -> bool:

    inside = False
    n = len(boundary_xy)
    for i in range(n):
        (x1, y1) = boundary_xy[i]
        (x2, y2) = boundary_xy[(i + 1) % n]
        if abs(y2 - y1) <= eps:
            continue

        y_lo, y_hi = (y1, y2) if y1 < y2 else (y2, y1)
        if not (py >= y_lo - eps and py < y_hi - eps):
            continue


        t = (py - y1) / (y2 - y1)
        x_at = x1 + t * (x2 - x1)
        if x_at > px + eps:
            inside = not inside
    return inside


def _segment_axis_aligned_is_inside(poly: Polygon,
                                    a: Point, b: Point,
                                    eps: float = EPS_INSIDE) -> bool:

    mx = 0.5 * (float(a.x()) + float(b.x()))
    my = 0.5 * (float(a.y()) + float(b.y()))
    boundary_xy = _poly_boundary_xy(poly)
    return _point_in_polygon_half_open(mx, my, boundary_xy, eps)


def _seg_key_axis_aligned(p: Point, q: Point, EPS: float):
    """Return a hashable key for an axis-aligned segment, order-independent."""
    x1, y1 = float(p.x()), float(p.y())
    x2, y2 = float(q.x()), float(q.y())
    if abs(y1 - y2) <= EPS:  # horizontal
        if x2 < x1:
            x1, x2 = x2, x1
        return ("H", _q(y1, EPS), _q(x1, EPS), _q(x2, EPS))
    else:  # vertical (not used here, but kept for consistency)
        if y2 < y1:
            y1, y2 = y2, y1
        return ("V", _q(x1, EPS), _q(y1, EPS), _q(y2, EPS))


def make_horizontal_grid(poly: Polygon, v_segments: List[Segment], *, EPS: float = 1e-12) -> Tuple[List[Segment], List[tuple[float, float]]]:
    boundary_pts = poly.boundary()
    n = len(boundary_pts)

    # vertical walls = interior verticals + vertical boundary edges
    vertical_walls: List[Segment] = list(v_segments)
    for i in range(n):
        a, b = boundary_pts[i], boundary_pts[(i + 1) % n]
        if abs(float(a.x()) - float(b.x())) <= EPS:  # vertical boundary edge
            vertical_walls.append(Segment(a, b))

    # slab vertices = boundary vertices + endpoints of vertical walls
    slab_vertices: List[Point] = list(boundary_pts)
    for seg in vertical_walls:
        slab_vertices.append(seg.source())
        slab_vertices.append(seg.target())

    # deduplicate slab vertices
    def _dedup_points(pts: List[Point], EPS: float) -> List[Point]:
        seen = set()
        out = []
        for p in pts:
            key = (_q(float(p.x()), EPS), _q(float(p.y()), EPS))
            if key not in seen:
                seen.add(key)
                out.append(p)
        return out

    slab_vertices = _dedup_points(slab_vertices, EPS)

    h_segments: List[Segment] = []
    steiner_pts: List[tuple[float, float]] = []
    seen_h = set()  # to avoid duplicates

    for v in slab_vertices:
        y_fnum = v.y()
        yv = float(y_fnum)
        xv = float(v.x())

        left_hits: List[Point] = []
        right_hits: List[Point] = []

        # check intersections with vertical walls
        for seg in vertical_walls:
            sy, ty = float(seg.source().y()), float(seg.target().y())
            seg_x = float(seg.source().x())  # same x for vertical
            if not (min(sy, ty) - EPS <= yv <= max(sy, ty) + EPS):
                continue
            p_int = Point(FieldNumber(seg_x), y_fnum)
            if p_int == v:
                continue
            if seg_x > xv + EPS:
                right_hits.append(p_int)
            elif seg_x < xv - EPS:
                left_hits.append(p_int)

        # fallback: nearest slab vertex on same y
        if not left_hits:
            left_hits = [p for p in slab_vertices if abs(float(p.y()) - yv) <= EPS and float(p.x()) < xv - EPS]
        if not right_hits:
            right_hits = [p for p in slab_vertices if abs(float(p.y()) - yv) <= EPS and float(p.x()) > xv + EPS]

        # choose farthest
        left_point  = min(left_hits,  key=lambda p: float(p.x())) if left_hits  else v
        right_point = max(right_hits, key=lambda p: float(p.x())) if right_hits else v

        # build segments
        if left_point != v:
            segL = Segment(v, left_point)
            if _segment_axis_aligned_is_inside(poly, v, left_point):
                key = _seg_key_axis_aligned(v, left_point, EPS)
                if key not in seen_h:
                    seen_h.add(key)
                    h_segments.append(segL)
                    steiner_pts.append(_as_tuple(left_point))

        if right_point != v:
            segR = Segment(v, right_point)
            if _segment_axis_aligned_is_inside(poly, v, right_point):
                key = _seg_key_axis_aligned(v, right_point, EPS)
                if key not in seen_h:
                    seen_h.add(key)
                    h_segments.append(segR)
                    steiner_pts.append(_as_tuple(right_point))

    return h_segments, steiner_pts


def _eq(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


def _dot(ax, ay, bx, by): return ax*bx + ay*by


def _angle_is_right_at(a: Tuple[float,float], b: Tuple[float,float], c: Tuple[float,float]) -> bool:
    # ∠ABC right ⇔ (BA · BC) ≈ 0
    bax, bay = a[0]-b[0], a[1]-b[1]
    bcx, bcy = c[0]-b[0], c[1]-b[1]
    return abs(_dot(bax, bay, bcx, bcy)) <= 1e-12


def _angle_is_obtuse_at(a: Tuple[float,float], b: Tuple[float,float], c: Tuple[float,float]) -> bool:
    # ∠ABC obtuse ⇔ (BA · BC) < 0
    bax, bay = a[0]-b[0], a[1]-b[1]
    bcx, bcy = c[0]-b[0], c[1]-b[1]
    return _dot(bax, bay, bcx, bcy) < -1e-12


def _signed_area(poly_xy: List[Tuple[float,float]]) -> float:
    s = 0.0
    for i in range(len(poly_xy)):
        x1,y1 = poly_xy[i]
        x2,y2 = poly_xy[(i+1) % len(poly_xy)]
        s += x1*y2 - x2*y1
    return 0.5 * s


def _sort_ccw_centered(center: Tuple[float, float], pts: List[Tuple[float, float]]):
    cx, cy = center
    return sorted(pts, key=lambda p: math.atan2(p[1]-cy, p[0]-cx))


# ---------- Lemma 5 classifier (expects simplified, CCW face) ----------
def _classify_face_lemma5(
    face_xy: List[Tuple[float,float]],
    boundary_edges: set[Tuple[Tuple[float,float], Tuple[float,float]]],
) -> FaceType:
    n = len(face_xy)

    # count axis-aligned and boundary edges
    vert_cnt = hori_cnt = bound_cnt = 0
    edges = []
    for i in range(n):
        p = face_xy[i]; q = face_xy[(i+1) % n]
        edges.append((p, q))
        if _eq(p[0], q[0]): vert_cnt += 1
        if _eq(p[1], q[1]): hori_cnt += 1
        if _edge_key(p, q) in boundary_edges: bound_cnt += 1

    # (1) rectangle: 4 corners, two V + two H, no boundary edges
    if n == 4 and vert_cnt == 2 and hori_cnt == 2 and bound_cnt == 0:
        return "RECTANGLE"

    # (2) RIGHT_TRI: 3 vertices, the triangle is right-angled and its hypotenuse is a boundary edge
    if n == 3:
        A, B, C = face_xy
        # test right angle and identify hypotenuse (edge opposite the right angle)
        right_at = None
        if _angle_is_right_at(B, A, C): right_at = 0  # angle at A
        elif _angle_is_right_at(A, B, C): right_at = 1  # angle at B
        elif _angle_is_right_at(A, C, B): right_at = 2  # angle at C

        if right_at is not None:
            # hypotenuse is between the other two vertices
            opp = {(0):(B,C), (1):(A,C), (2):(A,B)}[right_at]
            if _edge_key(*opp) in boundary_edges:
                return "RIGHT_TRI"

        # (3) OBTUSE_TRI: two boundary edges and obtuse at the non-boundary vertex
        if bound_cnt == 2:
            # the apex is the sole vertex not incident to both boundary edges
            # we can just check if any angle is obtuse
            if (_angle_is_obtuse_at(B, A, C) or
                _angle_is_obtuse_at(A, B, C) or
                _angle_is_obtuse_at(A, C, B)):
                return "OBTUSE_TRI"

        # fallback (rare numeric edge cases): treat as RIGHT
        return "RIGHT_TRI"

    # (4) SLAB: 4 corners, exactly two boundary edges and two vertical edges whose y-intervals do NOT overlap
    if n == 4 and bound_cnt == 2 and vert_cnt == 2:
        xs = [p[0] for p in face_xy]
        xmin, xmax = min(xs), max(xs)
        left  = sorted([p for p in face_xy if _eq(p[0], xmin)], key=lambda t: t[1])
        right = sorted([p for p in face_xy if _eq(p[0], xmax)], key=lambda t: t[1])
        if len(left) == 2 and len(right) == 2:
            L_lo, L_hi = left[0][1], left[1][1]
            R_lo, R_hi = right[0][1], right[1][1]
            if L_hi < R_lo - EPS or R_hi < L_lo - EPS:
                return "SLAB"

    # general fallback
    return "SLAB"


def _annotate_vertical_subdiv(face_idxs: List[int],
                              all_points: List[Tuple[float,float]]) -> Dict:
    P = [all_points[i] for i in face_idxs]
    xs = [p[0] for p in P]
    meta = {"vertical_legs": [], "subdiv": {"left": [], "right": []}}
    n = len(face_idxs)

    # determine left/right x of this face
    xmin, xmax = min(xs), max(xs)

    # collect vertical edges and their interior points (if any)
    for k in range(n):
        i, j = face_idxs[k], face_idxs[(k+1) % n]
        pi, pj = all_points[i], all_points[j]
        if _eq(pi[0], pj[0]):
            meta["vertical_legs"].append((i, j))
            x = pi[0]
            ylo, yhi = sorted((pi[1], pj[1]))
            # interior points on same x strictly between endpoints
            for t, pt in enumerate(all_points):
                if _eq(pt[0], x) and (ylo + EPS) < pt[1] < (yhi - EPS) and t not in (i, j):
                    side = "left" if _eq(x, xmin) else ("right" if _eq(x, xmax) else "left")
                    meta["subdiv"][side].append(t)
    return meta


def _edge_key(p, q):
    # direction-independent key
    return (p, q) if (p < q) else (q, p)


def _split_segments_into_planar_edges(
    poly: Polygon,
    v_segments: List[Segment],
    h_segments: List[Segment],
):
    """
    Returns:
      adj: dict[Tuple[float,float], List[Tuple[float,float]]]  # CCW-sorted neighbours
      boundary_edges: set[Tuple[Tuple[float,float], Tuple[float,float]]]  # undirected boundary sub-edges
    """
    # --- boundary as float tuples (CCW) ---
    boundary_xy: List[Tuple[float, float]] = [(float(p.x()), float(p.y())) for p in poly.boundary()]
    mB = len(boundary_xy)

    # --- pack verticals & horizontals (as ranges) ---
    V = []  # (x, ylo, yhi)
    for s in v_segments:
        x = float(s.source().x())
        y1 = float(s.source().y()); y2 = float(s.target().y())
        ylo, yhi = (y1, y2) if y1 <= y2 else (y2, y1)
        V.append((x, ylo, yhi))

    H = []  # (y, xlo, xhi)
    for s in h_segments:
        y = float(s.source().y())
        x1 = float(s.source().x()); x2 = float(s.target().x())
        xlo, xhi = (x1, x2) if x1 <= x2 else (x2, x1)
        H.append((y, xlo, xhi))

    # --- split points along vertical segments (by H and boundary edges) ---
    v_points: Dict[Tuple[float, float, float], List[Tuple[float, float]]] = {}
    for (x, ylo, yhi) in V:
        pts = [(x, ylo), (x, yhi)]

        # intersections with horizontals
        for (y, xlo, xhi) in H:
            if (ylo - EPS) <= y <= (yhi + EPS) and (xlo - EPS) <= x <= (xhi + EPS):
                pts.append((x, y))

        # intersections with boundary edges
        for i in range(mB):
            ax, ay = boundary_xy[i]
            bx, by = boundary_xy[(i + 1) % mB]

            # vertical boundary edge exactly at x
            if _eq(ax, bx) and _eq(ax, x):
                ylo_e, yhi_e = (ay, by) if ay <= by else (by, ay)
                yL = max(ylo, ylo_e); yU = min(yhi, yhi_e)
                if yL <= yU:
                    pts.extend([(x, yL), (x, yU)])
                continue

            # general edge crossing x
            if (min(ax, bx) - EPS) <= x <= (max(ax, bx) + EPS) and not _eq(ax, bx):
                t = (x - ax) / (bx - ax)
                if -EPS <= t <= 1 + EPS:
                    y_int = ay + t * (by - ay)
                    if (ylo - EPS) <= y_int <= (yhi + EPS):
                        pts.append((x, y_int))

        pts = sorted(set(pts), key=lambda p: p[1])  # by y
        v_points[(x, ylo, yhi)] = pts

    # --- split points along horizontal segments (by V and boundary edges) ---
    h_points: Dict[Tuple[float, float, float], List[Tuple[float, float]]] = {}
    for (y, xlo, xhi) in H:
        pts = [(xlo, y), (xhi, y)]

        # intersections with verticals
        for (x, ylo, yhi) in V:
            if (xlo - EPS) <= x <= (xhi + EPS) and (ylo - EPS) <= y <= (yhi + EPS):
                pts.append((x, y))

        # intersections with boundary edges
        for i in range(mB):
            ax, ay = boundary_xy[i]
            bx, by = boundary_xy[(i + 1) % mB]

            # horizontal boundary edge exactly at y
            if _eq(ay, by) and _eq(ay, y):
                xlo_e, xhi_e = (ax, bx) if ax <= bx else (bx, ax)
                xL = max(xlo, xlo_e); xU = min(xhi, xhi_e)
                if xL <= xU:
                    pts.extend([(xL, y), (xU, y)])
                continue

            # general edge crossing y
            if (min(ay, by) - EPS) <= y <= (max(ay, by) + EPS) and not _eq(ay, by):
                t = (y - ay) / (by - ay)
                if -EPS <= t <= 1 + EPS:
                    x_int = ax + t * (bx - ax)
                    if (xlo - EPS) <= x_int <= (xhi + EPS):
                        pts.append((x_int, y))

        pts = sorted(set(pts), key=lambda p: p[0])  # by x
        h_points[(y, xlo, xhi)] = pts

    # --- split points along boundary edges (by V and H) -> b_points ---
    b_points: List[List[Tuple[float, float]]] = []  # one split-list per boundary edge
    for i in range(mB):
        ax, ay = boundary_xy[i]
        bx, by = boundary_xy[(i + 1) % mB]
        pts = [(ax, ay), (bx, by)]

        # with verticals
        for (x, ylo, yhi) in V:
            if (min(ax, bx) - EPS) <= x <= (max(ax, bx) + EPS):
                if not _eq(ax, bx):
                    t = (x - ax) / (bx - ax)
                    if -EPS <= t <= 1 + EPS:
                        y_int = ay + t * (by - ay)
                        if (ylo - EPS) <= y_int <= (yhi + EPS):
                            pts.append((x, y_int))
                else:
                    # collinear vertical boundary edge; clamp against V range
                    ylo_e, yhi_e = (ay, by) if ay <= by else (by, ay)
                    yL = max(ylo, ylo_e); yU = min(yhi, yhi_e)
                    if yL <= yU:
                        pts.extend([(x, yL), (x, yU)])

        # with horizontals
        for (y, xlo, xhi) in H:
            if (min(ay, by) - EPS) <= y <= (max(ay, by) + EPS):
                if not _eq(ay, by):
                    t = (y - ay) / (by - ay)
                    if -EPS <= t <= 1 + EPS:
                        x_int = ax + t * (bx - ax)
                        if (xlo - EPS) <= x_int <= (xhi + EPS):
                            pts.append((x_int, y))
                else:
                    # collinear horizontal boundary edge; clamp against H range
                    xlo_e, xhi_e = (ax, bx) if ax <= bx else (bx, ax)
                    xL = max(xlo, xlo_e); xU = min(xhi, xhi_e)
                    if xL <= xU:
                        pts.extend([(xL, y), (xU, y)])

        # dedup & sort along the boundary edge by parameter
        if _eq(ax, bx):      # vertical edge -> sort by y
            pts = sorted(set(pts), key=lambda p: p[1])
        elif _eq(ay, by):    # horizontal edge -> sort by x
            pts = sorted(set(pts), key=lambda p: p[0])
        else:
            # general: sort by t along segment AB
            pts = sorted(set(pts), key=lambda p: (p[0] - ax) / (bx - ax))
        b_points.append(pts)

    # --- build adjacency and boundary_edges set ---
    adj: Dict[Tuple[float, float], List[Tuple[float, float]]] = {}
    boundary_edges: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()

    def _add_edge(p: Tuple[float, float], q: Tuple[float, float]) -> None:
        if _eq(p[0], q[0]) and _eq(p[1], q[1]):
            return
        adj.setdefault(p, []).append(q)
        adj.setdefault(q, []).append(p)

    # boundary edges (split) — also collect in boundary_edges
    for pts in b_points:
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            _add_edge(a, b)
            boundary_edges.add(_edge_key(a, b))

    # vertical edges (split)
    for pts in v_points.values():
        for i in range(len(pts) - 1):
            _add_edge(pts[i], pts[i + 1])

    # horizontal edges (split)
    for pts in h_points.values():
        for i in range(len(pts) - 1):
            _add_edge(pts[i], pts[i + 1])

    # CCW sort neighbours
    for v, nbrs in adj.items():
        adj[v] = _sort_ccw_centered(v, list(set(nbrs)))

    return adj, boundary_edges


def _pt_tup(p: Point | Tuple[float, float]) -> Tuple[float, float]:
    return (float(p.x()), float(p.y())) if isinstance(p, Point) else (float(p[0]), float(p[1]))


def _collinear(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
    (x1,y1),(x2,y2),(x3,y3) = a,b,c
    return abs((x2-x1)*(y3-y1) - (y2-y1)*(x3-x1)) <= EPS


def _simplify_collinear_cycle(cycle: List[Tuple[float,float]]) -> List[Tuple[float,float]]:
    if len(cycle) <= 3:
        return cycle[:]
    out = []
    m = len(cycle)
    for i in range(m):
        prev = cycle[(i-1) % m]
        cur  = cycle[i]
        nxt  = cycle[(i+1) % m]
        if _collinear(prev, cur, nxt):
            continue
        out.append(cur)
    return out if len(out) >= 3 else cycle[:]


# ---------- MAIN: extract faces, classify, map to indices ----------
def extract_faces_of_grid(
    poly: Polygon,
    v_segments: List[Segment],
    h_segments: List[Segment],
    global_points: List[Tuple[float, float]],
    *,
    EPS: float = 1e-12,
) -> List[Dict]:
    """
    Build planar graph from boundary ∪ V ∪ H (with all intersections split),
    walk all bounded faces (LEFT-face rule), simplify collinear runs,
    classify (Lemma 5), and return regions (with indices + meta).
    Improvements vs. previous version:
      - Drops *all* boundary rings (outer + holes), not just the outer face.
      - Uses EPS-quantized keys for cycle/edge equality.
      - O(1) point->index map for global_points.
    """

    # --- tiny quantization helpers ---
    q = lambda v: int(round(v / EPS))
    def qxy(x: float, y: float) -> Tuple[int, int]:
        return (q(x), q(y))

    # ---------- local helper ----------
    def _same_cycle_eps(a: List[Tuple[float, float]],
                        b: List[Tuple[float, float]]) -> bool:
        """a == b up to cyclic rotation/reversal using EPS-quantized coords."""
        if len(a) != len(b):
            return False
        A = [qxy(x, y) for (x, y) in a]
        B = [qxy(x, y) for (x, y) in b]
        # forward rotations
        for s in range(len(B)):
            if A == B[s:] + B[:s]:
                return True
        # reversed rotations
        Br = list(reversed(B))
        for s in range(len(Br)):
            if A == Br[s:] + Br[:s]:
                return True
        return False

    # ---------- 1) planar adjacency (+ boundary sub-edges) ----------
    adj, boundary_edges = _split_segments_into_planar_edges(poly, v_segments, h_segments)
    # REQUIREMENTS:
    #  - adj[v] neighbors are sorted CCW for the LEFT-face rule
    #  - boundary_edges contains undirected edges split at all intersections
    #  - boundary_edges keys should be normalized & EPS-robust

    # ---------- 2) half-edge face walk (LEFT-face rule) ----------
    used_dir: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    faces_xy: List[List[Tuple[float, float]]] = []

    for v in adj:
        for w in adj[v]:
            if (v, w) in used_dir:
                continue
            face = [v]
            prev, curr = v, w
            while True:
                used_dir.add((prev, curr))
                nbrs = adj[curr]
                k = nbrs.index(prev)  # prev must be neighbor (adj is consistent)
                # pick neighbor immediately BEFORE 'prev' in CCW order => turn LEFT
                nxt = nbrs[(k - 1) % len(nbrs)]
                if curr == v and nxt == w:
                    break
                face.append(curr)
                prev, curr = curr, nxt
            faces_xy.append(face)

    # ---------- 3) collect *all* boundary rings (outer + holes) ----------
    # CGAL binding for Polygon here: assume .boundary() returns all rings concatenated,
    # or (if your helper exposes them separately) pass them in. If you only have the
    # outer ring via poly.boundary(), add your hole rings here as needed.
    #
    # Below: we build a list of all ring cycles to exclude. If you already have
    # outer CCW and each hole CW as separate lists, set `boundary_rings_xy` to that.
    boundary_rings_xy: List[List[Tuple[float, float]]] = []

    # OUTER ring (CCW)
    outer_xy = [(float(p.x()), float(p.y())) for p in poly.boundary()]
    if outer_xy:
        boundary_rings_xy.append(outer_xy)

    # If you have accessors for holes, add them; otherwise, keep as-is.
    # Example placeholder:
    # for hole in poly.holes():  # if available
    #     ring_xy = [(float(p.x()), float(p.y())) for p in hole]  # likely CW
    #     boundary_rings_xy.append(ring_xy)

    # ---------- 4) drop boundary rings and keep only CCW (bounded) faces ----------
    bounded_faces_xy: List[List[Tuple[float, float]]] = []
    for f in faces_xy:
        # Drop any face that equals any boundary ring (outer OR hole)
        if any(_same_cycle_eps(f, R) for R in boundary_rings_xy):
            continue
        # keep only CCW faces as interior regions
        if _signed_area(f) > 0:
            bounded_faces_xy.append(f)

    # ---------- 5) simplify, classify (Lemma 5), map to indices, annotate ----------
    regions: List[Dict] = []

    # Build a fast (x,y)->index map for global_points
    idx_map: Dict[Tuple[int, int], int] = {qxy(x, y): i for i, (x, y) in enumerate(global_points)}

    for face in bounded_faces_xy:
        simp = _simplify_collinear_cycle(face)  # must preserve CCW
        if len(simp) < 3:
            continue

        # classification uses boundary sub-edges AFTER splitting
        ftype = _classify_face_lemma5(simp, boundary_edges)

        # map coords → global indices (append if new) using EPS-quantized dict
        idxs: List[int] = []
        for (x, y) in simp:
            key = qxy(x, y)
            found = idx_map.get(key)
            if found is None:
                global_points.append((x, y))
                found = len(global_points) - 1
                idx_map[key] = found
            idxs.append(found)

        region: Dict = {"type": ftype, "indices": idxs}
        if ftype in ("RIGHT_TRI", "OBTUSE_TRI", "SLAB"):
            region["meta"] = _annotate_vertical_subdiv(idxs, global_points)

        regions.append(region)

    return regions


def _to_exact_repr(val: float | int) -> str | int:
    """Return an int if val is integral, otherwise an exact rational string."""
    if float(val).is_integer():
        return int(round(val))  # e.g. 2.0 -> 2
    frac = Fraction(str(val)).limit_denominator()
    return f"{frac.numerator}/{frac.denominator}"