from fractions import Fraction

from cgshop2025_pyutils.data_schemas.instance import Cgshop2025Instance
from cgshop2025_pyutils.data_schemas.solution import Cgshop2025Solution
from cgshop2025_pyutils.verifier.verifier import verify
from cgshop2025_pyutils.geometry import Point

from bernEppstein2.geometry_utils import _to_exact_repr
from my_triangulation import ConstrainedTriangulation

class BESolver:
    def __init__(self, instance: Cgshop2025Instance):
        self.instance = instance


    def solve(self) -> Cgshop2025Solution:
        ct = ConstrainedTriangulation()

        # 1. load the instance into ct ............................
        for x, y in zip(instance.points_x, instance.points_y):
            ct.add_point(Point(x, y))
        ct.add_boundary(instance.region_boundary)
        for i, j in instance.additional_constraints:
            ct.add_segment(i, j)

        # 2. **do not call the private routine** – just ask for edges
        edges = ct.get_triangulation_edges()

        # 3. collect steiner points that the algorithm may have added
        n0 = instance.num_points
        steiner = ct.points[n0:]
        steiner_x = [_to_exact_repr(s[0]) for s in steiner]
        steiner_y = [_to_exact_repr(s[1]) for s in steiner]

        return Cgshop2025Solution(
            instance_uid=instance.instance_uid,
            steiner_points_x=steiner_x,
            steiner_points_y=steiner_y,
            edges=edges,
        )

if __name__ == "__main__":
    instance = Cgshop2025Instance(
        instance_uid="example",
        num_points=4,
        points_x=[0, 2, 4, 3],
        points_y=[0, 3, 1, -1],
        region_boundary=[0, 1, 2, 3],
       #  num_constraints=1,
       # additional_constraints=[[5, 6]],
    )

    solver = BESolver(instance)
    solution = solver.solve()
    print(f"\n--- Solver output for {solution.instance_uid} ---")
    print("• #Steiner points :", len(solution.steiner_points_x))
    print("• #Edges          :", len(solution.edges))
    print("  Edges list      :", solution.edges)
    # verification = verify(instance, solution)
    # if verification.errors:
    #     print("\n❌  Verifier found errors:")
    #     for e in verification.errors:
    #         print("   •", e)
    # else:
    #     print("\n✅  Verifier OK.")
    #     print("   non‑obtuse triangles :", verification.num_obtuse_triangles)
