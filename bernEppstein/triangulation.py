from typing import List, Tuple, Optional
from cgshop2025_pyutils.geometry import Point
import math


def triangle_is_non_obtuse(a, b, c, pts, eps=1e-12):
    pa, pb, pc = pts[a], pts[b], pts[c]
    ab2 = sqdist(pa, pb); bc2 = sqdist(pb, pc); ca2 = sqdist(pc, pa)
    # angle at A obtuse iff |AB|^2 + |AC|^2 < |BC|^2
    if ab2 + ca2 + eps < bc2: return False
    if ab2 + bc2 + eps < ca2: return False
    if bc2 + ca2 + eps < ab2: return False
    return True


def sqdist(p, q):
    dx, dy = p[0]-q[0], p[1]-q[1]
    return dx*dx + dy*dy


def conformize_mesh(tris: List[Tuple[int,int,int]],
                    P: List[Tuple[float,float]],
                    eps: float = 1e-12) -> List[Tuple[int,int,int]]:
    changed = True
    out = tris[:]
    while changed:
        changed = False
        new_out: List[Tuple[int,int,int]] = []
        for (i, j, k) in out:
            mids_ij = _interior_points_on_seg(i, j, P, eps)
            mids_jk = _interior_points_on_seg(j, k, P, eps)
            mids_ki = _interior_points_on_seg(k, i, P, eps)

            if mids_ij or mids_jk or mids_ki:
                new_out.extend(_conformize_triangle(i, j, k, P, eps))
                changed = True
            else:
                new_out.append(_orient_ccw(i, j, k, P, eps))
        out = new_out
    return out


def _orient_ccw(i, j, k, P, eps=1e-12):
    Ax,Ay = P[i]; Bx,By = P[j]; Cx,Cy = P[k]
    s = (Bx-Ax)*(Cy-Ay) - (By-Ay)*(Cx-Ax)
    return (i,j,k) if s > 0 else (i,k,j)


def _interior_points_on_seg(i: int, j: int, P: List[Tuple[float, float]], eps: float = 1e-12) -> List[int]:
    Xi, Yi = P[i]; Xj, Yj = P[j]
    res: List[Tuple[int, float]] = []
    for t_idx, (x, y) in enumerate(P):
        if t_idx == i or t_idx == j:
            continue

        if abs((Xj - Xi) * (y - Yi) - (Yj - Yi) * (x - Xi)) > eps:
            continue

        dx, dy = (Xj - Xi), (Yj - Yi)
        if abs(dx) >= abs(dy):
            if abs(dx) > eps:
                tpar = (x - Xi) / dx
            else:
                if abs(dy) <= eps:
                    continue
                tpar = (y - Yi) / dy
        else:
            if abs(dy) > eps:
                tpar = (y - Yi) / dy
            else:
                if abs(dx) <= eps:
                    continue
                tpar = (x - Xi) / dx
        if eps < tpar < 1.0 - eps:
            res.append((t_idx, tpar))
    res.sort(key=lambda it: it[1])
    return [t for (t, _) in res]


def _conformize_triangle(i, j, k, P, eps=1e-12):
    stack = [(i, j, k)]
    out = []
    while stack:
        a, b, c = stack.pop()
        for (u, v, w) in ((a,b,c), (b,c,a), (c,a,b)):
            mids = _interior_points_on_seg(u, v, P, eps)
            if mids:
                prev = u
                for p in mids:
                    stack.append(_orient_ccw(prev, p, w, P, eps))
                    prev = p
                stack.append(_orient_ccw(prev, v, w, P, eps))
                break
        else:
            out.append(_orient_ccw(a, b, c, P, eps))
    return out


