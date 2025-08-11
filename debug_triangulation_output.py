#!/usr/bin/env python3
"""
FIXED: Debug and resolve non-triangular faces issue
The problem is likely in the solution creation where edges are being generated incorrectly
"""

import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
from cgshop2025_pyutils.geometry import FieldNumber, Point


class TriangulationDebugger:
    """
    CRITICAL FIX: Debug and fix triangulation issues
    """

    def __init__(self, debug=True):
        self.debug = debug

    def debug_triangulation_creation(self, triangulation, steiner_points, original_points):
        """
        Debug the triangulation to edge conversion process
        """
        print("🔍 DEBUGGING TRIANGULATION → EDGES CONVERSION")
        print("=" * 60)

        # Check 1: Validate all triangles are actually triangles
        self._validate_triangles(triangulation)

        # Check 2: Analyze point mapping
        all_points = original_points + steiner_points
        point_mapping = self._create_point_mapping(all_points)

        # Check 3: Convert triangles to edges properly
        correct_edges = self._triangles_to_edges_fixed(triangulation, point_mapping)

        return correct_edges

    def _validate_triangles(self, triangulation):
        """
        CRITICAL: Ensure all shapes are actually triangles
        """
        print(f"Validating {len(triangulation)} triangles...")

        for i, triangle in enumerate(triangulation):
            if len(triangle.vertices) != 3:
                print(f"❌ ERROR: Triangle {i} has {len(triangle.vertices)} vertices!")
                print(f"   Vertices: {triangle.vertices}")
                raise ValueError(f"Non-triangular shape found: {len(triangle.vertices)} vertices")

            # Check for degenerate triangles
            area = triangle.area()
            if area <= FieldNumber(0):
                print(f"⚠️  WARNING: Triangle {i} is degenerate (area = {area.exact()})")

        print(f"✅ All {len(triangulation)} shapes are proper triangles")

    def _create_point_mapping(self, all_points):
        """
        FIXED: Create robust point mapping using exact coordinates
        """
        point_mapping = {}

        for i, point in enumerate(all_points):
            # Use exact string representation as key
            point_key = (point.x().exact(), point.y().exact())

            if point_key in point_mapping:
                print(f"⚠️  WARNING: Duplicate point found at {point_key}")
                print(f"   Existing index: {point_mapping[point_key]}, new index: {i}")
            else:
                point_mapping[point_key] = i

        print(f"✅ Point mapping created: {len(point_mapping)} unique points")
        return point_mapping

    def _triangles_to_edges_fixed(self, triangulation, point_mapping):
        """
        CRITICAL FIX: Convert triangles to edges with proper validation
        """
        edges = []
        edge_set = set()
        triangle_edge_count = {}

        print(f"Converting {len(triangulation)} triangles to edges...")

        for tri_idx, triangle in enumerate(triangulation):
            triangle_edges = []

            # Each triangle MUST generate exactly 3 edges
            for i in range(3):
                v1 = triangle.vertices[i]
                v2 = triangle.vertices[(i + 1) % 3]

                v1_key = (v1.x().exact(), v1.y().exact())
                v2_key = (v2.x().exact(), v2.y().exact())

                # CRITICAL: All vertices must be in mapping
                if v1_key not in point_mapping:
                    raise ValueError(f"Triangle {tri_idx} vertex {i} not found in point mapping: {v1_key}")

                if v2_key not in point_mapping:
                    raise ValueError(f"Triangle {tri_idx} vertex {i + 1} not found in point mapping: {v2_key}")

                idx1 = point_mapping[v1_key]
                idx2 = point_mapping[v2_key]

                # Create edge (canonical form: smaller index first)
                edge = tuple(sorted([idx1, idx2]))
                triangle_edges.append(edge)

                # Add to global edge list if not duplicate
                if edge not in edge_set:
                    edges.append([edge[0], edge[1]])
                    edge_set.add(edge)

            # VALIDATION: Each triangle must have exactly 3 distinct edges
            if len(set(triangle_edges)) != 3:
                print(f"❌ ERROR: Triangle {tri_idx} has non-distinct edges!")
                print(f"   Triangle edges: {triangle_edges}")
                raise ValueError(f"Triangle {tri_idx} has degenerate edges")

            triangle_edge_count[tri_idx] = len(triangle_edges)

        # Final validation
        total_triangle_edges = sum(triangle_edge_count.values())
        print(f"✅ Converted {len(triangulation)} triangles → {len(edges)} unique edges")
        print(f"   Total triangle edges: {total_triangle_edges} (should be {3 * len(triangulation)})")

        if total_triangle_edges != 3 * len(triangulation):
            print(f"⚠️  WARNING: Edge count mismatch!")

        return edges


