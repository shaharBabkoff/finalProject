#!/usr/bin/env python3
"""
Simple test instance to verify the Bern & Eppstein solver works end-to-end.
This tests the most basic functionality before moving to complex cases.
"""

import sys
import traceback
from cgshop2025_pyutils.geometry import FieldNumber, Point
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance, Cgshop2025Solution

try:
    from bern_eppstein_solver import BernEppsteinSolver

    print("✅ Successfully imported BernEppsteinSolver")
except ImportError as e:
    print(f"❌ Failed to import BernEppsteinSolver: {e}")
    print("Please make sure your solver module is properly installed")
    sys.exit(1)


def create_simple_triangle_instance():
    """Create the simplest possible instance: a right triangle"""
    print("\n🔍 Creating simple triangle instance...")

    # Right triangle: (0,0), (1,0), (0,1)
    instance = Cgshop2025Instance(
        instance_uid="simple_triangle",
        num_points=3,
        points_x=["0", "1", "0"],  # Use strings for exact rational representation
        points_y=["0", "0", "1"],
        region_boundary=[0, 1, 2],
        num_constraints=0,
        additional_constraints=[]
    )

    print(f"✅ Created instance: {instance.instance_uid}")
    print(f"   Points: {instance.num_points}")
    print(f"   Boundary: {instance.region_boundary}")

    return instance


def create_simple_square_instance():
    """Create a simple square instance"""
    print("\n🔍 Creating simple square instance...")

    # Unit square: (0,0), (1,0), (1,1), (0,1)
    instance = Cgshop2025Instance(
        instance_uid="simple_square",
        num_points=4,
        points_x=["0", "1", "1", "0"],
        points_y=["0", "0", "1", "1"],
        region_boundary=[0, 1, 2, 3],
        num_constraints=0,
        additional_constraints=[]
    )

    print(f"✅ Created instance: {instance.instance_uid}")
    print(f"   Points: {instance.num_points}")
    print(f"   Boundary: {instance.region_boundary}")

    return instance


