#!/usr/bin/env python3
"""
Simple standalone competition test
"""

import json
import time
import os
from pathlib import Path

try:
    from cgshop2025_pyutils.data_schemas import Cgshop2025Instance
    from cgshop2025_pyutils import verify
    from bern_eppstein_solver import BernEppsteinSolver

    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)


def test_single_instance(file_path, timeout=120):
    """Test solver on a single instance"""
    print(f"\n🔄 Testing: {file_path.name}")
    print("-" * 50)

    try:
        # Load instance
        with open(file_path, 'r') as f:
            data = json.load(f)

        instance = Cgshop2025Instance(**data)
        print(f"   Instance: {instance.instance_uid}")
        print(f"   Points: {instance.num_points}")
        print(f"   Constraints: {instance.num_constraints}")

        # Solve
        start_time = time.time()
        solver = BernEppsteinSolver(instance, {'debug': False})
        solution = solver.solve()
        solve_time = time.time() - start_time

        print(f"   ✅ Solved in {solve_time:.3f} seconds")
        print(f"   📊 Steiner points: {len(solution.steiner_points_x)}")
        print(f"   📊 Edges: {len(solution.edges)}")

        # Verify
        verification_result = verify(instance, solution)

        if hasattr(verification_result, 'errors') and verification_result.errors:
            print(f"   ❌ Verification errors: {verification_result.errors}")
            return False, solve_time, len(solution.steiner_points_x), len(solution.edges), -1
        else:
            print(f"   ✅ Verification passed")

            obtuse_count = getattr(verification_result, 'num_obtuse_triangles', 0)
            if obtuse_count == 0:
                print(f"   🎉 FEASIBLE! (0 obtuse triangles)")
            else:
                print(f"   ⚠️  {obtuse_count} obtuse triangles")

            return True, solve_time, len(solution.steiner_points_x), len(solution.edges), obtuse_count

    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False, 0, 0, 0, -1


def main():
    """Main competition test"""
    print("🏁 Simple Competition Instance Test")
    print("=" * 60)

    # Find instance files
    instances_dir = Path("instances")
    if not instances_dir.exists():
        print("❌ instances/ directory not found")
        return False

    instance_files = list(instances_dir.glob("cgshop2025_examples_ortho_*.json"))
    if not instance_files:
        print("❌ No competition instance files found")
        return False

    # Sort by number of points (extracted from filename)
    def extract_points(filename):
        # Extract number between "ortho_" and "_"
        parts = filename.stem.split('_')
        for i, part in enumerate(parts):
            if part == 'ortho' and i + 1 < len(parts):
                try:
                    return int(parts[i + 1])
                except ValueError:
                    pass
        return 0

    instance_files.sort(key=extract_points)

    print(f"Found {len(instance_files)} competition instances:")
    for f in instance_files:
        points = extract_points(f)
        print(f"   - {f.name} ({points} points)")

    # Test each instance
    results = []
    total_time = 0

    for i, file_path in enumerate(instance_files, 1):
        print(f"\n[{i}/{len(instance_files)}]", end=" ")

        success, solve_time, steiner_points, edges, obtuse_count = test_single_instance(file_path)
        total_time += solve_time

        result = {
            'file': file_path.name,
            'points': extract_points(file_path),
            'success': success,
            'solve_time': solve_time,
            'steiner_points': steiner_points,
            'edges': edges,
            'obtuse_triangles': obtuse_count,
            'feasible': obtuse_count == 0
        }
        results.append(result)

        if success:
            status = "🎉 FEASIBLE" if result['feasible'] else "✅ SOLVED"
            print(f"   → {status} ({solve_time:.3f}s)")
        else:
            print(f"   → ❌ FAILED")

    # Summary
    print("\n" + "=" * 60)
    print("🏆 COMPETITION TEST SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r['success']]
    feasible = [r for r in results if r['feasible']]

    print(f"Total instances: {len(results)}")
    print(f"Successful: {len(successful)}/{len(results)} ({len(successful) / len(results) * 100:.1f}%)")
    print(f"Feasible: {len(feasible)}/{len(results)} ({len(feasible) / len(results) * 100:.1f}%)")
    print(f"Total time: {total_time:.2f} seconds")

    if successful:
        avg_time = sum(r['solve_time'] for r in successful) / len(successful)
        max_time = max(r['solve_time'] for r in successful)
        print(f"Average solve time: {avg_time:.3f}s")
        print(f"Maximum solve time: {max_time:.3f}s")

        # Performance scaling
        print(f"\n📊 Performance Scaling:")
        for result in successful:
            status = "🎉" if result['feasible'] else "⚠️ "
            print(
                f"   {result['points']:3d} points: {result['solve_time']:.3f}s, {result['steiner_points']:2d} Steiner {status}")

    # Failed instances
    failed = [r for r in results if not r['success']]
    if failed:
        print(f"\n❌ Failed instances:")
        for result in failed:
            print(f"   {result['file']} ({result['points']} points)")

    # Assessment
    print(f"\n🎯 Competition Readiness Assessment:")
    if len(feasible) == len(results):
        print("   🏆 PERFECT! Ready for competition with optimal solutions!")
    elif len(successful) == len(results):
        print("   🥈 EXCELLENT! All instances solved, some optimizable!")
    elif len(successful) >= len(results) * 0.8:
        print("   🥉 GOOD! Most instances solved, continue improving!")
    else:
        print("   📈 DEVELOPING! Focus on larger instance optimization!")

    return len(successful) > 0


if __name__ == "__main__":
    success = main()
    print(f"\n{'🎉 SUCCESS!' if success else '❌ NEEDS WORK'}")