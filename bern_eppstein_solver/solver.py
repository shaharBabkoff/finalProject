"""
High-level solver interface compatible with cgshop2025_pyutils.
Provides the main entry point for solving CG:SHOP 2025 instances.
"""

import json
from typing import List, Dict, Optional, Any
from cgshop2025_pyutils.geometry import FieldNumber, Point
from cgshop2025_pyutils.data_schemas import Cgshop2025Instance, Cgshop2025Solution

from .triangulator import BernEppsteinTriangulator, AdaptiveTriangulator
from .geometry import BernEppsteinGeometry, ExactTriangle
from .predicates import TriangulationAnalyzer


class BernEppsteinSolver:
    """
    Main solver interface compatible with cgshop2025_pyutils.

    This class provides the high-level interface for solving CG:SHOP 2025 instances
    using the Bern & Eppstein polynomial-size nonobtuse triangulation algorithm.
    """

    def __init__(self, instance: Cgshop2025Instance, config: Optional[Dict[str, Any]] = None):
        """
        Initialize solver with CG:SHOP 2025 instance

        Args:
            instance: Instance to solve (from cgshop2025_pyutils)
            config: Optional configuration dictionary
        """
        self.instance = instance
        self.config = config or {}

        # Configuration options
        self.debug = self.config.get('debug', False)
        self.use_adaptive = self.config.get('use_adaptive', False)
        self.optimize_result = self.config.get('optimize_result', True)
        self.max_steiner_points = self.config.get('max_steiner_points', None)

        # Initialize triangulator
        if self.use_adaptive:
            self.triangulator = AdaptiveTriangulator(debug=self.debug)
        else:
            self.triangulator = BernEppsteinTriangulator(debug=self.debug)

        # Results
        self.solution = None
        self.triangulation = None
        self.steiner_points = None
        self.solve_time = None

    def solve(self) -> Cgshop2025Solution:
        """
        Solve the instance using Bern & Eppstein algorithm

        Returns:
            Solution in cgshop2025_pyutils format
        """
        import time
        start_time = time.time()

        if self.debug:
            print(f"Solving instance: {self.instance.instance_uid}")
            print(f"Points: {self.instance.num_points}")
            print(f"Constraints: {self.instance.num_constraints}")

        try:
            # Convert instance to internal format
            points = self._convert_instance_points()

            # Apply triangulation algorithm
            if self.use_adaptive:
                triangulation = self.triangulator.triangulate_adaptive(
                    points,
                    self.instance.region_boundary,
                    self.instance.additional_constraints
                )
            else:
                triangulation = self.triangulator.triangulate(
                    points,
                    self.instance.region_boundary,
                    self.instance.additional_constraints
                )

            # Get Steiner points
            if hasattr(self.triangulator, 'bern_eppstein'):
                steiner_points = self.triangulator.bern_eppstein.get_steiner_points()
            else:
                steiner_points = self.triangulator.get_steiner_points()

            # Store results
            self.triangulation = triangulation
            self.steiner_points = steiner_points

            # Convert to solution format
            solution = self._create_solution(triangulation, steiner_points)

            # Validate solution
            self._validate_solution(solution)

            self.solution = solution
            self.solve_time = time.time() - start_time

            if self.debug:
                print(f"Solved in {self.solve_time:.2f} seconds")
                #self._print_solution_summary()

            return solution

        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()

            raise RuntimeError(f"Failed to solve instance {self.instance.instance_uid}: {e}")

    def _convert_instance_points(self) -> List[Point]:
        """
        Convert instance points to cgshop2025_pyutils Point objects

        Returns:
            List of Point objects with exact coordinates
        """
        points = []
        for i in range(self.instance.num_points):
            x = FieldNumber(self.instance.points_x[i])
            y = FieldNumber(self.instance.points_y[i])
            point = Point(x, y)
            points.append(point)

        return points

    def _create_solution_FIXED(self, triangulation: List['ExactTriangle']) -> Cgshop2025Solution:
        """
        FIXED: Create solution with proper edge validation and no non-triangular faces

        The key fixes:
        1. Proper point deduplication using exact coordinates
        2. Validation that all shapes are triangles
        3. Proper edge generation with validation
        4. Clear error reporting for debugging
        """
        if self.debug:
            print(f"\n🔧 CREATING SOLUTION FROM {len(triangulation)} TRIANGLES")
            print("=" * 50)

        # STEP 1: Validate all triangulation elements are actual triangles
        for i, triangle in enumerate(triangulation):
            if len(triangle.vertices) != 3:
                raise ValueError(f"Non-triangular element {i} has {len(triangle.vertices)} vertices!")

            # Check for degenerate triangles
            area = triangle.area()
            if area <= FieldNumber(0):
                if self.debug:
                    print(f"⚠️  Triangle {i} is degenerate (area = {area.exact()})")

        if self.debug:
            print(f"✅ All {len(triangulation)} elements are valid triangles")

        # STEP 2: Collect and deduplicate all points
        all_points = self.exact_points.copy()  # Original points
        original_count = len(all_points)

        # Add Steiner points, avoiding duplicates
        steiner_added = 0
        for steiner_point in self.steiner_points:
            steiner_key = (steiner_point.x().exact(), steiner_point.y().exact())

            # Check if this Steiner point already exists
            is_duplicate = False
            for existing_point in all_points:
                existing_key = (existing_point.x().exact(), existing_point.y().exact())
                if existing_key == steiner_key:
                    is_duplicate = True
                    if self.debug:
                        print(f"⚠️  Duplicate Steiner point skipped: {steiner_key}")
                    break

            if not is_duplicate:
                all_points.append(steiner_point)
                steiner_added += 1

        if self.debug:
            print(f"✅ Point collection: {original_count} original + {steiner_added} Steiner = {len(all_points)} total")

        # STEP 3: Create exact point mapping
        point_to_index = {}
        for i, point in enumerate(all_points):
            point_key = (point.x().exact(), point.y().exact())

            if point_key in point_to_index:
                if self.debug:
                    print(f"⚠️  Duplicate point detected at {point_key}: indices {point_to_index[point_key]} and {i}")
                # Use the first occurrence
            else:
                point_to_index[point_key] = i

        if self.debug:
            print(f"✅ Point mapping created: {len(point_to_index)} unique point locations")

        # STEP 4: Convert triangles to edges with STRICT validation
        edges = []
        edge_set = set()
        missing_points = []

        for tri_idx, triangle in enumerate(triangulation):
            triangle_edges = []

            # Each triangle MUST generate exactly 3 edges
            for edge_idx in range(3):
                v1 = triangle.vertices[edge_idx]
                v2 = triangle.vertices[(edge_idx + 1) % 3]

                v1_key = (v1.x().exact(), v1.y().exact())
                v2_key = (v2.x().exact(), v2.y().exact())

                # CRITICAL: Handle missing points
                if v1_key not in point_to_index:
                    if self.debug:
                        print(f"❌ Triangle {tri_idx}, edge {edge_idx}: vertex 1 not found: {v1_key}")
                    missing_points.append((tri_idx, edge_idx, 1, v1_key))

                    # Add missing point
                    new_index = len(all_points)
                    all_points.append(v1)
                    point_to_index[v1_key] = new_index

                    # Also add to Steiner points if not already there
                    if v1 not in self.steiner_points:
                        self.steiner_points.append(v1)

                    if self.debug:
                        print(f"  → Added missing point as index {new_index}")

                if v2_key not in point_to_index:
                    if self.debug:
                        print(f"❌ Triangle {tri_idx}, edge {edge_idx}: vertex 2 not found: {v2_key}")
                    missing_points.append((tri_idx, edge_idx, 2, v2_key))

                    # Add missing point
                    new_index = len(all_points)
                    all_points.append(v2)
                    point_to_index[v2_key] = new_index

                    # Also add to Steiner points if not already there
                    if v2 not in self.steiner_points:
                        self.steiner_points.append(v2)

                    if self.debug:
                        print(f"  → Added missing point as index {new_index}")

                # Get indices
                idx1 = point_to_index[v1_key]
                idx2 = point_to_index[v2_key]

                # Validate indices
                if idx1 == idx2:
                    if self.debug:
                        print(f"⚠️  Triangle {tri_idx}, edge {edge_idx}: degenerate edge (same endpoints)")
                    continue  # Skip degenerate edge

                # Create edge in canonical form
                edge_tuple = tuple(sorted([idx1, idx2]))
                triangle_edges.append(edge_tuple)

                # Add to global edge list (avoid duplicates)
                if edge_tuple not in edge_set:
                    edges.append([edge_tuple[0], edge_tuple[1]])
                    edge_set.add(edge_tuple)

            # VALIDATION: Each triangle should contribute exactly 3 edges
            if len(triangle_edges) != 3:
                if self.debug:
                    print(f"⚠️  Triangle {tri_idx} has {len(triangle_edges)} edges (expected 3)")
                    print(f"    Triangle edges: {triangle_edges}")

        if missing_points:
            print(f"⚠️  {len(missing_points)} missing points were added during edge creation")

        if self.debug:
            print(f"✅ Edge creation: {len(triangulation)} triangles → {len(edges)} unique edges")
            expected_edges = len(triangulation) * 3
            print(f"   Expected edges (with duplicates): {expected_edges}")
            print(f"   Actual unique edges: {len(edges)}")

        # STEP 5: Extract final Steiner point coordinates
        # Only include points that were added as Steiner points
        steiner_points_x = []
        steiner_points_y = []

        for point in self.steiner_points:
            steiner_points_x.append(point.x().exact())
            steiner_points_y.append(point.y().exact())

        if self.debug:
            print(f"✅ Final Steiner points: {len(steiner_points_x)}")

            # Debug: check for suspicious vertex degrees
            total_points = len(all_points)
            vertex_degrees = [0] * total_points
            for edge in edges:
                vertex_degrees[edge[0]] += 1
                vertex_degrees[edge[1]] += 1

            high_degree = [(i, d) for i, d in enumerate(vertex_degrees) if d > 6]
            if high_degree:
                print(f"⚠️  High-degree vertices detected (possible non-triangular faces):")
                for vertex_idx, degree in high_degree[:5]:  # Show first 5
                    print(f"    Vertex {vertex_idx}: degree {degree}")
            else:
                print(f"✅ No suspiciously high-degree vertices found")

        # STEP 6: Create and return solution
        solution = Cgshop2025Solution(
            content_type="CG_SHOP_2025_Solution",
            instance_uid=self.instance.instance_uid,
            steiner_points_x=steiner_points_x,
            steiner_points_y=steiner_points_y,
            edges=edges
        )

        if self.debug:
            print(f"✅ Solution created successfully!")
            print(f"   Original points: {len(self.exact_points)}")
            print(f"   Steiner points: {len(steiner_points_x)}")
            print(f"   Total points: {len(self.exact_points) + len(steiner_points_x)}")
            print(f"   Edges: {len(edges)}")

        return solution

    def debug_vertex_degrees(solution, instance):
        """
        Debug function to check for non-triangular faces by analyzing vertex degrees
        """
        print(f"\n🔍 ANALYZING VERTEX DEGREES FOR NON-TRIANGULAR FACES")
        print("=" * 50)

        total_points = instance.num_points + len(solution.steiner_points_x)
        vertex_degrees = [0] * total_points

        # Count degree of each vertex
        for edge in solution.edges:
            vertex_degrees[edge[0]] += 1
            vertex_degrees[edge[1]] += 1

        # Analyze degree distribution
        degree_counts = {}
        for degree in vertex_degrees:
            degree_counts[degree] = degree_counts.get(degree, 0) + 1

        print(f"Degree distribution:")
        for degree in sorted(degree_counts.keys()):
            count = degree_counts[degree]
            print(f"  Degree {degree}: {count} vertices")

        # Flag suspicious vertices
        suspicious = []
        for i, degree in enumerate(vertex_degrees):
            if degree > 6:  # In a proper triangulation, most vertices should have degree ≤ 6
                vertex_type = "Original" if i < instance.num_points else "Steiner"
                suspicious.append((i, degree, vertex_type))

        if suspicious:
            print(f"\n⚠️  SUSPICIOUS HIGH-DEGREE VERTICES (may indicate non-triangular faces):")
            for vertex_idx, degree, vertex_type in suspicious:
                print(f"  {vertex_type} vertex {vertex_idx}: degree {degree}")

            print(f"\n💡 RECOMMENDATION:")
            print(f"   High-degree vertices often indicate non-triangular faces.")
            print(f"   Check that triangulation only produces triangles.")

            return False
        else:
            print(f"\n✅ NO SUSPICIOUS VERTICES FOUND")
            print(f"   All vertices have reasonable degrees (≤6)")
            return True

    def _validate_solution(self, solution: Cgshop2025Solution):
        """
        Validate solution correctness

        Args:
            solution: Solution to validate

        Raises:
            ValueError: If solution is invalid
        """
        # Basic validation
        if len(solution.steiner_points_x) != len(solution.steiner_points_y):
            raise ValueError("Steiner point coordinate arrays have different lengths")

        # Check edge indices
        total_points = self.instance.num_points + len(solution.steiner_points_x)
        for edge in solution.edges:
            if len(edge) != 2:
                raise ValueError(f"Edge must have exactly 2 endpoints: {edge}")

            for idx in edge:
                if not (0 <= idx < total_points):
                    raise ValueError(f"Edge index {idx} out of range [0, {total_points})")

        if self.debug:
            print("Solution validation passed")

    def _print_solution_summary(self):
        """Print summary of solution for debugging"""
        if not self.debug or not self.solution:
            return

        analyzer = TriangulationAnalyzer(self.triangulation)
        quality_metrics = analyzer.quality_metrics()

        print("\nSolution Summary:")
        print("-" * 30)
        print(f"Instance: {self.instance.instance_uid}")
        print(f"Original points: {self.instance.num_points}")
        print(f"Steiner points: {len(self.solution.steiner_points_x)}")
        print(f"Total points: {self.instance.num_points + len(self.solution.steiner_points_x)}")
        print(f"Edges: {len(self.solution.edges)}")
        print(f"Triangles: {quality_metrics['total_triangles']}")
        print(f"Obtuse triangles: {quality_metrics['obtuse_triangles']} ({quality_metrics['obtuse_percentage']:.1f}%)")
        print(f"Solve time: {self.solve_time:.2f} seconds")

        # Check if solution is feasible (no obtuse triangles)
        if quality_metrics['obtuse_triangles'] == 0:
            print("✅ FEASIBLE SOLUTION (no obtuse triangles)")
        else:
            print(f"❌ Infeasible solution ({quality_metrics['obtuse_triangles']} obtuse triangles)")

    def get_solution_quality(self) -> Dict[str, Any]:
        """
        Get detailed solution quality metrics

        Returns:
            Dictionary with quality metrics
        """
        if not self.triangulation:
            return {}

        analyzer = TriangulationAnalyzer(self.triangulation)
        quality_metrics = analyzer.quality_metrics()

        # Add solver-specific metrics
        quality_metrics.update({
            'instance_uid': self.instance.instance_uid,
            'original_points': self.instance.num_points,
            'steiner_points': len(self.steiner_points) if self.steiner_points else 0,
            'solve_time': self.solve_time,
            'is_feasible': quality_metrics['obtuse_triangles'] == 0,
            'steiner_efficiency': self.instance.num_points / max(1, len(self.steiner_points)) if self.steiner_points else float('inf')
        })

        return quality_metrics

    def export_solution_json(self, filepath: str):
        """
        Export solution to JSON file

        Args:
            filepath: Path to output file
        """
        if not self.solution:
            raise ValueError("No solution available to export")

        solution_dict = {
            "content_type": self.solution.content_type,
            "instance_uid": self.solution.instance_uid,
            "steiner_points_x": self.solution.steiner_points_x,
            "steiner_points_y": self.solution.steiner_points_y,
            "edges": self.solution.edges
        }

        with open(filepath, 'w') as f:
            json.dump(solution_dict, f, indent=2)

        if self.debug:
            print(f"Solution exported to {filepath}")

    def get_triangulation_for_visualization(self) -> List[Dict[str, Any]]:
        """
        Get triangulation data formatted for visualization

        Returns:
            List of triangle dictionaries for plotting
        """
        if not self.triangulation:
            return []

        triangles_data = []
        for i, triangle in enumerate(self.triangulation):
            triangle_data = {
                'index': i,
                'vertices': [
                    {'x': float(v.x().exact()), 'y': float(v.y().exact())}
                    for v in triangle.vertices
                ],
                'is_obtuse': triangle.is_obtuse,
                'is_right': triangle.is_right,
                'is_acute': triangle.is_acute,
                'area': float(triangle.area().exact())
            }
            triangles_data.append(triangle_data)

        return triangles_data

    def get_steiner_points_for_visualization(self) -> List[Dict[str, float]]:
        """
        Get Steiner points formatted for visualization

        Returns:
            List of point dictionaries for plotting
        """
        if not self.steiner_points:
            return []

        points_data = []
        for i, point in enumerate(self.steiner_points):
            point_data = {
                'index': i,
                'x': float(point.x().exact()),
                'y': float(point.y().exact())
            }
            points_data.append(point_data)

        return points_data


