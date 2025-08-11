# test_performance.py
import time
from bern_eppstein_solver.utils import BenchmarkUtils
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance

# Create multiple test instances
instances = []
for i in range(5):
    instance = Cgshop2025Instance(
        instance_uid=f"test_{i}",
        num_points=4,
        points_x=[0, i+1, i+1, 0],
        points_y=[0, 0, i+1, i+1],
        region_boundary=[0, 1, 2, 3],
        num_constraints=0,
        additional_constraints=[]
    )
    instances.append(instance)

# Run benchmark
benchmark = BenchmarkUtils()
results = benchmark.run_benchmark(instances, {'debug': False})

print(f"Benchmark results:")
print(f"Total instances: {results['total_instances']}")
print(f"Successful: {results['successful_solves']}")
print(f"Average time: {results.get('average_solve_time', 0):.3f}s")