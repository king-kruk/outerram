from outerram.types import RuntimePlan, Strategy
import outerram.validate as validate


def _plan(strategy):
    return RuntimePlan(strategy, strategy.value, 16, 4, 12, 20, 6 if strategy is Strategy.MOE_STREAM else None, "test")


def test_dense_ready_requires_flash_and_mlx_lm(monkeypatch):
    monkeypatch.setattr(validate, "software_report", lambda **kwargs: {"mlx_lm": {"installed": False, "version": None, "commit": None}, "mlx_flash": {"installed": True, "version": "0.4.0", "commit": None}, "streamlx": {"installed": False, "version": None, "commit": None, "home": "/x"}})
    status = validate.runtime_status(_plan(Strategy.DENSE_STREAM))
    assert status["installed"] is False


def test_resident_reports_expected_pin(monkeypatch):
    from outerram.runtime_pins import MLX_LM_REF
    monkeypatch.setattr(validate, "software_report", lambda **kwargs: {"mlx_lm": {"installed": True, "version": "x", "commit": MLX_LM_REF}, "mlx_flash": {"installed": False, "version": None, "commit": None}, "streamlx": {"installed": False, "version": None, "commit": None, "home": "/x"}})
    status = validate.runtime_status(_plan(Strategy.RESIDENT))
    assert status["pin_match"] is True
    assert status["expected_commit"] == MLX_LM_REF
    assert status["reproducible"] is True


def test_unknown_resident_commit_is_not_reproducible(monkeypatch):
    monkeypatch.setattr(validate, "software_report", lambda **kwargs: {"mlx_lm": {"installed": True, "version": "x", "commit": None}, "mlx_flash": {"installed": False, "version": None, "commit": None}, "streamlx": {"installed": False, "version": None, "commit": None, "home": "/x"}})
    status = validate.runtime_status(_plan(Strategy.RESIDENT))
    assert status["installed"] is True
    assert status["pin_match"] is None
    assert status["reproducible"] is False
