"""Constitutional Governance for the armOS Citizenry protocol.

Defines immutable safety constraints (Articles) that no command can override,
mutable policies (Laws) the governor can change, and hardware servo limits
that get written to EEPROM. The entire constitution is signed by the governor's
Ed25519 key so citizens can verify authenticity before accepting commands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Article:
    """An immutable safety rule. Cannot be changed after ratification."""

    number: int
    title: str
    text: str


@dataclass
class Law:
    """A mutable policy the governor can update between constitution versions."""

    id: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServoLimits:
    """Hardware safety limits written to STS3215 EEPROM."""

    max_torque: int = 500            # 0-1000 range
    protection_current: int = 250    # mA
    max_temperature: int = 65        # Celsius
    overload_torque: int = 90
    protective_torque: int = 50
    min_voltage: float = 6.0         # Volts


@dataclass
class Constitution:
    """The root governance document for an armOS citizenry."""

    # v1 fields (preserved for backward compatibility)
    version: int = 2
    governor_pubkey: str = ""        # legacy alias of authority_pubkey
    articles: list[Article] = field(default_factory=list)
    laws: list[Law] = field(default_factory=list)
    servo_limits: ServoLimits = field(default_factory=ServoLimits)
    signature: str = ""              # hex-encoded Ed25519 signature

    # v2 additions
    authority_pubkey: str = ""       # hex-encoded Ed25519 public key of the Authority
    node_key_version: int = 1
    tool_manifest_pinning: dict[str, str] = field(default_factory=dict)
    policy_pinning: dict[str, str] = field(default_factory=dict)
    embassy_topics: dict[str, str] = field(default_factory=dict)
    compliance_artefacts: dict[str, str] = field(default_factory=dict)

    # -- crypto -------------------------------------------------------------

    def _signable_payload(self) -> bytes:
        """Return the canonical bytes that get signed/verified."""
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, signing_key: SigningKey) -> None:
        """Sign with the Authority's private key.

        For v2, the signing pubkey populates ``authority_pubkey`` and is
        mirrored into ``governor_pubkey`` for backward compatibility with
        v1 verifiers. For v1 Constitutions (version == 1) only
        ``governor_pubkey`` is populated.
        """
        pub_hex = signing_key.verify_key.encode(encoder=HexEncoder).decode()
        if self.version >= 2:
            self.authority_pubkey = pub_hex
            self.governor_pubkey = pub_hex  # mirror for v1 verifiers
        else:
            self.governor_pubkey = pub_hex
        signed = signing_key.sign(self._signable_payload(), encoder=HexEncoder)
        self.signature = signed.signature.decode()

    def verify(self, verify_key: VerifyKey | None = None) -> bool:
        """Verify the signature.

        For v2 Constitutions, prefers ``authority_pubkey``; falls back to
        ``governor_pubkey`` for v1 compatibility.
        """
        if verify_key is None:
            pub_hex = self.authority_pubkey or self.governor_pubkey
            if not pub_hex:
                return False
            verify_key = VerifyKey(pub_hex.encode(), encoder=HexEncoder)
        try:
            verify_key.verify(
                self._signable_payload(),
                bytes.fromhex(self.signature),
            )
            return True
        except Exception:
            return False

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "version": self.version,
            "governor_pubkey": self.governor_pubkey,
            "authority_pubkey": self.authority_pubkey,
            "node_key_version": self.node_key_version,
            "articles": [asdict(a) for a in self.articles],
            "laws": [asdict(l) for l in self.laws],
            "servo_limits": asdict(self.servo_limits),
            "tool_manifest_pinning": dict(self.tool_manifest_pinning),
            "policy_pinning": dict(self.policy_pinning),
            "embassy_topics": dict(self.embassy_topics),
            "compliance_artefacts": dict(self.compliance_artefacts),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Constitution:
        """Deserialize from a dictionary. Accepts both v1 and v2 payloads."""
        return cls(
            version=d.get("version", 1),
            governor_pubkey=d.get("governor_pubkey", ""),
            authority_pubkey=d.get("authority_pubkey", ""),
            node_key_version=d.get("node_key_version", 1),
            articles=[Article(**a) for a in d.get("articles", [])],
            laws=[Law(**l) for l in d.get("laws", [])],
            servo_limits=ServoLimits(**d.get("servo_limits", {})),
            tool_manifest_pinning=dict(d.get("tool_manifest_pinning", {})),
            policy_pinning=dict(d.get("policy_pinning", {})),
            embassy_topics=dict(d.get("embassy_topics", {})),
            compliance_artefacts=dict(d.get("compliance_artefacts", {})),
            signature=d.get("signature", ""),
        )

    def to_bytes(self) -> bytes:
        """Serialize to bytes for wire transport."""
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode()

    @classmethod
    def from_bytes(cls, raw: bytes) -> Constitution:
        """Deserialize from bytes."""
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# Default constitution
# ---------------------------------------------------------------------------

def default_constitution() -> Constitution:
    """Create the standard armOS constitution with founding articles."""
    articles = [
        Article(
            number=1,
            title="Do No Harm",
            text=(
                "No command may cause physical harm to humans "
                "or destruction of another citizen."
            ),
        ),
        Article(
            number=2,
            title="Governor Authority",
            text=(
                "The governor can always halt, override, "
                "or recall any citizen."
            ),
        ),
        Article(
            number=3,
            title="Self-Preservation",
            text=(
                "A citizen must protect its own hardware through "
                "servo overload protection and thermal shutdown."
            ),
        ),
        Article(
            number=4,
            title="Truthful Reporting",
            text=(
                "Every citizen must truthfully report its state. "
                "No spoofing."
            ),
        ),
        Article(
            number=5,
            title="Collective Knowledge",
            text="Learned behaviors belong to the collective.",
        ),
        Article(
            number=6,
            title="Policy Within Servo Limits",
            text=(
                "Policy citizens shall not emit action targets outside "
                "ServoLimits. Defence in depth: ManipulatorCitizen also "
                "clamps on ingress."
            ),
        ),
    ]

    laws = [
        Law(
            id="idle_timeout",
            description="Arms return to home position after idle period.",
            params={"seconds": 300},
        ),
        Law(
            id="teleop_max_fps",
            description="Maximum teleop frame rate.",
            params={"fps": 60},
        ),
        Law(
            id="heartbeat_interval",
            description="Seconds between heartbeat pings.",
            params={"seconds": 2.0},
        ),
        Law(
            id="dataset.hf_repo_id",
            description="Hugging Face Hub repo for v3 dataset uploads (e.g. user/repo). Empty disables uploads.",
            params={"value": ""},
        ),
        Law(
            id="dataset.fps",
            description="Frames per second for v3 dataset videos.",
            params={"value": 30},
        ),
        Law(
            id="dataset.upload_after_episode",
            description="Whether ManipulatorCitizen uploads each closed episode to HF.",
            params={"value": True},
        ),
        Law(
            id="dataset.delete_after_upload",
            description="Whether to delete local episodes after verified HF upload.",
            params={"value": True},
        ),
        Law(
            id="dataset.retry_interval_s",
            description="Seconds between HFUploader retry attempts.",
            params={"value": 300},
        ),
        Law(
            id="dataset.max_local_episodes",
            description="Soft cap on local episode count before uploads-lagging warning.",
            params={"value": 50},
        ),
        Law(
            id="governor.recorder_enabled",
            description="Whether the GovernorNode is allowed to host an episode recorder. Always false — episodes record on the follower's node.",
            params={"value": False},
        ),
        Law(
            id="policy_citizen.observation_cameras",
            description="Two camera role names the policy uses for observation. Order matters: [primary, secondary].",
            params={"value": ["wrist", "base"]},
        ),
        Law(
            id="camera.broadcast_interval_s",
            description="Seconds between continuous JPEG frame broadcasts from CameraCitizens with a role assigned. Default 0.2 (5 Hz). Lower for faster policy reactions; raise to reduce LAN bandwidth.",
            params={"value": 0.2},
        ),
    ]

    return Constitution(
        version=2,
        articles=articles,
        laws=laws,
        servo_limits=ServoLimits(),
    )
