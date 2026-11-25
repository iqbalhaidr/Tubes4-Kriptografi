from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import ConfigError

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "profiles.toml"

MAX_COEFF_BITS_128: dict[int, int] = {1024: 27, 2048: 54, 4096: 109, 8192: 218, 16384: 438, 32768: 881}
BILL_MULT_DEPTH = 2 


@dataclass(frozen=True)
class CKKSProfile:
    name: str
    poly_modulus_degree: int
    coeff_modulus_bits: tuple[int, ...]
    scale_bits: int
    security_level: int
    max_abs_value: float

    @property
    def scale(self) -> float:
        return float(2**self.scale_bits)

    @property
    def slots(self) -> int:
        return self.poly_modulus_degree // 2

    @property
    def data_prime_count(self) -> int:
        return len(self.coeff_modulus_bits) - 1

    def summary(self) -> dict:
        return {
            "name": self.name,
            "N": self.poly_modulus_degree,
            "slots": self.slots,
            "coeff_modulus_bits": list(self.coeff_modulus_bits),
            "scale_bits": self.scale_bits,
            "security_level": self.security_level,
            "max_abs_value": self.max_abs_value,
        }

def _parse(name: str, raw: dict) -> CKKSProfile:
    required = ("poly_modulus_degree", "coeff_modulus_bits", "scale_bits", "security_level", "max_abs_value")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ConfigError(f"'{name}': Missing: {missing}")
    try:
        prof = CKKSProfile(
            name=name,
            poly_modulus_degree=int(raw["poly_modulus_degree"]),
            coeff_modulus_bits=tuple(raw["coeff_modulus_bits"]),
            scale_bits=int(raw["scale_bits"]),
            security_level=int(raw["security_level"]),
            max_abs_value=float(raw["max_abs_value"]),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{name}': Invalid ({exc})") from exc
    return prof


def _config_path(path: str | os.PathLike | None) -> Path:
    if path is not None:
        return Path(path)
    return Path(os.environ.get(CONFIG_PATH))


@lru_cache(maxsize=8)
def _load(path: Path) -> tuple[dict[str, CKKSProfile], str]:
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"File not found: {path}") from exc
    
    raw_profiles = data.get("profiles")
    profiles = {name: _parse(name, raw) for name, raw in raw_profiles.items()}
    default = data.get("default", next(iter(profiles)))
    return profiles, default


def load_profiles(path: str | os.PathLike | None = None) -> dict[str, CKKSProfile]:
    return dict(_load(_config_path(path))[0])


def get_profile(name: str | None = None, path: str | os.PathLike | None = None) -> CKKSProfile:
    profiles, default = _load(_config_path(path))
    chosen = name or default
    try:
        return profiles[chosen]
    except KeyError:
        raise ConfigError(f"Unknown profile: '{chosen}'; avaliable profiles: {sorted(profiles)}") from None
