"""
Polygon decomposition module for Bern & Eppstein algorithm.
Implements the horizontal and vertical line decomposition strategy.
"""

from typing import List, Dict, Set, Tuple, Optional
from cgshop2025_pyutils.geometry import FieldNumber, Point, Polygon
from .geometry import  BernEppsteinGeometry, ExactTriangle
from .predicates import GeometricPredicates


class Region:
    """Represents a region in the polygon decomposition"""

    def __init__(self, region_type: str, vertices: List[Point], region_id: int = 0):
        """
        Initialize a region

        Args:
            region_type: 'rectangle', 'right_triangle', 'obtuse_triangle', 'slab'
            vertices: Vertices defining the region boundary
            region_id: Unique identifier for the region
        """
        self.type = region_type
        self.vertices = vertices
        self.region_id = region_id
        self.subdivisions = {}  # Dictionary mapping edge to subdivision points
        self.constraints = []   # Additional constraints within region

    def add_subdivision_points(self, edge_index: int, points: List[Point]):
        """Add subdivision points to an edge of the region"""
        self.subdivisions[edge_index] = points

    def add_constraint(self, constraint_points: List[Point]):
        """Add internal constraint to region"""
        self.constraints.append(constraint_points)

    def get_edge_count(self) -> int:
        """Get number of edges in region"""
        return len(self.vertices)

    def is_convex(self) -> bool:
        """Check if region is convex"""
        if len(self.vertices) < 3:
            return False

        # Check if all turns are in same direction
        n = len(self.vertices)
        orientation_sign = None

        for i in range(n):
            p1 = self.vertices[i]
            p2 = self.vertices[(i + 1) % n]
            p3 = self.vertices[(i + 2) % n]

            orient = BernEppsteinGeometry.orientation(p1, p2, p3)
            if orient != 0:
                if orientation_sign is None:
                    orientation_sign = orient
                elif orientation_sign != orient:
                    return False

        return True

    def triangulate_rectangle(self) -> List[ExactTriangle]:
        """Triangulate a rectangular region"""
        if len(self.vertices) != 4:
            raise ValueError("Rectangle must have exactly 4 vertices")

        # Simple diagonal triangulation
        v = self.vertices
        return [
            ExactTriangle(v[0], v[1], v[2]),
            ExactTriangle(v[0], v[2], v[3])
        ]

    def triangulate_simple(self) -> List[ExactTriangle]:
        """Simple triangulation for convex regions"""
        if len(self.vertices) < 3:
            return []

        if len(self.vertices) == 3:
            return [ExactTriangle(*self.vertices)]

        # Fan triangulation from first vertex
        triangles = []
        for i in range(1, len(self.vertices) - 1):
            triangle = ExactTriangle(
                self.vertices[0],
                self.vertices[i],
                self.vertices[i + 1]
            )
            triangles.append(triangle)

        return triangles