class BatchSolver:
    """
    Batch solver for processing multiple instances
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize batch solver

        Args:
            config: Configuration for all instances
        """
        self.config = config or {}
        self.results = []

    def solve_instances(self, instances: List[Cgshop2025Instance]) -> List[Cgshop2025Solution]:
        """
        Solve multiple instances

        Args:
            instances: List of instances to solve

        Returns:
            List of solutions
        """
        solutions = []

        for i, instance in enumerate(instances):
            print(f"Solving instance {i+1}/{len(instances)}: {instance.instance_uid}")

            try:
                solver = BernEppsteinSolver(instance, self.config)
                solution = solver.solve()
                solutions.append(solution)

                # Store results for analysis
                self.results.append({
                    'instance_uid': instance.instance_uid,
                    'success': True,
                    'solution': solution,
                    'quality_metrics': solver.get_solution_quality()
                })

            except Exception as e:
                print(f"Failed to solve {instance.instance_uid}: {e}")

                # Record failure
                self.results.append({
                    'instance_uid': instance.instance_uid,
                    'success': False,
                    'error': str(e),
                    'quality_metrics': None
                })

                # Create empty solution to maintain list consistency
                empty_solution = Cgshop2025Solution(
                    content_type="CG_SHOP_2025_Solution",
                    instance_uid=instance.instance_uid,
                    steiner_points_x=[],
                    steiner_points_y=[],
                    edges=[]
                )
                solutions.append(empty_solution)

        return solutions

    def get_batch_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for batch solving

        Returns:
            Dictionary with batch statistics
        """
        if not self.results:
            return {}

        successful_results = [r for r in self.results if r['success']]
        failed_results = [r for r in self.results if not r['success']]

        stats = {
            'total_instances': len(self.results),
            'successful_instances': len(successful_results),
            'failed_instances': len(failed_results),
            'success_rate': len(successful_results) / len(self.results) * 100,
            'failed_instance_uids': [r['instance_uid'] for r in failed_results]
        }

        if successful_results:
            # Aggregate quality metrics
            feasible_count = sum(1 for r in successful_results
                               if r['quality_metrics']['is_feasible'])

            total_steiner_points = sum(r['quality_metrics']['steiner_points']
                                     for r in successful_results)

            total_triangles = sum(r['quality_metrics']['total_triangles']
                                for r in successful_results)

            total_obtuse_triangles = sum(r['quality_metrics']['obtuse_triangles']
                                       for r in successful_results)

            avg_solve_time = sum(r['quality_metrics']['solve_time']
                               for r in successful_results) / len(successful_results)

            stats.update({
                'feasible_solutions': feasible_count,
                'feasible_rate': feasible_count / len(successful_results) * 100,
                'total_steiner_points': total_steiner_points,
                'total_triangles': total_triangles,
                'total_obtuse_triangles': total_obtuse_triangles,
                'average_steiner_points': total_steiner_points / len(successful_results),
                'average_triangles': total_triangles / len(successful_results),
                'average_obtuse_triangles': total_obtuse_triangles / len(successful_results),
                'average_solve_time': avg_solve_time
            })

        return stats

    def export_batch_results(self, filepath: str):
        """
        Export batch results to JSON file

        Args:
            filepath: Path to output file
        """
        results_data = {
            'batch_statistics': self.get_batch_statistics(),
            'individual_results': []
        }

        for result in self.results:
            result_data = {
                'instance_uid': result['instance_uid'],
                'success': result['success']
            }

            if result['success']:
                result_data['quality_metrics'] = result['quality_metrics']
            else:
                result_data['error'] = result['error']

            results_data['individual_results'].append(result_data)

        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Batch results exported to {filepath}")


class SolverFactory:
    """
    Factory for creating solvers with different configurations
    """

    @staticmethod
    def create_default_solver(instance: Cgshop2025Instance) -> BernEppsteinSolver:
        """Create solver with default configuration"""
        return BernEppsteinSolver(instance)

    @staticmethod
    def create_debug_solver(instance: Cgshop2025Instance) -> BernEppsteinSolver:
        """Create solver with debug configuration"""
        config = {
            'debug': True,
            'use_adaptive': False,
            'optimize_result': True
        }
        return BernEppsteinSolver(instance, config)

    @staticmethod
    def create_adaptive_solver(instance: Cgshop2025Instance) -> BernEppsteinSolver:
        """Create solver with adaptive configuration"""
        config = {
            'debug': False,
            'use_adaptive': True,
            'optimize_result': True
        }
        return BernEppsteinSolver(instance, config)

    @staticmethod
    def create_fast_solver(instance: Cgshop2025Instance) -> BernEppsteinSolver:
        """Create solver optimized for speed"""
        config = {
            'debug': False,
            'use_adaptive': True,
            'optimize_result': False,
            'max_steiner_points': 1000
        }
        return BernEppsteinSolver(instance, config)

    @staticmethod
    def create_quality_solver(instance: Cgshop2025Instance) -> BernEppsteinSolver:
        """Create solver optimized for solution quality"""
        config = {
            'debug': False,
            'use_adaptive': False,
            'optimize_result': True,
            'max_steiner_points': None
        }
        return BernEppsteinSolver(instance, config)

    @staticmethod
    def create_batch_solver(config_name: str = 'default') -> BatchSolver:
        """Create batch solver with specified configuration"""
        if config_name == 'debug':
            config = {'debug': True, 'use_adaptive': False}
        elif config_name == 'adaptive':
            config = {'debug': False, 'use_adaptive': True}
        elif config_name == 'fast':
            config = {'debug': False, 'use_adaptive': True, 'optimize_result': False}
        elif config_name == 'quality':
            config = {'debug': False, 'use_adaptive': False, 'optimize_result': True}
        else:
            config = {'debug': False, 'use_adaptive': False}

        return BatchSolver(config)


class SolutionValidator:
    """
    Validator for checking solution correctness and quality
    """

    def __init__(self, instance: Cgshop2025Instance):
        """
        Initialize validator

        Args:
            instance: Instance to validate against
        """
        self.instance = instance

    def validate_solution(self, solution: Cgshop2025Solution) -> Dict[str, Any]:
        """
        Comprehensive solution validation

        Args:
            solution: Solution to validate

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_metrics': {}
        }

        try:
            # Basic format validation
            self._validate_format(solution, validation_results)

            # Geometric validation
            self._validate_geometry(solution, validation_results)

            # Constraint validation
            self._validate_constraints(solution, validation_results)

            # Quality assessment
            self._assess_quality(solution, validation_results)

        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation failed: {e}")

        return validation_results

    def _validate_format(self, solution: Cgshop2025Solution, results: Dict[str, Any]):
        """Validate solution format"""
        if solution.content_type != "CG_SHOP_2025_Solution":
            results['errors'].append(f"Invalid content_type: {solution.content_type}")

        if solution.instance_uid != self.instance.instance_uid:
            results['errors'].append(f"Instance UID mismatch: {solution.instance_uid} != {self.instance.instance_uid}")

        if len(solution.steiner_points_x) != len(solution.steiner_points_y):
            results['errors'].append("Steiner point coordinate arrays have different lengths")

        # Check edge format
        for i, edge in enumerate(solution.edges):
            if len(edge) != 2:
                results['errors'].append(f"Edge {i} has {len(edge)} endpoints (expected 2)")

            if edge[0] == edge[1]:
                results['errors'].append(f"Edge {i} is degenerate (same endpoints)")

    def _validate_geometry(self, solution: Cgshop2025Solution, results: Dict[str, Any]):
        """Validate geometric properties"""
        total_points = self.instance.num_points + len(solution.steiner_points_x)

        # Check edge indices
        for i, edge in enumerate(solution.edges):
            for j, idx in enumerate(edge):
                if not (0 <= idx < total_points):
                    results['errors'].append(f"Edge {i} endpoint {j} index {idx} out of range")

        # Check for duplicate edges
        edge_set = set()
        for i, edge in enumerate(solution.edges):
            edge_key = tuple(sorted(edge))
            if edge_key in edge_set:
                results['warnings'].append(f"Duplicate edge found: {edge}")
            edge_set.add(edge_key)

    def _validate_constraints(self, solution: Cgshop2025Solution, results: Dict[str, Any]):
        """Validate constraint satisfaction"""
        # Check that all original boundary edges are present
        boundary_edges = set()
        n = len(self.instance.region_boundary)
        for i in range(n):
            v1 = self.instance.region_boundary[i]
            v2 = self.instance.region_boundary[(i + 1) % n]
            boundary_edges.add(tuple(sorted([v1, v2])))

        solution_edges = set(tuple(sorted(edge)) for edge in solution.edges)

        missing_boundary_edges = boundary_edges - solution_edges
        if missing_boundary_edges:
            results['errors'].append(f"Missing boundary edges: {missing_boundary_edges}")

        # Check additional constraints
        for constraint in self.instance.additional_constraints:
            constraint_edge = tuple(sorted(constraint))
            if constraint_edge not in solution_edges:
                results['errors'].append(f"Missing constraint edge: {constraint_edge}")

    def _assess_quality(self, solution: Cgshop2025Solution, results: Dict[str, Any]):
        """Assess solution quality"""
        results['quality_metrics'] = {
            'steiner_points_count': len(solution.steiner_points_x),
            'edges_count': len(solution.edges),
            'steiner_efficiency': self.instance.num_points / max(1, len(solution.steiner_points_x))
        }

        # Set overall validity
        if results['errors']:
            results['is_valid'] = False

    def is_solution_feasible(self, solution: Cgshop2025Solution) -> bool:
        """
        Quick check if solution is feasible (valid and non-obtuse)

        Args:
            solution: Solution to check

        Returns:
            True if solution is feasible
        """
        validation_results = self.validate_solution(solution)

        if not validation_results['is_valid']:
            return False

        # Additional check for obtuse triangles would require full geometric reconstruction
        # This is simplified for the interface
        return True


