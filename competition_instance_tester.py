#!/usr/bin/env python3
"""
Test your solver on real CG-SHOP 2025 competition instances
"""

import json
import time
import shutil
from pathlib import Path


# Copy the instances to the instances directory
def setup_competition_instances():
    """Copy the competition instances to the instances directory"""
    print("🔧 Setting up competition instances...")

    instances_dir = Path("instances")
    instances_dir.mkdir(exist_ok=True)

    # Competition instance files you uploaded
    competition_files = [
        "cgshop2025_examples_ortho_10_ff68423e.instance.json",
        "cgshop2025_examples_ortho_20_b099d1fe.instance.json",
        "cgshop2025_examples_ortho_40_e5365b34.instance.json",
        "cgshop2025_examples_ortho_60_f31194db.instance.json",
        "cgshop2025_examples_ortho_80_f9b89ad1.instance.json",
        "cgshop2025_examples_ortho_100_5b9b478f.instance.json"
    ]

    copied_count = 0
    for filename in competition_files:
        src_path = Path(filename)
        dest_path = instances_dir / filename

        if src_path.exists():
            shutil.copy2(src_path, dest_path)
            print(f"   ✅ Copied: {filename}")
            copied_count += 1
        else:
            print(f"   ❌ Not found: {filename}")

    print(f"✅ Set up {copied_count} competition instances")
    return copied_count


def run_competition_test():
    """Run the competition test"""
    import subprocess
    import sys

    print("\n🏁 Running Competition Instance Test")
    print("=" * 50)

    # Run the real instance tester
    try:
        result = subprocess.run([
            sys.executable, "real_instance_tester.py"
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Main function"""
    print("🏆 CG-SHOP 2025 Competition Instance Tester")
    print("=" * 50)

    # Setup instances
    count = setup_competition_instances()

    if count == 0:
        print("❌ No competition instances found")
        return False

    # Run test
    success = run_competition_test()

    if success:
        print("\n🎉 Competition test completed successfully!")
        print("Your solver is ready for CG-SHOP 2025 competition!")
    else:
        print("\n❌ Competition test had issues")
        print("Check the output above for details")

    return success


if __name__ == "__main__":
    main()