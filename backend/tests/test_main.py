import logging

from src.core.config import Settings
from src.main import create_app


def test_create_app_warns_when_jwt_secret_is_the_placeholder_default(
    monkeypatch, caplog: "logging.LogCaptureFixture"
) -> None:
    monkeypatch.setattr("src.main.get_settings", lambda: Settings(jwt_secret="change-me"))

    with caplog.at_level(logging.WARNING, logger="src.main"):
        create_app()

    assert any("forgeable" in record.message for record in caplog.records)


def test_create_app_is_quiet_when_jwt_secret_is_overridden(
    monkeypatch, caplog: "logging.LogCaptureFixture"
) -> None:
    monkeypatch.setattr("src.main.get_settings", lambda: Settings(jwt_secret="a-real-random-secret"))

    with caplog.at_level(logging.WARNING, logger="src.main"):
        create_app()

    assert not any("forgeable" in record.message for record in caplog.records)
