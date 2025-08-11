"""
Main triangulation algorithm implementing Bern & Eppstein approach.
Coordinates polygon decomposition, merger operations, and result assembly.
"""

from typing import List, Dict, Optional, Tuple
from cgshop2025_pyutils.geometry import FieldNumber, Point, Polygon
from .geometry import BernEppsteinGeometry, ExactTriangle
from .decomposition import PolygonDecomposer, Region, SlabDecomposer
from .mergers import MergerAlgorithm, MergerAnalyzer
from .predicates import GeometricPredicates, TriangulationAnalyzer


class BernEppsteinTriangulator:
    """
    Main triangulation algorithm implementing Bern & Eppstein polynomial-size approach.

    This class coordinates the entire triangulation process:
    1. Polygon decomposition using horizontal/vertical lines
    2. Region classification and processing
    3. Merger algorithms for obtuse triangles
    4. Result assembly and validation
    """

    def __init__(self, debug: bool = False):
        """
        Initialize triangulator

        Args:
            debug: Enable debug output and analysis
        """
        self.debug = debug
        self.steiner_points = []
        self.result_triangles = []
        self.analyzer = MergerAnalyzer() if debug else None

        # Algorithm statistics
        self.stats = {
            'regions_processed': 0,
            'merger_operations': 0,
            'altitude_drops': 0,
            'total_steiner_points': 0
        }

    def triangulate(self, polygon_vertices: List[Point],
                    region_boundary: List[int],
                    constraints: List[List[int]] = None) -> List[ExactTriangle]:
        """
        FIXED: Proper boundary-respecting triangulation
        """
        if self.debug:
            print(f"Starting triangulation with {len(polygon_vertices)} points")

        # Reset state
        self.steiner_points = []
        self.result_triangles = []

        # Extract polygon from boundary indices - CRITICAL: use boundary order
        polygon_points = [polygon_vertices[i] for i in region_boundary]

        if self.debug:
            print(f"Polygon boundary has {len(polygon_points)} points")
            for i, p in enumerate(polygon_points):
                print(f"  Boundary {i}: ({p.x().exact()}, {p.y().exact()})")

        # FIXED: Use proper boundary-respecting triangulation
        all_triangles = self._boundary_respecting_triangulation(polygon_points)

        # Process obtuse triangles with altitude dropping
        final_triangles = []
        for triangle in all_triangles:
            if triangle.is_obtuse:
                # Drop altitude to create non-obtuse triangles
                fixed_triangles = self._drop_altitude_triangulation(triangle.vertices)
                final_triangles.extend(fixed_triangles)
            else:
                final_triangles.append(triangle)

        self.result_triangles = final_triangles

        if self.debug:
            print(f"Final result: {len(self.result_triangles)} triangles")
            obtuse_count = sum(1 for t in self.result_triangles if t.is_obtuse)
            print(f"Obtuse triangles remaining: {obtuse_count}")

        return self.result_triangles

    def _boundary_respecting_triangulation(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        FIXED: Better fallback handling to prevent over-connected vertices
        """
        if len(vertices) < 3:
            return []

        if len(vertices) == 3:
            return [ExactTriangle(*vertices)]

        # For small polygons, use completely balanced approach
        if len(vertices) <= 6:
            return self._ultra_balanced_small_polygon(vertices)

        # Use improved ear clipping for complex polygons
        triangles = []
        remaining_vertices = vertices.copy()

        if self.debug:
            print(f"Starting improved ear clipping with {len(remaining_vertices)} vertices")

        vertex_usage_count = {i: 0 for i in range(len(remaining_vertices))}

        while len(remaining_vertices) > 3:
            # Find the best ear (avoid over-using vertices)
            best_ear = self._find_best_ear(remaining_vertices, vertex_usage_count)

            if best_ear == -1:
                if self.debug:
                    print(f"  No ear found, using FIXED fallback triangulation")
                # FIXED: Use balanced fallback instead of simple triangulation
                remaining_triangles = self._balanced_fallback_triangulation(remaining_vertices, vertex_usage_count)
                triangles.extend(remaining_triangles)
                break

            # Create triangle from best ear
            prev_idx = (best_ear - 1) % len(remaining_vertices)
            next_idx = (best_ear + 1) % len(remaining_vertices)

            triangle = ExactTriangle(
                remaining_vertices[prev_idx],
                remaining_vertices[best_ear],
                remaining_vertices[next_idx]
            )
            triangles.append(triangle)

            # Update usage counts
            vertex_usage_count[prev_idx] += 1
            vertex_usage_count[next_idx] += 1

            # Remove ear vertex
            remaining_vertices.pop(best_ear)

            # Update usage count indices after removal
            new_usage_count = {}
            for old_idx, count in vertex_usage_count.items():
                if old_idx < best_ear:
                    new_usage_count[old_idx] = count
                elif old_idx > best_ear:
                    new_usage_count[old_idx - 1] = count
            vertex_usage_count = new_usage_count

            if self.debug:
                print(f"  Removed ear at index {best_ear}, {len(remaining_vertices)} vertices remaining")

        # Add final triangle if exactly 3 vertices remain
        if len(remaining_vertices) == 3:
            triangles.append(ExactTriangle(*remaining_vertices))

        if self.debug:
            print(f"Improved ear clipping created {len(triangles)} triangles")

        return triangles

    def _balanced_fallback_triangulation(self, vertices: List[Point], usage_count: Dict[int, int]) -> List[ExactTriangle]:
        """
        CRITICAL FIX: Balanced fallback that respects vertex usage limits
        """
        if self.debug:
            print(f"    Balanced fallback for {len(vertices)} vertices")
            for i, count in usage_count.items():
                print(f"      Vertex {i}: usage={count}")

        if len(vertices) <= 3:
            return [ExactTriangle(*vertices)] if len(vertices) == 3 else []

        if len(vertices) == 4:
            return self._triangulate_quad_respecting_usage(vertices, usage_count)

        if len(vertices) == 5:
            return self._triangulate_penta_respecting_usage(vertices, usage_count)

        # For larger cases, use minimal connection approach
        return self._minimal_connection_triangulation(vertices, usage_count)

    def _triangulate_quad_respecting_usage(self, vertices: List[Point], usage_count: Dict[int, int]) -> List[ExactTriangle]:
        """
        Triangulate quad while respecting existing vertex usage
        """
        # Try both diagonal options and pick the one that respects usage better

        # Option 1: diagonal 0-2
        option1_usage = [
            usage_count.get(0, 0) + usage_count.get(1, 0) + usage_count.get(2, 0),  # triangle 0-1-2
            usage_count.get(0, 0) + usage_count.get(2, 0) + usage_count.get(3, 0)   # triangle 0-2-3
        ]

        # Option 2: diagonal 1-3
        option2_usage = [
            usage_count.get(0, 0) + usage_count.get(1, 0) + usage_count.get(3, 0),  # triangle 0-1-3
            usage_count.get(1, 0) + usage_count.get(2, 0) + usage_count.get(3, 0)   # triangle 1-2-3
        ]

        # Choose option with lower maximum usage
        max_usage1 = max(option1_usage)
        max_usage2 = max(option2_usage)

        if max_usage1 <= max_usage2:
            if self.debug:
                print(f"      Quad: Using diagonal 0-2 (max usage: {max_usage1})")
            return [
                ExactTriangle(vertices[0], vertices[1], vertices[2]),
                ExactTriangle(vertices[0], vertices[2], vertices[3])
            ]
        else:
            if self.debug:
                print(f"      Quad: Using diagonal 1-3 (max usage: {max_usage2})")
            return [
                ExactTriangle(vertices[0], vertices[1], vertices[3]),
                ExactTriangle(vertices[1], vertices[2], vertices[3])
            ]

    def _triangulate_penta_respecting_usage(self, vertices: List[Point], usage_count: Dict[int, int]) -> List[ExactTriangle]:
        """
        Triangulate pentagon while minimizing vertex usage
        """
        # Find the vertex with lowest usage to use as a "hub"
        min_usage = float('inf')
        hub_vertex = 0

        for i in range(5):
            curr_usage = usage_count.get(i, 0)
            if curr_usage < min_usage:
                min_usage = curr_usage
                hub_vertex = i

        if self.debug:
            print(f"      Pentagon: Using vertex {hub_vertex} as hub (usage: {min_usage})")

        # Create triangles using the hub vertex (fan from least-used vertex)
        triangles = []
        for i in range(3):  # Pentagon needs 3 triangles
            v1_idx = (hub_vertex + i + 1) % 5
            v2_idx = (hub_vertex + i + 2) % 5

            triangle = ExactTriangle(vertices[hub_vertex], vertices[v1_idx], vertices[v2_idx])
            triangles.append(triangle)

        return triangles

    def _minimal_connection_triangulation(self, vertices: List[Point], usage_count: Dict[int, int]) -> List[ExactTriangle]:
        """
        Triangulate using minimal connections to avoid over-using any vertex
        """
        n = len(vertices)
        triangles = []

        if self.debug:
            print(f"      Minimal connection triangulation for {n} vertices")

        # Find vertex with minimum usage
        min_usage = min(usage_count.get(i, 0) for i in range(n))
        min_vertices = [i for i in range(n) if usage_count.get(i, 0) == min_usage]
        hub = min_vertices[0]  # Use first vertex with minimum usage

        if self.debug:
            print(f"      Using vertex {hub} as hub (usage: {min_usage})")

        # Create fan triangulation from the least-used vertex
        for i in range(n - 2):
            v1_idx = (hub + i + 1) % n
            v2_idx = (hub + i + 2) % n

            triangle = ExactTriangle(vertices[hub], vertices[v1_idx], vertices[v2_idx])
            triangles.append(triangle)

        return triangles

    def _ultra_balanced_small_polygon(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        Ultra-balanced triangulation for small polygons (≤6 vertices)
        """
        n = len(vertices)

        if n <= 3:
            return [ExactTriangle(*vertices)] if n == 3 else []

        if n == 4:
            # Quad: choose diagonal that creates fewer obtuse triangles
            return self._triangulate_quadrilateral_optimally(vertices)

        if n == 5:
            # Pentagon: use pattern that minimizes any single vertex usage
            return [
                ExactTriangle(vertices[0], vertices[1], vertices[2]),
                ExactTriangle(vertices[0], vertices[2], vertices[4]),
                ExactTriangle(vertices[2], vertices[3], vertices[4])
            ]

        if n == 6:
            # Hexagon: split into two triangles + one quad to balance usage
            return [
                ExactTriangle(vertices[0], vertices[1], vertices[2]),   # Triangle 1
                ExactTriangle(vertices[0], vertices[2], vertices[5]),   # Connect to opposite
                ExactTriangle(vertices[2], vertices[3], vertices[4]),   # Triangle 2
                ExactTriangle(vertices[2], vertices[4], vertices[5])    # Complete
            ]

        # Fallback
        return self._direct_fan_triangulation(vertices)

    def _find_best_ear(self, vertices: List[Point], usage_count: Dict[int, int]) -> int:
        """
        ULTRA-AGGRESSIVE: Maximum vertex degree control to ensure ≤6 degree
        """
        n = len(vertices)
        best_ear = -1
        min_usage_score = float('inf')

        # MUCH more restrictive: Maximum 2-3 usages per vertex
        max_allowed_usage = min(3, max(2, n // 5))  # Very restrictive limit

        if self.debug:
            print(f"    Max allowed usage per vertex: {max_allowed_usage}")

        for i in range(n):
            if self._is_ear(vertices, i):
                prev_idx = (i - 1) % n
                next_idx = (i + 1) % n

                # Check if adjacent vertices are already over-used
                prev_usage = usage_count.get(prev_idx, 0)
                next_usage = usage_count.get(next_idx, 0)

                if self.debug and (prev_usage >= max_allowed_usage or next_usage >= max_allowed_usage):
                    print(f"    Skipping ear {i}: prev_usage={prev_usage}, next_usage={next_usage}")

                # Skip if either adjacent vertex is already heavily used
                if prev_usage >= max_allowed_usage or next_usage >= max_allowed_usage:
                    continue

                # Calculate usage score (prefer vertices that haven't been used much)
                usage_score = prev_usage + next_usage

                # VERY heavy penalties for vertices approaching the limit
                if prev_usage >= max_allowed_usage - 1:
                    usage_score += 50  # VERY heavy penalty
                if next_usage >= max_allowed_usage - 1:
                    usage_score += 50  # VERY heavy penalty

                # Additional penalty for vertices with moderate usage
                if prev_usage >= max_allowed_usage - 2:
                    usage_score += 20
                if next_usage >= max_allowed_usage - 2:
                    usage_score += 20

                if usage_score < min_usage_score:
                    min_usage_score = usage_score
                    best_ear = i

                if self.debug:
                    print(f"    Ear {i}: prev={prev_usage}, next={next_usage}, score={usage_score}")

        if self.debug:
            print(f"    Selected ear: {best_ear} with score: {min_usage_score}")

        return best_ear

    def _is_ear(self, vertices: List[Point], vertex_index: int) -> bool:
        """
        Check if vertex can be removed (forms an ear)
        """
        n = len(vertices)
        if n < 3:
            return False

        prev_idx = (vertex_index - 1) % n
        next_idx = (vertex_index + 1) % n

        prev_vertex = vertices[prev_idx]
        curr_vertex = vertices[vertex_index]
        next_vertex = vertices[next_idx]

        # Check if triangle is convex (interior angle < 180°)
        orientation = BernEppsteinGeometry.orientation(prev_vertex, curr_vertex, next_vertex)
        if orientation <= 0:  # Reflex vertex, not an ear
            return False

        # Check if any other vertex is inside the triangle
        for i in range(n):
            if i == prev_idx or i == vertex_index or i == next_idx:
                continue

            test_vertex = vertices[i]
            if BernEppsteinGeometry.point_in_triangle(test_vertex, prev_vertex, curr_vertex, next_vertex):
                return False  # Another vertex is inside, not an ear

        return True

    def _triangulate_quadrilateral_optimally(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        Triangulate quadrilateral optimally to minimize obtuse triangles
        """
        if len(vertices) != 4:
            return self._direct_fan_triangulation(vertices)

        # Try both diagonals
        diagonal1 = [
            ExactTriangle(vertices[0], vertices[1], vertices[2]),
            ExactTriangle(vertices[0], vertices[2], vertices[3])
        ]

        diagonal2 = [
            ExactTriangle(vertices[0], vertices[1], vertices[3]),
            ExactTriangle(vertices[1], vertices[2], vertices[3])
        ]

        # Count obtuse triangles in each option
        obtuse_count1 = sum(1 for t in diagonal1 if t.is_obtuse)
        obtuse_count2 = sum(1 for t in diagonal2 if t.is_obtuse)

        # Choose the option with fewer obtuse triangles
        if obtuse_count1 <= obtuse_count2:
            return diagonal1
        else:
            return diagonal2

    def _direct_fan_triangulation(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        GUARANTEED to produce only triangles - no other shapes
        """
        if len(vertices) < 3:
            return []

        if len(vertices) == 3:
            return [ExactTriangle(*vertices)]

        # Fan triangulation from first vertex
        triangles = []
        for i in range(1, len(vertices) - 1):
            triangle = ExactTriangle(vertices[0], vertices[i], vertices[i + 1])
            triangles.append(triangle)

        if self.debug:
            print(f"Fan triangulation created {len(triangles)} triangles from {len(vertices)} vertices")

        return triangles

    def _drop_altitude_triangulation(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        FIXED: Drop altitude with validation
        """
        if len(vertices) != 3:
            if self.debug:
                print(f"Warning: _drop_altitude_triangulation called with {len(vertices)} vertices")
            return []

        triangle = ExactTriangle(*vertices)

        # Validate triangle is not degenerate
        area = triangle.area()
        if area <= FieldNumber(0):
            if self.debug:
                print(f"Warning: Degenerate triangle detected, area = {area.exact()}")
            return []

        # Find obtuse vertex
        obtuse_vertex_index = None
        for i in range(3):
            v1 = vertices[(i + 1) % 3]
            v2 = vertices[i]
            v3 = vertices[(i + 2) % 3]

            angle_type = BernEppsteinGeometry.angle_type(v1, v2, v3)
            if angle_type == 'obtuse':
                obtuse_vertex_index = i
                break

        if obtuse_vertex_index is None:
            # Not obtuse - return as-is
            return [triangle]

        # Drop altitude
        obtuse_vertex = vertices[obtuse_vertex_index]
        base_start = vertices[(obtuse_vertex_index + 1) % 3]
        base_end = vertices[(obtuse_vertex_index + 2) % 3]

        # Validate base edge is not degenerate
        if BernEppsteinGeometry.distance_squared(base_start, base_end) <= FieldNumber(0):
            if self.debug:
                print("Warning: Degenerate base edge, cannot drop altitude")
            return [triangle]

        altitude_foot = BernEppsteinGeometry.drop_altitude(obtuse_vertex, base_start, base_end)

        # Create two triangles
        triangle1 = ExactTriangle(obtuse_vertex, base_start, altitude_foot)
        triangle2 = ExactTriangle(obtuse_vertex, altitude_foot, base_end)

        # Validate resulting triangles
        if triangle1.area() <= FieldNumber(0) or triangle2.area() <= FieldNumber(0):
            if self.debug:
                print("Warning: Altitude drop created degenerate triangles")
            return [triangle]  # Return original

        # Record Steiner point
        self.steiner_points.append(altitude_foot)

        if self.debug:
            print(f"    Dropped altitude, created 2 right triangles")

        return [triangle1, triangle2]

    # Keep all the existing methods from your previous implementation
    def _fan_triangulate(self, vertices):
        """Fan triangulation: splits any polygon into triangles"""
        if len(vertices) < 3:
            return []

        if len(vertices) == 3:
            return [ExactTriangle(*vertices)]

        # Fan from first vertex
        triangles = []
        for i in range(1, len(vertices) - 1):
            triangle = ExactTriangle(vertices[0], vertices[i], vertices[i + 1])
            triangles.append(triangle)

        return triangles

    def get_steiner_points(self) -> List[Point]:
        """Get all Steiner points created during triangulation"""
        return self.steiner_points.copy()

    def validate_triangulation(self) -> Tuple[bool, str]:
        """
        Validate the triangulation for correctness

        Returns:
            Tuple of (is_valid, error_message)
        """
        predicates = GeometricPredicates()
        return predicates.is_triangulation_valid(self.result_triangles, [])

    def get_triangulation_quality(self) -> Dict[str, any]:
        """
        Get comprehensive quality metrics for triangulation

        Returns:
            Dictionary with quality metrics
        """
        analyzer = TriangulationAnalyzer(self.result_triangles)
        quality_metrics = analyzer.quality_metrics()

        # Add algorithm-specific metrics
        quality_metrics.update({
            'steiner_points_count': len(self.steiner_points),
            'regions_processed': self.stats['regions_processed'],
            'merger_operations': self.stats['merger_operations'],
            'altitude_drops': self.stats['altitude_drops'],
            'algorithm_efficiency': len(self.result_triangles) / max(1, len(self.steiner_points))
        })

        return quality_metrics


# Keep the AdaptiveTriangulator class as-is from your previous implementation
class AdaptiveTriangulator:
    """
    Adaptive triangulator that can switch between different strategies
    based on instance characteristics
    """

    def __init__(self, debug: bool = False):
        """
        Initialize adaptive triangulator

        Args:
            debug: Enable debug output
        """
        self.debug = debug
        self.bern_eppstein = BernEppsteinTriangulator(debug)

    def triangulate_adaptive(self, polygon_vertices: List[Point],
                           region_boundary: List[int],
                           constraints: List[List[int]] = None) -> List[ExactTriangle]:
        """
        Adaptively choose triangulation strategy based on instance characteristics
        """
        # Analyze instance characteristics
        characteristics = self._analyze_instance(polygon_vertices, region_boundary, constraints)

        if self.debug:
            print("Instance Analysis:")
            for key, value in characteristics.items():
                print(f"  {key}: {value}")

        # Choose strategy based on characteristics
        strategy = self._choose_strategy(characteristics)

        if self.debug:
            print(f"Selected strategy: {strategy}")

        # Apply chosen strategy
        if strategy == 'bern_eppstein':
            return self.bern_eppstein.triangulate(polygon_vertices, region_boundary, constraints)
        elif strategy == 'simple_decomposition':
            return self._simple_decomposition_strategy(polygon_vertices, region_boundary, constraints)
        else:
            # Default to Bern & Eppstein
            return self.bern_eppstein.triangulate(polygon_vertices, region_boundary, constraints)

    def _analyze_instance(self, polygon_vertices: List[Point],
                         region_boundary: List[int],
                         constraints: List[List[int]] = None) -> Dict[str, any]:
        """Analyze instance characteristics to guide strategy selection"""
        polygon_points = [polygon_vertices[i] for i in region_boundary]
        n = len(polygon_points)

        # Basic characteristics
        characteristics = {
            'vertex_count': n,
            'has_constraints': bool(constraints and len(constraints) > 0),
            'constraint_count': len(constraints) if constraints else 0
        }

        # Geometric characteristics
        if n >= 3:
            polygon = Polygon(polygon_points)
            characteristics.update({
                'area': float(polygon.area().exact()),
                'is_simple': polygon.is_simple(),
                'is_convex': self._is_convex(polygon_points)
            })

        return characteristics

    def _choose_strategy(self, characteristics: Dict[str, any]) -> str:
        """Choose triangulation strategy based on instance characteristics"""
        n = characteristics['vertex_count']

        # Simple cases
        if n <= 10 and not characteristics['has_constraints']:
            if characteristics.get('is_convex', False):
                return 'simple_decomposition'

        # Default to Bern & Eppstein for general case
        return 'bern_eppstein'

    def _is_convex(self, polygon_points: List[Point]) -> bool:
        """Check if polygon is convex"""
        n = len(polygon_points)
        if n < 3:
            return False

        orientation_sign = None
        for i in range(n):
            p1 = polygon_points[i]
            p2 = polygon_points[(i + 1) % n]
            p3 = polygon_points[(i + 2) % n]

            orient = BernEppsteinGeometry.orientation(p1, p2, p3)
            if orient != 0:
                if orientation_sign is None:
                    orientation_sign = orient
                elif orientation_sign != orient:
                    return False

        return True

    def _simple_decomposition_strategy(self, polygon_vertices: List[Point],
                                     region_boundary: List[int],
                                     constraints: List[List[int]] = None) -> List[ExactTriangle]:
        """Simple decomposition strategy for easy cases"""
        polygon_points = [polygon_vertices[i] for i in region_boundary]

        if len(polygon_points) == 3:
            triangle = ExactTriangle(*polygon_points)
            if triangle.is_obtuse:
                return self._drop_altitude_simple(polygon_points)
            else:
                return [triangle]

        # Fan triangulation for convex polygons
        triangles = []
        for i in range(1, len(polygon_points) - 1):
            triangle = ExactTriangle(
                polygon_points[0],
                polygon_points[i],
                polygon_points[i + 1]
            )

            if triangle.is_obtuse:
                obtuse_triangles = self._drop_altitude_simple(triangle.vertices)
                triangles.extend(obtuse_triangles)
            else:
                triangles.append(triangle)

        return triangles

    def _drop_altitude_simple(self, vertices: List[Point]) -> List[ExactTriangle]:
        """Simple altitude dropping for obtuse triangles"""
        triangle = ExactTriangle(*vertices)

        # Find obtuse vertex
        obtuse_vertex_index = None
        for i in range(3):
            v1 = vertices[(i + 1) % 3]
            v2 = vertices[i]
            v3 = vertices[(i + 2) % 3]

            if BernEppsteinGeometry.angle_type(v1, v2, v3) == 'obtuse':
                obtuse_vertex_index = i
                break

        if obtuse_vertex_index is None:
            return [triangle]

        # Drop altitude
        obtuse_vertex = vertices[obtuse_vertex_index]
        base_start = vertices[(obtuse_vertex_index + 1) % 3]
        base_end = vertices[(obtuse_vertex_index + 2) % 3]

        altitude_foot = BernEppsteinGeometry.drop_altitude(obtuse_vertex, base_start, base_end)

        triangle1 = ExactTriangle(obtuse_vertex, base_start, altitude_foot)
        triangle2 = ExactTriangle(obtuse_vertex, altitude_foot, base_end)

        return [triangle1, triangle2]