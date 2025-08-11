try:
    from bern_eppstein_solver import BernEppsteinSolver
    from bern_eppstein_solver.geometry import BernEppsteinGeometry, ExactTriangle
    from bern_eppstein_solver.triangulator import BernEppsteinTriangulator
    from bern_eppstein_solver.utils import VisualizationUtils
    from cgshop2025_pyutils.geometry import FieldNumber, Point  # Fixed import
    print("✅ All imports successful!")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()