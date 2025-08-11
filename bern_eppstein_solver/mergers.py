"""
Apex and side merger algorithms for Bern & Eppstein triangulation.
Implements the core recursive techniques for handling obtuse triangles with subdivisions.
"""

from typing import List, Dict, Optional, Tuple
from cgshop2025_pyutils.geometry import FieldNumber, Point
from .geometry import BernEppsteinGeometry, ExactTriangle
from .predicates import GeometricPredicates


class SubdivisionManager:
    """Manages subdivision points on triangle edges"""

    def __init__(self):
        self.edge_subdivisions = {}  # Maps edge to list of subdivision points

    def add_subdivision(self, edge_start: Point, edge_end: Point, subdivision_point: Point):
        """Add a subdivision point to an edge"""
        edge_key = self._edge_key(edge_start, edge_end)
        if edge_key not in self.edge_subdivisions:
            self.edge_subdivisions[edge_key] = []
        self.edge_subdivisions[edge_key].append(subdivision_point)

    def get_subdivisions(self, edge_start: Point, edge_end: Point) -> List[Point]:
        """Get subdivision points for an edge"""
        edge_key = self._edge_key(edge_start, edge_end)
        return self.edge_subdivisions.get(edge_key, [])

    def _edge_key(self, p1: Point, p2: Point) -> Tuple[str, str]:
        """Create consistent key for edge regardless of direction"""
        key1 = (p1.x().exact(), p1.y().exact())
        key2 = (p2.x().exact(), p2.y().exact())
        return tuple(sorted([key1, key2]))

    def count_total_subdivisions(self) -> int:
        """Count total subdivision points"""
        return sum(len(subdivs) for subdivs in self.edge_subdivisions.values())