def _area2(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _ensure_ccw_quad(idx: List[int], P: List[Tuple[float, float]]) -> List[int]:
    a,b,c,d = idx
    if _area2(P[a], P[b], P[c]) < 0.0:
        return [a, d, c, b]
    return idx


def triangulate_rectangle(indices: List[int],
                          points: List[Tuple[float, float]],
                          eps: float = 1e-12) -> List[Tuple[int, int, int]]:

    assert len(indices) == 4, "rectangle must have 4 vertices"

    # --- ensure CCW order of the quad (uses your helper) ---
    a, b, c, d = _ensure_ccw_quad(indices, points)

    # --- candidate splits: diagonal AC or BD (two triangles each) ---
    tris_ac = [(a, b, c), (a, c, d)]
    tris_bd = [(b, c, d), (b, d, a)]

    # --- angle helpers ---
    def angle_at(Bi: int, Ai: int, Ci: int) -> float:
        """Return ∠ABC in degrees."""
        B = points[Bi]; A = points[Ai]; C = points[Ci]
        ux, uy = A[0] - B[0], A[1] - B[1]
        vx, vy = C[0] - B[0], C[1] - B[1]
        nu = math.hypot(ux, uy); nv = math.hypot(vx, vy)
        if nu <= eps or nv <= eps:
            return 0.0
        t = (ux*vx + uy*vy) / (nu*nv)
        t = max(-1.0, min(1.0, t))
        return math.degrees(math.acos(t))

    def max_angle_of_tri(i: int, j: int, k: int) -> float:
        return max(
            angle_at(i, j, k),
            angle_at(j, i, k),
            angle_at(k, i, j)
        )

    def worst_angle(tris: List[Tuple[int, int, int]]) -> float:
        return max(max_angle_of_tri(*t) for t in tris)

    # --- choose the better diagonal (minimize worst angle); tie → shorter diagonal ---
    worst_ac = worst_angle(tris_ac)
    worst_bd = worst_angle(tris_bd)

    if abs(worst_ac - worst_bd) <= 1e-9:
        # tie-breaker: shorter diagonal
        def d2(i: int, j: int) -> float:
            pi, pj = points[i], points[j]
            dx, dy = pi[0] - pj[0], pi[1] - pj[1]
            return dx*dx + dy*dy
        use_ac = d2(a, c) <= d2(b, d)
        chosen = tris_ac if use_ac else tris_bd
    else:
        chosen = tris_ac if worst_ac < worst_bd else tris_bd

    # --- return exactly the two base triangles, CCW-oriented; NO conformize here ---
    out: List[Tuple[int, int, int]] = []
    for (i, j, k) in chosen:
        out.append(_orient_ccw(i, j, k, points, eps))
    return out


def triangulate_right_triangle(
    A_idx: int, C_idx: int, E_idx: int,
    points: List[Tuple[float, float]],
    *,
    eps: float = 1e-9,
    obtuse_fn=lambda idxs, pts, eps: triangulate_obtuse_triangle(idxs, pts, eps),
) -> Tuple[List[Tuple[int,int,int]], List[Tuple[float,float]]]:
    """
    Right-triangle (∠C = 90°) wrapper that forwards to the *obtuse* routine when needed,
    per the Bern–Eppstein text:

      • 0 subs → split by altitude from C to AE (two right triangles).
      • 1 sub on a leg → 3 right triangles, with one sub point now on base AE.
      • ≥2 on exactly one leg → add diagonal (bE or bA), then reduce to obtuse(A, b, E) or obtuse(A, d, E).
      • both legs → let your Lemma 4 'both legs' routine handle it (or directly call obtuse if you prefer).

    Returns (tris, new_pts). Tri indices are into points + new_pts.
    """

    Tri = Tuple[int,int,int]
    Pt  = Tuple[float,float]

    A, C, E = points[A_idx], points[C_idx], points[E_idx]
    tris: List[Tri] = []
    new_pts: List[Pt] = []
    base_len = len(points)

    def XY(i: int) -> Pt:
        return points[i] if i < base_len else new_pts[i - base_len]

    # ----- small numeric helpers -----
    def area2(P: Pt, Q: Pt, R: Pt) -> float:
        return (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])

    def push(i: int, j: int, k: int, tag: str = ""):
        P,Q,Rp = XY(i), XY(j), XY(k)
        if abs(area2(P,Q,Rp)) > eps:
            tris.append((i,j,k))

    def add_or_get(P: Pt, tol: float = 1e-12) -> int:
        # search original points
        for i,Q in enumerate(points):
            if abs(P[0]-Q[0])<=tol and abs(P[1]-Q[1])<=tol:
                return i
        # search added points
        for k,Q in enumerate(new_pts):
            if abs(P[0]-Q[0])<=tol and abs(P[1]-Q[1])<=tol:
                return base_len + k
        new_pts.append(P)
        idx = base_len + len(new_pts) - 1
        return idx

    def on_open_seg(P: Pt, X: Pt, Y: Pt) -> bool:
        vx,vy = (Y[0]-X[0], Y[1]-X[1])
        den = vx*vx + vy*vy
        if den == 0.0: return False
        cross = abs((P[0]-X[0])*vy - (P[1]-X[1])*vx)
        if cross > eps*math.sqrt(den): return False
        t = ((P[0]-X[0])*vx + (P[1]-X[1])*vy) / den
        return (eps < t < 1.0 - eps)

    def sort_on_leg(apex_idx: int, base_end_idx: int, cand: List[int]) -> List[int]:
        U, V = points[base_end_idx], points[apex_idx]     # base_end → apex
        vx, vy = (V[0]-U[0], V[1]-U[1])
        den = vx*vx + vy*vy if (vx or vy) else 1.0
        def t_of(i: int) -> float:
            P = points[i]
            return ((P[0]-U[0])*vx + (P[1]-U[1])*vy) / den
        return sorted(cand, key=t_of)

    def foot_of_perp(P: Pt, A_: Pt, B_: Pt) -> Pt:
        ax,ay = A_; bx,by = B_; px,py = P
        vx,vy = bx-ax, by-ay
        den = vx*vx + vy*vy
        if den == 0.0: return A_
        t = ((px-ax)*vx + (py-ay)*vy) / den
        t = max(0.0, min(1.0, t))
        return (ax + t*vx, ay + t*vy)

    # ----- collect leg points on AC and CE -----
    L_raw, R_raw = [], []
    for idx,P in enumerate(points):
        if idx in (A_idx, C_idx, E_idx): continue
        if on_open_seg(P, A, C): L_raw.append(idx)
        elif on_open_seg(P, C, E): R_raw.append(idx)

    L = sort_on_leg(C_idx, A_idx, L_raw)   # along A→…→C
    R = sort_on_leg(C_idx, E_idx, R_raw)   # along E→…→C

    # how many total subdivisions?
    n = len(L) + len(R)

    # 0) no subs → just split by altitude from C to AE (two right triangles)
    if n == 0:
        return tris, new_pts

    # 1) exactly one sub on a leg → “three right triangles, with one sub point on base AE”
    if n == 1:
        D  = foot_of_perp(C, A, E); Di = add_or_get(D)
        if len(L) == 1:
            b = L[0]; bpt = points[b]
            bp = foot_of_perp(bpt, A, E); bpi = add_or_get(bp)
            # (A, b, b′), (b, C, D), (C, D, E)
            push(A_idx, b,   bpi, tag="A-b-b′")
            push(b,     C_idx, Di,  tag="b-C-D")
            push(C_idx, E_idx, Di,  tag="C-E-D")
        else:
            d = R[0]; dpt = points[d]
            dp = foot_of_perp(dpt, A, E); dpi = add_or_get(dp)
            # (E, d, d′), (d, C, D), (C, D, A)
            push(E_idx, d,   dpi, tag="E-d-d′")
            push(d,     C_idx, Di, tag="d-C-D")
            push(C_idx, Di, A_idx, tag="C-D-A")
        return tris, new_pts

    # 2) ≥2 on exactly one leg → add diagonal (bE or dA) and reduce to obtuse case with n-1
    if (len(L) >= 2 and len(R) == 0) or (len(R) >= 2 and len(L) == 0):
        if len(L) >= 2:   # many on AC only
            b = L[-1]  # closest to C on AC
            # add △(b, C, E) (right triangle chunk at the top)
            push(b, C_idx, E_idx, tag="diag-bE")
            # reduce to obtuse on △(A, b, E) with the remaining AC points A→…→b
            # NOTE: obtuse routine reads points to detect leg points; no extra args needed.
            # extend points with any newly created right-tri points first (none here)
            if new_pts:
                points.extend(new_pts); base_len = len(points); new_pts.clear()
            # call obtuse on new frame A-b-E
            tris2, new2 = obtuse_fn([A_idx, b, E_idx], points, eps)
            tris.extend(tris2); new_pts.extend(new2)
            return tris, new_pts
        else:             # many on CE only
            d = R[-1]
            push(d, C_idx, A_idx, tag="diag-dA")
            if new_pts:
                points.extend(new_pts); base_len = len(points); new_pts.clear()
            tris2, new2 = obtuse_fn([A_idx, d, E_idx], points, eps)
            tris.extend(tris2); new_pts.extend(new2)
            return tris, new_pts

    # 3) points on both legs → use your general both-legs routine (Lemma 4)
    #    (Right angle doesn’t need a special path here.)

    tris3, new3 = triangulate_obtuse_triangle.triangulate_both_legs_lemma4(
        A_idx=A_idx, C_idx=C_idx, E_idx=E_idx,
        points=points, L=L, R=R, eps=eps
    )
    tris.extend(tris3); new_pts.extend(new3)
    return tris, new_pts


Point = Tuple[float, float]
Tri   = Tuple[int, int, int]