class PolygonDecomposer:
    """
    Implements polygon decomposition using horizontal and vertical lines
    as described in Bern & Eppstein algorithm
    """

    def __init__(self, polygon_vertices: List[Point], constraints: List[List[Point]] = None):
        """
        Initialize decomposer

        Args:
            polygon_vertices: Vertices of polygon in counterclockwise order
            constraints: Additional constraints (segments that must appear in triangulation)
        """
        self.polygon_vertices = polygon_vertices
        self.constraints = constraints or []
        self.vertical_lines = set()
        self.horizontal_lines = set()
        self.regions = []
        self.region_counter = 0

    def decompose(self) -> List[Region]:
        """
        Main decomposition method applying Bern & Eppstein strategy

        Returns:
            List of regions ready for triangulation
        """
        # Step 1: Draw vertical lines through each vertex
        self._create_vertical_lines()

        # Step 2: Create slabs between vertical lines
        slabs = self._create_slabs()

        # Step 3: Draw horizontal lines through vertices in each slab
        self._create_horizontal_lines(slabs)

        # Step 4: Identify and classify regions
        self._identify_regions()

        # Step 5: Handle constraints within regions
        self._process_constraints()

        return self.regions

    def _create_vertical_lines(self):
        """Draw vertical lines through each polygon vertex - FIXED"""
        for vertex in self.polygon_vertices:
            # Convert FieldNumber to exact string for hashing
            x_value = vertex.x().exact()
            self.vertical_lines.add(x_value)

        # Also add vertical lines through constraint endpoints
        for constraint in self.constraints:
            for point in constraint:
                x_value = point.x().exact()
                self.vertical_lines.add(x_value)

    def _create_slabs(self) -> List[Tuple[str, str]]:
        """
        Create vertical slabs between consecutive vertical lines - FIXED

        Returns:
            List of (left_x_str, right_x_str) tuples defining slabs
        """
        sorted_x_coords = sorted(self.vertical_lines)  # These are now strings
        slabs = []

        for i in range(len(sorted_x_coords) - 1):
            left_x = sorted_x_coords[i]
            right_x = sorted_x_coords[i + 1]
            slabs.append((left_x, right_x))

        return slabs

    def _identify_regions(self):
        """Identify and classify regions in the decomposition - FIXED"""
        sorted_x = sorted(self.vertical_lines)  # These are now strings
        sorted_y = sorted(self.horizontal_lines)  # These are now strings

        # Process each grid cell
        for i in range(len(sorted_x) - 1):
            for j in range(len(sorted_y) - 1):
                # Convert string coordinates back to FieldNumber
                left_x = FieldNumber(sorted_x[i])
                right_x = FieldNumber(sorted_x[i + 1])
                bottom_y = FieldNumber(sorted_y[j])
                top_y = FieldNumber(sorted_y[j + 1])

                # Create cell corners
                corners = [
                    Point(left_x, bottom_y),  # Bottom-left
                    Point(right_x, bottom_y),  # Bottom-right
                    Point(right_x, top_y),  # Top-right
                    Point(left_x, top_y)  # Top-left
                ]

                # Check if cell intersects polygon
                if self._cell_intersects_polygon(corners):
                    region = self._classify_region(corners)
                    if region:
                        self.regions.append(region)

    def _cell_intersects_polygon(self, corners: List[Point]) -> bool:
        """Check if grid cell intersects with polygon"""
        # Check if any corner is inside polygon
        polygon = Polygon(self.polygon_vertices)

        for corner in corners:
            if polygon.contains(corner) or polygon.on_boundary(corner):
                return True

        # Check if polygon edges intersect cell edges
        cell_edges = [
            (corners[0], corners[1]),  # Bottom
            (corners[1], corners[2]),  # Right
            (corners[2], corners[3]),  # Top
            (corners[3], corners[0])   # Left
        ]

        n = len(self.polygon_vertices)
        for i in range(n):
            poly_edge_start = self.polygon_vertices[i]
            poly_edge_end = self.polygon_vertices[(i + 1) % n]

            for cell_edge_start, cell_edge_end in cell_edges:
                if GeometricPredicates.segments_intersect(
                    poly_edge_start, poly_edge_end,
                    cell_edge_start, cell_edge_end
                ):
                    return True

        return False

    def _classify_region(self, corners: List[Point]) -> Optional[Region]:
        """
        Classify region based on its intersection with polygon boundary

        Returns:
            Classified region or None if region is outside polygon
        """
        # Find actual region vertices by intersecting with polygon
        region_vertices = self._compute_region_vertices(corners)

        if len(region_vertices) < 3:
            return None

        # Classify based on vertex count and geometric properties
        region_type = self._determine_region_type(region_vertices)

        region = Region(region_type, region_vertices, self.region_counter)
        self.region_counter += 1

        return region

    def _compute_region_vertices(self, corners: List[Point]) -> List[Point]:

        """
        Returns:
            List of regions ready for triangulation
        """
        # Step 1: Draw vertical lines through each vertex
        self._create_vertical_lines()
        
        # Step 2: Create slabs between vertical lines
        slabs = self._create_slabs()
        
        # Step 3: Draw horizontal lines through vertices in each slab
        self._create_horizontal_lines(slabs)
        
        # Step 4: Identify and classify regions
        self._identify_regions()
        
        # Step 5: Handle constraints within regions
        self._process_constraints()
        
        return self.regions
    
    def _create_vertical_lines(self):
        """Draw vertical lines through each polygon vertex"""
        for vertex in self.polygon_vertices:
            self.vertical_lines.add(vertex.x().exact())
        
        # Also add vertical lines through constraint endpoints
        for constraint in self.constraints:
            for point in constraint:
                self.vertical_lines.add(point.x().exact())
    
    def _create_slabs(self) -> List[Tuple[FieldNumber, FieldNumber]]:
        """
        Create vertical slabs between consecutive vertical lines

        Returns:
            List of (left_x, right_x) tuples defining slabs
        """
        sorted_x_coords = sorted(self.vertical_lines)
        slabs = []
        
        for i in range(len(sorted_x_coords) - 1):
            left_x = sorted_x_coords[i]
            right_x = sorted_x_coords[i + 1]
            slabs.append((left_x, right_x))
        
        return slabs

    def _create_horizontal_lines(self, slabs: List[Tuple[str, str]]):
        """Draw horizontal lines through vertices in each slab - FIXED"""
        for left_x_str, right_x_str in slabs:
            # Convert string coordinates back to FieldNumber for comparison
            left_x = FieldNumber(left_x_str)
            right_x = FieldNumber(right_x_str)

            slab_vertices = []

            # Find vertices within this slab
            for vertex in self.polygon_vertices:
                if left_x <= vertex.x() <= right_x:
                    slab_vertices.append(vertex)

            # Add constraint points within slab
            for constraint in self.constraints:
                for point in constraint:
                    if left_x <= point.x() <= right_x:
                        slab_vertices.append(point)

            # Add horizontal lines through all slab vertices
            for vertex in slab_vertices:
                # Convert FieldNumber to exact string for hashing
                y_value = vertex.y().exact()
                self.horizontal_lines.add(y_value)
    
    def _identify_regions(self):
        """Identify and classify regions in the decomposition"""
        sorted_x = sorted(self.vertical_lines)
        sorted_y = sorted(self.horizontal_lines)
        
        # Process each grid cell
        for i in range(len(sorted_x) - 1):
            for j in range(len(sorted_y) - 1):
                left_x = sorted_x[i]
                right_x = sorted_x[i + 1]
                bottom_y = sorted_y[j]
                top_y = sorted_y[j + 1]
                
                # Create cell corners
                corners = [
                    Point(FieldNumber(left_x), FieldNumber(bottom_y)),  # Bottom-left
                    Point(FieldNumber(right_x), FieldNumber(bottom_y)),  # Bottom-right
                    Point(FieldNumber(right_x), FieldNumber(top_y)),  # Top-right
                    Point(FieldNumber(left_x), FieldNumber(top_y))  # Top-left
                ]
                
                # Check if cell intersects polygon
                if self._cell_intersects_polygon(corners):
                    region = self._classify_region(corners)
                    if region:
                        self.regions.append(region)
    
    def _cell_intersects_polygon(self, corners: List[Point]) -> bool:
        """Check if grid cell intersects with polygon"""
        # Check if any corner is inside polygon
        polygon = Polygon(self.polygon_vertices)

        for corner in corners:
            if polygon.contains(corner) or polygon.on_boundary(corner):
                return True

        # Check if polygon edges intersect cell edges
        cell_edges = [
            (corners[0], corners[1]),  # Bottom
            (corners[1], corners[2]),  # Right
            (corners[2], corners[3]),  # Top
            (corners[3], corners[0])   # Left
        ]

        n = len(self.polygon_vertices)
        for i in range(n):
            poly_edge_start = self.polygon_vertices[i]
            poly_edge_end = self.polygon_vertices[(i + 1) % n]

            for cell_edge_start, cell_edge_end in cell_edges:
                if GeometricPredicates.segments_intersect(
                    poly_edge_start, poly_edge_end,
                    cell_edge_start, cell_edge_end
                ):
                    return True

        return False

    def _classify_region(self, corners: List[Point]) -> Optional[Region]:
        """
        Classify region based on its intersection with polygon boundary

        Returns:
            Classified region or None if region is outside polygon
        """
        # Find actual region vertices by intersecting with polygon
        region_vertices = self._compute_region_vertices(corners)
        
        if len(region_vertices) < 3:
            return None
        
        # Classify based on vertex count and geometric properties
        region_type = self._determine_region_type(region_vertices)
        
        region = Region(region_type, region_vertices, self.region_counter)
        self.region_counter += 1
        
        return region
    
    def _compute_region_vertices(self, corners: List[Point]) -> List[Point]:
        """
        Compute actual vertices of region by intersecting grid cell with polygon
        This is a simplified implementation - full version would handle all cases
        """
        polygon = Polygon(self.polygon_vertices)
        region_vertices = []
        
        # Add corners that are inside polygon
        for corner in corners:
            if polygon.contains(corner) or polygon.on_boundary(corner):
                region_vertices.append(corner)
        
        # Add intersection points between cell edges and polygon boundary
        # This is simplified - full implementation would be more comprehensive
        
        return region_vertices
    
    def _determine_region_type(self, vertices: List[Point]) -> str:
        """
        Determine region type based on geometry

        Args:
            vertices: Region boundary vertices

        Returns:
            Region type string
        """
        n = len(vertices)
        
        if n == 3:
            # Triangle - check if right or obtuse
            triangle = ExactTriangle(*vertices)
            if triangle.is_right:
                return 'right_triangle'
            elif triangle.is_obtuse:
                return 'obtuse_triangle'
            else:
                return 'acute_triangle'
        
        elif n == 4:
            # Quadrilateral - check if rectangle
            if self._is_rectangle(vertices):
                return 'rectangle'
            else:
                return 'quadrilateral'
        
        else:
            # General polygon
            return 'polygon'
    
    def _is_rectangle(self, vertices: List[Point]) -> bool:
        """Check if quadrilateral is a rectangle"""
        if len(vertices) != 4:
            return False
        
        # Check if all angles are right angles
        for i in range(4):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % 4]
            p3 = vertices[(i + 2) % 4]
            
            angle_type = BernEppsteinGeometry.angle_type(p1, p2, p3)
            if angle_type != 'right':
                return False
        
        return True
    
    def _process_constraints(self):
        """Process additional constraints within regions"""
        for region in self.regions:
            for constraint in self.constraints:
                # Check if constraint intersects this region
                constraint_in_region = self._constraint_intersects_region(constraint, region)
                if constraint_in_region:
                    region.add_constraint(constraint)
    
    def _constraint_intersects_region(self, constraint: List[Point], region: Region) -> bool:
        """Check if constraint intersects with region"""
        # Simplified check - would need more sophisticated intersection testing
        region_polygon = Polygon(region.vertices)

        for point in constraint:
            if region_polygon.contains(point) or region_polygon.on_boundary(point):
                return True

        return False


