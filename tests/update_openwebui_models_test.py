import importlib.util
import os
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
