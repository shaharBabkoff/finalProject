from cgshop2025_pyutils.geometry import FieldNumber, Point
from bern_eppstein_solver.geometry import BernEppsteinGeometry, ExactTriangle

# Test point creation
p1 = Point(FieldNumber(0), FieldNumber(0))
p2 = Point(FieldNumber(1), FieldNumber(0))
p3 = Point(FieldNumber(0), FieldNumber(1))

print(f"Points created: {p1}, {p2}, {p3}")

# Test triangle creation
triangle = ExactTriangle(p1, p2, p3)
print(f"Triangle is obtuse: {triangle.is_obtuse}")
print(f"Triangle is right: {triangle.is_right}")
print(f"Triangle area: {triangle.area().exact()}")

# Test angle calculation
angle_type = BernEppsteinGeometry.angle_type(p1, p2, p3)
print(f"Angle type at p2: {angle_type}")