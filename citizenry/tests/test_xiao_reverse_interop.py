"""Run the C++ emit_envelope binary, parse its output, and verify the
signature using the same canonical_signable_bytes computation Python uses.
This proves C++ → Python interop in the reverse direction.
"""
import json
import subprocess
from pathlib import Path

import nacl.signing
import nacl.encoding
import pytest

from citizenry.protocol import Envelope


@pytest.fixture
def cpp_output():
    bin_path = Path(__file__).resolve().parents[2] / "xiao-citizen" / "tests" / "emit_envelope"
    if not bin_path.exists():
        pytest.skip(f"build the binary first: cd {bin_path.parent} && make emit_envelope")
    out = subprocess.check_output([str(bin_path)])
    return json.loads(out)


def test_canonical_bytes_match(cpp_output):
    e = cpp_output["envelope"]
    env = Envelope(version=e["version"], type=e["type"], sender=e["sender"],
                   recipient=e["recipient"], timestamp=e["timestamp"], ttl=e["ttl"],
                   body=e["body"])
    py_canonical = env.signable_bytes()
    cpp_canonical = bytes.fromhex(cpp_output["canonical_hex"])
    assert py_canonical == cpp_canonical


def test_python_verifies_cpp_signature(cpp_output):
    e = cpp_output["envelope"]
    env = Envelope(version=e["version"], type=e["type"], sender=e["sender"],
                   recipient=e["recipient"], timestamp=e["timestamp"], ttl=e["ttl"],
                   body=e["body"])
    pubkey_bytes = bytes.fromhex(cpp_output["pubkey"])
    vk = nacl.signing.VerifyKey(pubkey_bytes)
    sig_bytes = bytes.fromhex(cpp_output["signature"])
    # raises BadSignatureError on mismatch
    vk.verify(env.signable_bytes(), sig_bytes)