def test_solver_basic_functionality(instance):
    """Test basic solver functionality"""
    print(f"\n🔍 Testing solver with {instance.instance_uid}...")

    try:
        # Create solver with debug enabled
        solver = BernEppsteinSolver(instance, {'debug': True})
        print("✅ Solver created successfully")

        # Attempt to solve
        print("🔄 Attempting to solve...")
        solution = solver.solve()
        print("✅ Solution generated!")

        # Basic solution validation
        print(f"   Steiner points: {len(solution.steiner_points_x)}")
        print(f"   Edges: {len(solution.edges)}")
        print(f"   Instance UID matches: {solution.instance_uid == instance.instance_uid}")

        return solution

    except Exception as e:
        print(f"❌ Solver failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return None


def analyze_solution(solution, instance):
    """Analyze the generated solution"""
    if valid_edges:
        print("   ✅ All edges are valid")
    else:
        print("   ❌ Some edges are invalid")
        return False

    # Check for duplicate edges
    edge_set = set()
    duplicate_edges = 0
    for edge in solution.edges:
        edge_key = tuple(sorted(edge))
        if edge_key in edge_set:
            duplicate_edges += 1
        edge_set.add(edge_key)

    if duplicate_edges > 0:
        print(f"   ⚠️  Found {duplicate_edges} duplicate edges")
    else:
        print("   ✅ No duplicate edges found")

    return True


def test_with_cgshop_verification(instance, solution):
    """Test solution with official CG-SHOP verification"""
    if not solution:
        return False

    print(f"\n🔍 Testing with CG-SHOP verification...")

    try:
        from cgshop2025_pyutils import verify
        print("✅ Successfully imported verify function")

        # Run verification
        result = verify(instance, solution)
        print(f"✅ Verification completed")

        # Check results
        if hasattr(result, 'errors') and result.errors:
            print(f"❌ Verification errors: {result.errors}")
            return False
        else:
            print("✅ Solution passed verification!")

            # Check for obtuse triangles
            if hasattr(result, 'num_obtuse_triangles'):
                obtuse_count = result.num_obtuse_triangles
                print(f"   Obtuse triangles: {obtuse_count}")

                if obtuse_count == 0:
                    print("   🎉 FEASIBLE SOLUTION (no obtuse triangles)!")
                else:
                    print(f"   ⚠️  Solution has {obtuse_count} obtuse triangles")

            return True

    except ImportError as e:
        print(f"❌ Cannot import verify function: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def identify_next_issues(test_results):
    """Identify what needs to be fixed next based on test results"""
    print(f"\n🔍 Identifying next issues to fix...")

    issues_found = []

    if not test_results['triangle_solved']:
        issues_found.append("❌ Cannot solve simple triangle - check basic triangulation")

    if not test_results['square_solved']:
        issues_found.append("❌ Cannot solve simple square - check polygon decomposition")

    if not test_results['verification_passed']:
        issues_found.append("❌ Verification failed - check solution format")

    if test_results.get('obtuse_triangles', 0) > 0:
        issues_found.append("⚠️  Solution has obtuse triangles - check merger algorithms")

    if not issues_found:
        print("✅ All basic tests passed! Ready for Step 3: Complete Merger Algorithms")
    else:
        print("Issues found:")
        for issue in issues_found:
            print(f"   {issue}")

        print("\nNext steps:")
        if not test_results['triangle_solved']:
            print("   1. Fix basic triangulation in triangulator.py")
            print("   2. Check decomposition.py for simple cases")
        elif not test_results['square_solved']:
            print("   1. Fix polygon decomposition logic")
            print("   2. Check region classification")
        elif not test_results['verification_passed']:
            print("   1. Fix solution format in solver.py")
            print("   2. Check coordinate conversion")
        else:
            print("   1. Implement proper merger algorithms")
            print("   2. Fix obtuse triangle handling")

    return issues_found


def main():
    """Run simple instance tests"""
    print("🧪 Testing Bern & Eppstein Solver with Simple Instances")
    print("=" * 60)

    test_results = {
        'triangle_solved': False,
        'square_solved': False,
        'verification_passed': False,
        'obtuse_triangles': 0
    }

    # Test 1: Simple triangle
    print("\n" + "=" * 40)
    print("TEST 1: Simple Triangle")
    print("=" * 40)

    triangle_instance = create_simple_triangle_instance()
    triangle_solution = test_solver_basic_functionality(triangle_instance)

    if triangle_solution:
        test_results['triangle_solved'] = True
        if analyze_solution(triangle_solution, triangle_instance):
            verification_passed = test_with_cgshop_verification(triangle_instance, triangle_solution)
            if verification_passed:
                test_results['verification_passed'] = True

    # Test 2: Simple square
    print("\n" + "=" * 40)
    print("TEST 2: Simple Square")
    print("=" * 40)

    square_instance = create_simple_square_instance()
    square_solution = test_solver_basic_functionality(square_instance)

    if square_solution:
        test_results['square_solved'] = True
        if analyze_solution(square_solution, square_instance):
            verification_passed = test_with_cgshop_verification(square_instance, square_solution)
            if verification_passed:
                test_results['verification_passed'] = True

    # Summary and next steps
    print("\n" + "=" * 60)
    print("🧪 Test Results Summary")
    print("=" * 60)

    print(f"Triangle solved: {'✅' if test_results['triangle_solved'] else '❌'}")
    print(f"Square solved: {'✅' if test_results['square_solved'] else '❌'}")
    print(f"Verification passed: {'✅' if test_results['verification_passed'] else '❌'}")

    issues = identify_next_issues(test_results)

    if not issues:
        print("\n🎉 All basic tests passed! Ready for the next step.")
    else:
        print(f"\n❌ Found {len(issues)} issues to fix before proceeding.")
        print("Please address these issues and run the test again.")

    return len(issues) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
    not solution:
    return False

print(f"\n🔍 Analyzing solution for {solution.instance_uid}...")

# Basic checks
total_points = instance.num_points + len(solution.steiner_points_x)
print(f"   Total points: {total_points} ({instance.num_points} original + {len(solution.steiner_points_x)} Steiner)")

# Check edge validity
valid_edges = True
for i, edge in enumerate(solution.edges):
    if len(edge) != 2:
        print(f"   ❌ Edge {i} has {len(edge)} endpoints (should be 2)")
        valid_edges = False
    elif edge[0] < 0 or edge[0] >= total_points or edge[1] < 0 or edge[1] >= total_points:
        print(f"   ❌ Edge {i} has invalid indices: {edge}")
        valid_edges = False
    elif edge[0] == edge[1]:
        print(f"   ❌ Edge {i} is degenerate (same endpoints): {edge}")
        valid_edges = False

if