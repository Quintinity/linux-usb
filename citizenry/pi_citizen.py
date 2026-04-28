"""Deprecated shim — PiCitizen was renamed to ManipulatorCitizen.

This re-export will be removed after Task 12.
"""
from .manipulator_citizen import ManipulatorCitizen

PiCitizen = ManipulatorCitizen  # legacy alias
