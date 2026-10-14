import importlib.util
import io
import json
import os
import sys
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "update-us-ai-models.py",
)
_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deploys",
    "development_tools",
    "ai_agent_devcontainer",
    "files",
    "opencode",
)
_spec = importlib.util.spec_from_file_location("update_us_ai_models", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_normalize_jsonc_removes_line_comments() -> None:
    text = '{\n  // hello\n  "x": 1\n}'
    assert mod.normalize_jsonc(text) == '{\n  \n  "x": 1\n}'


def test_normalize_jsonc_removes_block_comments() -> None:
    text = '{\n  /* block */\n  "x": 1\n}'
    assert mod.normalize_jsonc(text) == '{\n  \n  "x": 1\n}'


def test_normalize_jsonc_preserves_strings() -> None:
    text = '{"url": "http://example.com // not a comment"}'
    assert mod.normalize_jsonc(text) == text


def test_normalize_jsonc_preserves_escaped_quotes() -> None:
    text = '{"s": "say \\"hi\\" // still string"}'
    assert mod.normalize_jsonc(text) == text


def test_npm_name_unscoped() -> None:
    assert mod.npm_name("opencode-gemini-auth@1.4.9") == "opencode-gemini-auth"


def test_npm_name_scoped() -> None:
    assert mod.npm_name("@dietrichgebert/ponytail@4.8.4") == "@dietrichgebert/ponytail"


def test_npm_name_no_version() -> None:
    assert mod.npm_name("@scope/name") is None
    assert mod.npm_name("plain") is None


def test_update_config_parses_the_repo_jsonc_files(tmp_path: Path) -> None:
    for name in ("opencode.jsonc", "untracked-config.example.jsonc"):
        with open(os.path.join(_CONFIG_DIR, name)) as f:
            target = tmp_path / name
            target.write_text(f.read())
        mod.update_config([{"id": "byusage.example/model", "name": "Model"}], config_path=target)
        with open(target) as f:
            config = json.loads(mod.normalize_jsonc(f.read()))
        assert config["provider"]["vshn-us-ai"]["models"] == {
            "byusage.example/model": {"name": "Model"},
        }


def test_update_config_preserves_jsonc_comments_and_formatting(tmp_path: Path) -> None:
    config = tmp_path / "config.jsonc"
    original = """{
  // keep this comment
  "provider": {
    // keep this provider comment
    "other": {"models": {"keep": {"name": "Keep"}}},
    "vshn-us-ai": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "VSHN US AI",
      "models": {
        "old": {"name": "Old"},
      },
    },
  },
  // renovate: datasource=npm depName=example
  "plugin": ["example@1.0.0"],
}
"""
    config.write_text(original)

    mod.update_config([{"id": "new/model", "name": "New"}], config_path=config)

    result = config.read_text()
    assert "// keep this comment" in result
    assert "// keep this provider comment" in result
    assert "// renovate: datasource=npm depName=example" in result
    assert '"plugin": ["example@1.0.0"]' in result
    assert '"old": {"name": "Old"}' not in result
    assert '"new/model": {\n          "name": "New"\n        }' in result


class Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def read(self) -> bytes:
        return self.body

    def getcode(self) -> int:
        return 200


def test_fetch_models_sorts_ids_and_uses_provider_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mod,
        "urlopen",
        lambda request, timeout: Response(b'{"data":[{"id":"z-model"},{"id":"a-model","name":"A model"}]}'),
    )
    models = mod.fetch_models(base_url="https://provider.example")
    assert [model["id"] for model in models] == ["a-model", "z-model"]
    assert mod.get_display_name(models[0]) == "A model"
    assert mod.get_display_name(models[1]) == "z-model"


def test_fetch_models_rejects_invalid_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        b"[]",
        b'{"data":[]}',
        b'{"data":[{"id":"same"},{"id":"same"}]}',
        b'{"data":[{"id":1}]}',
        b'{"data":[{"id":"   "}]}',
        b"not-json",
    ]
    for body in responses:
        monkeypatch.setattr(mod, "urlopen", lambda request, timeout, body=body: Response(body))
        try:
            mod.fetch_models()
        except mod.ModelFetchError:
            pass
        else:
            raise AssertionError(f"accepted invalid response {body!r}")


