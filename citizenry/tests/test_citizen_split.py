"""Sanity tests for Task 3: citizen class split and rename.

Verifies that the new classes exist at their canonical paths, that
the legacy shim paths still work, and that the new files are in the
expected inheritance relationships.
"""

import pytest


# ── New canonical imports ──────────────────────────────────────────────────────

def test_manipulator_citizen_importable():
    from citizenry.manipulator_citizen import ManipulatorCitizen
    assert ManipulatorCitizen.__name__ == "ManipulatorCitizen"


def test_governor_citizen_importable():
    from citizenry.governor_citizen import GovernorCitizen
    assert GovernorCitizen.__name__ == "GovernorCitizen"


def test_leader_citizen_importable():
    from citizenry.leader_citizen import LeaderCitizen
    assert LeaderCitizen.__name__ == "LeaderCitizen"


# ── Legacy shim backward-compat ───────────────────────────────────────────────

def test_pi_citizen_shim_works():
    """from citizenry.pi_citizen import PiCitizen must still work."""
    from citizenry.pi_citizen import PiCitizen
    from citizenry.manipulator_citizen import ManipulatorCitizen
    assert PiCitizen is ManipulatorCitizen


def test_surface_citizen_shim_works():
    """from citizenry.surface_citizen import SurfaceCitizen must still work."""
    from citizenry.surface_citizen import SurfaceCitizen
    from citizenry.governor_citizen import GovernorCitizen
    assert issubclass(SurfaceCitizen, GovernorCitizen)


# ── Inheritance ────────────────────────────────────────────────────────────────

def test_manipulator_inherits_citizen():
    from citizenry.manipulator_citizen import ManipulatorCitizen
    from citizenry.citizen import Citizen
    assert issubclass(ManipulatorCitizen, Citizen)


def test_governor_inherits_citizen():
    from citizenry.governor_citizen import GovernorCitizen
    from citizenry.citizen import Citizen
    assert issubclass(GovernorCitizen, Citizen)


def test_leader_inherits_citizen():
    from citizenry.leader_citizen import LeaderCitizen
    from citizenry.citizen import Citizen
    assert issubclass(LeaderCitizen, Citizen)


# ── Instantiation smoke tests ──────────────────────────────────────────────────

def test_manipulator_citizen_instantiates():
    from citizenry.manipulator_citizen import ManipulatorCitizen
    c = ManipulatorCitizen(follower_port="/dev/null")
    assert c.citizen_type == "manipulator"
    assert "6dof_arm" in c.capabilities


def test_governor_citizen_instantiates():
    from citizenry.governor_citizen import GovernorCitizen
    c = GovernorCitizen()
    assert c.citizen_type == "governor"
    assert "govern" in c.capabilities
    assert not hasattr(c, '_follower_bus')
    assert not hasattr(c, '_leader_bus')
    assert hasattr(c, 'marketplace')
    assert hasattr(c, '_coordinator')


def test_leader_citizen_instantiates():
    from citizenry.leader_citizen import LeaderCitizen
    c = LeaderCitizen(leader_port="/dev/null")
    assert c.citizen_type == "leader"
    assert "teleop_source" in c.capabilities
    assert c._follower_key is None
    assert c._follower_addr is None


def test_surface_citizen_shim_instantiates():
    from citizenry.surface_citizen import SurfaceCitizen
    c = SurfaceCitizen(leader_port="/dev/null", teleop_fps=30.0)
    assert c.citizen_type == "governor"
    assert isinstance(c._leader_companion, type(c._leader_companion))
    assert c._leader_companion.leader_port == "/dev/null"
    assert c._leader_companion.teleop_fps == 30.0


def test_surface_citizen_teleop_attrs_proxy():
    """SurfaceCitizen proxies _teleop_active etc. to the leader companion."""
    from citizenry.surface_citizen import SurfaceCitizen
    c = SurfaceCitizen()
    # Default: not active
    assert c._teleop_active is False
    # Write through the proxy
    c._leader_companion._teleop_active = True
    assert c._teleop_active is True
