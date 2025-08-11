# test_cgshop_structure.py
try:
    import cgshop2025_pyutils

    print("✅ cgshop2025_pyutils package found")
    print(f"Package location: {cgshop2025_pyutils.__file__}")

    # Check what's available in the package
    print("\nAvailable modules:")
    import pkgutil

    for importer, modname, ispkg in pkgutil.iter_modules(cgshop2025_pyutils.__path__):
        print(f"  {modname}")

except ImportError as e:
    print(f"❌ cgshop2025_pyutils not found: {e}")

try:
    from cgshop2025_pyutils.geometry import FieldNumber, Point

    print("✅ FieldNumber and Point imported successfully")
except ImportError as e:
    print(f"❌ Cannot import FieldNumber/Point: {e}")