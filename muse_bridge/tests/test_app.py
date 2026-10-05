"""Credential migration and command isolation for the Home Assistant app."""
import importlib.util
import json
import stat
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("muse_app", Path(__file__).parents[1] / "main.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
TOKEN = "mgst_" + "A" * 43


@pytest.fixture
def settings(tmp_path, monkeypatch):
    shared = tmp_path / "share"
    shared.mkdir()
    state = tmp_path / "private"
    options = tmp_path / "options.json"
    options.write_text(json.dumps({"sdk_token": ""}))
    monkeypatch.setattr(app, "SHARED_DIR", shared)
    monkeypatch.setenv(app.config.STATE_DIR_ENV, str(state))
    monkeypatch.delenv(app.config.SDK_TOKEN_ENV, raising=False)
    return shared, state, options


def test_import_is_private_and_survives_restart(settings):
    shared, state, options = settings
    source = shared / "sdk_token"
    source.write_text(TOKEN)
    app.prepare_settings(options)
    assert not source.exists()
    assert (state / "sdk_token").read_text().strip() == TOKEN
    assert stat.S_IMODE((state / "sdk_token").stat().st_mode) == 0o600
    app.prepare_settings(options)
    assert app.config.sdk_token() == TOKEN


def test_invalid_import_is_preserved_without_logging_secret(settings):
    shared, state, options = settings
    (shared / "sdk_token").write_text("invalid-secret")
    with pytest.raises(ValueError) as error:
        app.prepare_settings(options)
    assert "invalid-secret" not in str(error.value)
    assert (shared / "sdk_token").exists()
    assert not (state / "sdk_token").exists()
    assert app.config.SDK_TOKEN_ENV not in app.os.environ


def test_missing_token_has_actionable_error(settings):
    with pytest.raises(ValueError, match="SDK token"):
        app.prepare_settings(settings[2])


def test_commands_are_rejected():
    assert app.ConversationOnlyExecutor().run("shell", {"command": "echo unsafe"})["ok"] is False


def test_pairing_import_retains_identity_and_forces_refresh(settings):
    shared, state, _ = settings
    source = shared / "pairing-import.json"
    source.write_text(json.dumps({"identity": {"mac":"02:00:00:ab:cd:ef"},
        "pairing": {"access_token":"fake-access", "refresh_token":"fake-refresh", "unexpected":"omit"}}))
    app.import_pairing()
    assert not source.exists()
    assert app.identity.load_or_create().node_id == "homelink-abcdef"
    pairing = app.config.load_json(app.config.PAIRING_FILE)
    assert pairing["access_token_saved_at"] == 0
    assert "unexpected" not in pairing
    assert stat.S_IMODE((state / app.config.PAIRING_FILE).stat().st_mode) == 0o600


def test_pairing_import_refuses_to_replace_live_identity(settings):
    shared, state, _ = settings
    app.config.save_json(app.config.PAIRING_FILE, {"access_token":"already-paired"})
    source = shared / "pairing-import.json"
    source.write_text('{}')
    with pytest.raises(ValueError, match="refusing to overwrite"):
        app.import_pairing()
    assert source.exists()
    assert app.config.load_json(app.config.PAIRING_FILE)["access_token"] == "already-paired"


@pytest.mark.parametrize("change", [
    {"identity":{"mac":"wrong"}},
    {"pairing":{"access_token":"only-one-token"}},
    {"pairing":{"access_token":"a", "refresh_token":"r", "api_url_v2":"http://example.com"}},
])
def test_pairing_import_validates_before_writing(settings, change):
    shared, state, _ = settings
    data = {"identity":{"mac":"02:00:00:ab:cd:ef"}, "pairing":{"access_token":"a", "refresh_token":"r"}}
    data.update(change)
    (shared / "pairing-import.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        app.import_pairing()
    assert not state.exists()