class FixedBernEppsteinSolver:
    """
    FIXED solver with proper triangulation debugging
    """

    def __init__(self, instance, config=None):
        self.instance = instance
        self.config = config or {}
        self.debug = self.config.get('debug', False)
        self.debugger = TriangulationDebugger(self.debug)

        # Initialize exact points
        self.exact_points = []
        self.steiner_points = []
        self._initialize_exact_points()

    def _initialize_exact_points(self):
        """Convert instance points to exact arithmetic"""
        self.exact_points = []

        for i in range(self.instance.num_points):
            x = FieldNumber(self.instance.points_x[i])
            y = FieldNumber(self.instance.points_y[i])
            point = Point(x, y)
            self.exact_points.append(point)

        if self.debug:
            print(f"Initialized {len(self.exact_points)} exact points")

    def solve(self):
        """
        FIXED solve with proper debugging
        """
        try:
            # Get boundary points
            boundary_points = [self.exact_points[i] for i in self.instance.region_boundary]

            if self.debug:
                print(f"Boundary points: {len(boundary_points)}")
                for i, p in enumerate(boundary_points):
                    print(f"  {i}: ({p.x().exact()}, {p.y().exact()})")

            # Simple triangulation for debugging
            triangulation = self._simple_triangulation(boundary_points)

            if self.debug:
                print(f"Created {len(triangulation)} triangles")
                for i, tri in enumerate(triangulation):
                    print(f"  Triangle {i}: {len(tri.vertices)} vertices")

            # FIXED: Use debugger to create solution
            edges = self.debugger.debug_triangulation_creation(
                triangulation, self.steiner_points, self.exact_points
            )

            # Create solution
            solution = self._create_solution_from_edges(edges)
            return solution

        except Exception as e:
            print(f"❌ Solve failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _simple_triangulation(self, boundary_points):
        """
        SIMPLE triangulation that GUARANTEES triangles only
        """
        triangles = []

        if len(boundary_points) < 3:
            return triangles

        if len(boundary_points) == 3:
            # Already a triangle
            triangle = ExactTriangle(*boundary_points)

            # Handle obtuse triangle
            if triangle.is_obtuse:
                fixed_triangles = self._drop_altitude_fixed(triangle)
                triangles.extend(fixed_triangles)
            else:
                triangles.append(triangle)
        else:
            # Fan triangulation - GUARANTEED to create only triangles
            for i in range(1, len(boundary_points) - 1):
                triangle = ExactTriangle(
                    boundary_points[0],
                    boundary_points[i],
                    boundary_points[i + 1]
                )

                # Handle obtuse triangles
                if triangle.is_obtuse:
                    fixed_triangles = self._drop_altitude_fixed(triangle)
                    triangles.extend(fixed_triangles)
                else:
                    triangles.append(triangle)

        return triangles

    def _drop_altitude_fixed(self, triangle):
        """
        FIXED altitude dropping with validation
        """
        if self.debug:
            print(f"  Dropping altitude for obtuse triangle")

        # Find obtuse vertex
        obtuse_idx = self._find_obtuse_vertex(triangle.vertices)
        if obtuse_idx is None:
            return [triangle]

        obtuse_vertex = triangle.vertices[obtuse_idx]
        base_start = triangle.vertices[(obtuse_idx + 1) % 3]
        base_end = triangle.vertices[(obtuse_idx + 2) % 3]

        # Drop altitude
        altitude_foot = self._drop_altitude(obtuse_vertex, base_start, base_end)

        # Create two triangles
        tri1 = ExactTriangle(obtuse_vertex, base_start, altitude_foot)
        tri2 = ExactTriangle(obtuse_vertex, altitude_foot, base_end)

        # Add Steiner point
        self.steiner_points.append(altitude_foot)

        if self.debug:
            print(f"    Created {2} triangles from altitude drop")
            print(f"    Steiner point: ({altitude_foot.x().exact()}, {altitude_foot.y().exact()})")

        return [tri1, tri2]

    def _find_obtuse_vertex(self, vertices):
        """Find obtuse vertex in triangle"""
        for i in range(3):
            v1 = vertices[(i + 1) % 3]
            v2 = vertices[i]
            v3 = vertices[(i + 2) % 3]

            if self._is_obtuse_angle(v1, v2, v3):
                return i
        return None

    def _is_obtuse_angle(self, p1, vertex, p2):
        """Check if angle is obtuse"""
        v1_x = p1.x() - vertex.x()
        v1_y = p1.y() - vertex.y()
        v2_x = p2.x() - vertex.x()
        v2_y = p2.y() - vertex.y()

        dot_product = v1_x * v2_x + v1_y * v2_y
        return dot_product < FieldNumber(0)

    def _drop_altitude(self, apex, base_start, base_end):
        """Drop perpendicular from apex to base"""
        base_x = base_end.x() - base_start.x()
        base_y = base_end.y() - base_start.y()

        apex_x = apex.x() - base_start.x()
        apex_y = apex.y() - base_start.y()

        base_len_sq = base_x * base_x + base_y * base_y

        if base_len_sq == FieldNumber(0):
            return base_start

        dot_product = apex_x * base_x + apex_y * base_y
        t = dot_product / base_len_sq

        foot_x = base_start.x() + t * base_x
        foot_y = base_start.y() + t * base_y

        return Point(foot_x, foot_y)

    def _create_solution_from_edges(self, edges):
        """
        FIXED: Create solution from validated edges
        """
        from cgshop2025_pyutils.data_schemas import Cgshop2025Solution

        # Extract Steiner point coordinates
        steiner_points_x = [p.x().exact() for p in self.steiner_points]
        steiner_points_y = [p.y().exact() for p in self.steiner_points]

        if self.debug:
            print(f"Creating solution with {len(edges)} edges")
            print(f"Steiner points: {len(steiner_points_x)}")

        return Cgshop2025Solution(
            content_type="CG_SHOP_2025_Solution",
            instance_uid=self.instance.instance_uid,
            steiner_points_x=steiner_points_x,
            steiner_points_y=steiner_points_y,
            edges=edges
        )


class ExactTriangle:
    """Simple triangle with exact arithmetic"""

    def __init__(self, p1, p2, p3):
        self.vertices = [p1, p2, p3]
        self._is_obtuse = None

    @property
    def is_obtuse(self):
        if self._is_obtuse is None:
            self._check_obtuse()
        return self._is_obtuse

    def _check_obtuse(self):
        """Check if any angle is obtuse"""
        self._is_obtuse = False

        for i in range(3):
            v1 = self.vertices[(i + 1) % 3]
            v2 = self.vertices[i]
            v3 = self.vertices[(i + 2) % 3]

            # Check if angle at v2 is obtuse
            vec1_x = v1.x() - v2.x()
            vec1_y = v1.y() - v2.y()
            vec2_x = v3.x() - v2.x()
            vec2_y = v3.y() - v2.y()

            dot_product = vec1_x * vec2_x + vec1_y * vec2_y

            if dot_product < FieldNumber(0):
                self._is_obtuse = True
                break

    def area(self):
        """Calculate triangle area"""
        p1, p2, p3 = self.vertices
        det = (p2.x() - p1.x()) * (p3.y() - p1.y()) - (p3.x() - p1.x()) * (p2.y() - p1.y())
        return abs(det) / FieldNumber(2)


def debug_fixed_implementation():
    """
    Debug the FIXED implementation
    """
    print("🔧 TESTING FIXED IMPLEMENTATION")
    print("=" * 50)

    # Load test instance
    instance_file = Path("instances/cgshop2025_examples_ortho_10_ff68423e.instance.json")

    if not instance_file.exists():
        print(f"❌ Instance file not found: {instance_file}")
        return

    with open(instance_file, 'r') as f:
        data = json.load(f)

    instance = Cgshop2025Instance(**data)
    print(f"Testing instance: {instance.instance_uid}")
    print(f"Points: {instance.num_points}")

    # Test with fixed solver
    solver = FixedBernEppsteinSolver(instance, {'debug': True})

    try:
        solution = solver.solve()

        print(f"\n✅ FIXED SOLUTION CREATED")
        print(f"Steiner points: {len(solution.steiner_points_x)}")
        print(f"Edges: {len(solution.edges)}")

        # Verify structure
        total_points = instance.num_points + len(solution.steiner_points_x)

        # Check edge validity
        valid_edges = True
        for i, edge in enumerate(solution.edges):
            if len(edge) != 2:
                print(f"❌ Edge {i} has {len(edge)} endpoints")
                valid_edges = False

            for j, idx in enumerate(edge):
                if not (0 <= idx < total_points):
                    print(f"❌ Edge {i} endpoint {j} out of range: {idx}")
                    valid_edges = False

        if valid_edges:
            print(f"✅ All edges are valid")

        # Check for high-degree vertices (sign of non-triangular faces)
        vertex_degrees = [0] * total_points
        for edge in solution.edges:
            vertex_degrees[edge[0]] += 1
            vertex_degrees[edge[1]] += 1

        high_degree = [i for i, d in enumerate(vertex_degrees) if d > 6]
        if high_degree:
            print(f"⚠️  High degree vertices (>6): {high_degree}")
        else:
            print(f"✅ No suspiciously high degree vertices")

        return solution

    except Exception as e:
        print(f"❌ Fixed implementation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    solution = debug_fixed_implementation()

    if solution:
        print(f"\n🎉 DEBUGGING COMPLETE - SOLUTION CREATED")
        print(f"Next step: Test with verification tools")
    else:
        print(f"\n💥 DEBUGGING FAILED - MORE FIXES NEEDED")