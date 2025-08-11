#!/usr/bin/env python3
"""
Main script for solving CG:SHOP 2025 instances using Bern & Eppstein algorithm.
This script provides a command-line interface for the solver.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent directory to path to import our solver
sys.path.append(str(Path(__file__).parent.parent))

from cgshop2025_pyutils import InstanceDatabase, verify, ZipWriter
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance

from bern_eppstein_solver import BernEppsteinSolver
from bern_eppstein_solver.utils import (
    VisualizationUtils, PerformanceProfiler, ConfigurationManager,
    FileUtils, LoggingUtils
)


def main():
    """Main entry point for the solve script"""
    parser = argparse.ArgumentParser(
        description='Solve CG:SHOP 2025 instances using Bern & Eppstein algorithm',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve single instance
  python solve_instance.py instance.json -o solution.json

  # Solve with debug output
  python solve_instance.py instance.json -o solution.json --debug

  # Solve all instances in directory
  python solve_instance.py instances/ -o solutions/ --batch

  # Solve with verification
  python solve_instance.py instance.json -o solution.json --verify

  # Solve with visualization
  python solve_instance.py instance.json -o solution.json --visualize --save-plots

  # Use adaptive strategy
  python solve_instance.py instance.json -o solution.json --adaptive

  # Benchmark mode
  python solve_instance.py instances/ --benchmark --export-benchmark results.json
        """
    )

    # Input/Output arguments
    parser.add_argument('input', help='Input instance file or directory')
    parser.add_argument('-o', '--output', help='Output solution file or directory')

    # Algorithm options
    parser.add_argument('--adaptive', action='store_true',
                       help='Use adaptive algorithm selection')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout in seconds (default: 300)')

    # Output options
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    parser.add_argument('--verify', action='store_true',
                       help='Verify solution using cgshop2025_pyutils')
    parser.add_argument('--visualize', action='store_true',
                       help='Create visualization of solution')
    parser.add_argument('--save-plots', action='store_true',
                       help='Save visualization plots to files')

    # Batch processing
    parser.add_argument('--batch', action='store_true',
                       help='Process all instances in input directory')
    parser.add_argument('--zip-output', action='store_true',
                       help='Create zip file for batch output')

    # Analysis options
    parser.add_argument('--benchmark', action='store_true',
                       help='Run benchmark analysis')
    parser.add_argument('--export-benchmark',
                       help='Export benchmark results to file')
    parser.add_argument('--profile', action='store_true',
                       help='Enable performance profiling')

    # Logging
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')

    args = parser.parse_args()

    # Setup logging
    logger = LoggingUtils(args.log_level)

    # Load configuration
    config = ConfigurationManager.get_default_config()
    if args.config:
        try:
            user_config = ConfigurationManager.load_config(args.config)
            config.update(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    # Override config with command line arguments
    config.update({
        'debug': args.debug,
        'use_adaptive': args.adaptive,
        'timeout_seconds': args.timeout,
        'visualization': {
            'enabled': args.visualize,
            'save_plots': args.save_plots
        },
        'performance': {
            'profile_enabled': args.profile
        }
    })

    # Validate configuration
    config_errors = ConfigurationManager.validate_config(config)
    if config_errors:
        print("Configuration errors:")
        for error in config_errors:
            print(f"  - {error}")
        sys.exit(1)

    # Setup profiler
    profiler = PerformanceProfiler() if args.profile else None

    try:
        if args.batch or Path(args.input).is_dir():
            # Batch processing
            results = handle_batch_processing(args, config, profiler, logger)
        else:
            # Single instance processing
            results = handle_single_instance(args, config, profiler, logger)

        # Export results if requested
        if args.export_benchmark and results:
            FileUtils.ensure_directory(Path(args.export_benchmark).parent)
            with open(args.export_benchmark, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results exported to {args.export_benchmark}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.log_error(e, "main")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Print profiling results
    if profiler:
        print("\nPerformance Profile:")
        profiler.print_timing_report()


def handle_single_instance(args, config, profiler, logger):
    """Handle single instance processing"""
    if profiler:
        profiler.start_timer("total")

    # Load instance
    if profiler:
        profiler.start_timer("load_instance")

    try:
        instance = FileUtils.load_instance_from_file(args.input)
        logger.log_solver_start(instance.instance_uid, config)
    except Exception as e:
        raise RuntimeError(f"Failed to load instance: {e}")

    if profiler:
        profiler.end_timer("load_instance")

    # Solve instance
    if profiler:
        profiler.start_timer("solve")

    solver = BernEppsteinSolver(instance, config)
    solution = solver.solve()

    if profiler:
        profiler.end_timer("solve")

    # Get quality metrics
    quality_metrics = solver.get_solution_quality()

    print(f"\nSolution Summary:")
    print(f"Instance: {instance.instance_uid}")
    print(f"Steiner points: {len(solution.steiner_points_x)}")
    print(f"Triangles: {quality_metrics.get('total_triangles', 0)}")
    print(f"Obtuse triangles: {quality_metrics.get('obtuse_triangles', 0)}")
    print(f"Feasible: {'✅' if quality_metrics.get('is_feasible', False) else '❌'}")
    print(f"Solve time: {quality_metrics.get('solve_time', 0):.3f}s")

    # Verify solution
    if args.verify:
        if profiler:
            profiler.start_timer("verify")

        try:
            result = verify(instance, solution)
            if result.errors:
                print(f"❌ Verification failed: {result.errors}")
            else:
                print(f"✅ Verification passed")
                if hasattr(result, 'num_obtuse_triangles'):
                    print(f"Obtuse triangles (verifier): {result.num_obtuse_triangles}")
        except Exception as e:
            print(f"Verification error: {e}")

        if profiler:
            profiler.end_timer("verify")

    # Save solution
    if args.output:
        if profiler:
            profiler.start_timer("save_solution")

        FileUtils.ensure_directory(Path(args.output).parent)
        FileUtils.save_solution_to_file(solution, args.output)

        if profiler:
            profiler.end_timer("save_solution")

    # Visualization
    if args.visualize:
        if profiler:
            profiler.start_timer("visualize")

        try:
            if hasattr(solver, 'triangulation') and solver.triangulation:
                # Create visualization
                title = f"Solution for {instance.instance_uid}"
                save_path = None

                if args.save_plots:
                    FileUtils.ensure_directory("plots")
                    save_path = f"plots/{instance.instance_uid}_triangulation.png"

                VisualizationUtils.plot_triangulation(
                    solver.triangulation,
                    solver.steiner_points,
                    title=title,
                    save_path=save_path
                )

                # Create quality report
                if args.save_plots:
                    quality_save_path = f"plots/{instance.instance_uid}_quality.png"
                    VisualizationUtils.create_quality_report_plot(
                        quality_metrics, quality_save_path
                    )
        except Exception as e:
            print(f"Visualization error: {e}")

        if profiler:
            profiler.end_timer("visualize")

    if profiler:
        profiler.end_timer("total")

    return {
        'instance_uid': instance.instance_uid,
        'success': True,
        'quality_metrics': quality_metrics,
        'solution': solution
    }


def handle_batch_processing(args, config, profiler, logger):
    """Handle batch processing of multiple instances"""
    if profiler:
        profiler.start_timer("total_batch")

    # Load instances
    if profiler:
        profiler.start_timer("load_instances")

    try:
        if Path(args.input).is_dir():
            instances = FileUtils.batch_load_instances(args.input)
        else:
            # Single file in batch mode
            instances = [FileUtils.load_instance_from_file(args.input)]

        print(f"Loaded {len(instances)} instances")
    except Exception as e:
        raise RuntimeError(f"Failed to load instances: {e}")

    if profiler:
        profiler.end_timer("load_instances")

    # Process instances
    if profiler:
        profiler.start_timer("solve_batch")

    solutions = []
    results = []

    for i, instance in enumerate(instances):
        print(f"\nProcessing {i+1}/{len(instances)}: {instance.instance_uid}")

        try:
            # Solve instance
            solver = BernEppsteinSolver(instance, config)
            solution = solver.solve()

            # Get metrics
            quality_metrics = solver.get_solution_quality()

            # Store results
            solutions.append(solution)
            results.append({
                'instance_uid': instance.instance_uid,
                'success': True,
                'quality_metrics': quality_metrics
            })

            # Verify if requested
            if args.verify:
                try:
                    result = verify(instance, solution)
                    if result.errors:
                        print(f"  ❌ Verification failed: {result.errors}")
                    else:
                        print(f"  ✅ Verification passed")
                except Exception as e:
                    print(f"  Verification error: {e}")

            # Print summary
            feasible = quality_metrics.get('is_feasible', False)
            print(f"  Result: {'✅' if feasible else '❌'} "
                  f"({quality_metrics.get('obtuse_triangles', 0)} obtuse, "
                  f"{len(solution.steiner_points_x)} Steiner)")

        except Exception as e:
            print(f"  ❌ Failed: {e}")

            # Create empty solution
            empty_solution = {
                "content_type": "CG_SHOP_2025_Solution",
                "instance_uid": instance.instance_uid,
                "steiner_points_x": [],
                "steiner_points_y": [],
                "edges": []
            }
            solutions.append(empty_solution)
            results.append({
                'instance_uid': instance.instance_uid,
                'success': False,
                'error': str(e)
            })

    if profiler:
        profiler.end_timer("solve_batch")

    # Save solutions
    if args.output:
        if profiler:
            profiler.start_timer("save_solutions")

        if args.zip_output or args.output.endswith('.zip'):
            # Create zip file
            zip_path = args.output if args.output.endswith('.zip') else args.output + '.zip'

            with ZipWriter(zip_path) as zw:
                for solution in solutions:
                    if isinstance(solution, dict):
                        # Convert dict to solution object
                        from cgshop2025_pyutils.data_schemas import Cgshop2025Solution
                        solution_obj = Cgshop2025Solution(**solution)
                        zw.add_solution(solution_obj)
                    else:
                        zw.add_solution(solution)

            print(f"Solutions saved to {zip_path}")
        else:
            # Save individual files
            FileUtils.ensure_directory(args.output)
            for solution in solutions:
                filename = f"{solution['instance_uid'] if isinstance(solution, dict) else solution.instance_uid}.solution.json"
                filepath = Path(args.output) / filename

                if isinstance(solution, dict):
                    with open(filepath, 'w') as f:
                        json.dump(solution, f, indent=2)
                else:
                    FileUtils.save_solution_to_file(solution, str(filepath))

        if profiler:
            profiler.end_timer("save_solutions")

    # Print batch summary
    successful = sum(1 for r in results if r['success'])
    feasible = sum(1 for r in results if r['success'] and r.get('quality_metrics', {}).get('is_feasible', False))

    print(f"\nBatch Summary:")
    print(f"Total instances: {len(instances)}")
    print(f"Successful: {successful} ({successful/len(instances)*100:.1f}%)")
    print(f"Feasible: {feasible} ({feasible/len(instances)*100:.1f}%)")

    if profiler:
        profiler.end_timer("total_batch")

    return {
        'total_instances': len(instances),
        'successful_instances': successful,
        'feasible_instances': feasible,
        'individual_results': results
    }


if __name__ == "__main__":
    main()