#!/usr/bin/env python3
"""
Test exact arithmetic fixes for Bern & Eppstein solver.
Run this to verify the geometry fixes work properly.
"""

import sys
import traceback
from cgshop2025_pyutils.geometry import FieldNumber, Point

# Import our fixed geometry module
# You'll need to replace this with the actual import path
try:
    from bern_eppstein_solver.geometry import BernEppsteinGeometry, ExactTriangle, ExactArithmetic

    print("✅ Successfully imported fixed geometry module")
except ImportError as e:
    print(f"❌ Failed to import geometry module: {e}")
    print("Please make sure the fixed geometry.py is in the correct location")
    sys.exit(1)


def test_exact_arithmetic_basics():
    """Test basic exact arithmetic operations"""
    print("\n🔍 Testing basic exact arithmetic...")

    # Test point creation
    p1 = BernEppsteinGeometry.create_exact_point(0, 0)
    p2 = BernEppsteinGeometry.create_exact_point(1, 0)
    p3 = BernEppsteinGeometry.create_exact_point(0, 1)

    print(f"✅ Created points: {p1}, {p2}, {p3}")

    # Test exact comparisons
    zero = FieldNumber(0)
    one = FieldNumber(1)

    assert p1.x() == zero, "Point x coordinate should be exactly zero"
    assert p2.x() == one, "Point x coordinate should be exactly one"
    print("✅ Exact comparisons work correctly")


def test_angle_computation():
    """Test angle type computation with exact arithmetic"""
    print("\n🔍 Testing angle computation...")

    # Right triangle: (0,0), (1,0), (0,1)
    p1 = BernEppsteinGeometry.create_exact_point(0, 0)
    p2 = BernEppsteinGeometry.create_exact_point(1, 0)
    p3 = BernEppsteinGeometry.create_exact_point(0, 1)

    # Test angle at p1 (should be right)
    angle_type = BernEppsteinGeometry.angle_type(p2, p1, p3)
    assert angle_type == 'right', f"Expected 'right' angle, got '{angle_type}'"
    print("✅ Right angle detection works")

    # Test triangle creation
    triangle = ExactTriangle(p1, p2, p3)
    assert triangle.is_right, "Triangle should be detected as right"
    print("✅ Triangle angle detection works")


def test_orientation():
    """Test orientation computation"""
    print("\n🔍 Testing orientation computation...")

    p1 = BernEppsteinGeometry.create_exact_point(0, 0)
    p2 = BernEppsteinGeometry.create_exact_point(1, 0)
    p3 = BernEppsteinGeometry.create_exact_point(0, 1)

    # Should be counter-clockwise
    orientation = BernEppsteinGeometry.orientation(p1, p2, p3)
    assert orientation == 1, f"Expected counter-clockwise (1), got {orientation}"
    print("✅ Orientation computation works")


def test_altitude_drop():
    """Test altitude dropping with exact arithmetic"""
    print("\n🔍 Testing altitude dropping...")

    # Right triangle with obtuse angle
    apex = BernEppsteinGeometry.create_exact_point(0, 2)
    base_start = BernEppsteinGeometry.create_exact_point(0, 0)
    base_end = BernEppsteinGeometry.create_exact_point(2, 0)

    # Drop altitude
    foot = BernEppsteinGeometry.drop_altitude(apex, base_start, base_end)

    # Should be at (0, 0) since apex is directly above base_start
    expected_x = FieldNumber(0)
    expected_y = FieldNumber(0)

    assert foot.x() == expected_x, f"Expected x={expected_x}, got {foot.x()}"
    assert foot.y() == expected_y, f"Expected y={expected_y}, got {foot.y()}"
    print("✅ Altitude dropping works correctly")


def test_exact_arithmetic_helpers():
    """Test the ExactArithmetic helper class"""
    print("\n🔍 Testing ExactArithmetic helpers...")

    # Test basic constants
    zero = ExactArithmetic.zero()
    one = ExactArithmetic.one()
    two = ExactArithmetic.two()

    assert zero == FieldNumber(0), "Zero helper should return exact zero"
    assert one == FieldNumber(1), "One helper should return exact one"
    assert two == FieldNumber(2), "Two helper should return exact two"
    print("✅ ExactArithmetic constants work")

    # Test fraction creation
    half = ExactArithmetic.from_fraction(1, 2)
    expected_half = FieldNumber(1) / FieldNumber(2)
    assert half == expected_half, "Fraction helper should work correctly"
    print("✅ Fraction creation works")


def test_triangle_properties():
    """Test triangle property computation"""
    print("\n🔍 Testing triangle properties...")

    # Create a known triangle
    p1 = BernEppsteinGeometry.create_exact_point(0, 0)
    p2 = BernEppsteinGeometry.create_exact_point(1, 0)
    p3 = BernEppsteinGeometry.create_exact_point(0, 1)

    triangle = ExactTriangle(p1, p2, p3)

    # Test area calculation
    area = triangle.area()
    expected_area = FieldNumber(1) / FieldNumber(2)  # 1/2 for right triangle with legs of length 1
    assert area == expected_area, f"Expected area {expected_area}, got {area}"
    print("✅ Triangle area calculation works")

    # Test hypotenuse detection
    hypotenuse = triangle.get_hypotenuse()
    # Should be the edge from p2 to p3 (longest side)
    assert (hypotenuse[0] == p2 and hypotenuse[1] == p3) or (hypotenuse[0] == p3 and hypotenuse[1] == p2), \
        "Hypotenuse should be the longest side"
    print("✅ Hypotenuse detection works")


def main():
    """Run all tests"""
    print("🧪 Testing Exact Arithmetic Fixes for Bern & Eppstein Solver")
    print("=" * 60)

    test_functions = [
        test_exact_arithmetic_basics,
        test_angle_computation,
        test_orientation,
        test_altitude_drop,
        test_exact_arithmetic_helpers,
        test_triangle_properties
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_func.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED: {e}")
            print(f"   Traceback: {traceback.format_exc()}")

    print("\n" + "=" * 60)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Exact arithmetic fixes are working correctly.")
        print("✅ Ready to proceed to Step 2: Testing with Simple Instance")
    else:
        print("❌ Some tests failed. Please fix the issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()