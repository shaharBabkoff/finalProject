"""
Utility functions for the Bern & Eppstein solver.
Includes visualization, debugging, and performance analysis tools.
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from cgshop2025_pyutils.geometry import Point, FieldNumber
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance, Cgshop2025Solution

from .geometry import ExactTriangle
from .solver import BernEppsteinSolver


class VisualizationUtils:
    """
    Utilities for visualizing triangulations and solutions
    """

    @staticmethod
    def plot_triangulation(triangulation: List[ExactTriangle],
                           steiner_points: List[Point] = None,
                           title: str = "Triangulation",
                           save_path: Optional[str] = None,
                           show_angles: bool = False):
        """
        Plot triangulation with optional Steiner points

        Args:
            triangulation: List of triangles to plot
            steiner_points: Optional Steiner points to highlight
            title: Plot title
            save_path: Optional path to save plot
            show_angles: Whether to show angle types
        """
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        # Plot triangles
        for i, triangle in enumerate(triangulation):
            # Extract coordinates
            coords = [(float(v.x().exact()), float(v.y().exact()))
                      for v in triangle.vertices]
            coords.append(coords[0])  # Close the triangle

            xs, ys = zip(*coords)

            # Color based on angle type
            if triangle.is_obtuse:
                color = 'red'
                alpha = 0.3
            elif triangle.is_right:
                color = 'blue'
                alpha = 0.3
            else:
                color = 'green'
                alpha = 0.3

            # Plot triangle
            ax.plot(xs, ys, 'k-', linewidth=1, alpha=0.8)
            ax.fill(xs, ys, color=color, alpha=alpha)

            # Optionally show triangle index
            if len(triangulation) < 50:  # Don't clutter for large triangulations
                centroid_x = sum(x for x, y in coords[:-1]) / 3
                centroid_y = sum(y for x, y in coords[:-1]) / 3
                ax.text(centroid_x, centroid_y, str(i), fontsize=8, ha='center')

        # Plot Steiner points
        if steiner_points:
            steiner_coords = [(float(p.x().exact()), float(p.y().exact()))
                              for p in steiner_points]
            if steiner_coords:
                xs, ys = zip(*steiner_coords)
                ax.scatter(xs, ys, c='red', s=50, marker='o',
                           label=f'Steiner points ({len(steiner_points)})', zorder=5)

        # Styling
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(title)

        # Legend
        legend_elements = []
        if any(t.is_obtuse for t in triangulation):
            legend_elements.append(patches.Patch(color='red', alpha=0.3, label='Obtuse'))
        if any(t.is_right for t in triangulation):
            legend_elements.append(patches.Patch(color='blue', alpha=0.3, label='Right'))
        if any(t.is_acute for t in triangulation):
            legend_elements.append(patches.Patch(color='green', alpha=0.3, label='Acute'))

        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.show()

    @staticmethod
    def plot_instance_and_solution(instance: Cgshop2025Instance,
                                   solution: Cgshop2025Solution,
                                   solver: BernEppsteinSolver,
                                   save_path: Optional[str] = None):
        """
        Plot instance and solution side by side

        Args:
            instance: Original instance
            solution: Solution to plot
            solver: Solver used (for accessing triangulation)
            save_path: Optional path to save plot
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Plot original instance
        VisualizationUtils._plot_instance(instance, ax1, "Original Instance")

        # Plot solution
        if hasattr(solver, 'triangulation') and solver.triangulation:
            VisualizationUtils._plot_solution_on_axis(
                solver.triangulation, solver.steiner_points, ax2, "Solution"
            )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.show()

    @staticmethod
    def _plot_instance(instance: Cgshop2025Instance, ax, title: str):
        """Plot instance on given axis"""
        # Plot boundary
        boundary_coords = [(instance.points_x[i], instance.points_y[i])
                           for i in instance.region_boundary]
        boundary_coords.append(boundary_coords[0])  # Close polygon

        xs, ys = zip(*boundary_coords)
        ax.plot(xs, ys, 'k-', linewidth=2, label='Boundary')

        # Plot constraints
        for constraint in instance.additional_constraints:
            if len(constraint) == 2:
                x1, y1 = instance.points_x[constraint[0]], instance.points_y[constraint[0]]
                x2, y2 = instance.points_x[constraint[1]], instance.points_y[constraint[1]]
                ax.plot([x1, x2], [y1, y2], 'r--', linewidth=1.5, alpha=0.7, label='Constraint')

        # Plot all points
        ax.scatter(instance.points_x, instance.points_y, c='blue', s=30, zorder=5, label='Points')

        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(title)
        ax.legend()

    @staticmethod
    def _plot_solution_on_axis(triangulation: List[ExactTriangle],
                               steiner_points: List[Point],
                               ax, title: str):
        """Plot solution on given axis"""
        # Plot triangles
        for triangle in triangulation:
            coords = [(float(v.x().exact()), float(v.y().exact()))
                      for v in triangle.vertices]
            coords.append(coords[0])  # Close triangle

            xs, ys = zip(*coords)

            # Color based on angle type
            if triangle.is_obtuse:
                color = 'red'
                alpha = 0.3
            elif triangle.is_right:
                color = 'blue'
                alpha = 0.3
            else:
                color = 'green'
                alpha = 0.3

            ax.plot(xs, ys, 'k-', linewidth=1, alpha=0.8)
            ax.fill(xs, ys, color=color, alpha=alpha)

        # Plot Steiner points
        if steiner_points:
            steiner_coords = [(float(p.x().exact()), float(p.y().exact()))
                              for p in steiner_points]
            if steiner_coords:
                xs, ys = zip(*steiner_coords)
                ax.scatter(xs, ys, c='red', s=50, marker='o', zorder=5)

        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(title)

    @staticmethod
    def create_quality_report_plot(quality_metrics: Dict[str, Any],
                                   save_path: Optional[str] = None):
        """
        Create a plot showing quality metrics

        Args:
            quality_metrics: Quality metrics dictionary
            save_path: Optional path to save plot
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

        # Triangle type distribution
        triangle_types = ['Obtuse', 'Right', 'Acute']
        triangle_counts = [
            quality_metrics.get('obtuse_triangles', 0),
            quality_metrics.get('right_triangles', 0),
            quality_metrics.get('acute_triangles', 0)
        ]
        colors = ['red', 'blue', 'green']

        ax1.pie(triangle_counts, labels=triangle_types, colors=colors, autopct='%1.1f%%')
        ax1.set_title('Triangle Type Distribution')

        # Steiner points vs triangles
        metrics_names = ['Steiner Points', 'Triangles']
        metrics_values = [
            quality_metrics.get('steiner_points_count', 0),
            quality_metrics.get('total_triangles', 0)
        ]

        ax2.bar(metrics_names, metrics_values, color=['orange', 'purple'])
        ax2.set_title('Points and Triangles')
        ax2.set_ylabel('Count')

        # Quality metrics
        quality_names = ['Obtuse %', 'Feasible', 'Efficiency']
        quality_values = [
            quality_metrics.get('obtuse_percentage', 0),
            100 if quality_metrics.get('is_feasible', False) else 0,
            quality_metrics.get('steiner_efficiency', 0)
        ]

        ax3.bar(quality_names, quality_values, color=['red', 'green', 'blue'])
        ax3.set_title('Quality Metrics')
        ax3.set_ylabel('Value')

        # Algorithm statistics
        if 'solve_time' in quality_metrics:
            alg_names = ['Solve Time (s)', 'Regions', 'Mergers']
            alg_values = [
                quality_metrics.get('solve_time', 0),
                quality_metrics.get('regions_processed', 0),
                quality_metrics.get('merger_operations', 0)
            ]

            ax4.bar(alg_names, alg_values, color=['cyan', 'magenta', 'yellow'])
            ax4.set_title('Algorithm Statistics')
            ax4.set_ylabel('Count')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.show()


class PerformanceProfiler:
    """
    Performance profiling utilities for the solver
    """

    def __init__(self):
        self.timings = {}
        self.start_times = {}

    def start_timer(self, name: str):
        """Start timing an operation"""
        self.start_times[name] = time.time()

    def end_timer(self, name: str) -> float:
        """End timing an operation and return elapsed time"""
        if name in self.start_times:
            elapsed = time.time() - self.start_times[name]
            self.timings[name] = elapsed
            del self.start_times[name]
            return elapsed
        return 0.0

    def get_timing_summary(self) -> Dict[str, float]:
        """Get summary of all timings"""
        return self.timings.copy()

    def print_timing_report(self):
        """Print timing report"""
        print("Performance Timing Report:")
        print("-" * 40)

        total_time = sum(self.timings.values())

        for name, time_taken in sorted(self.timings.items(), key=lambda x: x[1], reverse=True):
            percentage = (time_taken / total_time * 100) if total_time > 0 else 0
            print(f"{name:25s}: {time_taken:8.3f}s ({percentage:5.1f}%)")

        print("-" * 40)
        print(f"{'Total':25s}: {total_time:8.3f}s")


class DebugUtils:
    """
    Debugging utilities for the solver
    """

    @staticmethod
    def export_debug_triangulation(triangulation: List[ExactTriangle],
                                   steiner_points: List[Point],
                                   filepath: str):
        """
        Export detailed triangulation data for debugging

        Args:
            triangulation: List of triangles
            steiner_points: List of Steiner points
            filepath: Path to export file
        """
        debug_data = {
            'triangles': [],
            'steiner_points': [],
            'statistics': {
                'total_triangles': len(triangulation),
                'obtuse_triangles': sum(1 for t in triangulation if t.is_obtuse),
                'right_triangles': sum(1 for t in triangulation if t.is_right),
                'acute_triangles': sum(1 for t in triangulation if t.is_acute),
                'total_steiner_points': len(steiner_points)
            }
        }

        # Export triangles
        for i, triangle in enumerate(triangulation):
            triangle_data = {
                'index': i,
                'vertices': [
                    {'x': v.x().exact(), 'y': v.y().exact()}
                    for v in triangle.vertices
                ],
                'properties': {
                    'is_obtuse': triangle.is_obtuse,
                    'is_right': triangle.is_right,
                    'is_acute': triangle.is_acute,
                    'area': triangle.area().exact()
                }
            }
            debug_data['triangles'].append(triangle_data)

        # Export Steiner points
        for i, point in enumerate(steiner_points):
            point_data = {
                'index': i,
                'x': point.x().exact(),
                'y': point.y().exact()
            }
            debug_data['steiner_points'].append(point_data)

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(debug_data, f, indent=2)

        print(f"Debug data exported to {filepath}")

    @staticmethod
    def validate_triangulation_integrity(triangulation: List[ExactTriangle]) -> List[str]:
        """
        Validate triangulation for common issues

        Args:
            triangulation: List of triangles to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check for degenerate triangles
        for i, triangle in enumerate(triangulation):
            if triangle.area() <= FieldNumber(0):
                errors.append(f"Triangle {i} is degenerate (area = {triangle.area().exact()})")

        # Check for duplicate triangles
        triangle_signatures = set()
        for i, triangle in enumerate(triangulation):
            # Create signature from sorted vertex coordinates
            signature = tuple(sorted(
                (v.x().exact(), v.y().exact()) for v in triangle.vertices
            ))

            if signature in triangle_signatures:
                errors.append(f"Triangle {i} is duplicate")
            triangle_signatures.add(signature)

        return errors

    @staticmethod
    def analyze_angle_distribution(triangulation: List[ExactTriangle]) -> Dict[str, Any]:
        """
        Analyze the distribution of angles in triangulation

        Args:
            triangulation: List of triangles

        Returns:
            Dictionary with angle analysis
        """
        angle_stats = {
            'total_angles': len(triangulation) * 3,
            'acute_angles': 0,
            'right_angles': 0,
            'obtuse_angles': 0,
            'angle_distribution': []
        }

        for triangle in triangulation:
            triangle._compute_angles()  # Ensure angles are computed

            for angle_type in triangle._angle_types:
                angle_stats[f'{angle_type}_angles'] += 1

        # Calculate percentages
        total = angle_stats['total_angles']
        angle_stats['acute_percentage'] = angle_stats['acute_angles'] / total * 100
        angle_stats['right_percentage'] = angle_stats['right_angles'] / total * 100
        angle_stats['obtuse_percentage'] = angle_stats['obtuse_angles'] / total * 100

        return angle_stats


