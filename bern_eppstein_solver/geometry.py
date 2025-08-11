"""
Fixed geometry utilities with proper exact arithmetic for CG-SHOP 2025.
All operations use FieldNumber for exact computation.
"""

from typing import List, Optional, Tuple
from cgshop2025_pyutils.geometry import FieldNumber, Point, Segment, Polygon


class BernEppsteinGeometry:
    """Extended geometry using official cgshop2025_pyutils primitives with exact arithmetic"""

    @staticmethod
    def create_exact_point(x, y) -> Point:
        """Create point using exact arithmetic"""
        return Point(FieldNumber(x), FieldNumber(y))

    @staticmethod
    def angle_type(p1: Point, p2: Point, p3: Point) -> str:
        """
        Determine angle type at vertex p2 using exact arithmetic
        FIXED: Proper exact arithmetic throughout
        """
        # Vector from p2 to p1 and p2 to p3
        v1_x = p1.x() - p2.x()
        v1_y = p1.y() - p2.y()
        v2_x = p3.x() - p2.x()
        v2_y = p3.y() - p2.y()

        # Dot product using FieldNumber arithmetic
        dot_product = v1_x * v2_x + v1_y * v2_y

        # FIXED: Use FieldNumber(0) for comparison
        zero = FieldNumber(0)
        if dot_product > zero:
            return 'acute'
        elif dot_product == zero:
            return 'right'
        else:
            return 'obtuse'

    @staticmethod
    def orientation(p: Point, q: Point, r: Point) -> int:
        """
        Exact orientation test using FieldNumber arithmetic
        FIXED: Proper exact arithmetic and comparisons
        """
        det = (q.x() - p.x()) * (r.y() - p.y()) - (q.y() - p.y()) * (r.x() - p.x())

        zero = FieldNumber(0)
        if det > zero:
            return 1  # Counter-clockwise
        elif det < zero:
            return -1  # Clockwise
        else:
            return 0  # Collinear

    @staticmethod
    def drop_altitude(apex: Point, base_start: Point, base_end: Point) -> Point:
        """
        Drop perpendicular from apex to base line segment
        FIXED: Proper exact arithmetic and zero handling
        """
        # Base vector
        base_x = base_end.x() - base_start.x()
        base_y = base_end.y() - base_start.y()

        # Vector from base_start to apex
        apex_x = apex.x() - base_start.x()
        apex_y = apex.y() - base_start.y()

        # Project apex vector onto base vector
        base_len_sq = base_x * base_x + base_y * base_y

        # FIXED: Proper zero check with FieldNumber
        zero = FieldNumber(0)
        if base_len_sq == zero:
            return base_start

        dot_product = apex_x * base_x + apex_y * base_y
        t = dot_product / base_len_sq

        # Foot of perpendicular
        foot_x = base_start.x() + t * base_x
        foot_y = base_start.y() + t * base_y

        return Point(foot_x, foot_y)

    @staticmethod
    def perpendicular_intersection(p1: Point, line1_start: Point, line1_end: Point,
                                   p2: Point, line2_start: Point, line2_end: Point) -> Optional[Point]:
        """
        Find intersection of perpendiculars from p1 to line1 and p2 to line2
        FIXED: Proper exact arithmetic and zero handling
        """
        # Direction vectors of the lines
        dir1_x = line1_end.x() - line1_start.x()
        dir1_y = line1_end.y() - line1_start.y()
        dir2_x = line2_end.x() - line2_start.x()
        dir2_y = line2_end.y() - line2_start.y()

        # Perpendicular directions (rotate 90 degrees)
        perp1_x = -dir1_y
        perp1_y = dir1_x
        perp2_x = -dir2_y
        perp2_y = dir2_x

        # Line equations: p1 + t1 * perp1 = p2 + t2 * perp2
        # Solve for intersection
        det = perp1_x * perp2_y - perp1_y * perp2_x

        # FIXED: Proper zero check
        zero = FieldNumber(0)
        if det == zero:
            return None  # Parallel perpendiculars

        diff_x = p2.x() - p1.x()
        diff_y = p2.y() - p1.y()
        t1 = (diff_x * perp2_y - diff_y * perp2_x) / det

        intersection_x = p1.x() + t1 * perp1_x
        intersection_y = p1.y() + t1 * perp1_y

        return Point(intersection_x, intersection_y)

    @staticmethod
    def point_in_triangle(p: Point, t1: Point, t2: Point, t3: Point) -> bool:
        """Test if point is inside triangle using orientation tests"""
        d1 = BernEppsteinGeometry.orientation(p, t1, t2)
        d2 = BernEppsteinGeometry.orientation(p, t2, t3)
        d3 = BernEppsteinGeometry.orientation(p, t3, t1)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)

    @staticmethod
    def distance_squared(p1: Point, p2: Point) -> FieldNumber:
        """Calculate squared distance between two points"""
        dx = p1.x() - p2.x()
        dy = p1.y() - p2.y()
        return dx * dx + dy * dy

    @staticmethod
    def create_point_from_coords(x_val, y_val) -> Point:
        """
        Create Point with proper FieldNumber conversion
        FIXED: Handles various input types correctly
        """
        if isinstance(x_val, FieldNumber):
            x = x_val
        else:
            x = FieldNumber(x_val)

        if isinstance(y_val, FieldNumber):
            y = y_val
        else:
            y = FieldNumber(y_val)

        return Point(x, y)