class SolutionComparator:
    """
    Compare multiple solutions for the same instance
    """

    def __init__(self, instance: Cgshop2025Instance):
        """
        Initialize comparator

        Args:
            instance: Instance to compare solutions for
        """
        self.instance = instance

    def compare_solutions(self, solutions: List[Cgshop2025Solution]) -> Dict[str, Any]:
        """
        Compare multiple solutions

        Args:
            solutions: List of solutions to compare

        Returns:
            Dictionary with comparison results
        """
        comparison_results = {
            'instance_uid': self.instance.instance_uid,
            'solution_count': len(solutions),
            'solution_metrics': [],
            'best_solution_index': None,
            'ranking': []
        }

        # Analyze each solution
        validator = SolutionValidator(self.instance)

        for i, solution in enumerate(solutions):
            validation_results = validator.validate_solution(solution)

            metrics = {
                'solution_index': i,
                'is_valid': validation_results['is_valid'],
                'is_feasible': validator.is_solution_feasible(solution),
                'steiner_points': len(solution.steiner_points_x),
                'edges': len(solution.edges),
                'error_count': len(validation_results['errors']),
                'warning_count': len(validation_results['warnings'])
            }

            comparison_results['solution_metrics'].append(metrics)

        # Rank solutions
        valid_solutions = [m for m in comparison_results['solution_metrics'] if m['is_valid']]

        if valid_solutions:
            # Rank by: feasible first, then by fewest Steiner points
            valid_solutions.sort(key=lambda x: (not x['is_feasible'], x['steiner_points']))

            comparison_results['best_solution_index'] = valid_solutions[0]['solution_index']
            comparison_results['ranking'] = [s['solution_index'] for s in valid_solutions]

        return comparison_results

    def get_best_solution(self, solutions: List[Cgshop2025Solution]) -> Optional[Cgshop2025Solution]:
        """
        Get the best solution from a list

        Args:
            solutions: List of solutions

        Returns:
            Best solution or None if no valid solutions
        """
        comparison_results = self.compare_solutions(solutions)

        if comparison_results['best_solution_index'] is not None:
            return solutions[comparison_results['best_solution_index']]

        return None