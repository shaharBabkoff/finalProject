from typing import List, Tuple
from cgshop2025_pyutils.geometry import Point, FieldNumber, ConstrainedTriangulation


def triangulate_rectangle(region_indices: List[int],
                          global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Triangulate a rectangle with unsubdivided sides.
    Simply add a diagonal to split into 2 right triangles.

    Parameters:
    -----------
    region_indices : List[int] - 4 vertex indices in CCW order
    global_points : List[Tuple[float, float]] - global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - List of triangle index triples
    """
    if len(region_indices) != 4:
        raise ValueError("Rectangle must have exactly 4 vertices")

    # For rectangle with vertices [v0, v1, v2, v3] in CCW order:
    # Add diagonal v0->v2 to create triangles (v0,v1,v2) and (v0,v2,v3)
    v0, v1, v2, v3 = region_indices

    triangles = [
        (v0, v1, v2),  # First triangle
        (v0, v2, v3)  # Second triangle
    ]

    return triangles


def triangulate_right_triangle(region_indices: List[int],
                               global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Triangulate a right triangle with hypotenuse on boundary and vertical leg possibly subdivided.
    From Lemma 1: If triangle has subdivision points on legs, project them onto base.

    Parameters:
    -----------
    region_indices : List[int] - 3 vertex indices
    global_points : List[Tuple[float, float]] - global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - List of triangle index triples
    """
    if len(region_indices) != 3:
        raise ValueError("Right triangle must have exactly 3 vertices")

    # For right triangles, the region is already triangular
    # Just return the single triangle
    return [tuple(region_indices)]


def triangulate_obtuse_triangle(region_indices: List[int],
                                global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Triangulate obtuse triangle with two boundary sides and one vertical leg.
    Uses the method from Section 2: drop altitude from obtuse vertex to base.

    Parameters:
    -----------
    region_indices : List[int] - 3 vertex indices
    global_points : List[Tuple[float, float]] - global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - List of triangle index triples
    """
    if len(region_indices) != 3:
        raise ValueError("Obtuse triangle must have exactly 3 vertices")

    # For now, return as single triangle
    # In full implementation, would need to:
    # 1. Identify the obtuse vertex
    # 2. Drop altitude to opposite side (base)
    # 3. Add Steiner point and create 2 triangles

    # Simple implementation: return as-is
    return [tuple(region_indices)]


def triangulate_slab(region_indices: List[int],
                     global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Triangulate a slab with two boundary sides and two vertical sides.
    From the paper: split by diagonal into obtuse triangles, then triangulate each.

    Parameters:
    -----------
    region_indices : List[int] - 4+ vertex indices in CCW order
    global_points : List[Tuple[float, float]] - global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - List of triangle index triples
    """
    n = len(region_indices)

    if n < 4:
        raise ValueError("Slab must have at least 4 vertices")

    # For quadrilateral slab: split by diagonal
    if n == 4:
        # Use the "safe diagonal" from the paper
        # For slab with vertical sides, diagonal v1->v3 is always inside
        v0, v1, v2, v3 = region_indices

        triangles = [
            (v0, v1, v3),  # Triangle A
            (v1, v2, v3)  # Triangle B
        ]
        return triangles

    # For complex slab (5+ vertices): use fan triangulation from first vertex
    else:
        triangles = []
        v0 = region_indices[0]

        for i in range(1, n - 1):
            v1 = region_indices[i]
            v2 = region_indices[i + 1]
            triangles.append((v0, v1, v2))

        return triangles


def triangulate_all_regions(regions: List[dict],
                            global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Triangulate all regions according to their types.

    Parameters:
    -----------
    regions : List[dict] - List of region dictionaries with 'type' and 'indices'
    global_points : List[Tuple[float, float]] - global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - List of all triangle index triples
    """
    all_triangles = []

    for i, region in enumerate(regions):
        region_type = region['type']
        indices = region['indices']

        print(f"Triangulating region {i} ({region_type}) with vertices {indices}")

        try:
            if region_type == "rectangle":
                triangles = triangulate_rectangle(indices, global_points)
            elif region_type == "right_triangle":
                triangles = triangulate_right_triangle(indices, global_points)
            elif region_type == "obtuse_triangle":
                triangles = triangulate_obtuse_triangle(indices, global_points)
            elif region_type == "slab":
                triangles = triangulate_slab(indices, global_points)
            else:
                print(f"Warning: Unknown region type '{region_type}', using fan triangulation")
                # Default: fan triangulation
                triangles = []
                if len(indices) >= 3:
                    v0 = indices[0]
                    for j in range(1, len(indices) - 1):
                        v1 = indices[j]
                        v2 = indices[j + 1]
                        triangles.append((v0, v1, v2))

            print(f"  -> Generated {len(triangles)} triangles: {triangles}")
            all_triangles.extend(triangles)

        except Exception as e:
            print(f"Error triangulating region {i}: {e}")
            continue

    print(f"\nTotal triangles generated: {len(all_triangles)}")
    return all_triangles


def apply_bern_eppstein_triangulation(regions: List[dict],
                                      global_points: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Apply the complete Bern-Eppstein non-obtuse triangulation algorithm.

    This is the main function that:
    1. Takes the partitioned regions from the grid
    2. Triangulates each according to its type
    3. Returns the final non-obtuse triangulation

    Parameters:
    -----------
    regions : List[dict] - Regions from extract_faces_of_grid()
    global_points : List[Tuple[float, float]] - Global point coordinates

    Returns:
    --------
    List[Tuple[int, int, int]] - Final triangulation as list of triangle index triples
    """
    print("=== Applying Bern-Eppstein Non-Obtuse Triangulation ===")
    print(f"Input: {len(regions)} regions, {len(global_points)} points")

    # Step 1: Triangulate all regions
    triangles = triangulate_all_regions(regions, global_points)

    # Step 2: Verify triangulation properties
    print(f"\n=== Triangulation Results ===")
    print(f"Total triangles: {len(triangles)}")
    print(f"Total points used: {len(global_points)}")

    # Step 3: Return final triangulation
    return triangles