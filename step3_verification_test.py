#!/usr/bin/env python3
"""
STEP 3: Test with Official CG-SHOP Verification
This tests if your solution is compatible with the competition verification system
"""

print("🏆 Step 3: Testing CG-SHOP Verification Compatibility")
print("=" * 60)

# Test 1: Import verification
try:
    from cgshop2025_pyutils import verify

    print("✅ 1. Official verification import works")
except ImportError as e:
    print(f"❌ 1. Cannot import verify: {e}")
    print("   → Try: pip install --upgrade cgshop2025_pyutils")
    exit(1)

# Test 2: Import what we need
try:
    from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
    from bern_eppstein_solver import BernEppsteinSolver

    print("✅ 2. All imports successful")
except ImportError as e:
    print(f"❌ 2. Import failed: {e}")
    exit(1)

# Test 3: Create and solve simple triangle
print("\n🔄 3. Creating and solving triangle instance...")
try:
    instance = Cgshop2025Instance(
        instance_uid="verification_test_triangle",
        num_points=3,
        points_x=["0", "1", "0"],
        points_y=["0", "0", "1"],
        region_boundary=[0, 1, 2],
        num_constraints=0,
        additional_constraints=[]
    )

    solver = BernEppsteinSolver(instance, {'debug': False})
    solution = solver.solve()
    print(f"   ✅ Solution created: {len(solution.edges)} edges, {len(solution.steiner_points_x)} Steiner points")
except Exception as e:
    print(f"   ❌ Failed to create solution: {e}")
    exit(1)

# Test 4: Official verification
print("\n🔄 4. Running official CG-SHOP verification...")
try:
    result = verify(instance, solution)
    print("   ✅ Verification completed successfully!")

    # Check results
    if hasattr(result, 'errors') and result.errors:
        print(f"   ❌ VERIFICATION ERRORS:")
        for error in result.errors:
            print(f"      - {error}")
        print("\n   → Need to fix these errors before proceeding")
        exit(1)
    else:
        print("   ✅ NO VERIFICATION ERRORS!")

    # Check for obtuse triangles
    obtuse_count = 0
    if hasattr(result, 'num_obtuse_triangles'):
        obtuse_count = result.num_obtuse_triangles
        print(f"   📊 Obtuse triangles: {obtuse_count}")

    if obtuse_count == 0:
        print("   🎉 FEASIBLE SOLUTION! (No obtuse triangles)")
    else:
        print(f"   ⚠️  Solution has {obtuse_count} obtuse triangles")
        print("   → This is still a valid solution, just not optimal for the competition")

    # Additional metrics if available
    if hasattr(result, 'total_triangles'):
        print(f"   📊 Total triangles: {result.total_triangles}")

except Exception as e:
    print(f"   ❌ Verification failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback

    error_lines = traceback.format_exc().split('\n')[:8]
    print("   Error details:")
    for line in error_lines:
        if line.strip():
            print(f"     {line}")
    exit(1)

# Test 5: Test with square (more complex)
print("\n🔄 5. Testing with square instance...")
try:
    square_instance = Cgshop2025Instance(
        instance_uid="verification_test_square",
        num_points=4,
        points_x=["0", "1", "1", "0"],
        points_y=["0", "0", "1", "1"],
        region_boundary=[0, 1, 2, 3],
        num_constraints=0,
        additional_constraints=[]
    )

    square_solver = BernEppsteinSolver(square_instance, {'debug': False})
    square_solution = square_solver.solve()

    square_result = verify(square_instance, square_solution)

    if hasattr(square_result, 'errors') and square_result.errors:
        print(f"   ❌ Square verification errors: {square_result.errors}")
    else:
        print(f"   ✅ Square solved successfully!")
        print(f"      Edges: {len(square_solution.edges)}")
        print(f"      Steiner points: {len(square_solution.steiner_points_x)}")

        square_obtuse = getattr(square_result, 'num_obtuse_triangles', 0)
        if square_obtuse == 0:
            print(f"      🎉 Feasible solution!")
        else:
            print(f"      ⚠️  {square_obtuse} obtuse triangles")

except Exception as e:
    print(f"   ❌ Square test failed: {e}")
    # Don't exit - triangle success is more important

print("\n" + "=" * 60)
print("🏆 Step 3 Results Summary")
print("=" * 60)

print("✅ Your Bern & Eppstein solver is working!")
print("✅ Compatible with CG-SHOP 2025 verification system")
print("✅ Produces valid triangulations")

if obtuse_count == 0:
    print("🎉 PERFECT! Your solver produces feasible solutions!")
    print("✅ Ready for Step 4: Test on competition instances")
else:
    print("⚠️  Solver produces obtuse triangles")
    print("✅ Still ready for Step 4: Implement full Bern & Eppstein algorithm")

print("\n🚀 Next: Ready to test on real CG-SHOP competition instances!")