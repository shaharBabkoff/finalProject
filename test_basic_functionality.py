# tests/test_basic_functionality.py
import unittest
from cgshop2025_pyutils.geometry import FieldNumber, Point
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
from bern_eppstein_solver import BernEppsteinSolver
from bern_eppstein_solver.geometry import ExactTriangle


class TestBasicFunctionality(unittest.TestCase):

    def test_point_creation(self):
        """Test exact point creation"""
        p = Point(FieldNumber(1), FieldNumber(2))
        self.assertEqual(p.x(), FieldNumber(1))
        self.assertEqual(p.y(), FieldNumber(2))

    def test_triangle_creation(self):
        """Test triangle creation and angle detection"""
        # Right triangle
        p1 = Point(FieldNumber(0), FieldNumber(0))
        p2 = Point(FieldNumber(1), FieldNumber(0))
        p3 = Point(FieldNumber(0), FieldNumber(1))

        triangle = ExactTriangle(p1, p2, p3)
        self.assertTrue(triangle.is_right)
        self.assertFalse(triangle.is_obtuse)

    def test_simple_instance_solving(self):
        """Test solving a simple triangle"""
        instance = Cgshop2025Instance(
            instance_uid="test_triangle",
            num_points=3,
            points_x=[0, 1, 0],
            points_y=[0, 0, 1],
            region_boundary=[0, 1, 2],
            num_constraints=0,
            additional_constraints=[]
        )

        solver = BernEppsteinSolver(instance)
        solution = solver.solve()

        self.assertIsNotNone(solution)
        self.assertEqual(solution.instance_uid, "test_triangle")


if __name__ == '__main__':
    unittest.main()