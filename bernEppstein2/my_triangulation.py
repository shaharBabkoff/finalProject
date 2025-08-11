
from cgshop2025_pyutils.geometry._bindings import (
    Point, FieldNumber, Polygon, Segment
)
from bernEppstein2.geometry_utils import build_polygon_from_indices, make_vertical_grid, make_horizontal_grid, split_slab_diag, extract_faces_of_grid
from triangulation import apply_bern_eppstein_triangulation

class ConstrainedTriangulation:
    """
    Drop‑in replacement for cgshop2025_pyutils.geometry._bindings.ConstrainedTriangulation
    Implement YOUR non‑obtuse algorithm here.
    """
    def __init__(self):
        self.points: list[tuple[float, float]] = []
        self.boundary: list[int] = []
        self.constraints: list[tuple[int, int]] = []
        self.triangles: list[tuple[int, int, int]] = []

    # ---- API identical to the CGAL binding --------------------------------
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

    # ----------------------------------------------------------------------
    # Here is where you insert global slicing + Section‑2 refinement
    # ----------------------------------------------------------------------
    def _run_non_obtuse_algorithm(self) -> None:
        # ---------- 0. BUILD POLYGON OBJECT FROM BOUNDARY ---------------
        poly = build_polygon_from_indices(self.boundary, self.points)

        # ---------- 1. VERTICAL SLICING ---------------------------------
        v_segments, v_vertices = make_vertical_grid(poly)
        print(v_segments[0].source())
        print(v_segments[0].target())
        # ---- 1a. *here* remove duplicates ------------------------------
        unique_vs, seen_keys = [], set()
        for seg in v_segments:
            src = (float(seg.source().x()), float(seg.source().y()))
            tgt = (float(seg.target().x()), float(seg.target().y()))
            key = tuple(sorted((src, tgt)))  # direction‑independent key
            if key not in seen_keys:
                seen_keys.add(key)
                unique_vs.append(seg)
        v_segments = unique_vs  # replace the list
        # append new coordinates to global list and remember their indices
        start_idx = len(self.points)
        self.points.extend(v_vertices)  # add Steiner tuples

        # convert those tuples to CGAL Points so we can reuse them
        steiner_points_as_CGAL = [
            Point(FieldNumber(x), FieldNumber(y)) for (x, y) in v_vertices
        ]

        # build the full list of reference points for the horizontal pass
        reference_pts = list(poly.boundary()) + steiner_points_as_CGAL

        # --- 2. horizontal slicing ----------------------------------------------
        h_segments, h_vertices = make_horizontal_grid(poly, v_segments)

        self.points.extend(h_vertices)  # add second‑stage Steiner

        # ---------- 3. COLLECT REGIONS OF THE GRID (RECT / TRI / SLAB) --
        regions = extract_faces_of_grid(poly, v_segments, h_segments, self.points)
        print("\n=== GRID REGIONS =========================================")
        for k, R in enumerate(regions, 1):
            rtype = R["type"]
            idxs = R["indices"]
            coords = [self.points[i] for i in idxs]
            print(f"{k:>3}. {rtype:<12}  idx={idxs}  pts={coords}")
        print("==========================================================\n")
        # Create mapping from old indices to new indices
        unique_points = []
        old_to_new_index = {}

        for i, point in enumerate(self.points):
            # Convert to tuple for comparison
            if isinstance(point, tuple):
                coord = point
            else:
                coord = (point[0], point[1])

            # Check if this coordinate already exists
            found_index = None
            for j, existing_point in enumerate(unique_points):
                existing_coord = existing_point if isinstance(existing_point, tuple) else (
                existing_point[0], existing_point[1])
                if abs(coord[0] - existing_coord[0]) < 1e-10 and abs(coord[1] - existing_coord[1]) < 1e-10:
                    found_index = j
                    break

            if found_index is not None:
                # Point already exists, map old index to existing index
                old_to_new_index[i] = found_index
                print(f"  Duplicate: Point {i} {coord} -> maps to existing point {found_index}")
            else:
                # New unique point
                old_to_new_index[i] = len(unique_points)
                unique_points.append(coord)
                print(f"  Unique: Point {i} {coord} -> new index {len(unique_points) - 1}")

        # Update self.points with unique points only
        self.points = unique_points

        # Update all region indices to use new indices
        for region in regions:
            region['indices'] = [old_to_new_index[old_idx] for old_idx in region['indices']]


        #
        #
        # # ---------- 5. APPLY BERN-EPPSTEIN TRIANGULATION ----------------
        #
        #
        # # Apply triangulation to all regions
        # triangles = apply_bern_eppstein_triangulation(regions, self.points)
        #
        # # Store the triangles in self.triangles
        # self.triangles.extend(triangles)
        #
        # print(f"\n=== Final Results ===")
        # print(f"Total points: {len(self.points)}")
        # print(f"Total triangles: {len(self.triangles)}")
        #
        # # Print all points with their indices
        # print(f"\n=== Point Index Mapping ===")
        # for i, point in enumerate(self.points):
        #     if isinstance(point, tuple):
        #         print(f"Point {i}: {point}")
        #     else:
        #         # Handle case where point might be a different type
        #         print(f"Point {i}: ({point[0]}, {point[1]})")
        #
        # print(f"\n=== Triangle List ===")
        # print(f"Triangles (indices): {self.triangles}")
        #
        # # Print triangles with coordinates
        # print(f"\n=== Triangles with Coordinates ===")
        # for i, (a, b, c) in enumerate(self.triangles):
        #     coord_a = self.points[a] if isinstance(self.points[a], tuple) else (self.points[a][0], self.points[a][1])
        #     coord_b = self.points[b] if isinstance(self.points[b], tuple) else (self.points[b][0], self.points[b][1])
        #     coord_c = self.points[c] if isinstance(self.points[c], tuple) else (self.points[c][0], self.points[c][1])
        #
        #     print(f"Triangle {i}: [{a}, {b}, {c}] -> {coord_a}, {coord_b}, {coord_c}")

        # ---------- 5. DONE – triangles & Steiner points ready ---------
        # self.triangles   now holds ONLY non‑obtuse triangles
        # self.points      contains original + all Steiner vertices

    # def _refine_and_append(self, tri_region) -> None:
    #     """
    #     Call your Section‑2 routine on one (obtuse / right) triangle that
    #     may have subdivision points on its legs.
    #
    #     The routine returns:
    #         steiner_coords : list[(x,y)]
    #         tris           : list[(idxA, idxB, idxC)]
    #
    #     We append the coords to self.points, remap indices, and extend
    #     self.triangles.
    #     """
    #     # --- 1. gather existing indices & coords on the two legs -------
    #     apex, footL, footR, legL_indices, legR_indices = \
    #         extract_triangle_structure(tri_region, self.points)
    #
    #     # --- 2. run Section‑2 routine (to be implemented elsewhere) ----
    #     steiner_pts, new_tris_local = refine_obtuse_triangle_section2(
    #         apex, footL, footR,
    #         legL_indices, legR_indices,
    #         self.points
    #     )
    #     #  steiner_pts = list[(x,y)]
    #     #  new_tris_local = list of index‑triplets *in the local system*
    #     #                   (i.e. 0 .. n_local-1)
    #
    #     # --- 3. append new points globally and fix indices -------------
    #     start_idx = len(self.points)
    #     self.points.extend(steiner_pts)
    #
    #     # Map local indices → global list positions
    #     idx_map = build_index_mapping(
    #         apex, footL, footR,
    #         legL_indices, legR_indices,
    #         start_idx, len(steiner_pts)
    #     )
    #     for a, b, c in new_tris_local:
    #         self.triangles.append(
    #             (idx_map[a], idx_map[b], idx_map[c])
    #         )
