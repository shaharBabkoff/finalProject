#!/usr/bin/env python3
"""
STEP 2 TEST ONLY - Test basic solver functionality
Run this after Step 1 passes
"""

print("🔧 Step 2: Testing Basic Solver Functionality")
print("=" * 50)

# Test 1: Import solver
try:
    from bern_eppstein_solver import BernEppsteinSolver

    print("✅ 1. BernEppsteinSolver imports work")
except ImportError as e:
    print(f"❌ 1. BernEppsteinSolver import failed: {e}")
    print("   → Check your __init__.py file")
    exit(1)

# Test 2: Import instance creation
try:
    from cgshop2025_pyutils.data_schemas import Cgshop2025Instance

    print("✅ 2. Instance creation imports work")
except ImportError as e:
    print(f"❌ 2. Instance import failed: {e}")
    exit(1)

# Test 3: Create simple triangle instance
try:
    instance = Cgshop2025Instance(
        instance_uid="test_triangle",
        num_points=3,
        points_x=["0", "1", "0"],  # Right triangle
        points_y=["0", "0", "1"],
        region_boundary=[0, 1, 2],
        num_constraints=0,
        additional_constraints=[]
    )
    print("✅ 3. Triangle instance creation works")
except Exception as e:
    print(f"❌ 3. Instance creation failed: {e}")
    exit(1)

# Test 4: Create solver (don't solve yet)
try:
    solver = BernEppsteinSolver(instance, {'debug': True})
    print("✅ 4. Solver creation works")
except Exception as e:
    print(f"❌ 4. Solver creation failed: {e}")
    print(f"   Error details: {e}")
    exit(1)

# Test 5: Try to solve (this might fail - that's OK)
try:
    print("🔄 5. Attempting to solve...")
    solution = solver.solve()
    print("✅ 5. Solver.solve() completed successfully!")
    print(f"   Steiner points: {len(solution.steiner_points_x)}")
    print(f"   Edges: {len(solution.edges)}")

    # Test 6: Basic solution validation
    if solution.instance_uid == instance.instance_uid:
        print("✅ 6. Solution format looks correct")
    else:
        print("❌ 6. Solution instance UID mismatch")

except Exception as e:
    print(f"❌ 5. Solver.solve() failed: {e}")
    print(f"   This is expected - we'll fix it in the next step")
    print(f"   Error type: {type(e).__name__}")

    # Show first few lines of error for debugging
    import traceback

    error_lines = traceback.format_exc().split('\n')[:10]
    print("   Error details:")
    for line in error_lines:
        if line.strip():
            print(f"     {line}")

    exit(1)

print("\n🎉 Step 2 COMPLETE - Basic solver functionality works!")
print("✅ Ready for Step 3: Complete any missing implementations")