class ConfigurationManager:
    """
    Manage solver configurations
    """

    @staticmethod
    def load_config(filepath: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file

        Args:
            filepath: Path to configuration file

        Returns:
            Configuration dictionary
        """
        with open(filepath, 'r') as f:
            config = json.load(f)

        return config

    @staticmethod
    def save_config(config: Dict[str, Any], filepath: str):
        """
        Save configuration to JSON file

        Args:
            config: Configuration dictionary
            filepath: Path to save file
        """
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Configuration saved to {filepath}")

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get default solver configuration

        Returns:
            Default configuration dictionary
        """
        return {
            'debug': False,
            'use_adaptive': False,
            'optimize_result': True,
            'max_steiner_points': None,
            'timeout_seconds': 300,
            'visualization': {
                'enabled': False,
                'save_plots': False,
                'plot_directory': './plots'
            },
            'performance': {
                'profile_enabled': False,
                'export_debug_data': False,
                'debug_directory': './debug'
            }
        }

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration parameters

        Args:
            config: Configuration to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check required fields
        if 'debug' not in config:
            errors.append("Missing 'debug' field in configuration")

        # Check types
        if not isinstance(config.get('debug'), bool):
            errors.append("'debug' must be a boolean")

        if 'max_steiner_points' in config:
            max_points = config['max_steiner_points']
            if max_points is not None and (not isinstance(max_points, int) or max_points <= 0):
                errors.append("'max_steiner_points' must be a positive integer or None")

        if 'timeout_seconds' in config:
            timeout = config['timeout_seconds']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("'timeout_seconds' must be a positive number")

        return errors


class BenchmarkUtils:
    """
    Utilities for benchmarking solver performance
    """

    def __init__(self):
        self.benchmark_results = []

    def run_benchmark(self, instances: List[Cgshop2025Instance],
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run benchmark on multiple instances

        Args:
            instances: List of instances to benchmark
            config: Optional solver configuration

        Returns:
            Benchmark results
        """
        results = {
            'total_instances': len(instances),
            'successful_solves': 0,
            'failed_solves': 0,
            'total_time': 0.0,
            'individual_results': []
        }

        profiler = PerformanceProfiler()

        for i, instance in enumerate(instances):
            print(f"Benchmarking instance {i + 1}/{len(instances)}: {instance.instance_uid}")

            profiler.start_timer(f"instance_{i}")

            try:
                solver = BernEppsteinSolver(instance, config)
                solution = solver.solve()

                solve_time = profiler.end_timer(f"instance_{i}")

                quality_metrics = solver.get_solution_quality()

                instance_result = {
                    'instance_uid': instance.instance_uid,
                    'success': True,
                    'solve_time': solve_time,
                    'steiner_points': len(solution.steiner_points_x),
                    'triangles': quality_metrics.get('total_triangles', 0),
                    'obtuse_triangles': quality_metrics.get('obtuse_triangles', 0),
                    'is_feasible': quality_metrics.get('is_feasible', False)
                }

                results['successful_solves'] += 1
                results['total_time'] += solve_time

            except Exception as e:
                solve_time = profiler.end_timer(f"instance_{i}")

                instance_result = {
                    'instance_uid': instance.instance_uid,
                    'success': False,
                    'solve_time': solve_time,
                    'error': str(e)
                }

                results['failed_solves'] += 1
                results['total_time'] += solve_time

            results['individual_results'].append(instance_result)

        # Calculate aggregate statistics
        successful_results = [r for r in results['individual_results'] if r['success']]

        if successful_results:
            results['average_solve_time'] = sum(r['solve_time'] for r in successful_results) / len(successful_results)
            results['average_steiner_points'] = sum(r['steiner_points'] for r in successful_results) / len(
                successful_results)
            results['average_triangles'] = sum(r['triangles'] for r in successful_results) / len(successful_results)
            results['feasible_solutions'] = sum(1 for r in successful_results if r['is_feasible'])
            results['feasible_rate'] = results['feasible_solutions'] / len(successful_results) * 100

        return results

    def export_benchmark_results(self, results: Dict[str, Any], filepath: str):
        """
        Export benchmark results to JSON file

        Args:
            results: Benchmark results
            filepath: Path to export file
        """
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Benchmark results exported to {filepath}")

    def create_benchmark_report(self, results: Dict[str, Any]) -> str:
        """
        Create human-readable benchmark report

        Args:
            results: Benchmark results

        Returns:
            Formatted report string
        """
        report_lines = [
            "Benchmark Results Report",
            "=" * 50,
            f"Total instances: {results['total_instances']}",
            f"Successful solves: {results['successful_solves']}",
            f"Failed solves: {results['failed_solves']}",
            f"Success rate: {results['successful_solves'] / results['total_instances'] * 100:.1f}%",
            f"Total time: {results['total_time']:.2f} seconds",
            ""
        ]

        if results['successful_solves'] > 0:
            report_lines.extend([
                "Average Performance:",
                f"  Solve time: {results.get('average_solve_time', 0):.3f} seconds",
                f"  Steiner points: {results.get('average_steiner_points', 0):.1f}",
                f"  Triangles: {results.get('average_triangles', 0):.1f}",
                f"  Feasible solutions: {results.get('feasible_solutions', 0)} ({results.get('feasible_rate', 0):.1f}%)",
                ""
            ])

        # Add individual results summary
        report_lines.append("Individual Results:")
        for result in results['individual_results']:
            if result['success']:
                feasible_str = "✅" if result['is_feasible'] else "❌"
                report_lines.append(
                    f"  {result['instance_uid']}: {result['solve_time']:.3f}s, "
                    f"{result['steiner_points']} Steiner, "
                    f"{result['obtuse_triangles']} obtuse {feasible_str}"
                )
            else:
                report_lines.append(f"  {result['instance_uid']}: FAILED - {result['error']}")

        return "\n".join(report_lines)


class FileUtils:
    """
    File handling utilities
    """

    @staticmethod
    def ensure_directory(directory: str):
        """
        Ensure directory exists, create if it doesn't

        Args:
            directory: Directory path
        """
        Path(directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_unique_filename(base_path: str, extension: str = "") -> str:
        """
        Get unique filename by adding number suffix if file exists

        Args:
            base_path: Base path without extension
            extension: File extension (with or without dot)

        Returns:
            Unique filename
        """
        if not extension.startswith('.') and extension:
            extension = '.' + extension

        filepath = base_path + extension
        counter = 1

        while Path(filepath).exists():
            filepath = f"{base_path}_{counter}{extension}"
            counter += 1

        return filepath

    @staticmethod
    def load_instance_from_file(filepath: str) -> Cgshop2025Instance:
        """
        Load instance from JSON file

        Args:
            filepath: Path to instance file

        Returns:
            Loaded instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        return Cgshop2025Instance(**data)

    @staticmethod
    def save_solution_to_file(solution: Cgshop2025Solution, filepath: str):
        """
        Save solution to JSON file

        Args:
            solution: Solution to save
            filepath: Path to save file
        """
        solution_dict = {
            "content_type": solution.content_type,
            "instance_uid": solution.instance_uid,
            "steiner_points_x": solution.steiner_points_x,
            "steiner_points_y": solution.steiner_points_y,
            "edges": solution.edges
        }

        with open(filepath, 'w') as f:
            json.dump(solution_dict, f, indent=2)

        print(f"Solution saved to {filepath}")

    @staticmethod
    def batch_load_instances(directory: str) -> List[Cgshop2025Instance]:
        """
        Load all instances from directory

        Args:
            directory: Directory containing instance files

        Returns:
            List of loaded instances
        """
        instances = []
        instance_dir = Path(directory)

        for filepath in instance_dir.glob("*.json"):
            try:
                instance = FileUtils.load_instance_from_file(str(filepath))
                instances.append(instance)
            except Exception as e:
                print(f"Failed to load {filepath}: {e}")

        return instances

    @staticmethod
    def batch_save_solutions(solutions: List[Cgshop2025Solution], directory: str):
        """
        Save multiple solutions to directory

        Args:
            solutions: List of solutions to save
            directory: Directory to save solutions
        """
        FileUtils.ensure_directory(directory)

        for solution in solutions:
            filename = f"{solution.instance_uid}.solution.json"
            filepath = Path(directory) / filename
            FileUtils.save_solution_to_file(solution, str(filepath))


class LoggingUtils:
    """
    Logging utilities for detailed debugging
    """

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize logging

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        import logging

        self.logger = logging.getLogger("BernEppsteinSolver")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Create console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_solver_start(self, instance_uid: str, config: Dict[str, Any]):
        """Log solver start"""
        self.logger.info(f"Starting solver for instance {instance_uid}")
        self.logger.debug(f"Configuration: {config}")

    def log_decomposition_result(self, regions_count: int, region_types: Dict[str, int]):
        """Log decomposition results"""
        self.logger.info(f"Decomposition created {regions_count} regions")
        self.logger.debug(f"Region types: {region_types}")

    def log_triangulation_result(self, triangles_count: int, steiner_points: int, obtuse_count: int):
        """Log triangulation results"""
        self.logger.info(f"Triangulation: {triangles_count} triangles, {steiner_points} Steiner points")
        if obtuse_count > 0:
            self.logger.warning(f"Solution has {obtuse_count} obtuse triangles")
        else:
            self.logger.info("✅ Feasible solution (no obtuse triangles)")

    def log_error(self, error: Exception, context: str = ""):
        """Log error with context"""
        self.logger.error(f"Error in {context}: {str(error)}")
        self.logger.debug(f"Error details: {error}", exc_info=True)

    def log_performance(self, operation: str, time_taken: float):
        """Log performance metrics"""
        self.logger.debug(f"Performance: {operation} took {time_taken:.3f} seconds")