from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
from bern_eppstein_solver import BernEppsteinSolver

# Create a simple triangle instance
instance = Cgshop2025Instance(
    instance_uid="test_triangle",
    num_points=3,
    points_x=[0, 1, 0],
    points_y=[0, 0, 1],
    region_boundary=[0, 1, 2],
    num_constraints=0,
    additional_constraints=[]
)

print(f"Created instance: {instance.instance_uid}")
print(f"Points: {instance.num_points}")

# Test solver
try:
    solver = BernEppsteinSolver(instance, {'debug': True})
    solution = solver.solve()

    print(f"✅ Solution generated!")
    print(f"Steiner points: {len(solution.steiner_points_x)}")
    print(f"Edges: {len(solution.edges)}")

except Exception as e:
    print(f"❌ Solver error: {e}")
    import traceback

    traceback.print_exc()