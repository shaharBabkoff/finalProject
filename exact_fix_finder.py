#!/usr/bin/env python3
"""
This script helps you find the exact lines to fix in decomposition.py
"""

print("🔍 Finding lines to fix in decomposition.py")
print("=" * 50)

# Read your decomposition.py file
try:
    with open("bern_eppstein_solver/decomposition.py", "r") as f:
        lines = f.readlines()

    print(f"✅ Found decomposition.py with {len(lines)} lines")

    # Find the problematic line
    problem_lines = []
    for i, line in enumerate(lines, 1):
        if "self.vertical_lines.add(vertex.x())" in line:
            problem_lines.append(i)
            print(f"❌ PROBLEM LINE {i}: {line.strip()}")

    if problem_lines:
        print(f"\n🔧 EXACT FIX NEEDED:")
        print("Replace this line:")
        print("   self.vertical_lines.add(vertex.x())")
        print("With this line:")
        print("   self.vertical_lines.add(vertex.x().exact())")

        # Show context around the problem
        for line_num in problem_lines:
            print(f"\n📍 Context around line {line_num}:")
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 2)
            for i in range(start, end):
                marker = ">>> " if i == line_num - 1 else "    "
                print(f"{marker}{i + 1:3d}: {lines[i].rstrip()}")
    else:
        print("❓ Could not find the problematic line")
        print("   The error might be somewhere else")

        # Look for any add() calls on vertical_lines
        print("\n🔍 Looking for any vertical_lines.add() calls:")
        for i, line in enumerate(lines, 1):
            if "vertical_lines.add" in line:
                print(f"   Line {i}: {line.strip()}")

except FileNotFoundError:
    print("❌ Could not find decomposition.py file")
    print("   Make sure you're running this from the right directory")
except Exception as e:
    print(f"❌ Error reading file: {e}")