class ApexMerger:
    """
    Implements apex merger operation from Bern & Eppstein algorithm.
    Combines apex vertex with adjacent subdivision point using perpendicular intersections.
    """

    def __init__(self, triangle_vertices: List[Point], subdivision_manager: SubdivisionManager):
        """
        Initialize apex merger

        Args:
            triangle_vertices: [apex, base_start, base_end] where apex is obtuse vertex
            subdivision_manager: Manages subdivision points on edges
        """
        self.triangle_vertices = triangle_vertices
        self.subdivision_manager = subdivision_manager
        self.apex = triangle_vertices[0]
        self.base_start = triangle_vertices[1]
        self.base_end = triangle_vertices[2]

    def can_apply(self) -> bool:
        """
        Check if apex merger can be applied

        Returns:
            True if merger is geometrically feasible
        """
        # Get subdivisions on legs adjacent to apex
        leg1_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_start)
        leg2_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_end)

        # Need at least one subdivision on a leg
        if not leg1_subdivisions and not leg2_subdivisions:
            return False

        # Find closest subdivision to apex
        closest_subdivision = self._find_closest_subdivision_to_apex()
        if not closest_subdivision:
            return False

        # Check if perpendiculars intersect appropriately
        intersection = self._compute_apex_merger_point(closest_subdivision)
        return intersection is not None

    def apply(self) -> Tuple[List[ExactTriangle], List[Point]]:
        """
        Apply apex merger operation

        Returns:
            Tuple of (connecting_triangles, new_steiner_points)
        """
        closest_subdivision = self._find_closest_subdivision_to_apex()
        if not closest_subdivision:
            raise ValueError("Cannot apply apex merger - no suitable subdivision found")

        # Compute merger point
        merger_point = self._compute_apex_merger_point(closest_subdivision)
        if not merger_point:
            raise ValueError("Cannot compute apex merger intersection point")

        # Create connecting triangles
        connecting_triangles = self._create_apex_connecting_triangles(
            closest_subdivision, merger_point
        )

        # Project other subdivisions onto new configuration
        new_steiner_points = self._project_subdivisions_after_apex_merger(
            closest_subdivision, merger_point
        )

        return connecting_triangles, new_steiner_points

    def _find_closest_subdivision_to_apex(self) -> Optional[Point]:
        """Find subdivision point closest to apex vertex"""
        leg1_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_start)
        leg2_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_end)

        all_subdivisions = leg1_subdivisions + leg2_subdivisions
        if not all_subdivisions:
            return None

        # Find closest by distance
        min_distance_sq = None
        closest_point = None

        for subdivision in all_subdivisions:
            dist_sq = BernEppsteinGeometry.distance_squared(self.apex, subdivision)
            if min_distance_sq is None or dist_sq < min_distance_sq:
                min_distance_sq = dist_sq
                closest_point = subdivision

        return closest_point

    def _compute_apex_merger_point(self, subdivision: Point) -> Optional[Point]:
        """
        Compute intersection point for apex merger using perpendiculars

        Args:
            subdivision: Subdivision point to merge with apex

        Returns:
            Intersection point or None if parallel
        """
        # Find which leg contains the subdivision
        leg1_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_start)

        if subdivision in leg1_subdivisions:
            # Subdivision is on leg apex-base_start
            leg_start, leg_end = self.apex, self.base_start
            opposite_vertex = self.base_end
        else:
            # Subdivision is on leg apex-base_end
            leg_start, leg_end = self.apex, self.base_end
            opposite_vertex = self.base_start

        # Construct perpendiculars and find intersection
        return BernEppsteinGeometry.perpendicular_intersection(
            subdivision, leg_start, leg_end,
            opposite_vertex, self.base_start, self.base_end
        )

    def _create_apex_connecting_triangles(self, subdivision: Point,
                                        merger_point: Point) -> List[ExactTriangle]:
        """Create triangles that connect the merged configuration"""
        connecting_triangles = []

        # Triangle connecting apex, subdivision, and merger point
        apex_triangle = ExactTriangle(self.apex, subdivision, merger_point)
        connecting_triangles.append(apex_triangle)

        # Triangle connecting merger point to base
        base_triangle = ExactTriangle(merger_point, self.base_start, self.base_end)
        connecting_triangles.append(base_triangle)

        return connecting_triangles

    def _project_subdivisions_after_apex_merger(self, merged_subdivision: Point,
                                               merger_point: Point) -> List[Point]:
        """Project remaining subdivisions after apex merger"""
        new_steiner_points = [merger_point]

        # Project subdivisions on other leg
        leg1_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_start)
        leg2_subdivisions = self.subdivision_manager.get_subdivisions(self.apex, self.base_end)

        # Determine which leg to project
        if merged_subdivision in leg1_subdivisions:
            remaining_subdivisions = [s for s in leg1_subdivisions if s != merged_subdivision]
            remaining_subdivisions.extend(leg2_subdivisions)
        else:
            remaining_subdivisions = [s for s in leg2_subdivisions if s != merged_subdivision]
            remaining_subdivisions.extend(leg1_subdivisions)

        # Project remaining subdivisions (simplified - would need proper geometric projection)
        for subdivision in remaining_subdivisions:
            projected_point = self._project_point_to_new_configuration(subdivision, merger_point)
            if projected_point:
                new_steiner_points.append(projected_point)

        return new_steiner_points

    def _project_point_to_new_configuration(self, point: Point, merger_point: Point) -> Optional[Point]:
        """Project a subdivision point to new triangle configuration"""
        # Simplified projection - full implementation would depend on geometric details
        return point  # Placeholder


