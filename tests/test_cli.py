from pathlib import Path

import pytest

from email_digest.cli import (
    FALLBACK_JUDGMENT,
    assemble_triaged,
    build_parser,
    config_home,
    load_api_key,
    parse_accounts,
)


def test_parse_accounts_splits_and_strips():
    assert parse_accounts("personal, school ,, work") == ["personal", "school", "work"]


def test_config_home_defaults_to_dot_dir(monkeypatch):
    monkeypatch.delenv("EMAIL_DIGEST_HOME", raising=False)
    assert config_home() == Path.home() / ".email-digest"


def test_config_home_respects_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMAIL_DIGEST_HOME", str(tmp_path))
    assert config_home() == tmp_path


def test_assemble_triaged_uses_judgment_when_present():
    emails = [{"id": "1", "subject": "x"}]
    judgments = {
        "1": {"importance": "high", "category": "internship", "summary": "s",
              "is_event": False, "has_free_food": False}
    }
    triaged = assemble_triaged(emails, judgments)
    assert triaged[0][1]["importance"] == "high"


def test_assemble_triaged_falls_back_for_missing_ids_and_drops_nothing():
    emails = [{"id": "1"}, {"id": "2"}]
    judgments = {
        "1": {"importance": "low", "category": "other", "summary": "s",
              "is_event": False, "has_free_food": False}
    }
    triaged = assemble_triaged(emails, judgments)
    assert [e["id"] for e, _ in triaged] == ["1", "2"]
    assert triaged[0][1]["importance"] == "low"
    assert triaged[1][1] == FALLBACK_JUDGMENT


def test_build_parser_defaults():
    args = build_parser().parse_args([])
    assert args.accounts == "personal,school"
    assert args.lookback_hours is None
    assert args.no_save is False


def test_version_flag_exits():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])


def test_load_api_key_overrides_empty_ambient_value(monkeypatch, tmp_path):
    # An empty ANTHROPIC_API_KEY already in the environment must NOT shadow the
    # real value in <home>/.env (regression: load_dotenv needs override=True).
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=test-key-value\n")
    assert load_api_key(tmp_path) == "test-key-value"
