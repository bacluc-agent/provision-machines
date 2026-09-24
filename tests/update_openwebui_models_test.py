import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

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


def load_module(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