class SideMerger:
    """
    Implements side merger operation from Bern & Eppstein algorithm.
    Combines adjacent subdivision points on triangle legs.
    """

    def __init__(self, triangle_vertices: List[Point], subdivision_manager: SubdivisionManager):
        """
        Initialize side merger

        Args:
            triangle_vertices: Triangle vertices [v1, v2, v3]
            subdivision_manager: Manages subdivision points
        """
        self.triangle_vertices = triangle_vertices
        self.subdivision_manager = subdivision_manager

    def can_apply(self) -> bool:
        """Check if side merger can be applied"""
        adjacent_pairs = self._find_adjacent_subdivision_pairs()
        return len(adjacent_pairs) > 0

    def apply(self) -> Tuple[List[ExactTriangle], List[Point]]:
        """
        Apply side merger operation

        Returns:
            Tuple of (connecting_triangles, new_steiner_points)
        """
        adjacent_pairs = self._find_adjacent_subdivision_pairs()
        if not adjacent_pairs:
            raise ValueError("Cannot apply side merger - no adjacent subdivisions found")

        # Use first available pair
        point1, point2, edge_info = adjacent_pairs[0]

        # Create new leg position by projecting
        new_leg_points = self._create_merged_leg(point1, point2, edge_info)

        # Create connecting triangles
        connecting_triangles = self._create_side_connecting_triangles(
            point1, point2, new_leg_points
        )

        # Update subdivision configuration
        new_steiner_points = self._update_subdivisions_after_side_merger(
            point1, point2, new_leg_points
        )

        return connecting_triangles, new_steiner_points

    def _find_adjacent_subdivision_pairs(self) -> List[Tuple[Point, Point, dict]]:
        """
        Find pairs of adjacent subdivision points that can be merged

        Returns:
            List of (point1, point2, edge_info) tuples
        """
        adjacent_pairs = []

        # Check each edge of triangle
        for i in range(3):
            v1 = self.triangle_vertices[i]
            v2 = self.triangle_vertices[(i + 1) % 3]

            subdivisions = self.subdivision_manager.get_subdivisions(v1, v2)

            # Sort subdivisions along edge
            sorted_subdivisions = self._sort_points_along_edge(subdivisions, v1, v2)

            # Find adjacent pairs
            for j in range(len(sorted_subdivisions) - 1):
                point1 = sorted_subdivisions[j]
                point2 = sorted_subdivisions[j + 1]

                edge_info = {
                    'edge_start': v1,
                    'edge_end': v2,
                    'edge_index': i
                }

                adjacent_pairs.append((point1, point2, edge_info))

        return adjacent_pairs

    def _sort_points_along_edge(self, points: List[Point], edge_start: Point,
                               edge_end: Point) -> List[Point]:
        """Sort points along edge from start to end"""
        if not points:
            return []

        # Calculate parameter t for each point along edge
        edge_vec_x = edge_end.x() - edge_start.x()
        edge_vec_y = edge_end.y() - edge_start.y()

        points_with_t = []
        for point in points:
            point_vec_x = point.x() - edge_start.x()
            point_vec_y = point.y() - edge_start.y()

            # Project onto edge vector
            if edge_vec_x != FieldNumber(0):
                t = point_vec_x / edge_vec_x
            elif edge_vec_y != FieldNumber(0):
                t = point_vec_y / edge_vec_y
            else:
                t = FieldNumber(0)

            points_with_t.append((t, point))

        # Sort by parameter t
        points_with_t.sort(key=lambda x: x[0])

        return [point for t, point in points_with_t]

    def _create_merged_leg(self, point1: Point, point2: Point,
                          edge_info: dict) -> List[Point]:
        """
        Create new leg position by projecting points

        Args:
            point1, point2: Adjacent subdivision points to merge
            edge_info: Information about the edge containing points

        Returns:
            Points defining new leg position
        """
        # Find perpendicular direction to original edge
        edge_start = edge_info['edge_start']
        edge_end = edge_info['edge_end']

        edge_vec_x = edge_end.x() - edge_start.x()
        edge_vec_y = edge_end.y() - edge_start.y()

        # Perpendicular vector (rotated 90 degrees)
        perp_vec_x = -edge_vec_y
        perp_vec_y = edge_vec_x

        # Project points perpendicular to edge
        # This is simplified - full implementation would determine optimal projection distance
        projection_distance = FieldNumber("0.1")  # Small offset

        new_point1 = Point(
            point1.x() + projection_distance * perp_vec_x,
            point1.y() + projection_distance * perp_vec_y
        )

        new_point2 = Point(
            point2.x() + projection_distance * perp_vec_x,
            point2.y() + projection_distance * perp_vec_y
        )

        return [new_point1, new_point2]

    def _create_side_connecting_triangles(self, point1: Point, point2: Point,
                                        new_leg_points: List[Point]) -> List[ExactTriangle]:
        """Create triangles connecting original and new leg positions"""
        connecting_triangles = []

        if len(new_leg_points) >= 2:
            new_point1, new_point2 = new_leg_points[0], new_leg_points[1]

            # Create quadrilateral and triangulate
            quad_triangle1 = ExactTriangle(point1, point2, new_point2)
            quad_triangle2 = ExactTriangle(point1, new_point2, new_point1)

            connecting_triangles.extend([quad_triangle1, quad_triangle2])

        return connecting_triangles

    def _update_subdivisions_after_side_merger(self, point1: Point, point2: Point,
                                             new_leg_points: List[Point]) -> List[Point]:
        """Update subdivision configuration after merger"""
        # Add new points as Steiner points
        new_steiner_points = new_leg_points.copy()

        # Remove merged points from subdivision tracking
        # (This would be handled by the subdivision manager in full implementation)

        return new_steiner_points


