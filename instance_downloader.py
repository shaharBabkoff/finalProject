#!/usr/bin/env python3
"""
CG-SHOP Instance Downloader Helper
Helps you set up test instances for your solver
"""

import os
import json
from pathlib import Path
from cgshop2025_pyutils.geometry import FieldNumber, Point
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance


def create_sample_instances():
    """Create sample instances for testing if no real ones are available"""
    print("🔧 Creating sample test instances...")

    instances_dir = Path("instances")
    instances_dir.mkdir(exist_ok=True)

    # Sample 1: Triangle
    triangle_instance = {
        "content_type": "CG_SHOP_2025_Instance",
        "instance_uid": "sample_triangle",
        "num_points": 3,
        "points_x": ["0", "3", "0"],
        "points_y": ["0", "0", "4"],
        "region_boundary": [0, 1, 2],
        "num_constraints": 0,
        "additional_constraints": []
    }

    # Sample 2: Square
    square_instance = {
        "content_type": "CG_SHOP_2025_Instance",
        "instance_uid": "sample_square",
        "num_points": 4,
        "points_x": ["0", "2", "2", "0"],
        "points_y": ["0", "0", "2", "2"],
        "region_boundary": [0, 1, 2, 3],
        "num_constraints": 0,
        "additional_constraints": []
    }

    # Sample 3: Pentagon
    pentagon_instance = {
        "content_type": "CG_SHOP_2025_Instance",
        "instance_uid": "sample_pentagon",
        "num_points": 5,
        "points_x": ["0", "2", "3", "1", "-1"],
        "points_y": ["0", "0", "2", "3", "2"],
        "region_boundary": [0, 1, 2, 3, 4],
        "num_constraints": 0,
        "additional_constraints": []
    }

    # Sample 4: Hexagon
    hexagon_instance = {
        "content_type": "CG_SHOP_2025_Instance",
        "instance_uid": "sample_hexagon",
        "num_points": 6,
        "points_x": ["0", "2", "3", "2", "0", "-1"],
        "points_y": ["0", "0", "1", "2", "2", "1"],
        "region_boundary": [0, 1, 2, 3, 4, 5],
        "num_constraints": 0,
        "additional_constraints": []
    }

    # Sample 5: Square with constraint
    constrained_square = {
        "content_type": "CG_SHOP_2025_Instance",
        "instance_uid": "sample_square_constrained",
        "num_points": 4,
        "points_x": ["0", "3", "3", "0"],
        "points_y": ["0", "0", "3", "3"],
        "region_boundary": [0, 1, 2, 3],
        "num_constraints": 1,
        "additional_constraints": [[0, 2]]  # Diagonal constraint
    }

    instances = [
        ("sample_triangle.json", triangle_instance),
        ("sample_square.json", square_instance),
        ("sample_pentagon.json", pentagon_instance),
        ("sample_hexagon.json", hexagon_instance),
        ("sample_square_constrained.json", constrained_square)
    ]

    for filename, instance_data in instances:
        filepath = instances_dir / filename
        with open(filepath, 'w') as f:
            json.dump(instance_data, f, indent=2)
        print(f"   ✅ Created: {filename}")

    print(f"\n✅ Created {len(instances)} sample instances in 'instances/' directory")
    return len(instances)


def check_for_real_instances():
    """Check if real CG-SHOP instances are available"""
    instances_dir = Path("instances")

    if not instances_dir.exists():
        return False, []

    # Look for JSON files that might be real instances
    json_files = list(instances_dir.glob("*.json"))

    # Filter out our sample instances
    real_instances = []
    for file_path in json_files:
        if not file_path.name.startswith("sample_"):
            real_instances.append(file_path)

    return len(real_instances) > 0, real_instances


def main():
    """Main setup function"""
    print("📥 CG-SHOP Instance Setup Helper")
    print("=" * 40)

    # Check for real instances
    has_real, real_files = check_for_real_instances()

    if has_real:
        print(f"✅ Found {len(real_files)} real instance files:")
        for file_path in real_files[:5]:  # Show first 5
            print(f"   - {file_path.name}")
        if len(real_files) > 5:
            print(f"   ... and {len(real_files) - 5} more")

        print("\n🚀 You're ready to test on real instances!")
        print("   Run: python real_instance_tester.py")
    else:
        print("❌ No real CG-SHOP instances found")
        print("\n📥 To get real instances:")
        print("   1. Visit: https://cgshop.ibr.cs.tu-bs.de/competition/cg-shop-2025/")
        print("   2. Download instance files")
        print("   3. Put them in 'instances/' directory")
        print("   4. Run this script again")

        print("\n🔧 For now, creating sample instances to test with...")
        count = create_sample_instances()

        print(f"\n✅ Setup complete! You can test with {count} sample instances.")
        print("   Run: python real_instance_tester.py")

    return True


if __name__ == "__main__":
    main()