class SlabDecomposer:
    """
    Specialized decomposer for slab-based decomposition
    Used for complex regions that need further subdivision
    """
    
    def __init__(self, region: Region):
        self.region = region
        self.sub_regions = []
    
    def decompose_slab(self) -> List[Region]:
        """
        Decompose a slab region into triangles using diagonal splitting

        Returns:
            List of triangular sub-regions
        """
        vertices = self.region.vertices
        
        if len(vertices) < 4:
            # Already triangular
            return [self.region]
        
        # Split polygon using ear clipping or diagonal method
        triangular_regions = self._triangulate_polygon(vertices)
        
        return triangular_regions
    
    def _triangulate_polygon(self, vertices: List[Point]) -> List[Region]:
        """
        Triangulate polygon using ear clipping algorithm

        Args:
            vertices: Polygon vertices in order

        Returns:
            List of triangular regions
        """
        if len(vertices) < 3:
            return []
        
        if len(vertices) == 3:
            # Already a triangle
            triangle_region = Region('triangle', vertices)
            return [triangle_region]
        
        triangular_regions = []
        remaining_vertices = vertices.copy()
        
        while len(remaining_vertices) > 3:
            # Find an ear (triangle that can be removed)
            ear_index = self._find_ear(remaining_vertices)
            
            if ear_index == -1:
                # No ear found - shouldn't happen for simple polygons
                break
            
            # Create triangle from ear
            n = len(remaining_vertices)
            triangle_vertices = [
                remaining_vertices[(ear_index - 1) % n],
                remaining_vertices[ear_index],
                remaining_vertices[(ear_index + 1) % n]
            ]
            
            triangle_region = Region('triangle', triangle_vertices)
            triangular_regions.append(triangle_region)
            
            # Remove ear vertex
            remaining_vertices.pop(ear_index)
        
        # Add final triangle
        if len(remaining_vertices) == 3:
            final_triangle = Region('triangle', remaining_vertices)
            triangular_regions.append(final_triangle)
        
        return triangular_regions
    
    def _find_ear(self, vertices: List[Point]) -> int:
        """
        Find an ear in the polygon (a vertex that can be removed to form a triangle)

        Args:
            vertices: Current polygon vertices

        Returns:
            Index of ear vertex, or -1 if none found
        """
        n = len(vertices)
        
        for i in range(n):
            # Check if vertex i is an ear
            prev_vertex = vertices[(i - 1) % n]
            curr_vertex = vertices[i]
            next_vertex = vertices[(i + 1) % n]
            
            # Check if triangle is convex (interior angle < 180°)
            if BernEppsteinGeometry.orientation(prev_vertex, curr_vertex, next_vertex) <= 0:
                continue  # Reflex vertex, not an ear
            
            # Check if any other vertex is inside the triangle
            triangle = ExactTriangle(prev_vertex, curr_vertex, next_vertex)
            is_ear = True
            
            for j in range(n):
                if j == i or j == (i - 1) % n or j == (i + 1) % n:
                    continue
                
                if triangle.contains_point(vertices[j]):
                    is_ear = False
                    break
            
            if is_ear:
                return i
        
        return -1


