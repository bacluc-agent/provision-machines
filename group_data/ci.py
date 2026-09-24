vshn_tools = {"enabled": True}

basicsetup = {
    "enabled": True,
}

docker = {
    "enabled": True,
    "provision_daemon_json": True,
}

bash = {
    "enabled": True,
}

shell_includes = {
    "enabled": True,
}

zsh = {
    "enabled": False,
}

basic_utils = {
    "enable_go": True,
    "python": {
        "venvs": ["test-env"],
    },
}

flatpaks: list[str] = []

fluxcd = {
    "enabled": True,
}

fzf = {
    "enabled": True,
}

git_lfs = {
    "enabled": True,
}

kubectl = {
    "enabled": False,
    "enable_oidc_plugin": True,
}

nvm = {
    "_sudo_for_global_install": True,
}

tmux = {
    "enabled": True,
}

nvim = {
    "enabled": False,
}

lazygit = {
    "enabled": True,
}

ollama = {
    "enabled": False,
}

t3_code = {
    "enabled": True,
}

homebrew = {
    "enabled": True,
}

snap = {
    "enabled": False,
}

snaps: list[str] = []

sysctl = {
    "enabled": True,
}

motd = {
    "enable_disk_usage": True,
}

vifm = {
    "enabled": True,
}

jetbrains = {
    "enabled": True,
}

okular = {
    "enabled": True,
}

zed = {
    "enabled": False,
}

hashicorp_apt_repo = {
    "enabled": False,
}

hashicorp_vault_cli = {
    "enabled": False,
}

openwebui = {
    "enabled": False,
    "router_backend": "AISIX",
    "router_config_path": "aisix-resources.yaml",
    "openai_compatible_base_url": "http://aisix:3000/v1",
    "default_models": [
        "chat",
        "chat_thinking",
        "web_research",
        "translate_de",
        "translate_en",
        "fix_grammar_en",
        "fix_grammar_de",
        "linux_cli",
    ],
    "model_map": {
        "chat": "router-chat",
        "chat_thinking": "router-chat-thinking",
        "web_research": "router-web-research",
        "translate_de": "router-translate-de",
        "translate_en": "router-translate-en",
        "fix_grammar_en": "router-fix-grammar-en",
        "fix_grammar_de": "router-fix-grammar-de",
        "linux_cli": "router-linux-cli",
    },
    "presets": [
        {"id": "chat", "name": "Chat", "system": "You are a helpful assistant.", "web_search": False},
        {
            "id": "chat_thinking",
            "name": "Chat (Thinking)",
            "system": "Think carefully before answering.",
            "web_search": False,
        },
        {
            "id": "web_research",
            "name": "Web Research",
            "system": "Research answers with web search and cite the sources.",
            "web_search": True,
        },
        {
            "id": "translate_de",
            "name": "Translate to German",
            "system": "Translate the user's text into German and return only the translation.",
            "web_search": False,
        },
        {
            "id": "translate_en",
            "name": "Translate to English",
            "system": "Translate the user's text into English and return only the translation.",
            "web_search": False,
        },
        {
            "id": "fix_grammar_en",
            "name": "Fix English Grammar",
            "system": "Correct English grammar and preserve the original meaning.",
            "web_search": False,
        },
        {
            "id": "fix_grammar_de",
            "name": "Fix German Grammar",
            "system": "Correct German grammar and preserve the original meaning.",
            "web_search": False,
        },
        {
            "id": "linux_cli",
            "name": "Linux CLI",
            "system": "Help with Linux command-line tasks and return safe, practical commands.",
            "web_search": False,
        },
    ],
    "extra_env": {
        "ENABLE_OPENAI_API": "true",
        "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
        "OPENAI_API_KEYS": "${OPENWEBUI_CALLER_KEY}",
        "DEFAULT_MODELS": "chat,chat_thinking,web_research,translate_de,translate_en,fix_grammar_en,fix_grammar_de,linux_cli",
        "ENABLE_MODEL_FILTER": "true",
        "MODEL_FILTER_LIST": "chat,chat_thinking,web_research,translate_de,translate_en,fix_grammar_en,fix_grammar_de,linux_cli",
    },
    # Set in local.py — copied into the OpenWebUI project .env with mode 600
    "BRAVE_API_KEY": "",
    # Set in local.py — copied into the OpenWebUI project .env with mode 600
    "ZEN_API_KEY": "",
    "ZEN_API_BASE": "https://opencode.ai/zen/go/v1",
    "ZEN_MODEL": "deepseek-v4-flash",
    # Set in local.py — copied into the OpenWebUI project .env with mode 600
    "OLLAMA_API_KEY": "",
    "OLLAMA_API_BASE": "http://host.docker.internal:11434/v1",
    "OLLAMA_MODEL": "qwen2.5:3b",
    # Set in local.py — copied into the OpenWebUI project .env with mode 600
    "OPENWEBUI_CALLER_KEY": "",
    # Set in local.py — copied into the OpenWebUI project .env with mode 600
    "OPENWEBUI_ADMIN_API_KEY": "",
}

vagrant = {
    "enabled": False,
}

ubuntu_cleanup = {
    "enabled": True,
}

ubuntu_desktop = {
    "enabled": False,
}

displaylink_driver = {
    "enabled": False,
}

charging_state_monitor = {
    "enabled": False,
}
