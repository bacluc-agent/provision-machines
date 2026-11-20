from typing import Any

from openwebui_env import env_lines

BASE: dict[str, Any] = {
    "opencode_api_key": "oc-key-1",
    "opencode_api_key_2": "oc-key-2",
    "opencode_api_key_3": "oc-key-3",
    "opencode_base_url": "https://opencode.example/v1",
    "requesty_api_key": "requesty-key",
    "requesty_base_url": "https://requesty.example/v1",
    "cortecs_api_key": "cortecs-key",
    "cortecs_base_url": "https://cortecs.example/v1",
    "openwebui_caller_key": "caller-key",
    "zen_model_chat": "zen-chat",
    "zen_model_chat_thinking": "zen-thinking",
    "zen_model_web_research": "zen-web",
    "zen_model_fast": "zen-fast",
    "requesty_model_chat": "requesty-chat",
    "cortecs_model_chat": "cortecs-chat",
    "extra_env": {},
}


def test_env_lines_base_order_and_caller_key_mirror() -> None:
    assert env_lines(BASE) == [
        "OPENCODE_API_KEY=oc-key-1",
        "OPENCODE_API_KEY_2=oc-key-2",
        "OPENCODE_API_KEY_3=oc-key-3",
        "OPENCODE_BASE_URL=https://opencode.example/v1",
        "REQUESTY_API_KEY=requesty-key",
        "REQUESTY_BASE_URL=https://requesty.example/v1",
        "CORTECS_API_KEY=cortecs-key",
        "CORTECS_BASE_URL=https://cortecs.example/v1",
        "OPENWEBUI_CALLER_KEY=caller-key",
        "OPENAI_API_KEYS=caller-key",
        "ZEN_MODEL_CHAT=zen-chat",
        "ZEN_MODEL_CHAT_THINKING=zen-thinking",
        "ZEN_MODEL_WEB_RESEARCH=zen-web",
        "ZEN_MODEL_FAST=zen-fast",
        "REQUESTY_MODEL_CHAT=requesty-chat",
        "CORTECS_MODEL_CHAT=cortecs-chat",
    ]


def test_env_lines_appends_extra_env_in_insertion_order() -> None:
    openwebui = {
        **BASE,
        "extra_env": {
            "ENABLE_OPENAI_API": "true",
            "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
            "DEFAULT_MODELS": "chat,chat_thinking",
        },
    }

    assert env_lines(openwebui)[-3:] == [
        "ENABLE_OPENAI_API=true",
        "OPENAI_API_BASE_URL=http://aisix:3000/v1",
        "DEFAULT_MODELS=chat,chat_thinking",
    ]


def test_env_lines_ignores_openai_api_keys_in_extra_env() -> None:
    openwebui = {
        **BASE,
        "extra_env": {
            "OPENAI_API_KEYS": "overridden",
            "ENABLE_API_KEYS": "true",
        },
    }

    lines = env_lines(openwebui)

    assert lines.count("OPENAI_API_KEYS=caller-key") == 1
    assert "OPENAI_API_KEYS=overridden" not in lines
    assert lines[-1] == "ENABLE_API_KEYS=true"