def triangulate_obtuse_triangle(
    indices: List[int],
    points: List[Point],
    eps: float = 1e-8
) -> Tuple[List[Tri], List[Point]]:
    """
    Triangulate a (possibly obtuse) triangle with optional subdivision points on its legs.
    Returns:
      tris    : list of triangle index triples (indices into points + new_pts)
      new_pts : added Steiner points (projections, apex foot, m, b', etc.)

    Router (clear 4 cases):
      Case 0: NO subdivisions on either leg
      Case 1: EXACTLY ONE subdivision on exactly one leg (Lemma 2; inside/outside)
      Case 2: >= 2 subdivisions on exactly one leg (ribbon on that leg)
      Case 3: subdivisions on BOTH legs (ribbons on both)
    """
    # --------------- small geometry helpers ---------------
    def angle_at(B: Point, A: Point, C: Point) -> float:  # ∠ABC (degrees)
        v1 = (A[0]-B[0], A[1]-B[1]); v2 = (C[0]-B[0], C[1]-B[1])
        n1 = math.hypot(*v1); n2 = math.hypot(*v2)
        if n1 == 0 or n2 == 0: return 0.0
        t = max(-1.0, min(1.0, (v1[0]*v2[0] + v1[1]*v2[1])/(n1*n2)))
        return math.degrees(math.acos(t))

    def tri_area(P: Point, Q: Point, R: Point) -> float:
        return 0.5*abs((Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0]))

    def on_open_segment_strict(P: Point, A: Point, B: Point, tol=1e-12) -> bool:
        ax, ay = A; bx, by = B; px, py = P
        vx, vy = bx-ax, by-ay
        den = vx*vx + vy*vy
        if den == 0.0: return False
        cross = abs((px-ax)*vy - (py-ay)*vx)
        if cross > tol * math.sqrt(den): return False
        t = ((px-ax)*vx + (py-ay)*vy) / den
        return (tol < t < 1.0 - tol)

    def foot_of_perp(P: Point, A: Point, B: Point) -> Point:
        """Orthogonal projection of P onto the (clamped) segment AB."""
        ax, ay = A; bx, by = B; px, py = P
        vx, vy = bx-ax, by-ay
        den = vx*vx + vy*vy
        if den == 0.0: return A
        t = ((px-ax)*vx + (py-ay)*vy) / den
        t = max(0.0, min(1.0, t))  # clamp to segment
        return (ax + t*vx, ay + t*vy)

    def add_or_get_index(X: Point, base_len: int, new_pts: List[Point], tol=1e-12) -> int:
        # 1) look in points
        for i, P in enumerate(points):
            if abs(P[0] - X[0]) <= tol and abs(P[1] - X[1]) <= tol:
                return i
        # 2) look in new_pts
        for k, P in enumerate(new_pts):
            if abs(P[0] - X[0]) <= tol and abs(P[1] - X[1]) <= tol:
                return base_len + k
        # 3) append
        new_pts.append(X)
        return base_len + (len(new_pts) - 1)

    def max_angle_of_triangle(tri: Tri,
                              base_len: int,
                              acc_new: List[Point]) -> float:
        def C(i: int) -> Point:
            return points[i] if i < base_len else acc_new[i - base_len-1]
        i, j, k = tri
        P, Q, R = C(i), C(j), C(k)
        def ang(B, A, Cc): return angle_at(B, A, Cc)
        a1 = ang(Q, P, R); a2 = ang(R, Q, P); a3 = ang(P, R, Q)
        return max(a1, a2, a3)

    def get_xy(idx: int) -> Point:
        return points[idx] if idx < base_len else new_pts[idx - base_len-1]

    def push(i: int, j: int, k: int, tag: str):
        """Add a triangle if non-degenerate; print what we add."""
        P, Q, R_ = get_xy(i), get_xy(j), get_xy(k)
        if tri_area(P, Q, R_) > eps:
            tris.append((i, j, k))

    def triangulate_trapezoid(p_i: int, p_j: int, f_i: int, f_j: int, tag: str):
        """
        Trapezoid defined by two leg points (p_i, p_j) and their base projections (f_i, f_j).
        Pick diagonal that minimizes max-angle among the two triangles.
        """
        cand1 = [(p_i, p_j, f_j), (p_i, f_j, f_i)]
        cand2 = [(p_j, f_i, f_j), (p_i, p_j, f_i)]
        ok1 = all(max_angle_of_triangle(t, base_len, new_pts) <= 90.0000001 for t in cand1)
        ok2 = all(max_angle_of_triangle(t, base_len, new_pts) <= 90.0000001 for t in cand2)
        if ok1 and not ok2:
            for t in cand1: push(*t, tag=tag)
        elif ok2 and not ok1:
            for t in cand2: push(*t, tag=tag)
        else:
            m1 = max(max_angle_of_triangle(cand1[0], base_len, new_pts),
                     max_angle_of_triangle(cand1[1], base_len, new_pts))
            m2 = max(max_angle_of_triangle(cand2[0], base_len, new_pts),
                     max_angle_of_triangle(cand2[1], base_len, new_pts))
            diag = "p_i→f_j" if m1 <= m2 else "p_j→f_i"
            for t in (cand1 if m1 <= m2 else cand2): push(*t, tag=tag)

    # ---- lines and intersections for CASE 1 (Lemma 2) ----
    def perp_line_through(P: Point, A: Point, B: Point) -> Tuple[Point, Point]:
        vx, vy = (B[0]-A[0], B[1]-A[1])
        nx, ny = (vy, -vx)
        return (P, (P[0] + nx, P[1] + ny))

    def line_intersection(L1: Tuple[Point, Point], L2: Tuple[Point, Point]) -> Optional[Point]:
        (P, Q), (R, S) = L1, L2
        ux, uy = (Q[0]-P[0], Q[1]-P[1])
        vx, vy = (S[0]-R[0], S[1]-R[1])
        wx, wy = (R[0]-P[0], R[1]-P[1])
        d = ux*vy - uy*vx
        if abs(d) <= eps:
            return None
        t = (wx*vy - wy*vx)/d
        X = (P[0] + t*ux, P[1] + t*uy)
        return X

    def inside_triangle(P: Point, A: Point, C: Point, E: Point, tol=1e-12) -> bool:
        v0 = (E[0]-A[0], E[1]-A[1])
        v1 = (C[0]-A[0], C[1]-A[1])
        v2 = (P[0]-A[0], P[1]-A[1])
        d00 = v0[0]*v0[0] + v0[1]*v0[1]
        d01 = v0[0]*v1[0] + v0[1]*v1[1]
        d11 = v1[0]*v1[0] + v1[1]*v1[1]
        d20 = v2[0]*v0[0] + v2[1]*v0[1]
        d21 = v2[0]*v1[0] + v2[1]*v1[1]
        det = d00*d11 - d01*d01
        if abs(det) <= tol:
            return False
        v = (d11*d20 - d01*d21)/det
        w = (d00*d21 - d01*d20)/det
        u = 1.0 - v - w
        inside = (u >= -tol) and (v >= -tol) and (w >= -tol)
        return inside

    def one_subdivision_case(
            A_i: int,
            C_i: int,
            E_i: int,
            leg: str,  # "left" (AC) or "right" (CE)
            b_idx: int,
    ) -> Tuple[List[Tri], List[Point]]:
        """
        Case 1 (Lemma 2): exactly one subdivision point on exactly one leg.
        Works with combined indices (original + Steiner). Uses XY() to read coords.
        """

        # Combined-index accessor
        def XY(i: int) -> Point:
            return points[i] if i < base_len else new_pts[i - base_len]


        # Read points using combined accessor
        A_pt = XY(A_i)
        C_pt = XY(C_i)
        E_pt = XY(E_i)
        b_pt = XY(b_idx)

        # Build the two perpendiculars:  Lb = ⟂(leg)@b,  Lc = ⟂(other leg)@apex
        if leg == "left":  # leg is A–C
            Lb = perp_line_through(b_pt, C_pt, A_pt)  # ⟂ to CA at b
            Lc = perp_line_through(C_pt, C_pt, E_pt)  # ⟂ to CE at apex
            which = "⊥(CA)@b & ⊥(CE)@apex"
        else:  # leg == "right" (E–C)
            Lb = perp_line_through(b_pt, C_pt, E_pt)  # ⟂ to CE at b
            Lc = perp_line_through(C_pt, C_pt, A_pt)  # ⟂ to CA at apex
            which = "⊥(CE)@b & ⊥(CA)@apex"


        m = line_intersection(Lb, Lc)


        inside = (m is not None) and inside_triangle(m, A_pt, C_pt, E_pt, tol=eps)


        if inside:
            # ---- INSIDE: apex-merger ----
            m_idx = add_or_get_index(m, base_len, new_pts)

            if leg == "left":
                # △(A,b,m), △(b,C,m), △(C,m,E)
                push(A_i, b_idx, m_idx, tag="CASE1-ins")
                push(b_idx, C_i, m_idx, tag="CASE1-ins")
                push(C_i, m_idx, E_i, tag="CASE1-ins")
            else:
                # △(E,b,m), △(b,C,m), △(C,m,A)
                push(E_i, b_idx, m_idx, tag="CASE1-ins")
                push(b_idx, C_i, m_idx, tag="CASE1-ins")
                push(C_i, m_idx, A_i, tag="CASE1-ins")

            # Split △(A, m, E) by altitude from m to AE (no subdivisions there)
            M = XY(m_idx)
            Hm = foot_of_perp(M, A_pt, E_pt)
            hm_idx = add_or_get_index(Hm, base_len, new_pts)
            push(m_idx, hm_idx, A_i, tag="CASE1-ins-tail")
            push(m_idx, E_i, hm_idx, tag="CASE1-ins-tail")

            return tris, new_pts

        # ---- OUTSIDE: delayed apex-merger ----



        def line_intersection_unclamped(L1, L2):
            (P, Q), (R, S) = L1, L2
            ux, uy = (Q[0] - P[0], Q[1] - P[1])
            vx, vy = (S[0] - R[0], S[1] - R[1])
            wx, wy = (R[0] - P[0], R[1] - P[1])
            d = ux * vy - uy * vx
            if abs(d) <= eps:
                return None
            t = (wx * vy - wy * vx) / d
            return (P[0] + t * ux, P[1] + t * uy)

        A_pt, C_pt, E_pt = XY(A_i), XY(C_i), XY(E_i)
        b_pt = XY(b_idx)

        # base as a line (unclamped)
        Lbase = (A_pt, E_pt)
        bprime = line_intersection_unclamped(Lb, Lbase)
        if bprime is None:
            bprime = foot_of_perp(b_pt, A_pt, E_pt)  # robust fallback (clamped to AE)
        bprime_idx = add_or_get_index(bprime, base_len, new_pts)


        if leg == "left":
            # realize bb′ and b′c

            push(A_i, b_idx, bprime_idx, tag="CASE1-out")
            push(b_idx, C_i, bprime_idx, tag="CASE1-out")

            # Remaining no-subdiv triangle △(b′,C,E): split by altitude from C onto segment (b′,E)

            Hc = foot_of_perp(C_pt, XY(bprime_idx), E_pt)
            hc_idx = add_or_get_index(Hc, base_len, new_pts)
            # two triangles around the altitude
            push(C_i, hc_idx, bprime_idx, tag="CASE1-out-tail")
            push(C_i, E_i, hc_idx, tag="CASE1-out-tail")

        else:  # leg == "right"

            push(E_i, b_idx, bprime_idx, tag="CASE1-out")
            push(b_idx, C_i, bprime_idx, tag="CASE1-out")

            # Remaining no-subdiv triangle △(A,C,b′): split by altitude from C onto segment (A,b′)

            Hc = foot_of_perp(C_pt, A_pt, XY(bprime_idx))
            hc_idx = add_or_get_index(Hc, base_len, new_pts)
            push(C_i, hc_idx, A_i, tag="CASE1-out-tail")
            push(C_i, bprime_idx, hc_idx, tag="CASE1-out-tail")

        return tris, new_pts

    def _reduce_one_step(
            *,
            leg: str,  # "left" (AC) or "right" (CE)
            subdiv: List[int],  # indices on that leg (sorted baseEnd → … → apex)
            A_idx: int, C_idx: int, E_idx: int,
    ) -> Tuple[bool, int, int, int, str, List[int]]:
        """
        Try a single Lemma-3 'apex-merger (m inside)' reduction.
        If success: emit the bm/cm + cross triangles, set new apex=m, project the
        remaining (except b) onto the rail baseEnd–m → new subdiv list (n-1).
        Returns: (reduced, A_idx, C_idx, E_idx, leg, new_subdiv)
        """

        # Combined-index accessor (original + Steiner)
        def XY(i: int) -> Point:
            return points[i] if i < base_len else new_pts[i - base_len]

        # Helper: project along (⊥ to the leg) onto the rail (A–m or E–m)
        def project_along_leg_normal_onto_rail(
                P: Tuple[float, float],
                *,
                leg: str,
                A_pt: Tuple[float, float],
                C_pt: Tuple[float, float],
                E_pt: Tuple[float, float],
                rail_P: Tuple[float, float],  # A if left, E if right
                rail_Q: Tuple[float, float],  # m
        ) -> Tuple[float, float]:
            if leg == "left":
                Lnorm = perp_line_through(P, C_pt, A_pt)  # ⟂ CA at P
            else:
                Lnorm = perp_line_through(P, C_pt, E_pt)  # ⟂ CE at P
            Lrail = (rail_P, rail_Q)  # infinite line through rail
            X = line_intersection(Lnorm, Lrail)
            if X is None:
                # robust fallback: clamp to segment rail_P–rail_Q
                X = foot_of_perp(P, rail_P, rail_Q)
            return X

        assert leg in ("left", "right")
        if len(subdiv) < 2:
            return False, A_idx, C_idx, E_idx, leg, subdiv
        A_pt = XY(A_idx)
        C_pt = XY(C_idx)
        E_pt = XY(E_idx)
        base_end_idx = A_idx if leg == "left" else E_idx
        base_end_pt = XY(base_end_idx)

        b_idx = subdiv[-1]  # closest to apex
        b_pt = XY(b_idx)


        if leg == "left":
            Lb = perp_line_through(b_pt, C_pt, A_pt)  # ⟂ CA at b
            Lc = perp_line_through(C_pt, C_pt, E_pt)  # ⟂ CE at apex
        else:
            Lb = perp_line_through(b_pt, C_pt, E_pt)  # ⟂ CE at b
            Lc = perp_line_through(C_pt, C_pt, A_pt)  # ⟂ CA at apex

        m = line_intersection(Lb, Lc)
        inside = (m is not None) and inside_triangle(m, A_pt, C_pt, E_pt, tol=eps)

        # ======================= OUTSIDE (delayed apex–merger) =======================
        if not inside:


            # other base endpoint for splitting the remaining triangle later
            other_base_idx = (E_idx if leg == "left" else A_idx)
            other_base_pt = XY(other_base_idx)

            # b′ = intersection of ⟂(leg)@b with the (infinite) base line A–E; fallback = orthogonal foot
            bprime = line_intersection(Lb, (A_pt, E_pt))
            if bprime is None:
                bprime = foot_of_perp(b_pt, A_pt, E_pt)
            bprime_idx = add_or_get_index(bprime, base_len, new_pts)


            # Project earlier leg points (all except b) onto rail (base_end – b′) along ⟂(leg)
            rem = subdiv[:-1]
            proj: List[int] = []
            if rem:
                rail_P, rail_Q = base_end_pt, XY(bprime_idx)
                for i in rem:
                    Pi = XY(i)
                    Fi = project_along_leg_normal_onto_rail(
                        Pi, leg=leg, A_pt=A_pt, C_pt=C_pt, E_pt=E_pt,
                        rail_P=rail_P, rail_Q=rail_Q
                    )
                    fi_idx = add_or_get_index(Fi, base_len, new_pts)
                    proj.append(fi_idx)


                # near-base wedge
                if leg == "left":
                    push(A_idx, rem[0], proj[0], tag="L3/out-wedge")
                else:
                    push(E_idx, rem[0], proj[0], tag="L3/out-wedge")

                # middle trapezoids
                for k in range(len(rem) - 1):
                    triangulate_trapezoid(rem[k], rem[k + 1], proj[k], proj[k + 1],
                                          tag="L3/out-trap")

                # top trapezoid (rem[-1], b) with (proj[-1], b′)
                triangulate_trapezoid(rem[-1], b_idx, proj[-1], bprime_idx,
                                      tag="L3/out-top")
            else:
                # single small triangle to realize bb′ at the base end
                push(base_end_idx, b_idx, bprime_idx, tag="L3/out-single")

            # Apex triangle △(b, C, b′)
            push(b_idx, C_idx, bprime_idx, tag="L3/out-apex")

            # Split remaining △(b′, C, other_base) by altitude from C
            Hc = foot_of_perp(C_pt, XY(bprime_idx), other_base_pt)
            hc_idx = add_or_get_index(Hc, base_len, new_pts)
            push(C_idx, hc_idx, bprime_idx, tag="L3/out-tail")
            push(C_idx, other_base_idx, hc_idx, tag="L3/out-tail")

            # This step consumes the leg ribbon entirely.
            return True, A_idx, C_idx, E_idx, leg, []

        # ======================= INSIDE (apex–merger succeeds) =======================
        # commit m
        m_idx = add_or_get_index(m, base_len, new_pts)


        # realize bm and cm; and cross triangle to the other base end
        push(b_idx, C_idx, m_idx, tag="L3-bcm")
        if leg == "left":
            push(C_idx, m_idx, E_idx, tag="L3-cross")  # △(C,m,E)
        else:
            push(C_idx, m_idx, A_idx, tag="L3-cross")  # △(C,m,A)

        # project remaining leg points (except b) onto rail (baseEnd–m)
        rem = subdiv[:-1]
        new_subdiv: List[int] = []
        if rem:
            # project each remaining point along ⟂(leg) onto rail (baseEnd–m)
            rail_P, rail_Q = base_end_pt, XY(m_idx)
            for i in rem:
                Pi = XY(i)
                Fi = project_along_leg_normal_onto_rail(
                    Pi, leg=leg, A_pt=A_pt, C_pt=C_pt, E_pt=E_pt,
                    rail_P=rail_P, rail_Q=rail_Q
                )
                fi_idx = add_or_get_index(Fi, base_len, new_pts)
                new_subdiv.append(fi_idx)

            # near-base wedge
            if leg == "left":
                push(A_idx, rem[0], new_subdiv[0], tag="L3-ABM-wedge")
            else:
                push(E_idx, rem[0], new_subdiv[0], tag="L3-EBM-wedge")

            # middle trapezoids
            for k in range(len(rem) - 1):
                triangulate_trapezoid(rem[k], rem[k + 1], new_subdiv[k], new_subdiv[k + 1],
                                      tag="L3-ABM-trap" if leg == "left" else "L3-EBM-trap")

            # top trapezoid with (rem[-1], b) and (f_last, m)
            triangulate_trapezoid(rem[-1], b_idx, new_subdiv[-1], m_idx,
                                  tag="L3-ABM-top" if leg == "left" else "L3-EBM-top")
            # For n=2 → rem has 1 element → we push exactly:
            #   • wedge, and
            #   • top trapezoid (which becomes 2 triangles),
            # totaling **3 triangles** inside ABM (as you expected).


        # Update the subproblem to △(A,m,E) with points on A–m (or E–m)
        C_idx = m_idx  # new apex
        # leg stays the same name wrt the new frame
        return True, A_idx, C_idx, E_idx, leg, new_subdiv

    def mult_sub_one_leg_case(leg: str, leg_points: List[int]) -> Tuple[List[Tri], List[Point]]:

        """
        Case 'multi on one leg': keep reducing n→n-1 with Lemma-3 while m is inside.
        When down to 1 → call your 'one_subdivision_case'.
        If a reduce step fails (m outside/parallel), fall back to the AE-ribbon and return.
        """

        def XY(i: int) -> Point:
            return points[i] if i < base_len else new_pts[i - base_len]
        # work on a live frame of the current triangle
        A_i, C_i, E_i = base_left, apex, base_right
        subdiv = list(leg_points)  # already sorted baseEnd→apex

        # main reducer loop
        while len(subdiv) >= 2:
            reduced, A_i, C_i, E_i, leg, subdiv = _reduce_one_step(
                leg=leg, subdiv=subdiv, A_idx=A_i, C_idx=C_i, E_idx=E_i
            )
            if not reduced:
                # fallback: your original trapezoid ribbon to AE on the *current* frame
                A_pt, C_pt, E_pt = points[A_i], points[C_i], points[E_i]
                D = foot_of_perp(C_pt, A_pt, E_pt)
                Di = add_or_get_index(D, base_len, new_pts)

                proj = [add_or_get_index(foot_of_perp(points[i], A_pt, E_pt), base_len, new_pts)
                        for i in subdiv]

                if leg == "left":
                    # base wedge
                    push(A_i, subdiv[0], proj[0], tag="CASE2-fallback")
                    # consecutive trapezoids
                    for k in range(len(subdiv) - 1):
                        triangulate_trapezoid(subdiv[k], subdiv[k + 1], proj[k], proj[k + 1], tag="CASE2-fallback")
                    # top + other empty side
                    triangulate_trapezoid(subdiv[-1], C_i, proj[-1], Di, tag="CASE2-fallback-top")
                    push(C_i, E_i, Di, tag="CASE2-fallback-other")
                else:
                    push(E_i, subdiv[0], proj[0], tag="CASE2-fallback")
                    for k in range(len(subdiv) - 1):
                        triangulate_trapezoid(subdiv[k], subdiv[k + 1], proj[k], proj[k + 1], tag="CASE2-fallback")
                    triangulate_trapezoid(subdiv[-1], C_i, proj[-1], Di, tag="CASE2-fallback-top")
                    push(C_i, Di, A_i, tag="CASE2-fallback-other")
                return tris, new_pts

        # here: len(subdiv) is 0 or 1
        if len(subdiv) == 0:
            A_pt, C_pt, E_pt = XY(A_i), XY(C_i), XY(E_i)
            D = foot_of_perp(C_pt, A_pt, E_pt)
            Di = add_or_get_index(D, base_len, new_pts)
            push(C_i, Di, A_i, tag="CASE2-end-case0")
            push(C_i, E_i, Di, tag="CASE2-end-case0")
            return tris, new_pts

        b_idx = subdiv[0]
        return one_subdivision_case(A_i, C_i, E_i, leg, b_idx)

    def triangulate_both_legs_lemma4(
            A_idx: int, C_idx: int, E_idx: int,
            points: List[Point],
            L: List[int],  # subdivision indices on AC, sorted A→C
            R: List[int],  # subdivision indices on CE, sorted E→C
            eps: float = 1e-9,
    ) -> Tuple[List[Tri], List[Point]]:
        """
        Bern–Eppstein, Lemma 4: obtuse △A C E (obtuse at C), with subdivisions on both legs.
        Handles all branches needed to triangulate the configuration. Prints progress.

        Inputs
        ------
        A_idx, C_idx, E_idx : indices of A, C (obtuse apex), E in `points`
        points              : initial vertices (A,C,E) plus any pre-existing points
        L                   : indices of points on AC, sorted (A→…→C)
        R                   : indices of points on CE, sorted (E→…→C)

        Returns
        -------
        (tris, new_pts)     : triangles (indices into points+new_pts) and any Steiner points added
        """

        # --------------------- local storage ---------------------
        tris: List[Tri] = []
        new_pts: List[Point] = []
        base_len = len(points)

        def XY(i: int) -> Point:
            return points[i] if i < base_len else new_pts[i - base_len]

        # --------------------- numeric helpers -------------------
        def _area2(P: Point, Q: Point, R: Point) -> float:
            return (Q[0] - P[0]) * (R[1] - P[1]) - (Q[1] - P[1]) * (R[0] - P[0])

        def angle_deg(A: Point, B: Point, C: Point) -> float:  # ∠ABC
            bax, bay = A[0] - B[0], A[1] - B[1]
            bcx, bcy = C[0] - B[0], C[1] - B[1]
            den = math.hypot(bax, bay) * math.hypot(bcx, bcy)
            if den == 0: return 0.0
            t = max(-1.0, min(1.0, (bax * bcx + bay * bcy) / den))
            return math.degrees(math.acos(t))

        def max_angle_of_triangle(t: Tri) -> float:
            i, j, k = t
            A, B, C = XY(i), XY(j), XY(k)
            return max(angle_deg(B, A, C), angle_deg(A, B, C), angle_deg(A, C, B))

        def push(i: int, j: int, k: int, tag: str = ""):
            P, Q, R = XY(i), XY(j), XY(k)
            if abs(_area2(P, Q, R)) > eps:
                tris.append((i, j, k))


        def add_point(P: Point) -> int:
            new_pts.append(P)
            idx = base_len + len(new_pts) - 1
            return idx

        # ------------ geometry: lines, perpendiculars, projections ------------
        def perp_line_through(P: Point, U: Point, V: Point) -> Tuple[Point, Point]:
            # direction ⟂ to UV at P: n = (-(Vy-Uy), Vx-Ux)
            dx, dy = V[0] - U[0], V[1] - U[1]
            n = (-dy, dx)
            # if degenerate, fudge
            if abs(n[0]) + abs(n[1]) < 1e-18:
                n = (1.0, 0.0)
            return (P, (P[0] + n[0], P[1] + n[1]))

        def line_intersection(L1: Tuple[Point, Point], L2: Tuple[Point, Point]) -> Optional[Point]:
            (P, Q), (R, S) = L1, L2
            ux, uy = Q[0] - P[0], Q[1] - P[1]
            vx, vy = S[0] - R[0], S[1] - R[1]
            wx, wy = R[0] - P[0], R[1] - P[1]
            d = ux * vy - uy * vx
            if abs(d) <= eps:
                return None
            t = (wx * vy - wy * vx) / d
            return (P[0] + t * ux, P[1] + t * uy)

        def foot_of_perp(P: Point, A: Point, B: Point) -> Point:
            ax, ay = A;
            bx, by = B;
            px, py = P
            vx, vy = bx - ax, by - ay
            den = vx * vx + vy * vy
            if den == 0.0: return A
            t = ((px - ax) * vx + (py - ay) * vy) / den
            t = max(0.0, min(1.0, t))
            return (ax + t * vx, ay + t * vy)

        def inside_triangle(P: Point, A: Point, B: Point, C: Point) -> bool:
            # barycentric with area signs (strictly inside or on edges)
            a = _area2(B, C, P)
            b = _area2(C, A, P)
            c = _area2(A, B, P)
            ap = _area2(B, C, A)
            bp = _area2(C, A, B)
            cp = _area2(A, B, C)

            # same orientation tolerantly
            def same_sign(x, y): return x * y >= -1e-12

            return same_sign(a, ap) and same_sign(b, bp) and same_sign(c, cp)

        def triangulate_trapezoid(p_i: int, p_j: int, f_i: int, f_j: int, tag: str = "trap"):
            # two diagonals; pick the split with smaller worst angle; both are checked for obtuseness
            cand1 = [(p_i, p_j, f_j), (p_i, f_j, f_i)]
            cand2 = [(p_j, f_i, f_j), (p_i, p_j, f_i)]

            def ok(c):
                return all(max_angle_of_triangle(t) <= 90.0000001 for t in c)

            ok1, ok2 = ok(cand1), ok(cand2)
            if ok1 and not ok2:
                for t in cand1: push(*t, tag=f"{tag}/1")
            elif ok2 and not ok1:
                for t in cand2: push(*t, tag=f"{tag}/2")
            else:
                m1 = max(max_angle_of_triangle(cand1[0]), max_angle_of_triangle(cand1[1]))
                m2 = max(max_angle_of_triangle(cand2[0]), max_angle_of_triangle(cand2[1]))
                for t in (cand1 if m1 <= m2 else cand2): push(*t, tag=f"{tag}/min")

        def project_along_leg_normal_onto_rail(
                P: Point, *, leg: str, rail_P: Point, rail_Q: Point,
                A_pt: Point, C_pt: Point, E_pt: Point
        ) -> Point:
            if leg == "left":
                Lnorm = perp_line_through(P, C_pt, A_pt)  # ⟂ CA at P
            else:
                Lnorm = perp_line_through(P, C_pt, E_pt)  # ⟂ CE at P
            X = line_intersection(Lnorm, (rail_P, rail_Q))
            if X is None:
                X = foot_of_perp(P, rail_P, rail_Q)
            return X

        # -------------- helpers to try apex-merger on a given side --------------
        def try_apex_merger(side: str, A_i: int, C_i: int, E_i: int,
                            Ls: List[int], Rs: List[int]) -> Tuple[bool, int, int, int, List[int], List[int]]:
            """
            side = 'left' tries AC-side apex-merger (b with C), otherwise CE-side (d with C).
            On success:
              • emits triangles
              • fills the in-triangle wedge+traps on that side
              • projects points to new rails (A–m or E–m)
              • returns reduced frame (A, m, E) and updated lists
            """
            A_pt, C_pt, E_pt = XY(A_i), XY(C_i), XY(E_i)
            if side == "left":
                if not Ls: return (False, A_i, C_i, E_i, Ls, Rs)
                b_idx = Ls[-1];
                b_pt = XY(b_idx)
                Lb = perp_line_through(b_pt, C_pt, A_pt)  # ⟂ CA @ b
                Lc = perp_line_through(C_pt, C_pt, E_pt)  # ⟂ CE @ C
                other_base_idx, leg_name = E_i, "left"

            else:
                if not Rs: return (False, A_i, C_i, E_i, Ls, Rs)
                b_idx = Rs[-1];
                b_pt = XY(b_idx)
                Lb = perp_line_through(b_pt, C_pt, E_pt)  # ⟂ CE @ d
                Lc = perp_line_through(C_pt, C_pt, A_pt)  # ⟂ AC @ C
                other_base_idx, leg_name = A_i, "right"


            m = line_intersection(Lb, Lc)
            inside = (m is not None) and inside_triangle(m, A_pt, C_pt, E_pt)

            if not inside:
                return (False, A_i, C_i, E_i, Ls, Rs)

            # build projections of remaining points on that leg onto (baseEnd–m)
            m_idx = add_point(m)
            if side == "left":
                rem = Ls[:-1]
                railP = A_pt
                # constant triangles
                push(b_idx, C_i, m_idx, tag="L4-bcm")
                push(C_i, m_idx, other_base_idx, tag="L4-cross")
            else:
                rem = Rs[:-1]
                railP = E_pt
                push(b_idx, C_i, m_idx, tag="L4-dcm")
                push(C_i, m_idx, other_base_idx, tag="L4-cross")

            proj: List[int] = []
            for p in rem:
                Fi = project_along_leg_normal_onto_rail(
                    XY(p), leg=leg_name, rail_P=railP, rail_Q=XY(m_idx),
                    A_pt=A_pt, C_pt=C_pt, E_pt=E_pt
                )
                proj.append(add_point(Fi))

            # fill wedge+traps in △(baseEnd, ..., b, m)
            if rem:
                if side == "left":
                    push(A_i, rem[0], proj[0], tag="L4-ABM-wedge")
                else:
                    push(E_i, rem[0], proj[0], tag="L4-EBM-wedge")
                for i in range(len(rem) - 1):
                    triangulate_trapezoid(rem[i], rem[i + 1], proj[i], proj[i + 1],
                                          tag="L4-trap")
                triangulate_trapezoid(rem[-1], b_idx, proj[-1], m_idx,
                                      tag="L4-top-trap")
            else:
                if side == "left":
                    push(A_i, b_idx, m_idx, tag="L4-ABM-single")
                else:
                    push(E_i, b_idx, m_idx, tag="L4-EBM-single")

            # re-express points on the opposite leg to the new rail
            if side == "left":
                Rs2: List[int] = []
                for q in Rs:
                    Fq = project_along_leg_normal_onto_rail(
                        XY(q), leg="right", rail_P=E_pt, rail_Q=XY(m_idx),
                        A_pt=A_pt, C_pt=C_pt, E_pt=E_pt
                    )
                    Rs2.append(add_point(Fq))
                return (True, A_i, m_idx, E_i, proj, Rs2)
            else:
                Ls2: List[int] = []
                for p in Ls:
                    Fp = project_along_leg_normal_onto_rail(
                        XY(p), leg="left", rail_P=A_pt, rail_Q=XY(m_idx),
                        A_pt=A_pt, C_pt=C_pt, E_pt=E_pt
                    )
                    Ls2.append(add_point(Fp))
                return (True, A_i, m_idx, E_i, Ls2, proj)

        # ----------- “no apex merger” branch (left side, b′ on base) ----------
        def no_apex_left_bprime_on_base(
                A_i: int, C_i: int, E_i: int, Ls: List[int], Rs: List[int]
        ) -> bool:
            """Implements the quoted paragraph for the AC side when b′ ∈ AE."""
            if not Ls or not Rs:
                return False
            A_pt, C_pt, E_pt = XY(A_i), XY(C_i), XY(E_i)
            b_idx, d_idx = Ls[-1], Rs[-1]
            b_pt, d_pt = XY(b_idx), XY(d_idx)

            # L_b : ⟂(AC) at b; intersect with base AE (segment)
            Lb = perp_line_through(b_pt, C_pt, A_pt)
            bprime = line_intersection(Lb, (A_pt, E_pt))
            if bprime is None:
                # parallel → fallback to orth projection
                bprime = foot_of_perp(b_pt, A_pt, E_pt)
            # ensure it's actually on the segment (tolerantly)
            ax, ay = A_pt;
            ex, ey = E_pt;
            bx, by = bprime
            seg_ok = (min(ax, ex) - 1e-9 <= bx <= max(ax, ex) + 1e-9 and
                      min(ay, ey) - 1e-9 <= by <= max(ay, ey) + 1e-9)
            if not seg_ok:
                return False

            bprime_idx = add_point(bprime)

            # “triangulate the trapezoids along AB” on rail A–b′
            remL = Ls[:-1]
            proj: List[int] = []
            for p in remL:
                Fi = project_along_leg_normal_onto_rail(
                    XY(p), leg="left", rail_P=A_pt, rail_Q=bprime,
                    A_pt=A_pt, C_pt=C_pt, E_pt=E_pt
                )
                proj.append(add_point(Fi))
            if remL:
                push(A_i, remL[0], proj[0], tag="L4-b′/wedge")
                for i in range(len(remL) - 1):
                    triangulate_trapezoid(remL[i], remL[i + 1], proj[i], proj[i + 1],
                                          tag="L4-b′/trap")
                triangulate_trapezoid(remL[-1], b_idx, proj[-1], bprime_idx,
                                      tag="L4-b′/top")
            else:
                push(A_i, b_idx, bprime_idx, tag="L4-b′/single")

            # “add edges b′c, b′d; drop altitude from c to b′d”
            Hc = foot_of_perp(XY(C_i), XY(bprime_idx), d_pt)
            hc_idx = add_point(Hc)
            push(C_i, hc_idx, bprime_idx, tag="L4-b′/C-alt")
            push(C_i, d_idx, hc_idx, tag="L4-b′/C-alt")

            # “reduce to triangulating b′de recursively, with n_r subdivisions on base b′e”
            # project CE points along ⟂(CE) onto base b′–E and fan from d
            base_proj: List[int] = []
            for q in Rs:
                Fq = project_along_leg_normal_onto_rail(
                    XY(q), leg="right", rail_P=XY(bprime_idx), rail_Q=E_pt,
                    A_pt=A_pt, C_pt=C_pt, E_pt=E_pt
                )
                base_proj.append(add_point(Fq))
            # sort base proj along b′→E
            bx, by = XY(bprime_idx);
            ex, ey = E_pt
            vx, vy = ex - bx, ey - by
            den = vx * vx + vy * vy if vx or vy else 1.0
            base_proj.sort(key=lambda i: ((XY(i)[0] - bx) * vx + (XY(i)[1] - by) * vy) / den)

            # fan from apex d across base b′–E via base subdivisions (all triangles use apex = d)
            last = bprime_idx
            for p in base_proj:
                push(d_idx, last, p, tag="L4-b′de/fan")
                last = p
            push(d_idx, last, E_i, tag="L4-b′de/fan")

            # We consumed *all* AC ribbon up to b′ and triangulated b′de fully → done with both-legs case here.
            return True

        # ====================== MAIN LOOP (Lemma 4) ======================


        while L and R:
            # 1) try AC apex-merger
            ok, A_idx, C_idx, E_idx, L, R = try_apex_merger("left", A_idx, C_idx, E_idx, L, R)
            if ok:

                continue

            # 2) try CE apex-merger
            ok, A_idx, C_idx, E_idx, L, R = try_apex_merger("right", A_idx, C_idx, E_idx, L, R)
            if ok:

                continue

            # 3) “So assume no apex merger is possible … let b′ … such that projection AB→AB′ forms only good trapezoids …”
            #    We implement the *on-base* b′ branch fully. If that fails numerically, try the symmetric CE side; if that
            #    also fails, do a safe delayed merge (fallback).
            if no_apex_left_bprime_on_base(A_idx, C_idx, E_idx, L, R):
                # both-legs case resolved completely in this branch
                L, R = [], []  # break loop
                break

            # symmetric attempt on CE (swap roles A↔E, L↔R)
            # (Implement the same construction for d′ on AE by symmetry.)
            # Minimal symmetric fallback: do delayed merge on the *closer* side.
            # Choose which side is closer to C:
            def t_param_on_leg(idx: int, U: Point, V: Point) -> float:
                P = XY(idx);
                vx, vy = V[0] - U[0], V[1] - U[1]
                den = vx * vx + vy * vy or 1.0
                return ((P[0] - U[0]) * vx + (P[1] - U[1]) * vy) / den

            b_idx, d_idx = L[-1], R[-1]
            tL = t_param_on_leg(b_idx, XY(A_idx), XY(C_idx))
            tR = t_param_on_leg(d_idx, XY(E_idx), XY(C_idx))
            side = "left" if tL >= tR else "right"

            if side == "left":
                A_pt, C_pt, E_pt = XY(A_idx), XY(C_idx), XY(E_idx)
                b_pt = XY(b_idx)
                # Add triangles realizing delayed merge, as in Lemma 3 outside case
                # b′ = intersection of ⟂(AC)@b with line(A,E); fallback = foot
                Lb = perp_line_through(b_pt, C_pt, A_pt)
                bprime = line_intersection(Lb, (A_pt, E_pt)) or foot_of_perp(b_pt, A_pt, E_pt)
                bprime_idx = add_point(bprime)
                push(A_idx, b_idx, bprime_idx, tag="L4/delayed/A")
                push(b_idx, C_idx, bprime_idx, tag="L4/delayed/A")
                # Right side empty → split △(b′,C,E) by altitude from C
                Hc = foot_of_perp(XY(C_idx), XY(bprime_idx), E_pt)
                hc_idx = add_point(Hc)
                push(C_idx, hc_idx, bprime_idx, tag="L4/delayed/A-tail")
                push(C_idx, E_idx, hc_idx, tag="L4/delayed/A-tail")
                # consume that point
                L = L[:-1]
            else:
                A_pt, C_pt, E_pt = XY(A_idx), XY(C_idx), XY(E_idx)
                d_pt = XY(d_idx)
                Ld = perp_line_through(d_pt, C_pt, E_pt)
                dprime = line_intersection(Ld, (A_pt, E_pt)) or foot_of_perp(d_pt, A_pt, E_pt)
                dprime_idx = add_point(dprime)
                push(E_idx, d_idx, dprime_idx, tag="L4/delayed/E")
                push(d_idx, C_idx, dprime_idx, tag="L4/delayed/E")
                Hc = foot_of_perp(XY(C_idx), A_pt, XY(dprime_idx))
                hc_idx = add_point(Hc)
                push(C_idx, hc_idx, A_idx, tag="L4/delayed/E-tail")
                push(C_idx, dprime_idx, hc_idx, tag="L4/delayed/E-tail")
                R = R[:-1]


        return tris, new_pts

    # ----------------- locate obtuse apex -----------------
    a, b, c = indices
    A0, B0, C0 = points[a], points[b], points[c]
    angA, angB, angC = angle_at(A0, B0, C0), angle_at(B0, A0, C0), angle_at(C0, A0, B0)

    if angA > 90.0:     apex, base_left, base_right = a, b, c
    elif angB > 90.0:   apex, base_left, base_right = b, a, c
    elif angC > 90.0:   apex, base_left, base_right = c, a, b
    else:
        return [(a, b, c)], []


    # ----------------- collect leg points -----------------
    L_raw, R_raw = [], []
    for idx, P in enumerate(points):
        if idx in (apex, base_left, base_right):
            continue
        if on_open_segment_strict(P, points[apex], points[base_left]):
            L_raw.append(idx)
        elif on_open_segment_strict(P, points[apex], points[base_right]):
            R_raw.append(idx)

    def sort_on_leg(apex_idx: int, base_end_idx: int, cand: List[int]) -> List[int]:
        """Sort along base_end → apex."""
        A = points[base_end_idx]; Cpt = points[apex_idx]
        vx, vy = Cpt[0]-A[0], Cpt[1]-A[1]
        den = vx*vx + vy*vy if (vx or vy) else 1.0
        def t_of(i: int) -> float:
            P = points[i]
            return ((P[0]-A[0])*vx + (P[1]-A[1])*vy) / den
        return sorted(cand, key=t_of)

    L = sort_on_leg(apex, base_left,  L_raw)
    R = sort_on_leg(apex, base_right, R_raw)

    # ----------------- common base & storage -----------------
    new_pts: List[Point] = []
    base_len = len(points)  # keep this constant until the function returns!
    Uxy, Vxy = points[base_left], points[base_right]

    # Apex foot on base (used in cases 0, 2, 3; and 1-outside sometimes)
    D = foot_of_perp(points[apex], Uxy, Vxy)
    Di = add_or_get_index(D, base_len, new_pts)  # <- keep this; gives a stable index

    tris: List[Tri] = []
    #move to case 0

    # ----------------- CASE 0: no subdivisions -----------------
    if len(L) == 0 and len(R) == 0:
        # Split big triangle by altitude from apex
        push(apex, Di, base_left,  tag="CASE0")
        push(apex, base_right, Di, tag="CASE0")
        return tris, new_pts

    # ----------------- CASE 1: exactly one subdivision (on one leg) -----------------
    if (len(L) + len(R)) == 1:
        leg = "left" if len(L) == 1 else "right"
        b_idx = L[0] if leg == "left" else R[0]
        A_i, C_i, E_i = base_left, apex, base_right
        return one_subdivision_case(A_i, C_i, E_i, leg, b_idx)

    # ----------------- CASE 2: ≥ 2 on one leg only -----------------
    if (len(L) >= 2 and len(R) == 0) or (len(R) >= 2 and len(L) == 0):
        leg = "left" if len(L) >= 2 else "right"
        leg_points = L if leg == "left" else R
        return mult_sub_one_leg_case(leg, leg_points)

    # ----------------- CASE 3: points on both legs -----------------
    if L and R:
        # Call your Lemma 4 routine on the current frame
        tris3, new3 = triangulate_both_legs_lemma4(
            A_idx=base_left,
            C_idx=apex,
            E_idx=base_right,
            points=points,  # do NOT extend this inside the callee
            L=L,  # AC points sorted A→…→C
            R=R,  # CE points sorted E→…→C
            eps=eps,
        )
        # Merge results and return
        tris.extend(tris3)
        new_pts.extend(new3)
        return tris, new_pts


