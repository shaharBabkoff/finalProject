
from cgshop2025_pyutils.geometry._bindings import (
    Point, FieldNumber, Polygon, Segment
)
from bernEppstein.geometry_utils import build_polygon_from_indices, make_vertical_grid, make_horizontal_grid, \
    extract_faces_of_grid, EPS
from triangulation import apply_bern_eppstein_triangulation


class ConstrainedTriangulation:
    def __init__(self):
        self.points: list[tuple[float, float]] = []
        self.boundary: list[int] = []
        self.constraints: list[tuple[int, int]] = []
        self.triangles: list[tuple[int, int, int]] = []

    def add_point(self, p) -> int:
        """Add a vertex and return its global index."""
        if isinstance(p, Point):
            self.points.append((float(p.x()), float(p.y())))
        else:                       # כבר tuple או list
            x, y = p
            self.points.append((float(x), float(y)))
        return len(self.points) - 1

    def add_boundary(self, idx_list):
        self.boundary = list(idx_list)

    def add_segment(self, i, j):
        self.constraints.append((i, j))

    def get_triangulation_edges(self):
        if not self.triangles:
            self._run_non_obtuse_algorithm()
        edges = set()
        for a, b, c in self.triangles:
            edges |= {tuple(sorted((a, b))),
                      tuple(sorted((b, c))),
                      tuple(sorted((c, a)))}
        return list(edges)

    def clean_segments(self, segments, poly, orientation=""):
        """
        Clean a list of segments by:
        1. Removing duplicates (ignoring direction).
        2. Removing polygon boundary edges.

        Parameters
        ----------
        segments : list[Segment]
            Candidate segments (vertical or horizontal).
        poly : Polygon
            Polygon boundary for filtering.
        orientation : str
            "vertical" or "horizontal" - used only for debug printing.

        Returns
        -------
        list[Segment]
            Cleaned list of unique, non-boundary segments.
        """
        # --- Build set of polygon boundary edges as coordinate-pairs
        boundary_edges = []
        b_pts = list(poly.boundary())
        for i in range(len(b_pts)):
            p1, p2 = b_pts[i], b_pts[(i + 1) % len(b_pts)]
            src = (float(p1.x()), float(p1.y()))
            tgt = (float(p2.x()), float(p2.y()))
            boundary_edges.append(tuple(sorted((src, tgt))))

        # --- Remove duplicates & boundary overlaps
        unique, seen_keys = [], set()
        for seg in segments:
            src = (float(seg.source().x()), float(seg.source().y()))
            tgt = (float(seg.target().x()), float(seg.target().y()))
            key = tuple(sorted((src, tgt)))

            if key in seen_keys:
                continue
            if key in boundary_edges:
                continue

            seen_keys.add(key)
            unique.append(seg)

        return unique

    def merge_overlapping_segments(self, segments, poly, orientation="vertical"):
        B = list(poly.boundary())
        boundary_pairs = set()
        boundary_intervals = {}
        for i in range(len(B)):
            p1, p2 = B[i], B[(i + 1) % len(B)]
            a = (float(p1.x()), float(p1.y()))
            b = (float(p2.x()), float(p2.y()))
            key_pair = tuple(sorted((a, b)))
            boundary_pairs.add(key_pair)
            if orientation == "vertical" and abs(a[0] - b[0]) < 1e-12:
                x = a[0]
                lo, hi = sorted([a[1], b[1]])
                boundary_intervals.setdefault(x, []).append((lo, hi))
            elif orientation == "horizontal" and abs(a[1] - b[1]) < 1e-12:
                y = a[1]
                lo, hi = sorted([a[0], b[0]])
                boundary_intervals.setdefault(y, []).append((lo, hi))

        def subtract_intervals(base_lo, base_hi, blockers):
            if not blockers:
                return [(base_lo, base_hi)]
            segs = [(base_lo, base_hi)]
            for blo_lo, blo_hi in blockers:
                new_segs = []
                for lo, hi in segs:
                    if blo_hi <= lo or hi <= blo_lo:
                        new_segs.append((lo, hi))
                        continue
                    if lo < blo_lo:
                        new_segs.append((lo, min(hi, blo_lo)))
                    if blo_hi < hi:
                        new_segs.append((max(lo, blo_hi), hi))
                segs = [(lo, hi) for (lo, hi) in new_segs if hi - lo > 1e-12]
            return segs

        interior_pieces = {}
        for seg in segments:
            x1, y1 = float(seg.source().x()), float(seg.source().y())
            x2, y2 = float(seg.target().x()), float(seg.target().y())
            pair_key = tuple(sorted(((x1, y1), (x2, y2))))
            if pair_key in boundary_pairs:
                continue

            if orientation == "vertical":
                assert abs(x1 - x2) < 1e-12
                key = x1
                lo, hi = sorted([y1, y2])
            else:  # horizontal
                assert abs(y1 - y2) < 1e-12
                key = y1
                lo, hi = sorted([x1, x2])

            pieces = subtract_intervals(lo, hi, boundary_intervals.get(key, []))
            if not pieces:
                continue
            interior_pieces.setdefault(key, []).extend(pieces)

        cleaned = []
        for key, ivals in interior_pieces.items():
            ivals.sort()
            merged = []
            cur_lo, cur_hi = ivals[0]
            for lo, hi in ivals[1:]:
                if lo <= cur_hi + 1e-12:
                    cur_hi = max(cur_hi, hi)
                else:
                    merged.append((cur_lo, cur_hi))
                    cur_lo, cur_hi = lo, hi
            merged.append((cur_lo, cur_hi))

            for lo, hi in merged:
                if orientation == "vertical":
                    cleaned.append(
                        Segment(Point(FieldNumber(key), FieldNumber(lo)),
                                Point(FieldNumber(key), FieldNumber(hi))))
                else:
                    cleaned.append(
                        Segment(Point(FieldNumber(lo), FieldNumber(key)),
                                Point(FieldNumber(hi), FieldNumber(key))))

        return cleaned

    def _run_non_obtuse_algorithm(self) -> None:

        # ---------- 0. BUILD POLYGON OBJECT FROM BOUNDARY ---------------
        poly = build_polygon_from_indices(self.boundary, self.points)
        # ---------- 1. VERTICAL SLICING ---------------------------------
        v_segments, v_vertices = make_vertical_grid(poly)
        # ---- 1a. *here* remove duplicates AND drop polygon boundary edges------------------------------
        v_segments = self.clean_segments(v_segments, poly, "vertical")
        v_segments = self.merge_overlapping_segments(v_segments, poly, "vertical")
        self.points.extend(v_vertices)  # add Steiner tuples
        steiner_points_as_CGAL = [
            Point(FieldNumber(x), FieldNumber(y)) for (x, y) in v_vertices
        ]
        # build the full list of reference points for the horizontal pass
        reference_pts = list(poly.boundary()) + steiner_points_as_CGAL
        # --- 2. horizontal slicing ----------------------------------------------
        h_segments, h_vertices = make_horizontal_grid(poly, v_segments)
        h_segments = self.clean_segments(h_segments, poly, "horizontal")
        h_segments = self.merge_overlapping_segments(h_segments, poly, "horizontal")
        self.points.extend(h_vertices)  # add second‑stage Steiner
        # ---------- 3) regions ----------
        regions = extract_faces_of_grid(poly, v_segments, h_segments, self.points)
        # ---------- 4) dedup points + remap ----------
        unique_points: list[tuple[float, float]] = []
        old_to_new: dict[int, int] = {}

        def _same_xy(a, b) -> bool:
            return abs(a[0] - b[0]) < EPS and abs(a[1] - b[1]) < EPS
        for i, P in enumerate(self.points):
            found = None
            for j, Q in enumerate(unique_points):
                if _same_xy(P, Q):
                    found = j
                    break
            if found is None:
                old_to_new[i] = len(unique_points)
                unique_points.append(P)
            else:
                old_to_new[i] = found

        self.points = unique_points
        for R in regions:
            R["indices"] = [old_to_new[idx] for idx in R["indices"]]
        # ---------- 5) triangulate ----------
        triangles = apply_bern_eppstein_triangulation(regions, self.points)
        self.triangles = triangles