class RegionClassifier:
    """
    Advanced region classification for complex geometric shapes
    """
    
    @staticmethod
    def classify_by_boundary_intersection(vertices: List[Point], 
                                        polygon_boundary: List[Point]) -> str:
        """
        Classify region based on how it intersects polygon boundary

        Args:
            vertices: Region vertices
            polygon_boundary: Original polygon boundary

        Returns:
            Detailed region classification
        """
        # Count boundary vertices
        boundary_set = set((v.x(), v.y()) for v in polygon_boundary)
        boundary_vertices_in_region = sum(
            1 for v in vertices 
            if (v.x(), v.y()) in boundary_set
        )
        
        n = len(vertices)
        
        if boundary_vertices_in_region == 0:
            return 'interior_region'
        elif boundary_vertices_in_region == 1:
            return 'single_boundary_contact'
        elif boundary_vertices_in_region == 2:
            if n == 3:
                return 'boundary_triangle'
            else:
                return 'boundary_edge_region'
        else:
            return 'complex_boundary_region'
    
    @staticmethod
    def analyze_angles(vertices: List[Point]) -> Dict[str, int]:
        """
        Analyze angle distribution in region

        Args:
            vertices: Region vertices

        Returns:
            Dictionary with angle counts
        """
        angle_counts = {'acute': 0, 'right': 0, 'obtuse': 0}
        n = len(vertices)
        
        for i in range(n):
            v1 = vertices[(i - 1) % n]
            v2 = vertices[i]
            v3 = vertices[(i + 1) % n]
            
            angle_type = BernEppsteinGeometry.angle_type(v1, v2, v3)
            angle_counts[angle_type] += 1
        
        return angle_counts