# run_all_tests.py
import subprocess
import sys

tests = [
    "test_imports.py",
    "test_geometry.py",
    "test_simple_instance.py",
    "test_integration.py",
    "test_performance.py"
]

for test in tests:
    print(f"\n{'=' * 50}")
    print(f"Running {test}")
    print('=' * 50)

    try:
        result = subprocess.run([sys.executable, test],
                                capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"Error running {test}: {e}")