class MergerAlgorithm:
    """
    Main merger algorithm coordinating apex and side mergers.
    Implements the recursive triangulation procedure from Bern & Eppstein.
    """

    def __init__(self, triangle_vertices: List[Point],
                 initial_subdivisions: Dict[str, List[Point]] = None):
        """
        Initialize merger algorithm

        Args:
            triangle_vertices: Initial triangle vertices
            initial_subdivisions: Initial subdivision points on edges
        """
        self.triangle_vertices = triangle_vertices
        self.subdivision_manager = SubdivisionManager()
        self.result_triangles = []
        self.steiner_points = []

        # Initialize subdivisions
        if initial_subdivisions:
            self._initialize_subdivisions(initial_subdivisions)

    def triangulate_with_mergers(self) -> List[ExactTriangle]:
        """
        Main recursive triangulation using merger operations

        Returns:
            List of non-obtuse triangles
        """
        return self._recursive_triangulate(self.triangle_vertices, self.subdivision_manager)

    def _recursive_triangulate(self, vertices: List[Point],
                              subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Recursive triangulation procedure implementing Bern & Eppstein algorithm

        Args:
            vertices: Current triangle vertices
            subdivision_manager: Current subdivision state

        Returns:
            List of non-obtuse triangles
        """
        # Base cases
        if self._is_base_case(vertices, subdivision_manager):
            return self._handle_base_case(vertices, subdivision_manager)

        # Try apex merger first
        apex_merger = ApexMerger(vertices, subdivision_manager)
        if apex_merger.can_apply():
            return self._apply_apex_merger_recursively(apex_merger)

        # Fall back to side merger
        side_merger = SideMerger(vertices, subdivision_manager)
        if side_merger.can_apply():
            return self._apply_side_merger_recursively(side_merger)


    def _is_base_case(self, vertices: List[Point],
                     subdivision_manager: SubdivisionManager) -> bool:
        """
        Check if current configuration is a base case

        Base cases:
        1. Right triangle with at most 1 subdivision
        2. Obtuse triangle with no subdivisions
        3. Non-obtuse triangle (any subdivisions)
        """
        triangle = ExactTriangle(*vertices)
        total_subdivisions = subdivision_manager.count_total_subdivisions()

        # Non-obtuse triangle is always a base case
        if not triangle.is_obtuse:
            return True

        # Obtuse triangle with no subdivisions
        if triangle.is_obtuse and total_subdivisions == 0:
            return True

        # Right triangle with at most 1 subdivision
        if triangle.is_right and total_subdivisions <= 1:
            return True

        return False

    def _handle_base_case(self, vertices: List[Point],
                         subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """Handle base cases according to Bern & Eppstein algorithm"""
        triangle = ExactTriangle(*vertices)
        total_subdivisions = subdivision_manager.count_total_subdivisions()

        if not triangle.is_obtuse:
            # Non-obtuse triangle - handle subdivisions if any
            if total_subdivisions == 0:
                return [triangle]
            else:
                return self._triangulate_non_obtuse_with_subdivisions(vertices, subdivision_manager)

        if triangle.is_obtuse and total_subdivisions == 0:
            # Obtuse triangle with no subdivisions - drop altitude
            return self._drop_altitude_triangulation(vertices)

        if triangle.is_right and total_subdivisions <= 1:
            # Right triangle with at most 1 subdivision
            return self._handle_right_triangle_with_subdivision(vertices, subdivision_manager)

        # Shouldn't reach here
        return [triangle]

    def _apply_apex_merger_recursively(self, apex_merger: ApexMerger) -> List[ExactTriangle]:
        """Apply apex merger and recursively solve subproblems"""
        connecting_triangles, new_steiner_points = apex_merger.apply()

        # Add Steiner points to result
        self.steiner_points.extend(new_steiner_points)

        # Create reduced problem and solve recursively
        # This is simplified - full implementation would properly construct reduced triangle
        reduced_vertices = self._construct_reduced_triangle_after_apex_merger(
            apex_merger, new_steiner_points
        )

        if reduced_vertices:
            reduced_subdivision_manager = self._update_subdivisions_after_apex_merger(
                apex_merger, new_steiner_points
            )

            recursive_triangles = self._recursive_triangulate(
                reduced_vertices, reduced_subdivision_manager
            )

            return connecting_triangles + recursive_triangles

        return connecting_triangles

    def _apply_side_merger_recursively(self, side_merger: SideMerger) -> List[ExactTriangle]:
        """Apply side merger and recursively solve subproblems"""
        connecting_triangles, new_steiner_points = side_merger.apply()

        # Add Steiner points to result
        self.steiner_points.extend(new_steiner_points)

        # Create reduced problem
        reduced_vertices = self._construct_reduced_triangle_after_side_merger(
            side_merger, new_steiner_points
        )

        if reduced_vertices:
            reduced_subdivision_manager = self._update_subdivisions_after_side_merger(
                side_merger, new_steiner_points
            )

            recursive_triangles = self._recursive_triangulate(
                reduced_vertices, reduced_subdivision_manager
            )

            return connecting_triangles + recursive_triangles

        return connecting_triangles

    def _drop_altitude_triangulation(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        Handle obtuse triangle with no subdivisions by dropping altitude

        Args:
            vertices: Triangle vertices [obtuse_vertex, base_start, base_end]

        Returns:
            Two right triangles
        """
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
            # Not obtuse? Return as-is
            return [triangle]

        # Get obtuse vertex and opposite edge
        obtuse_vertex = vertices[obtuse_vertex_index]
        base_start = vertices[(obtuse_vertex_index + 1) % 3]
        base_end = vertices[(obtuse_vertex_index + 2) % 3]

        # Drop altitude from obtuse vertex to opposite edge
        altitude_foot = BernEppsteinGeometry.drop_altitude(obtuse_vertex, base_start, base_end)

        # Create two right triangles
        triangle1 = ExactTriangle(obtuse_vertex, base_start, altitude_foot)
        triangle2 = ExactTriangle(obtuse_vertex, altitude_foot, base_end)

        # Add altitude foot as Steiner point
        self.steiner_points.append(altitude_foot)

        return [triangle1, triangle2]

    def _handle_right_triangle_with_subdivision(self, vertices: List[Point],
                                              subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Handle right triangle with one subdivision using perpendicular

        Args:
            vertices: Right triangle vertices
            subdivision_manager: Contains subdivision information

        Returns:
            Triangulated result
        """
        triangle = ExactTriangle(*vertices)

        if subdivision_manager.count_total_subdivisions() == 0:
            return [triangle]

        # Find subdivision point and create perpendicular
        # This is simplified - full implementation would find the actual subdivision
        # and create appropriate perpendicular triangulation

        return [triangle]  # Placeholder

    def _triangulate_non_obtuse_with_subdivisions(self, vertices: List[Point],
                                                subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Triangulate non-obtuse triangle that has subdivision points

        Args:
            vertices: Triangle vertices
            subdivision_manager: Contains subdivision points

        Returns:
            Triangulated result
        """
        # For non-obtuse triangles, we can use simpler triangulation methods
        # This is a placeholder for the full subdivision handling

        triangle = ExactTriangle(*vertices)
        return [triangle]

    def _fallback_triangulation(self, vertices: List[Point],
                              subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Fallback triangulation when no merger operations are possible

        This shouldn't happen in correct Bern & Eppstein implementation,
        but provides safety net
        """
        triangle = ExactTriangle(*vertices)

        if triangle.is_obtuse:
            # Drop altitude as fallback
            return self._drop_altitude_triangulation(vertices)
        else:
            return [triangle]

    def _construct_reduced_triangle_after_apex_merger(self, apex_merger: ApexMerger,
                                                    new_steiner_points: List[Point]) -> Optional[List[Point]]:
        """Construct reduced triangle after apex merger operation"""
        # This would construct the new triangle with reduced subdivisions
        # Simplified implementation
        return None

    def _construct_reduced_triangle_after_side_merger(self, side_merger: SideMerger,
                                                    new_steiner_points: List[Point]) -> Optional[List[Point]]:
        """Construct reduced triangle after side merger operation"""
        # This would construct the new triangle with reduced subdivisions
        # Simplified implementation
        return None

    def _update_subdivisions_after_apex_merger(self, apex_merger: ApexMerger,
                                             new_steiner_points: List[Point]) -> SubdivisionManager:
        """Update subdivision manager after apex merger"""
        # Create new subdivision manager with updated subdivisions
        new_manager = SubdivisionManager()
        # Copy and update subdivisions based on merger result
        return new_manager

    def _update_subdivisions_after_side_merger(self, side_merger: SideMerger,
                                             new_steiner_points: List[Point]) -> SubdivisionManager:
        """Update subdivision manager after side merger"""
        # Create new subdivision manager with updated subdivisions
        new_manager = SubdivisionManager()
        # Copy and update subdivisions based on merger result
        return new_manager

    def _initialize_subdivisions(self, initial_subdivisions: Dict[str, List[Point]]):
        """Initialize subdivision manager with initial subdivision points"""
        for edge_key, subdivisions in initial_subdivisions.items():
            # Parse edge key and add subdivisions
            # This would need proper edge parsing from the key format
            pass

    def get_all_steiner_points(self) -> List[Point]:
        """Get all Steiner points created during triangulation"""
        return self.steiner_points.copy()

    def get_subdivision_count(self) -> int:
        """Get total number of subdivision points in current configuration"""
        return self.subdivision_manager.count_total_subdivisions()


class MergerAnalyzer:
    """
    Analyze merger operations and algorithm performance
    """

    def __init__(self):
        self.merger_history = []
        self.steiner_point_count = 0
        self.triangle_count = 0

    def record_apex_merger(self, triangle_vertices: List[Point],
                          steiner_points_added: int):
        """Record apex merger operation"""
        self.merger_history.append({
            'type': 'apex_merger',
            'triangle': triangle_vertices,
            'steiner_points': steiner_points_added,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += steiner_points_added

    def record_side_merger(self, triangle_vertices: List[Point],
                          steiner_points_added: int):
        """Record side merger operation"""
        self.merger_history.append({
            'type': 'side_merger',
            'triangle': triangle_vertices,
            'steiner_points': steiner_points_added,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += steiner_points_added

    def record_altitude_drop(self, triangle_vertices: List[Point]):
        """Record altitude drop operation"""
        self.merger_history.append({
            'type': 'altitude_drop',
            'triangle': triangle_vertices,
            'steiner_points': 1,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += 1

    def get_algorithm_statistics(self) -> Dict[str, any]:
        """Get comprehensive algorithm statistics"""
        apex_mergers = sum(1 for op in self.merger_history if op['type'] == 'apex_merger')
        side_mergers = sum(1 for op in self.merger_history if op['type'] == 'side_merger')
        altitude_drops = sum(1 for op in self.merger_history if op['type'] == 'altitude_drop')

        return {
            'total_operations': len(self.merger_history),
            'apex_mergers': apex_mergers,
            'side_mergers': side_mergers,
            'altitude_drops': altitude_drops,
            'total_steiner_points': self.steiner_point_count,
            'total_triangles': self.triangle_count,
            'average_steiner_per_operation': self.steiner_point_count / max(1, len(self.merger_history))
        }

    def print_merger_sequence(self):
        """Print sequence of merger operations for debugging"""
        print("Merger Operation Sequence:")
        print("-" * 50)

        for i, op in enumerate(self.merger_history):
            print(f"Step {i + 1}: {op['type']}")
            print(f"  Steiner points added: {op['steiner_points']}")
            print(f"  Triangle vertices: {len(op['triangle'])}")
            print()

        stats = self.get_algorithm_statistics()
        print("Final Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    def _is_base_case(self, vertices: List[Point],
                     subdivision_manager: SubdivisionManager) -> bool:
        """
        Check if current configuration is a base case

        Base cases:
        1. Right triangle with at most 1 subdivision
        2. Obtuse triangle with no subdivisions
        3. Non-obtuse triangle (any subdivisions)
        """
        triangle = ExactTriangle(*vertices)
        total_subdivisions = subdivision_manager.count_total_subdivisions()

        # Non-obtuse triangle is always a base case
        if not triangle.is_obtuse:
            return True

        # Obtuse triangle with no subdivisions
        if triangle.is_obtuse and total_subdivisions == 0:
            return True

        # Right triangle with at most 1 subdivision
        if triangle.is_right and total_subdivisions <= 1:
            return True

        return False

    def _handle_base_case(self, vertices: List[Point],
                         subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """Handle base cases according to Bern & Eppstein algorithm"""
        triangle = ExactTriangle(*vertices)
        total_subdivisions = subdivision_manager.count_total_subdivisions()

        if not triangle.is_obtuse:
            # Non-obtuse triangle - handle subdivisions if any
            if total_subdivisions == 0:
                return [triangle]
            else:
                return self._triangulate_non_obtuse_with_subdivisions(vertices, subdivision_manager)

        if triangle.is_obtuse and total_subdivisions == 0:
            # Obtuse triangle with no subdivisions - drop altitude
            return self._drop_altitude_triangulation(vertices)

        if triangle.is_right and total_subdivisions <= 1:
            # Right triangle with at most 1 subdivision
            return self._handle_right_triangle_with_subdivision(vertices, subdivision_manager)

        # Shouldn't reach here
        return [triangle]

    def _apply_apex_merger_recursively(self, apex_merger: ApexMerger) -> List[ExactTriangle]:
        """Apply apex merger and recursively solve subproblems"""
        connecting_triangles, new_steiner_points = apex_merger.apply()

        # Add Steiner points to result
        self.steiner_points.extend(new_steiner_points)

        # Create reduced problem and solve recursively
        # This is simplified - full implementation would properly construct reduced triangle
        reduced_vertices = self._construct_reduced_triangle_after_apex_merger(
            apex_merger, new_steiner_points
        )

        if reduced_vertices:
            reduced_subdivision_manager = self._update_subdivisions_after_apex_merger(
                apex_merger, new_steiner_points
            )

            recursive_triangles = self._recursive_triangulate(
                reduced_vertices, reduced_subdivision_manager
            )

            return connecting_triangles + recursive_triangles

        return connecting_triangles

    def _apply_side_merger_recursively(self, side_merger: SideMerger) -> List[ExactTriangle]:
        """Apply side merger and recursively solve subproblems"""
        connecting_triangles, new_steiner_points = side_merger.apply()

        # Add Steiner points to result
        self.steiner_points.extend(new_steiner_points)

        # Create reduced problem
        reduced_vertices = self._construct_reduced_triangle_after_side_merger(
            side_merger, new_steiner_points
        )

        if reduced_vertices:
            reduced_subdivision_manager = self._update_subdivisions_after_side_merger(
                side_merger, new_steiner_points
            )

            recursive_triangles = self._recursive_triangulate(
                reduced_vertices, reduced_subdivision_manager
            )

            return connecting_triangles + recursive_triangles

        return connecting_triangles

    def _drop_altitude_triangulation(self, vertices: List[Point]) -> List[ExactTriangle]:
        """
        Handle obtuse triangle with no subdivisions by dropping altitude

        Args:
            vertices: Triangle vertices [obtuse_vertex, base_start, base_end]

        Returns:
            Two right triangles
        """
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
            # Not obtuse? Return as-is
            return [triangle]

        # Get obtuse vertex and opposite edge
        obtuse_vertex = vertices[obtuse_vertex_index]
        base_start = vertices[(obtuse_vertex_index + 1) % 3]
        base_end = vertices[(obtuse_vertex_index + 2) % 3]

        # Drop altitude from obtuse vertex to opposite edge
        altitude_foot = BernEppsteinGeometry.drop_altitude(obtuse_vertex, base_start, base_end)

        # Create two right triangles
        triangle1 = ExactTriangle(obtuse_vertex, base_start, altitude_foot)
        triangle2 = ExactTriangle(obtuse_vertex, altitude_foot, base_end)

        # Add altitude foot as Steiner point
        self.steiner_points.append(altitude_foot)

        return [triangle1, triangle2]

    def _handle_right_triangle_with_subdivision(self, vertices: List[Point],
                                              subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Handle right triangle with one subdivision using perpendicular

        Args:
            vertices: Right triangle vertices
            subdivision_manager: Contains subdivision information

        Returns:
            Triangulated result
        """
        triangle = ExactTriangle(*vertices)

        if subdivision_manager.count_total_subdivisions() == 0:
            return [triangle]

        # Find subdivision point and create perpendicular
        # This is simplified - full implementation would find the actual subdivision
        # and create appropriate perpendicular triangulation

        return [triangle]  # Placeholder

    def _triangulate_non_obtuse_with_subdivisions(self, vertices: List[Point],
                                                subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Triangulate non-obtuse triangle that has subdivision points

        Args:
            vertices: Triangle vertices
            subdivision_manager: Contains subdivision points

        Returns:
            Triangulated result
        """
        # For non-obtuse triangles, we can use simpler triangulation methods
        # This is a placeholder for the full subdivision handling

        triangle = ExactTriangle(*vertices)
        return [triangle]

    def _fallback_triangulation(self, vertices: List[Point],
                              subdivision_manager: SubdivisionManager) -> List[ExactTriangle]:
        """
        Fallback triangulation when no merger operations are possible

        This shouldn't happen in correct Bern & Eppstein implementation,
        but provides safety net
        """
        triangle = ExactTriangle(*vertices)

        if triangle.is_obtuse:
            # Drop altitude as fallback
            return self._drop_altitude_triangulation(vertices)
        else:
            return [triangle]

    def _construct_reduced_triangle_after_apex_merger(self, apex_merger: ApexMerger,
                                                    new_steiner_points: List[Point]) -> Optional[List[Point]]:
        """Construct reduced triangle after apex merger operation"""
        # This would construct the new triangle with reduced subdivisions
        # Simplified implementation
        return None

    def _construct_reduced_triangle_after_side_merger(self, side_merger: SideMerger,
                                                    new_steiner_points: List[Point]) -> Optional[List[Point]]:
        """Construct reduced triangle after side merger operation"""
        # This would construct the new triangle with reduced subdivisions
        # Simplified implementation
        return None

    def _update_subdivisions_after_apex_merger(self, apex_merger: ApexMerger,
                                             new_steiner_points: List[Point]) -> SubdivisionManager:
        """Update subdivision manager after apex merger"""
        # Create new subdivision manager with updated subdivisions
        new_manager = SubdivisionManager()
        # Copy and update subdivisions based on merger result
        return new_manager

    def _update_subdivisions_after_side_merger(self, side_merger: SideMerger,
                                             new_steiner_points: List[Point]) -> SubdivisionManager:
        """Update subdivision manager after side merger"""
        # Create new subdivision manager with updated subdivisions
        new_manager = SubdivisionManager()
        # Copy and update subdivisions based on merger result
        return new_manager

    def _initialize_subdivisions(self, initial_subdivisions: Dict[str, List[Point]]):
        """Initialize subdivision manager with initial subdivision points"""
        for edge_key, subdivisions in initial_subdivisions.items():
            # Parse edge key and add subdivisions
            # This would need proper edge parsing from the key format
            pass

    def get_all_steiner_points(self) -> List[Point]:
        """Get all Steiner points created during triangulation"""
        return self.steiner_points.copy()

    def get_subdivision_count(self) -> int:
        """Get total number of subdivision points in current configuration"""
        return self.subdivision_manager.count_total_subdivisions()


class MergerAnalyzer:
    """
    Analyze merger operations and algorithm performance
    """

    def __init__(self):
        self.merger_history = []
        self.steiner_point_count = 0
        self.triangle_count = 0

    def record_apex_merger(self, triangle_vertices: List[Point],
                          steiner_points_added: int):
        """Record apex merger operation"""
        self.merger_history.append({
            'type': 'apex_merger',
            'triangle': triangle_vertices,
            'steiner_points': steiner_points_added,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += steiner_points_added

    def record_side_merger(self, triangle_vertices: List[Point],
                          steiner_points_added: int):
        """Record side merger operation"""
        self.merger_history.append({
            'type': 'side_merger',
            'triangle': triangle_vertices,
            'steiner_points': steiner_points_added,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += steiner_points_added

    def record_altitude_drop(self, triangle_vertices: List[Point]):
        """Record altitude drop operation"""
        self.merger_history.append({
            'type': 'altitude_drop',
            'triangle': triangle_vertices,
            'steiner_points': 1,
            'step': len(self.merger_history)
        })
        self.steiner_point_count += 1

    def get_algorithm_statistics(self) -> Dict[str, any]:
        """Get comprehensive algorithm statistics"""
        apex_mergers = sum(1 for op in self.merger_history if op['type'] == 'apex_merger')
        side_mergers = sum(1 for op in self.merger_history if op['type'] == 'side_merger')
        altitude_drops = sum(1 for op in self.merger_history if op['type'] == 'altitude_drop')

        return {
            'total_operations': len(self.merger_history),
            'apex_mergers': apex_mergers,
            'side_mergers': side_mergers,
            'altitude_drops': altitude_drops,
            'total_steiner_points': self.steiner_point_count,
            'total_triangles': self.triangle_count,
            'average_steiner_per_operation': self.steiner_point_count / max(1, len(self.merger_history))
        }

    def print_merger_sequence(self):
        """Print sequence of merger operations for debugging"""
        print("Merger Operation Sequence:")
        print("-" * 50)

        for i, op in enumerate(self.merger_history):
            print(f"Step {i+1}: {op['type']}")
            print(f"  Steiner points added: {op['steiner_points']}")
            print(f"  Triangle vertices: {len(op['triangle'])}")
            print()

        stats = self.get_algorithm_statistics()
        print("Final Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")