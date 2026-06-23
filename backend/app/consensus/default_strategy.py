"""Zero-arg consensus strategy so the bot's `self.strategy_class()` contract
works unchanged. Registered in the Strategy table via `register_strategy`."""
from __future__ import annotations

from app.consensus.base import ConsensusStrategy
from app.consensus.voters import build_default_voters
from app import models

CONSENSUS_CLASS_PATH = "app.consensus.default_strategy:DefaultConsensusStrategy"


class DefaultConsensusStrategy(ConsensusStrategy):
    name = "Ensemble Consensus (default)"

    def __init__(self):
        # ponytail: paper bootstraps with default voter weights, not walk-forward
        # weights — load WF weights here later if a real edge shows up.
        super().__init__(voters=build_default_voters())


def register_strategy(db) -> "models.Strategy":
    """Idempotent: ensure a Strategy row points at DefaultConsensusStrategy."""
    row = db.query(models.Strategy).filter_by(name=DefaultConsensusStrategy.name).one_or_none()
    if row is None:
        row = models.Strategy(
            name=DefaultConsensusStrategy.name,
            class_path=CONSENSUS_CLASS_PATH,
            params_schema={},
            description="Weighted supermajority vote across independent voters.",
            is_builtin=True,
        )
        db.add(row); db.commit(); db.refresh(row)
    elif row.class_path != CONSENSUS_CLASS_PATH:
        row.class_path = CONSENSUS_CLASS_PATH
        db.commit()
    return row
