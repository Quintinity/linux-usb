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

    version: int = 1
    governor_pubkey: str = ""        # hex-encoded Ed25519 public key
    articles: list[Article] = field(default_factory=list)
    laws: list[Law] = field(default_factory=list)
    servo_limits: ServoLimits = field(default_factory=ServoLimits)
    signature: str = ""              # hex-encoded Ed25519 signature

    # -- crypto -------------------------------------------------------------

    def _signable_payload(self) -> bytes:
        """Return the canonical bytes that get signed/verified.

        The signature field itself is excluded so that signing and
        verification are consistent.
        """
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, signing_key: SigningKey) -> None:
        """Sign this constitution with the governor's private key."""
        self.governor_pubkey = signing_key.verify_key.encode(
            encoder=HexEncoder
        ).decode()
        signed = signing_key.sign(self._signable_payload(), encoder=HexEncoder)
        self.signature = signed.signature.decode()

    def verify(self, verify_key: VerifyKey | None = None) -> bool:
        """Verify the signature. Uses embedded governor_pubkey if none given.

        Returns True on success, False on failure.
        """
        if verify_key is None:
            if not self.governor_pubkey:
                return False
            verify_key = VerifyKey(
                self.governor_pubkey.encode(), encoder=HexEncoder
            )
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
            "articles": [asdict(a) for a in self.articles],
            "laws": [asdict(l) for l in self.laws],
            "servo_limits": asdict(self.servo_limits),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Constitution:
        """Deserialize from a dictionary."""
        return cls(
            version=d["version"],
            governor_pubkey=d.get("governor_pubkey", ""),
            articles=[Article(**a) for a in d.get("articles", [])],
            laws=[Law(**l) for l in d.get("laws", [])],
            servo_limits=ServoLimits(**d.get("servo_limits", {})),
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
    ]

    return Constitution(
        version=1,
        articles=articles,
        laws=laws,
        servo_limits=ServoLimits(),
    )
