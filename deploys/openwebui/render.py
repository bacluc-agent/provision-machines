from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

SAFE_ENV_VALUE = re.compile(r"[A-Za-z0-9_./:+,@=-]+")


def _dotenv_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("environment values cannot contain newlines")
    if value.startswith("${") and value.endswith("}"):
        return f'"{value}"'
    if not value or SAFE_ENV_VALUE.fullmatch(value):
        return value
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def render_env(data: dict[str, object], aisix_version: str) -> str:
    values: dict[str, str] = {"AISIX_VERSION": aisix_version}
    for key in (
        "BRAVE_API_KEY",
        "ZEN_API_KEY",
        "ZEN_API_BASE",
        "ZEN_MODEL",
        "OLLAMA_API_KEY",
        "OLLAMA_API_BASE",
        "OLLAMA_MODEL",
        "OPENWEBUI_CALLER_KEY",
        "OPENWEBUI_ADMIN_API_KEY",
    ):
        value = data.get(key, "")
        values[key] = str(value)
    extra_env = data.get("extra_env", {})
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            values[str(key)] = str(value)
    return "".join(f"{key}={_dotenv_value(value)}\n" for key, value in values.items())


def render_manifest(data: dict[str, object]) -> str:
    manifest = {
        "default_models": data["default_models"],
        "model_map": data["model_map"],
        "presets": data["presets"],
    }
    return json.dumps(manifest, indent=2) + "\n"


def reconciliation_command(compose_project_dir: str) -> str:
    script = shlex.quote(f"{compose_project_dir}/update-openwebui-models.py")
    manifest = shlex.quote(f"{compose_project_dir}/openwebui-models.json")
    resources = shlex.quote(f"{compose_project_dir}/aisix-resources.yaml")
    env_file = shlex.quote(f"{compose_project_dir}/.env")
    url = shlex.quote("http://127.0.0.1:13307")
    return (
        "systemctl start openwebui.service && "
        "docker kill --signal=HUP aisix >/dev/null && "
        f"python3 {script} --url {url} --manifest {manifest} --resources {resources} --env-file {env_file}"
    )


def render_compose(path: str, aisix_version: str) -> str:
    return Path(path).read_text(encoding="utf-8").replace("${AISIX_VERSION}", aisix_version)
