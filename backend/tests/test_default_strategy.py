from app.consensus.default_strategy import DefaultConsensusStrategy, CONSENSUS_CLASS_PATH


def test_constructs_with_no_args_and_has_voters():
    s = DefaultConsensusStrategy()
    assert len(s.voters) > 0


def test_class_path_resolves_via_importlib():
    import importlib
    module_path, class_name = CONSENSUS_CLASS_PATH.rsplit(":", 1)
    cls = getattr(importlib.import_module(module_path), class_name)
    assert cls is DefaultConsensusStrategy
    assert cls() is not None  # zero-arg construct, matches bot.py self.strategy_class()
