import copy
import importlib.util
import io
import json
import os
import subprocess
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request

import pytest

MODEL_IDS = [
    "chat",
    "chat_thinking",
    "web_research",
    "translate_de",
    "translate_en",
    "fix_grammar_en",
    "fix_grammar_de",
    "linux_cli",
]
ROUTER_MODEL_IDS = [
    "router-chat",
    "router-chat-thinking",
    "router-web-research",
    "router-translate-de",
    "router-translate-en",
    "router-fix-grammar-en",
    "router-fix-grammar-de",
    "router-linux-cli",
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ROOT, "scripts", "update-openwebui-models.py")


def load_module(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class RecordingOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[Request] = []

    def __call__(self, request: Request, timeout: float) -> FakeResponse:
        del timeout
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return cast(FakeResponse, response)


class ModelApiOpener:
    def __init__(
        self,
        exported: list[dict[str, object]],
        *,
        sync_status: int = 200,
        sync_response: object | None = None,
    ) -> None:
        self.exported = copy.deepcopy(exported)
        self.sync_status = sync_status
        self.sync_response = sync_response
        self.sync_payloads: list[dict[str, object]] = []
        self.import_payloads: list[dict[str, object]] = []
        self.deleted: list[str] = []
        self.requests: list[Request] = []
        self.paths: list[tuple[str, str]] = []

    def __call__(self, request: Request, timeout: float) -> FakeResponse:
        del timeout
        path = urlparse(request.full_url).path
        self.requests.append(request)
        self.paths.append((request.method or "", path))
        if path == "/ready":
            return FakeResponse({})
        if path == "/api/v1/users/user":
            return FakeResponse({"id": "admin-user"})
        if path == "/api/v1/auths/signin":
            return FakeResponse({"token": "session-token", "id": "admin-user"})
        if path == "/api/v1/models/export":
            return FakeResponse(copy.deepcopy(self.exported))
        if path == "/api/v1/models/sync":
            assert request.data is not None
            payload = json.loads(cast(bytes, request.data))
            assert isinstance(payload, dict)
            self.sync_payloads.append(cast(dict[str, object], payload))
            if self.sync_status != 200:
                raise HTTPError(request.full_url, self.sync_status, "failed", Message(), io.BytesIO(b"private"))
            models = payload.get("models")
            assert isinstance(models, list)
            if self.sync_response is None:
                self.exported = copy.deepcopy(cast(list[dict[str, object]], models))
                return FakeResponse(copy.deepcopy(self.exported))
            return FakeResponse(self.sync_response)
        if path == "/api/v1/models/import":
            assert request.data is not None
            payload = json.loads(cast(bytes, request.data))
            assert isinstance(payload, dict)
            self.import_payloads.append(cast(dict[str, object], payload))
            models = cast(list[dict[str, object]], payload["models"])
            self.exported.extend(copy.deepcopy(models))
            return FakeResponse(True)
        if path == "/api/v1/models/model/delete":
            assert request.data is not None
            payload = json.loads(cast(bytes, request.data))
            assert isinstance(payload, dict)
            model_id = payload["id"]
            assert isinstance(model_id, str)
            self.deleted.append(model_id)
            self.exported = [model for model in self.exported if model.get("id") != model_id]
            return FakeResponse(True)
        raise AssertionError(f"unexpected request path: {path}")


def load_reconciler() -> ModuleType:
    assert os.path.isfile(SCRIPT_PATH)
    return load_module("update_openwebui_models", SCRIPT_PATH)


def require_callable(module: ModuleType, name: str) -> Callable[..., Any]:
    function = cast(Callable[..., Any] | None, getattr(module, name, None))
    assert function is not None
    return function


def load_all_module(name: str) -> ModuleType:
    with patch.dict(os.environ, {"CI": ""}):
        return load_module(name, os.path.join(ROOT, "group_data", "all.py"))


def test_openwebui_group_data_contract() -> None:
    all_data = load_all_module("openwebui_all")
    ci_data = load_module("openwebui_ci", os.path.join(ROOT, "group_data", "ci.py"))

    assert all_data.openwebui["enabled"] is True
    assert ci_data.openwebui["enabled"] is False
    for source in (all_data, ci_data):
        openwebui = source.openwebui
        assert openwebui.get("router_backend") == "AISIX"
        assert openwebui.get("router_config_path") == "aisix-resources.yaml"
        assert openwebui.get("openai_compatible_base_url") == "http://aisix:3000/v1"
        assert openwebui.get("default_models") == MODEL_IDS
        assert openwebui.get("model_map") == dict(zip(MODEL_IDS, ROUTER_MODEL_IDS, strict=True))
        assert [preset["id"] for preset in openwebui.get("presets", [])] == MODEL_IDS
        assert [preset["name"] for preset in openwebui["presets"]] == [
            "Chat",
            "Chat (Thinking)",
            "Web Research",
            "Translate to German",
            "Translate to English",
            "Fix English Grammar",
            "Fix German Grammar",
            "Linux CLI",
        ]
        assert [preset["web_search"] for preset in openwebui["presets"]] == [
            False,
            False,
            True,
            False,
            False,
            False,
            False,
            False,
        ]
        assert all(preset["system"] for preset in openwebui["presets"])
        assert openwebui.get("extra_env") == {
            "ENABLE_OPENAI_API": "true",
            "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
            "OPENAI_API_KEYS": "${OPENWEBUI_CALLER_KEY}",
            "DEFAULT_MODELS": ",".join(MODEL_IDS),
            "ENABLE_MODEL_FILTER": "true",
            "MODEL_FILTER_LIST": ",".join(MODEL_IDS),
        }


def test_openwebui_group_data_contains_only_empty_secret_placeholders() -> None:
    all_data = load_all_module("openwebui_all_secrets")
    ci_data = load_module("openwebui_ci_secrets", os.path.join(ROOT, "group_data", "ci.py"))

    for source in (all_data, ci_data):
        openwebui = source.openwebui
        assert openwebui.get("BRAVE_API_KEY") == ""
        assert openwebui.get("ZEN_API_KEY") == ""
        assert openwebui.get("OLLAMA_API_KEY") == ""
        assert openwebui.get("OPENWEBUI_CALLER_KEY") == ""
        assert openwebui.get("OPENWEBUI_ADMIN_API_KEY") == ""
        assert openwebui.get("ZEN_API_BASE") == "https://opencode.ai/zen/go/v1"
        assert openwebui.get("ZEN_MODEL") == "deepseek-v4-flash"
        assert openwebui.get("OLLAMA_API_BASE") == "http://host.docker.internal:11434/v1"
        assert openwebui.get("OLLAMA_MODEL") == "qwen2.5:3b"


def test_compose_renders_aisix_gateway_and_openwebui_contract() -> None:
    compose_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "docker-compose.yml"
    environment = os.environ.copy()
    environment.update(
        {
            "AISIX_VERSION": "1.4.0",
            "ZEN_API_KEY": "test-zen-key",
            "ZEN_API_BASE": "https://example.invalid/zen/v1",
            "ZEN_MODEL": "test-zen-model",
            "OLLAMA_API_KEY": "test-ollama-key",
            "OLLAMA_API_BASE": "http://host.docker.internal:11434/v1",
            "OLLAMA_MODEL": "test-ollama-model",
            "OPENWEBUI_CALLER_KEY": "test-caller-key",
            "ENABLE_OPENAI_API": "true",
            "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
            "OPENAI_API_KEYS": "test-caller-key",
            "DEFAULT_MODELS": ",".join(MODEL_IDS),
            "ENABLE_MODEL_FILTER": "true",
            "MODEL_FILTER_LIST": ",".join(MODEL_IDS),
        }
    )
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "config", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    services = json.loads(result.stdout)["services"]

    assert "aisix" in services
    aisix = services["aisix"]
    assert aisix["image"] == "ghcr.io/api7/aisix:1.4.0"
    assert aisix["expose"] == ["3000"]
    assert "ports" not in aisix
    assert aisix["extra_hosts"] == ["host.docker.internal=host-gateway"]
    assert aisix["restart"] == "unless-stopped"
    assert aisix["environment"] == {
        "ZEN_API_KEY": "test-zen-key",
        "ZEN_API_BASE": "https://example.invalid/zen/v1",
        "ZEN_MODEL": "test-zen-model",
        "OLLAMA_API_KEY": "test-ollama-key",
        "OLLAMA_API_BASE": "http://host.docker.internal:11434/v1",
        "OLLAMA_MODEL": "test-ollama-model",
        "OPENWEBUI_CALLER_KEY": "test-caller-key",
    }
    mounts = {mount["target"]: mount for mount in aisix["volumes"]}
    assert mounts["/etc/aisix/config.yaml"]["read_only"] is True
    assert mounts["/etc/aisix/resources.yaml"]["read_only"] is True

    openwebui = services["open-webui"]
    assert openwebui["image"] == "ghcr.io/open-webui/open-webui:v0.11.4"
    assert openwebui["environment"] == {
        "WEBUI_AUTH": "False",
        "ENABLE_OPENAI_API": "true",
        "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
        "OPENAI_API_KEYS": "test-caller-key",
        "DEFAULT_MODELS": ",".join(MODEL_IDS),
        "ENABLE_MODEL_FILTER": "true",
        "MODEL_FILTER_LIST": ",".join(MODEL_IDS),
    }


def test_aisix_resources_validate_with_nonsecret_environment(tmp_path: Path) -> None:
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    assert resources_path.is_file()

    env_path = tmp_path / ".env"
    env_path.write_text(
        "ZEN_API_KEY=test-zen-key\n"
        "ZEN_API_BASE=https://example.invalid/zen/v1\n"
        "ZEN_MODEL=test-zen-model\n"
        "OLLAMA_API_KEY=test-ollama-key\n"
        "OLLAMA_API_BASE=http://host.docker.internal:11434/v1\n"
        "OLLAMA_MODEL=test-ollama-model\n"
        "OPENWEBUI_CALLER_KEY=test-caller-key\n"
    )
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--env-file",
            str(env_path),
            "--entrypoint",
            "/usr/local/bin/aisix",
            "--volume",
            f"{resources_path}:/etc/aisix/resources.yaml:ro",
            "ghcr.io/api7/aisix:1.4.0",
            "validate",
            "--resources",
            "/etc/aisix/resources.yaml",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_reconciler_import_is_side_effect_free() -> None:
    reconciler = load_reconciler()
    assert reconciler.__name__ == "update_openwebui_models"


def test_aisix_parser_returns_router_targets_without_secret_values() -> None:
    reconciler = load_reconciler()
    parse = require_callable(reconciler, "parse_aisix_model_names")
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"

    routes = parse(resources_path)

    assert routes == {
        "router-chat": ["zen-chat", "ollama-chat"],
        "router-chat-thinking": ["zen-thinking", "ollama-thinking"],
        "router-web-research": ["zen-web", "ollama-web"],
        "router-translate-de": ["zen-translation", "ollama-translation"],
        "router-translate-en": ["zen-translation", "ollama-translation"],
        "router-fix-grammar-en": ["zen-grammar", "ollama-grammar"],
        "router-fix-grammar-de": ["zen-grammar", "ollama-grammar"],
        "router-linux-cli": ["zen-linux", "ollama-linux"],
    }
    assert "ZEN_API_KEY" not in repr(routes)
    assert "OPENWEBUI_CALLER_KEY" not in repr(routes)


@pytest.mark.parametrize(
    "replacement",
    [
        ('_format_version: "1"', '_format_version: "2"'),
        ("  - display_name: zen-chat", "\t- display_name: zen-chat"),
        ("display_name: zen-chat", "display_name: &zen zen-chat"),
        ("display_name: router-chat\n", "display_name: router-chat\n  - display_name: router-chat\n"),
        ("      targets:\n", "      targets: [\n"),
        ("      targets:\n", ""),
        ("        - model: zen-chat\n", "        - model: missing-target\n"),
        ("          priority: 10\n", "          priority: ${PRIORITY}\n"),
    ],
)
def test_aisix_parser_rejects_unsupported_or_malformed_resources(tmp_path: Path, replacement: tuple[str, str]) -> None:
    reconciler = load_reconciler()
    parse = require_callable(reconciler, "parse_aisix_model_names")
    source_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    text = source_path.read_text().replace(*replacement)
    resources_path = tmp_path / "resources.yaml"
    resources_path.write_text(text)

    with pytest.raises(ValueError):
        parse(resources_path)


def test_manifest_loader_and_router_validation(tmp_path: Path) -> None:
    reconciler = load_reconciler()
    load_manifest = require_callable(reconciler, "load_manifest")
    parse = require_callable(reconciler, "parse_aisix_model_names")
    validate = require_callable(reconciler, "validate_router_models")
    all_data = load_all_module("manifest_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    manifest_path = tmp_path / "openwebui-models.json"
    manifest_path.write_text(json.dumps(manifest))
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"

    loaded = load_manifest(manifest_path)
    routes = parse(resources_path)
    validate(loaded, routes)

    invalid_manifest = json.loads(json.dumps(manifest))
    invalid_manifest["model_map"]["chat"] = "router-missing"
    with pytest.raises(ValueError):
        validate(invalid_manifest, routes)


def test_build_models_matches_eight_fixed_payload_contract() -> None:
    reconciler = load_reconciler()
    build_models = require_callable(reconciler, "build_models")
    all_data = load_all_module("payload_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    specs = [
        ("chat", "Chat", "You are a helpful assistant.", False),
        ("chat_thinking", "Chat (Thinking)", "Think carefully before answering.", False),
        ("web_research", "Web Research", "Research answers with web search and cite the sources.", True),
        (
            "translate_de",
            "Translate to German",
            "Translate the user's text into German and return only the translation.",
            False,
        ),
        (
            "translate_en",
            "Translate to English",
            "Translate the user's text into English and return only the translation.",
            False,
        ),
        ("fix_grammar_en", "Fix English Grammar", "Correct English grammar and preserve the original meaning.", False),
        ("fix_grammar_de", "Fix German Grammar", "Correct German grammar and preserve the original meaning.", False),
        (
            "linux_cli",
            "Linux CLI",
            "Help with Linux command-line tasks and return safe, practical commands.",
            False,
        ),
    ]
    expected = []
    for model_id, name, system, web_search in specs:
        params = {"system": system}
        if web_search:
            params["function_calling"] = "native"
        expected.append(
            {
                "id": model_id,
                "user_id": "admin-user",
                "base_model_id": all_data.openwebui["model_map"][model_id],
                "name": name,
                "params": params,
                "meta": {
                    "capabilities": {
                        "vision": False,
                        "citations": web_search,
                        "web_search": web_search,
                        "image_generation": False,
                        "code_interpreter": False,
                    },
                    "defaultFeatureIds": ["web_search"] if web_search else [],
                    "builtinTools": {"web_search": web_search},
                },
                "access_grants": [],
                "is_active": True,
                "updated_at": 1700000000,
                "created_at": 1700000000,
            }
        )

    assert build_models(manifest, [], user_id="admin-user", now=1700000000) == expected


def test_build_models_preserves_existing_fields_and_rejects_base_id_collision() -> None:
    reconciler = load_reconciler()
    build_models = require_callable(reconciler, "build_models")
    all_data = load_all_module("preserve_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    existing = [
        {
            "id": "chat",
            "user_id": "owner",
            "base_model_id": "router-chat",
            "name": "old",
            "params": {},
            "meta": {},
            "access_grants": [{"principal_type": "user", "principal_id": "x", "permission": "read"}],
            "is_active": True,
            "updated_at": 10,
            "created_at": 11,
        }
    ]

    models = build_models(manifest, existing, user_id="admin-user", now=20)
    assert models[0]["user_id"] == "owner"
    assert models[0]["access_grants"] == [{"principal_type": "user", "principal_id": "x", "permission": "read"}]
    assert models[0]["updated_at"] == 10
    assert models[0]["created_at"] == 11

    with pytest.raises(ValueError):
        build_models(
            manifest,
            [{"id": "chat", "base_model_id": None, "preset": False}],
            user_id="admin-user",
            now=20,
        )


def test_build_sync_payload_keeps_unrelated_rows_after_managed_presets() -> None:
    reconciler = load_reconciler()
    build_sync_payload = require_callable(reconciler, "build_sync_payload")
    all_data = load_all_module("sync_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    unrelated: dict[str, object] = {
        "id": "base-model",
        "user_id": "owner",
        "base_model_id": None,
        "name": "Base",
        "params": {},
        "meta": {},
        "access_grants": [],
        "is_active": True,
        "updated_at": 1,
        "created_at": 1,
    }

    payload = build_sync_payload(manifest, [unrelated], user_id="admin-user", now=2)

    assert [model["id"] for model in payload[:8]] == MODEL_IDS
    assert payload[8] == unrelated


def test_verify_models_reports_missing_managed_id_even_with_extra_rows() -> None:
    reconciler = load_reconciler()
    build_models = require_callable(reconciler, "build_models")
    verify_models = require_callable(reconciler, "verify_models")
    all_data = load_all_module("verify_missing_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    expected = build_models(manifest, [], user_id="admin-user", now=1)
    actual = [expected[0], {"id": "extra", "base_model_id": None}]

    with pytest.raises(RuntimeError, match="missing"):
        verify_models(expected, actual)


def test_read_env_file_requires_private_mode(tmp_path: Path) -> None:
    reconciler = load_reconciler()
    read_env_file = require_callable(reconciler, "read_env_file")
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=test-secret\n")
    env_path.chmod(0o600)
    assert read_env_file(env_path) == {"OPENWEBUI_ADMIN_API_KEY": "test-secret"}

    env_path.chmod(0o644)
    with pytest.raises(PermissionError):
        read_env_file(env_path)


def test_request_json_does_not_expose_error_body_or_secret_headers() -> None:
    reconciler = load_reconciler()
    request_json = require_callable(reconciler, "request_json")
    error = HTTPError(
        "http://127.0.0.1:13307/api/v1/models/sync",
        401,
        "Unauthorized",
        Message(),
        io.BytesIO(b'{"token":"super-secret"}'),
    )
    opener = RecordingOpener([error])

    with pytest.raises(RuntimeError) as raised:
        request_json("GET", "http://127.0.0.1:13307/api/v1/models/export", opener=opener, attempts=1)

    assert getattr(raised.value, "status", None) == 401
    assert "super-secret" not in str(raised.value)


def test_authenticate_uses_admin_api_key_header_without_exposing_it_in_request_line() -> None:
    reconciler = load_reconciler()
    authenticate = require_callable(reconciler, "authenticate")
    opener = RecordingOpener([FakeResponse({"id": "admin-user"})])

    headers, user_id = authenticate(
        "http://127.0.0.1:13307",
        {"OPENWEBUI_ADMIN_API_KEY": "admin-secret"},
        opener=opener,
    )

    assert user_id == "admin-user"
    assert headers == {"x-api-key": "admin-secret"}
    request = opener.requests[0]
    assert request.full_url == "http://127.0.0.1:13307/api/v1/users/user"
    assert "admin-secret" not in request.full_url
    assert request.get_header("X-api-key") == "admin-secret"


def test_authenticate_signs_in_when_no_admin_key_is_configured() -> None:
    reconciler = load_reconciler()
    authenticate = require_callable(reconciler, "authenticate")
    opener = RecordingOpener([FakeResponse({"token": "session-token", "id": "admin-user"})])

    headers, user_id = authenticate("http://127.0.0.1:13307", {}, opener=opener)

    assert user_id == "admin-user"
    assert headers == {"Authorization": "Bearer session-token"}
    request = opener.requests[0]
    assert request.full_url == "http://127.0.0.1:13307/api/v1/auths/signin"
    assert request.data is not None
    assert json.loads(cast(bytes, request.data)) == {"email": "", "password": ""}


def test_wait_ready_retries_transient_failures_with_bounded_backoff() -> None:
    reconciler = load_reconciler()
    wait_ready = require_callable(reconciler, "wait_ready")
    opener = RecordingOpener([URLError("not ready"), URLError("not ready"), FakeResponse({})])
    sleeps: list[float] = []

    wait_ready(
        "http://127.0.0.1:13307",
        {},
        attempts=3,
        backoff=0.5,
        opener=opener,
        sleep=sleeps.append,
    )

    assert len(opener.requests) == 3
    assert sleeps == [0.5, 1.0]


def test_reconcile_exports_syncs_verifies_and_is_idempotent(tmp_path: Path) -> None:
    reconciler = load_reconciler()
    reconcile = require_callable(reconciler, "reconcile")
    all_data = load_all_module("reconcile_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=admin-secret\n")
    env_path.chmod(0o600)
    opener = ModelApiOpener([])

    first = reconcile(
        "http://127.0.0.1:13307",
        manifest,
        resources_path,
        env_path,
        opener=opener,
        sleep=lambda _seconds: None,
        now=1700000000,
    )
    second = reconcile(
        "http://127.0.0.1:13307",
        manifest,
        resources_path,
        env_path,
        opener=opener,
        sleep=lambda _seconds: None,
        now=1700000000,
    )

    assert [model["id"] for model in first] == MODEL_IDS
    assert second == first
    assert len(opener.sync_payloads) == 2
    assert opener.sync_payloads[0] == opener.sync_payloads[1]
    sync_models = cast(list[dict[str, object]], opener.sync_payloads[0]["models"])
    assert [model["id"] for model in sync_models[:8]] == MODEL_IDS
    assert opener.import_payloads == []
    assert opener.deleted == []
    assert opener.paths[:5] == [
        ("GET", "/ready"),
        ("GET", "/api/v1/users/user"),
        ("GET", "/api/v1/models/export"),
        ("POST", "/api/v1/models/sync"),
        ("GET", "/api/v1/models/export"),
    ]
    assert opener.sync_payloads[0]["models"] == first


def test_reconcile_requires_authenticated_requests_when_no_admin_key_is_set(tmp_path: Path) -> None:
    reconciler = load_reconciler()
    reconcile = require_callable(reconciler, "reconcile")
    all_data = load_all_module("reconcile_no_key_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=\n")
    env_path.chmod(0o600)
    opener = ModelApiOpener([])

    reconcile(
        "http://127.0.0.1:13307",
        manifest,
        resources_path,
        env_path,
        opener=opener,
        sleep=lambda _seconds: None,
        now=1700000000,
    )

    assert ("POST", "/api/v1/auths/signin") in opener.paths
    export_request = next(request for request in opener.requests if urlparse(request.full_url).path.endswith("/export"))
    assert export_request.get_header("Authorization") == "Bearer session-token"


@pytest.mark.parametrize("status", [401, 403, 422])
def test_reconcile_treats_sync_auth_and_schema_errors_as_terminal(tmp_path: Path, status: int) -> None:
    reconciler = load_reconciler()
    reconcile = require_callable(reconciler, "reconcile")
    all_data = load_all_module(f"terminal_{status}_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=admin-secret\n")
    env_path.chmod(0o600)
    opener = ModelApiOpener([], sync_status=status)

    with pytest.raises(RuntimeError) as raised:
        reconcile(
            "http://127.0.0.1:13307",
            manifest,
            resources_path,
            env_path,
            opener=opener,
            sleep=lambda _seconds: None,
            now=1700000000,
        )

    assert getattr(raised.value, "status", None) == status
    assert opener.import_payloads == []


def test_reconcile_rejects_empty_sync_response(tmp_path: Path) -> None:
    reconciler = load_reconciler()
    reconcile = require_callable(reconciler, "reconcile")
    all_data = load_all_module("empty_sync_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=admin-secret\n")
    env_path.chmod(0o600)
    opener = ModelApiOpener([], sync_response=[])

    with pytest.raises(RuntimeError, match="empty"):
        reconcile(
            "http://127.0.0.1:13307",
            manifest,
            resources_path,
            env_path,
            opener=opener,
            sleep=lambda _seconds: None,
            now=1700000000,
        )

    assert opener.import_payloads == []


@pytest.mark.parametrize("status", [404, 405, 501])
def test_reconcile_import_fallback_deletes_stale_exported_ids(tmp_path: Path, status: int) -> None:
    reconciler = load_reconciler()
    reconcile = require_callable(reconciler, "reconcile")
    all_data = load_all_module(f"fallback_{status}_source")
    manifest = {
        "default_models": all_data.openwebui["default_models"],
        "model_map": all_data.openwebui["model_map"],
        "presets": all_data.openwebui["presets"],
    }
    resources_path = Path(ROOT) / "deploys" / "openwebui" / "files" / "aisix-resources.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENWEBUI_ADMIN_API_KEY=admin-secret\n")
    env_path.chmod(0o600)
    stale: dict[str, object] = {
        "id": "stale-model",
        "user_id": "admin-user",
        "base_model_id": None,
        "name": "Stale",
        "params": {},
        "meta": {},
        "access_grants": [],
        "is_active": True,
        "updated_at": 1,
        "created_at": 1,
    }
    opener = ModelApiOpener([stale], sync_status=status)

    result = reconcile(
        "http://127.0.0.1:13307",
        manifest,
        resources_path,
        env_path,
        opener=opener,
        sleep=lambda _seconds: None,
        now=1700000000,
    )

    assert [model["id"] for model in result] == MODEL_IDS
    assert len(opener.import_payloads) == 1
    assert opener.deleted == ["stale-model"]
    imported_models = cast(list[dict[str, object]], opener.import_payloads[0]["models"])
    assert [model["id"] for model in imported_models] == MODEL_IDS
