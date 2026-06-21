"""
Loads and validates scoring.yaml config.
Provides a singleton CONFIG object imported by other modules.
"""
from pathlib import Path
import logging
from dataclasses import dataclass, field
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


@dataclass
class ScoringConfig:
    eligibility_weights: Dict[str, float]
    scoring_weights: Dict[str, float]
    thresholds: Dict[str, float]
    chains: Dict[str, List[str]]
    alerts: Dict[str, float]
    yield_optimizer: Dict = field(default_factory=dict)
    magic_eden: Dict = field(default_factory=dict)
    layerzero_cadencer: Dict = field(default_factory=dict)
    version: str = "1.0"


DEFAULT_CONFIG = ScoringConfig(
    version="1.0",
    eligibility_weights={
        "base_score": 0.20,
        "window_urgency": 0.35,
        "chain_priority": 0.20,
        "funding_recency": 0.15,
        "tvl_trend_bonus": 0.10,
    },
    scoring_weights={
        "tvl": 0.30,
        "growth_7d": 0.40,
        "funding": 0.20,
        "maturity": 0.10,
    },
    thresholds={
        "min_eligibility_score": 10,
        "high_urgency_score": 75,
        "medium_urgency_score": 50,
        "execution_min_score": 30,
    },
    chains={
        "priority_1": ["arbitrum", "base", "solana", "sonic", "berachain"],
        "priority_2": ["optimism", "zksync", "scroll", "linea", "polygon", "mantle"],
    },
    alerts={
        "wallet_inactivity_days": 3,
        "high_aoi_threshold": 70,
        "min_active_days_per_week": 2,
    },
)


def _validate_weights(weights: Dict[str, float], name: str, tolerance: float = 0.01):
    total = sum(weights.values())
    if abs(total - 1.0) > tolerance:
        raise ConfigError(
            f"{name} weights sum to {total:.3f}, expected 1.0 (±{tolerance})"
        )
    for k, v in weights.items():
        if v < 0 or v > 1:
            raise ConfigError(
                f"{name} weight '{k}' = {v} is outside [0, 1]"
            )


def _validate_thresholds(thresholds: Dict[str, float]):
    for k, v in thresholds.items():
        if not isinstance(v, (int, float)) or v < 0:
            raise ConfigError(f"Threshold '{k}' = {v} must be a positive number")


def load_config(path: str = "config/scoring.yaml") -> ScoringConfig:
    """Load YAML config, validate weights sum to 1.0, return ScoringConfig."""
    config_path = Path(path)
    if not config_path.is_file():
        logger.warning(f"Config file {path} not found, using hardcoded defaults")
        return DEFAULT_CONFIG

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Malformed YAML in {path}: {e}")

    if not isinstance(raw, dict):
        raise ConfigError(f"Config {path} must be a top-level mapping")

    ew = raw.get("eligibility_weights", DEFAULT_CONFIG.eligibility_weights)
    sw = raw.get("scoring_weights", DEFAULT_CONFIG.scoring_weights)
    th = raw.get("thresholds", DEFAULT_CONFIG.thresholds)
    ch = raw.get("chains", DEFAULT_CONFIG.chains)
    al = raw.get("alerts", DEFAULT_CONFIG.alerts)
    yo = raw.get("yield_optimizer", {})
    me = raw.get("magic_eden", {})
    lz = raw.get("layerzero_cadencer", {})
    ver = raw.get("version", "1.0")

    _validate_weights(ew, "eligibility_weights")
    _validate_weights(sw, "scoring_weights")
    _validate_thresholds(th)

    return ScoringConfig(
        version=ver,
        eligibility_weights=ew,
        scoring_weights=sw,
        thresholds=th,
        chains=ch,
        alerts=al,
        yield_optimizer=yo,
        magic_eden=me,
        layerzero_cadencer=lz,
    )


CONFIG = load_config()
