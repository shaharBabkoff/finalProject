"""
Bern & Eppstein Nonobtuse Triangulation Solver for CG:SHOP 2025

This package implements the polynomial-size nonobtuse triangulation algorithm
by Bern & Eppstein (1991) for the CG:SHOP 2025 competition.

Main components:
- BernEppsteinSolver: High-level solver interface compatible with cgshop2025_pyutils
- BernEppsteinTriangulator: Core triangulation algorithm implementation
- BernEppsteinGeometry: Extended geometry utilities using exact arithmetic
"""

from .solver import BernEppsteinSolver
from .triangulator import BernEppsteinTriangulator
from .geometry import BernEppsteinGeometry, ExactTriangle

__version__ = "1.0.0"
__author__ = "CG:SHOP 2025 Participant"
__email__ = "participant@example.com"

__all__ = [
    "BernEppsteinSolver",
    "BernEppsteinTriangulator",
    "BernEppsteinGeometry",
    "ExactTriangle"
]