class ExactTriangle:
    """
    Triangle with exact coordinates and comprehensive angle analysis
    FIXED: Proper exact arithmetic throughout
    """

    def __init__(self, p1: Point, p2: Point, p3: Point):
        """Initialize triangle with three exact points"""
        self.vertices = [p1, p2, p3]
        self._angles_computed = False
        self._angle_types = None

    @property
    def is_obtuse(self) -> bool:
        """Check if triangle has any obtuse angles"""
        if not self._angles_computed:
            self._compute_angles()
        return any(angle_type == 'obtuse' for angle_type in self._angle_types)

    @property
    def is_right(self) -> bool:
        """Check if triangle has any right angles"""
        if not self._angles_computed:
            self._compute_angles()
        return any(angle_type == 'right' for angle_type in self._angle_types)

    @property
    def is_acute(self) -> bool:
        """Check if triangle has all acute angles"""
        if not self._angles_computed:
            self._compute_angles()
        return all(angle_type == 'acute' for angle_type in self._angle_types)

    def _compute_angles(self):
        """Compute angle types using exact arithmetic"""
        self._angle_types = []

        for i in range(3):
            v1 = self.vertices[(i + 1) % 3]
            v2 = self.vertices[i]
            v3 = self.vertices[(i + 2) % 3]

            angle_type = BernEppsteinGeometry.angle_type(v1, v2, v3)
            self._angle_types.append(angle_type)

        self._angles_computed = True

    def get_hypotenuse(self) -> Tuple[Point, Point]:
        """Get the longest side (hypotenuse) of the triangle"""
        edges = [
            (self.vertices[0], self.vertices[1]),
            (self.vertices[1], self.vertices[2]),
            (self.vertices[2], self.vertices[0])
        ]

        # Find longest edge using exact arithmetic
        max_length_sq = FieldNumber(0)
        hypotenuse = edges[0]

        for edge in edges:
            length_sq = BernEppsteinGeometry.distance_squared(edge[0], edge[1])
            if length_sq > max_length_sq:
                max_length_sq = length_sq
                hypotenuse = edge

        return hypotenuse

    def get_legs(self) -> List[Tuple[Point, Point]]:
        """Get the two shorter sides (legs) of the triangle"""
        hypotenuse = self.get_hypotenuse()

        all_edges = [
            (self.vertices[0], self.vertices[1]),
            (self.vertices[1], self.vertices[2]),
            (self.vertices[2], self.vertices[0])
        ]

        legs = []
        for edge in all_edges:
            # Check if this edge is the hypotenuse (in either direction)
            if not ((edge[0] == hypotenuse[0] and edge[1] == hypotenuse[1]) or
                    (edge[0] == hypotenuse[1] and edge[1] == hypotenuse[0])):
                legs.append(edge)

        return legs

    def area(self) -> FieldNumber:
        """Calculate triangle area using exact arithmetic"""
        p1, p2, p3 = self.vertices

        # Using cross product formula: |det| / 2
        det = (p2.x() - p1.x()) * (p3.y() - p1.y()) - (p3.x() - p1.x()) * (p2.y() - p1.y())

        # Return absolute value
        zero = FieldNumber(0)
        if det < zero:
            det = -det

        two = FieldNumber(2)
        return det / two

    def contains_point(self, p: Point) -> bool:
        """Check if point is inside triangle"""
        return BernEppsteinGeometry.point_in_triangle(p, *self.vertices)

    def to_segments(self) -> List[Segment]:
        """Convert triangle to list of segments for verification"""
        return [
            Segment(self.vertices[0], self.vertices[1]),
            Segment(self.vertices[1], self.vertices[2]),
            Segment(self.vertices[2], self.vertices[0])
        ]

    def __repr__(self) -> str:
        """String representation of triangle"""
        angle_str = "unknown"
        if self._angles_computed:
            if self.is_obtuse:
                angle_str = "obtuse"
            elif self.is_right:
                angle_str = "right"
            elif self.is_acute:
                angle_str = "acute"

        return f"ExactTriangle({angle_str}, vertices={len(self.vertices)})"


class ExactArithmetic:
    """
    Utility class for exact arithmetic operations
    ADDED: Helper methods for common exact arithmetic patterns
    """

    @staticmethod
    def zero() -> FieldNumber:
        """Return exact zero"""
        return FieldNumber(0)

    @staticmethod
    def one() -> FieldNumber:
        """Return exact one"""
        return FieldNumber(1)

    @staticmethod
    def two() -> FieldNumber:
        """Return exact two"""
        return FieldNumber(2)

    @staticmethod
    def from_fraction(numerator: int, denominator: int) -> FieldNumber:
        """Create FieldNumber from fraction"""
        return FieldNumber(numerator) / FieldNumber(denominator)

    @staticmethod
    def compare_points(p1: Point, p2: Point) -> bool:
        """Compare two points for exact equality"""
        return p1.x() == p2.x() and p1.y() == p2.y()

    @staticmethod
    def is_zero(value: FieldNumber) -> bool:
        """Check if FieldNumber is exactly zero"""
        return value == FieldNumber(0)

    @staticmethod
    def abs(value: FieldNumber) -> FieldNumber:
        """Absolute value of FieldNumber"""
        zero = FieldNumber(0)
        return value if value >= zero else -value