def triangulate_slab(region_indices: List[int],
                     points: List[Tuple[float, float]],
                     eps: float = 1e-9
                     ) -> Tuple[List[Tuple[int,int,int]], List[Tuple[float,float]]]:
    """
    Triangulate a SLAB exactly as in the paper:
      1) Split by the safe diagonal TL -> BR.
      2) Triangulate each obtuse triangle via the Section-2 routine
         (perpendicular projections, good trapezoids, including the apex-trapezoid).
    Returns (tris, new_pts).
    """

    if len(region_indices) < 4:
        raise ValueError("SLAB region must have at least 4 vertices")

    # --- helpers to detect the two vertical sides and their extremes ---
    def is_close(a, b, tol=eps): return abs(a-b) <= tol

    xs = [points[i][0] for i in region_indices]
    x_min, x_max = min(xs), max(xs)

    left_side  = [i for i in region_indices if is_close(points[i][0], x_min)]
    right_side = [i for i in region_indices if is_close(points[i][0], x_max)]
    if len(left_side) == 0 or len(right_side) == 0:
        raise ValueError("SLAB detection failed: couldn't find two vertical sides")

    TL = max(left_side,  key=lambda i: points[i][1])
    BL = min(left_side,  key=lambda i: points[i][1])

    TR = max(right_side, key=lambda i: points[i][1])
    BR = min(right_side, key=lambda i: points[i][1])

    # --- split by safe diagonal TL->BR ---
    triA = [TL, TR, BR]
    triB = [TL, BR, BL]

    # --- call the obtuse-triangle routine on both halves ---
    tris_all: List[Tuple[int,int,int]] = []
    new_pts_all: List[Tuple[float,float]] = []

    # A: (TL, TR, BR)
    tris_A, new_A = triangulate_obtuse_triangle(triA, points)
    tris_all.extend(tris_A)
    new_pts_all.extend(new_A)

    points_plus = points + new_A
    tris_B, new_B = triangulate_obtuse_triangle(triB, points_plus)
    tris_all.extend(tris_B)
    new_pts_all.extend(new_B)

    return tris_all, new_pts_all


