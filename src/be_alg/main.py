from fractions import Fraction
from dcel import DCEL
from slab_partition import slab_partition
from viz_utils import show_slab_partition


def test_simple_polygon():
    """Test with a simple polygon"""
    print("Testing simple polygon...")

    # Define a simple polygon
    pts = [(0, 0), (4, 0), (4, 3), (2, 4), (0, 3)]
    pts = [(Fraction(x), Fraction(y)) for x, y in pts]

    # Create DCEL
    dcel = DCEL.from_polygon(boundary_indices=list(range(len(pts))), points=pts)

    # Apply slab partition
    slab_partition(dcel, debug=True)

    # Visualize result
    show_slab_partition(dcel, "Simple Polygon - Slab Partition")

    # Print statistics
    print(f"Final statistics:")
    print(f"  Vertices: {len(dcel.vertices)}")
    print(f"  Edges: {len(dcel.half_edges) // 2}")  # Half-edges come in pairs
    print(f"  Faces: {len(dcel.faces) - 1}")  # Exclude outer face

    # Print face types
    face_types = {}
    for face in dcel.faces:
        if face is not dcel.outer_face and hasattr(face, 'ftype') and face.ftype:
            face_types[face.ftype.name] = face_types.get(face.ftype.name, 0) + 1

    print(f"  Face types: {face_types}")


def test_paper_example():
    """Test with the example from the paper"""
    print("Testing paper example...")

    # Example from the paper
    pts = [(0, 0), (7, 0), (7, 3), (5, 5), (3, 5), (1, 4), (0, 2)]
    pts = [(Fraction(x), Fraction(y)) for x, y in pts]

    dcel = DCEL.from_polygon(boundary_indices=list(range(len(pts))), points=pts)
    slab_partition(dcel, debug=True)
    show_slab_partition(dcel, "Paper Example - Slab Partition")


if __name__ == "__main__":
    test_simple_polygon()
    test_paper_example()