#!/usr/bin/env python3
"""
Direct competition test - bypasses file setup issues
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.getcwd())

from real_instance_tester import RealInstanceTester


def main():
    """Run competition test directly"""
    print("🏁 Direct Competition Instance Test")
    print("=" * 50)

    # Check if instances directory exists
    if not os.path.exists("instances"):
        print("❌ instances/ directory not found")
        print("   Run: python create_competition_instances.py first")
        return False

    # List files in instances directory
    import os
    instance_files = [f for f in os.listdir("instances") if f.endswith(".json")]
    print(f"Found {len(instance_files)} instance files:")
    for f in instance_files[:10]:  # Show first 10
        print(f"   - {f}")

    if len(instance_files) == 0:
        print("❌ No JSON files found in instances/ directory")
        return False

    # Create tester and run
    tester = RealInstanceTester("instances")

    # Run tests on all files (no limit for competition test)
    results = tester.run_batch_test(max_instances=10, timeout=120)  # 2 minutes per instance

    # Print summary
    tester.print_summary_report(results)

    # Success if all instances solved
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print(f"\n🏆 FINAL COMPETITION RESULTS:")
    print(f"   Solved: {success_count}/{total_count} instances")

    if success_count == total_count:
        print("   🎉 PERFECT! Your solver handles all competition instances!")
    elif success_count >= total_count * 0.8:
        print("   🥈 EXCELLENT! Your solver handles most competition instances!")
    else:
        print("   📈 GOOD START! Continue optimizing for larger instances")

    return success_count > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)