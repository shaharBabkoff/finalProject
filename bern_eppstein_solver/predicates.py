"""
Geometric predicates and tests for the Bern & Eppstein algorithm.
All predicates use exact arithmetic via cgshop2025_pyutils FieldNumber.
"""

from typing import List, Optional, Tuple
from cgshop2025_pyutils.geometry import FieldNumber, Point, Segment
from .geometry import BernEppsteinGeometry, ExactTriangle


class GeometricPredicates:
    """Collection of exact geometric predicates for triangulation algorithm"""

    @staticmethod
    def is_triangle_non_obtuse(triangle: ExactTriangle) -> bool:
        """
        Test if triangle has no obtuse angles (all angles ≤ 90°)

        Args:
            triangle: Triangle to test

        Returns:
            True if triangle is non-obtuse
        """
        return not triangle.is_obtuse

    @staticmethod
    def can_apply_apex_merger(apex: Point, subdivision_points: List[Point],
                              opposite_vertex: Point) -> bool:
        """
        Test if apex merger is geometrically feasible

        Args:
            apex: Apex vertex of triangle
            subdivision_points: Points subdividing the legs
            opposite_vertex: Vertex opposite to apex

        Returns:
            True if apex merger can be applied
        """
        if not subdivision_points:
            return False

        # Find first subdivision point closest to apex
        first_subdivision = subdivision_points[0]  # Simplified - would need proper ordering

        # Check if perpendiculars intersect appropriately
        # This is a simplified test - full implementation would check geometric constraints
        try:
            # Attempt to construct apex merger point
            intersection = BernEppsteinGeometry.perpendicular_intersection(
                first_subdivision, apex, opposite_vertex,
                apex, apex, opposite_vertex  # Simplified line definitions
            )
            return intersection is not None
        except:
            return False

    @staticmethod
    def can_apply_side_merger(subdivision_points: List[Point]) -> bool:
        """
        Test if side merger is feasible

        Args:
            subdivision_points: Points subdividing triangle legs

        Returns:
            True if side merger can be applied
        """
        # Need at least two adjacent subdivision points
        return len(subdivision_points) >= 2

    @staticmethod
    def are_points_collinear(p1: Point, p2: Point, p3: Point, tolerance: Optional[FieldNumber] = None) -> bool:
        """
        Test if three points are collinear using exact arithmetic

        Args:
            p1, p2, p3: Points to test
            tolerance: Optional tolerance (not needed for exact arithmetic)

        Returns:
            True if points are collinear
        """
        return BernEppsteinGeometry.orientation(p1, p2, p3) == 0

    @staticmethod
    def is_point_on_segment(point: Point, segment_start: Point, segment_end: Point) -> bool:
        """
        Test if point lies on line segment

        Args:
            point: Point to test
            segment_start, segment_end: Segment endpoints

        Returns:
            True if point is on segment
        """
        # First check collinearity
        if not GeometricPredicates.are_points_collinear(point, segment_start, segment_end):
            return False

        # Check if point is between segment endpoints
        min_x = min(segment_start.x(), segment_end.x())
        max_x = max(segment_start.x(), segment_end.x())
        min_y = min(segment_start.y(), segment_end.y())
        max_y = max(segment_start.y(), segment_end.y())

        return (min_x <= point.x() <= max_x and
                min_y <= point.y() <= max_y)

    @staticmethod
    def segments_intersect(seg1_start: Point, seg1_end: Point,
                           seg2_start: Point, seg2_end: Point) -> bool:
        """
        Test if two line segments intersect

        Args:
            seg1_start, seg1_end: First segment endpoints
            seg2_start, seg2_end: Second segment endpoints

        Returns:
            True if segments intersect
        """
        # Use cgshop2025_pyutils Segment intersection
        seg1 = Segment(seg1_start, seg1_end)
        seg2 = Segment(seg2_start, seg2_end)

        return seg1.does_intersect(seg2)

    @staticmethod
    def point_in_polygon(point: Point, polygon_vertices: List[Point]) -> bool:
        """
        Test if point is inside polygon using winding number

        Args:
            point: Point to test
            polygon_vertices: Vertices of polygon in order

        Returns:
            True if point is inside polygon
        """
        if len(polygon_vertices) < 3:
            return False

        # Ray casting algorithm using exact arithmetic
        ray_intersections = 0
        n = len(polygon_vertices)

        for i in range(n):
            v1 = polygon_vertices[i]
            v2 = polygon_vertices[(i + 1) % n]

            # Check if ray from point to right intersects edge v1-v2
            if ((v1.y() > point.y()) != (v2.y() > point.y())):
                # Calculate intersection x-coordinate
                slope = (v2.x() - v1.x()) / (v2.y() - v1.y())
                intersect_x = v1.x() + slope * (point.y() - v1.y())

                if point.x() < intersect_x:
                    ray_intersections += 1

        return ray_intersections % 2 == 1

    @staticmethod
    def is_triangulation_valid(triangles: List[ExactTriangle],
                               boundary_points: List[Point]) -> Tuple[bool, str]:
        """
        Validate triangulation for correctness

        Args:
            triangles: List of triangles in triangulation
            boundary_points: Original boundary points

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not triangles:
            return False, "No triangles in triangulation"

        # Check 1: All triangles are valid (non-degenerate)
        for i, triangle in enumerate(triangles):
            if triangle.area() <= FieldNumber(0):
                return False, f"Triangle {i} is degenerate (zero or negative area)"

        # Check 2: No overlapping triangles (simplified check)
        # Full implementation would check for proper edge sharing

        # Check 3: Triangulation covers the polygon
        # Simplified - would need more sophisticated coverage test

        return True, "Triangulation appears valid"

    @staticmethod
    def find_obtuse_triangles(triangles: List[ExactTriangle]) -> List[int]:
        """
        Find indices of obtuse triangles in triangulation

        Args:
            triangles: List of triangles to check

        Returns:
            List of indices of obtuse triangles
        """
        obtuse_indices = []

        for i, triangle in enumerate(triangles):
            if triangle.is_obtuse:
                obtuse_indices.append(i)

        return obtuse_indices

    @staticmethod
    def compute_angle_bounds(triangles: List[ExactTriangle]) -> Tuple[FieldNumber, FieldNumber]:
        """
        Compute minimum and maximum angles in triangulation

        Args:
            triangles: List of triangles

        Returns:
            Tuple of (min_angle, max_angle) in radians
        """
        import math

        min_angle = FieldNumber(math.pi)  # Start with 180 degrees
        max_angle = FieldNumber(0)

        for triangle in triangles:
            # Calculate angles using law of cosines
            for i in range(3):
                v1 = triangle.vertices[i]
                v2 = triangle.vertices[(i + 1) % 3]
                v3 = triangle.vertices[(i + 2) % 3]

                # Side lengths squared
                a_sq = BernEppsteinGeometry.distance_squared(v2, v3)
                b_sq = BernEppsteinGeometry.distance_squared(v1, v3)
                c_sq = BernEppsteinGeometry.distance_squared(v1, v2)

                # Cosine of angle at v1
                # cos(angle) = (b² + c² - a²) / (2bc)
                cos_numerator = b_sq + c_sq - a_sq
                cos_denominator = FieldNumber(2) * (b_sq * c_sq).sqrt()

                if cos_denominator > FieldNumber(0):
                    cos_angle = cos_numerator / cos_denominator

                    # Convert to angle (approximation for monitoring)
                    # Note: This uses floating point for angle calculation
                    angle_approx = math.acos(float(cos_angle.exact()))
                    angle_field = FieldNumber(angle_approx)

                    min_angle = min(min_angle, angle_field)
                    max_angle = max(max_angle, angle_field)

        return min_angle, max_angle

    @staticmethod
    def is_steiner_point_necessary(point: Point, triangle: ExactTriangle) -> bool:
        """
        Test if adding a Steiner point would improve triangle quality

        Args:
            point: Potential Steiner point location
            triangle: Triangle to potentially subdivide

        Returns:
            True if Steiner point would help
        """
        # Check if point is inside triangle
        if not triangle.contains_point(point):
            return False

        # Check if adding point would create non-obtuse triangles
        # This is a simplified heuristic - full implementation would
        # check the resulting subdivision quality

        return triangle.is_obtuse  # Only add if current triangle is obtuse


class TriangulationAnalyzer:
    """Analyze triangulation quality and properties"""

    def __init__(self, triangles: List[ExactTriangle]):
        self.triangles = triangles
        self.predicates = GeometricPredicates()

    def count_obtuse_triangles(self) -> int:
        """Count number of obtuse triangles"""
        return len(self.predicates.find_obtuse_triangles(self.triangles))

    def count_right_triangles(self) -> int:
        """Count number of right triangles"""
        return sum(1 for t in self.triangles if t.is_right)

    def count_acute_triangles(self) -> int:
        """Count number of acute triangles"""
        return sum(1 for t in self.triangles if t.is_acute)

    def total_area(self) -> FieldNumber:
        """Calculate total area of triangulation"""
        return sum(t.area() for t in self.triangles)

    def quality_metrics(self) -> dict:
        """Compute comprehensive quality metrics"""
        total = len(self.triangles)
        obtuse = self.count_obtuse_triangles()
        right = self.count_right_triangles()
        acute = self.count_acute_triangles()

        min_angle, max_angle = self.predicates.compute_angle_bounds(self.triangles)

        return {
            'total_triangles': total,
            'obtuse_triangles': obtuse,
            'right_triangles': right,
            'acute_triangles': acute,
            'obtuse_percentage': float(obtuse) / total * 100 if total > 0 else 0,
            'min_angle_radians': float(min_angle.exact()),
            'max_angle_radians': float(max_angle.exact()),
            'total_area': float(self.total_area().exact())
        }

    def is_valid_triangulation(self) -> Tuple[bool, str]:
        """Check if triangulation is valid"""
        return self.predicates.is_triangulation_valid(self.triangles, [])