def triangulate_all_regions(regions: List[dict],
                            global_points: List[Tuple[float, float]]
                            ) -> List[Tuple[int, int, int]]:
    """
    Triangulate all regions by type. Key details:
      • For each region we first create the base triangles, check non-obtuseness
        on the base triangles only, and only then conformize (split along edge points).
      • Rectangle never gets swallowed: either succeeds or falls back to a simple diagonal.
      • Other types fail-fast rather than leaving holes.
    """

    def _push_conformized(dst: List[Tuple[int,int,int]],
                          base_tris: List[Tuple[int,int,int]]) -> None:
        # Run local conformize for every triangle (splits along on-edge points)
        for (i, j, k) in base_tris:
            dst.extend(_conformize_triangle(i, j, k, global_points))

    def _max_angle_deg(i: int, j: int, k: int) -> float:
        import math
        A = global_points[i]; B = global_points[j]; C = global_points[k]

        def angle_at(V, P, Q) -> float:
            ux, uy = P[0] - V[0], P[1] - V[1]
            vx, vy = Q[0] - V[0], Q[1] - V[1]
            nu = (ux*ux + uy*uy) ** 0.5
            nv = (vx*vx + vy*vy) ** 0.5
            if nu == 0.0 or nv == 0.0:
                return 0.0
            t = max(-1.0, min(1.0, (ux*vx + uy*vy) / (nu*nv)))
            return math.degrees(math.acos(t))

        return max(angle_at(A, B, C), angle_at(B, A, C), angle_at(C, A, B))

    all_triangles: List[Tuple[int, int, int]] = []

    for i, region in enumerate(regions):
        region_type = str(region.get("type", "")).upper()
        indices = region["indices"]

        produced: List[Tuple[int,int,int]] = []

        try:
            # ---------- RECTANGLE ----------
            if region_type == "RECTANGLE":
                base_tris = triangulate_rectangle(indices, global_points)

                # check non-obtuse on base tris only (pre-conformize)
                for (a, b, c) in base_tris:
                    if not triangle_is_non_obtuse(a, b, c, global_points):
                        mx = _max_angle_deg(a, b, c)

                _push_conformized(produced, base_tris)

            # ---------- RIGHT_TRI ----------
            elif region_type == "RIGHT_TRI":
                base_tris = triangulate_right_triangle(indices, global_points)

                for (a, b, c) in base_tris:
                    if not triangle_is_non_obtuse(a, b, c, global_points):
                        mx = _max_angle_deg(a, b, c)

                _push_conformized(produced, base_tris)

            # ---------- OBTUSE_TRI ----------
            elif region_type == "OBTUSE_TRI":
                base_tris, new_pts = triangulate_obtuse_triangle(indices, global_points)
                pts_for_check = global_points + (new_pts or [])
                # for (a, b, c) in base_tris:
                #     if not triangle_is_non_obtuse(a, b, c, pts_for_check):
                #         print(f"[WARN] obtuse-tri routine produced an obtuse base tri ({a},{b},{c})")

                if new_pts:
                    global_points.extend(new_pts)
                _push_conformized(produced, base_tris)

            # ---------- SLAB ----------
            elif region_type == "SLAB":
                base_tris, new_pts = triangulate_slab(indices, global_points)
                pts_for_check = global_points + (new_pts or [])
                for (a, b, c) in base_tris:
                    if not triangle_is_non_obtuse(a, b, c, pts_for_check):
                        print(f"[WARN] slab routine produced an obtuse base tri ({a},{b},{c})")

                if new_pts:
                    global_points.extend(new_pts)
                _push_conformized(produced, base_tris)

            # ---------- fallback for unknown polygons: fan ----------
            else:
                print(f"Warning: Unknown region type '{region_type}', using fan triangulation")
                if len(indices) >= 3:
                    v0 = indices[0]
                    base_tris = [(v0, indices[j], indices[j+1]) for j in range(1, len(indices)-1)]
                    for (a, b, c) in base_tris:
                        if not triangle_is_non_obtuse(a, b, c, global_points):
                            mx = _max_angle_deg(a, b, c)
                            print(f"[WARN] fan produced an obtuse base tri "
                                  f"({a},{b},{c}) max_angle≈{mx:.4f}°")
                    _push_conformized(produced, base_tris)

            all_triangles.extend(produced)


        except Exception as e:

            print(f"Error triangulating region {i}: {e}")

            if region_type == "RECTANGLE":
                try:
                    base_tris = triangulate_rectangle(indices, global_points)
                    _push_conformized(all_triangles, base_tris)

                    continue
                except Exception as ee:
                    print(f"  Rectangle fallback also failed: {ee}")
                    raise
            else:

                raise

    return all_triangles


def apply_bern_eppstein_triangulation(regions, global_points):

    triangles = triangulate_all_regions(regions, global_points)

    triangles = conformize_mesh(triangles, global_points)

    # for (a, b, c) in triangles:
    #     if not triangle_is_non_obtuse(a, b, c, global_points):
    #         print(f"[WARN] post-conformize obtuse tri: ({a},{b},{c})")
    print(f"Total triangles: {len(triangles)}; points: {len(global_points)}")
    return triangles



