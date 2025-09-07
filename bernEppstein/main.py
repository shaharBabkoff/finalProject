from cgshop2025_pyutils.data_schemas.instance import Cgshop2025Instance
from cgshop2025_pyutils.data_schemas.solution import Cgshop2025Solution
from cgshop2025_pyutils.geometry import Point
from bernEppstein.geometry_utils import _to_exact_repr
from my_triangulation import ConstrainedTriangulation


class BESolver:
    def __init__(self, instance: Cgshop2025Instance):
        self.instance = instance

    def solve(self) -> Cgshop2025Solution:
        ct = ConstrainedTriangulation()

        for x, y in zip(self.instance.points_x, self.instance.points_y):
            ct.add_point(Point(x, y))

        ct.add_boundary(self.instance.region_boundary)

        for i, j in getattr(self.instance, "additional_constraints", []):
            ct.add_segment(i, j)
        edges = ct.get_triangulation_edges()
        n0 = self.instance.num_points
        steiner = ct.points[n0:]
        steiner_x = [_to_exact_repr(s[0]) for s in steiner]
        steiner_y = [_to_exact_repr(s[1]) for s in steiner]

        return Cgshop2025Solution(
            instance_uid=self.instance.instance_uid,
            steiner_points_x=steiner_x,
            steiner_points_y=steiner_y,
            edges=edges,
        )