def test_fetch_models_rejects_http_url_and_timeout_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    errors = [
        HTTPError("https://provider.example/models", 500, "failure", Message(), io.BytesIO()),
        URLError("unreachable"),
        TimeoutError(),
    ]
    for error in errors:
        monkeypatch.setattr(mod, "urlopen", lambda request, timeout, error=error: (_ for _ in ()).throw(error))
        try:
            mod.fetch_models()
        except mod.ModelFetchError:
            pass
        else:
            raise AssertionError(f"accepted network error {error!r}")


def test_fetch_models_rejects_non_2xx_response_object(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Response(b'{"data":[{"id":"model"}]}')
    response.status = 503
    monkeypatch.setattr(mod, "urlopen", lambda request, timeout: response)

    with pytest.raises(mod.ModelFetchError):
        mod.fetch_models()


def test_whitespace_model_name_falls_back_to_id() -> None:
    assert mod.get_display_name({"id": "model", "name": "  "}) == "model"
    assert mod.get_display_name({"id": "model", "name": " Display "}) == " Display "


def test_filter_models_does_not_use_a_catalog() -> None:
    models = [{"id": "provider.new-model"}, {"id": "another-model"}]
    assert mod.filter_models(models) == models
    assert mod.filter_models(models, mode="all") == models
    assert mod.filter_models(models, price_class="provider") == [models[0]]


def test_list_is_read_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "config.jsonc"
    config.write_text('{"provider": {"vshn-us-ai": {"models": {"old": {"name": "Old"}}}}}')
    monkeypatch.setattr(mod, "urlopen", lambda request, timeout: Response(b'{"data":[{"id":"new"}]}'))
    monkeypatch.setattr(
        sys,
        "argv",
        ["update-us-ai-models.py", "--list", "--api-key", "test", "--config-path", str(config)],
    )
    mod.main()
    assert config.read_text() == '{"provider": {"vshn-us-ai": {"models": {"old": {"name": "Old"}}}}}'
    assert "new" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["--all"], ["--price-class", "provider"]])
def test_cli_compatibility_flags_update(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, arguments: list[str]) -> None:
    config = tmp_path / "config.jsonc"
    config.write_text('{"provider": {"vshn-us-ai": {}}}')
    monkeypatch.setattr(mod, "urlopen", lambda request, timeout: Response(b'{"data":[{"id":"provider/model"}]}'))
    monkeypatch.setattr(
        sys,
        "argv",
        ["update-us-ai-models.py", *arguments, "--api-key", "test", "--config-path", str(config)],
    )

    mod.main()

    assert '"provider/model"' in config.read_text()


def test_failed_refresh_leaves_config_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = tmp_path / "config.jsonc"
    original = '{"provider": {"vshn-us-ai": {"models": {"old": {"name": "Old"}}}}}'
    config.write_text(original)
    monkeypatch.setattr(mod, "urlopen", lambda request, timeout: Response(b'{"data":[]}'))
    monkeypatch.setattr(sys, "argv", ["update-us-ai-models.py", "--api-key", "test", "--config-path", str(config)])
    try:
        mod.main()
    except SystemExit as error:
        assert error.code == 1
    assert config.read_text() == original


def test_successful_refresh_updates_only_selected_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = tmp_path / "config.jsonc"
    config.write_text(
        '{"provider":{"other":{"models":{"keep":{"name":"Keep"}}},"vshn-us-ai":{"models":{"old":{"name":"Old"}}}}}'
    )
    monkeypatch.setattr(
        mod,
        "urlopen",
        lambda request, timeout: Response(b'{"data":[{"id":"z-model"},{"id":"a-model","name":"A model"}]}'),
    )
    monkeypatch.setattr(sys, "argv", ["update-us-ai-models.py", "--api-key", "test", "--config-path", str(config)])
    mod.main()
    result = json.loads(config.read_text())
    assert result["provider"]["other"] == {"models": {"keep": {"name": "Keep"}}}
    assert result["provider"]["vshn-us-ai"]["models"] == {
        "a-model": {"name": "A model"},
        "z-model": {"name": "z-model"},
    }
