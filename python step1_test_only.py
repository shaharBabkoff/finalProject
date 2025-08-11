#!/usr/bin/env python3
"""
STEP 1 TEST ONLY - Test exact arithmetic fixes
Run this after replacing geometry.py with the fixed version
"""

print("🔧 Step 1: Testing Exact Arithmetic Fixes")
print("=" * 50)

# Test 1: Import cgshop2025_pyutils
try:
    from cgshop2025_pyutils.geometry import FieldNumber, Point
    print("✅ 1. cgshop2025_pyutils imports work")
except ImportError as e:
    print(f"❌ 1. cgshop2025_pyutils import failed: {e}")
    print("   → Install with: pip install cgshop2025_pyutils")
    exit(1)

# Test 2: Import your fixed geometry module
try:
    from bern_eppstein_solver.geometry import BernEppsteinGeometry, ExactTriangle
    print("✅ 2. Your geometry module imports work")
except ImportError as e:
    print(f"❌ 2. Your geometry module import failed: {e}")
    print("   → Make sure you replaced geometry.py with the fixed version")
    exit(1)

# Test 3: Create exact points
try:
    p1 = BernEppsteinGeometry.create_exact_point(0, 0)
    p2 = BernEppsteinGeometry.create_exact_point(1, 0)
    p3 = BernEppsteinGeometry.create_exact_point(0, 1)
    print("✅ 3. Exact point creation works")
except Exception as e:
    print(f"❌ 3. Point creation failed: {e}")
    exit(1)

# Test 4: Test exact arithmetic
try:
    # Test angle computation
    angle = BernEppsteinGeometry.angle_type(p2, p1, p3)
    if angle == 'right':
        print("✅ 4. Angle computation works (detected right angle)")
    else:
        print(f"❌ 4. Angle computation failed: expected 'right', got '{angle}'")
        exit(1)
except Exception as e:
    print(f"❌ 4. Angle computation failed: {e}")
    exit(1)

# Test 5: Triangle creation
try:
    triangle = ExactTriangle(p1, p2, p3)
    if triangle.is_right:
        print("✅ 5. Triangle creation works (detected right triangle)")
    else:
        print("❌ 5. Triangle creation failed (should be right triangle)")
        exit(1)
except Exception as e:
    print(f"❌ 5. Triangle creation failed: {e}")
    exit(1)

print("\n🎉 Step 1 COMPLETE - Exact arithmetic is working!")
print("✅ Ready for Step 2: Test basic solver functionality")