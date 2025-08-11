
from cgshop2025_pyutils import verify
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
from bern_eppstein_solver import BernEppsteinSolver

# Create test instance
instance = Cgshop2025Instance(
    instance_uid="test_integration",
    num_points=4,
    points_x=[0, 2, 2, 0],
    points_y=[0, 0, 2, 2],
    region_boundary=[0, 1, 2, 3],
    num_constraints=0,
    additional_constraints=[]
)

# Solve
solver = BernEppsteinSolver(instance, {'debug': True})
solution = solver.solve()

# Verify with official utils
try:
    result = verify(instance, solution)
    print(f"✅ Verification result: {result}")
    if result.errors:
        print(f"❌ Errors: {result.errors}")
    else:
        print(f"✅ Solution is valid!")
        print(f"Obtuse triangles: {getattr(result, 'num_obtuse_triangles', 'N/A')}")
except Exception as e:
    print(f"❌ Verification failed: {e}")