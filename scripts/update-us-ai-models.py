#!/usr/bin/env python3
"""Update the VSHN US AI models in the opencode config."""

import argparse
import getpass
import json
import os
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE_URL = "https://us-ai.corp.vshn.net/api/v1"
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deploys",
    "development_tools",
    "ai_agent_devcontainer",
    "files",
    "opencode",
    "opencode.jsonc",
)
PROVIDER_NAME = "vshn-us-ai"


class ModelFetchError(Exception):
    pass


def fetch_models(api_key=None, base_url=None):
    url = (base_url or API_BASE_URL).rstrip("/") + "/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            status = getattr(response, "status", None) or response.getcode()
            if not 200 <= status < 300:
                raise ModelFetchError("provider returned a non-success status")
            data = json.loads(response.read().decode())
    except HTTPError as error:
        raise ModelFetchError("provider request failed") from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeError) as error:
        raise ModelFetchError("provider request failed") from error

    if not isinstance(data, dict) or not isinstance(data.get("data"), list) or not data["data"]:
        raise ModelFetchError("provider returned an invalid model response")

    models = data["data"]
    if any(not isinstance(model, dict) or not isinstance(model.get("id"), str) or not model["id"] for model in models):
        raise ModelFetchError("provider returned an invalid model response")
    ids = [model["id"] for model in models]
    if len(ids) != len(set(ids)):
        raise ModelFetchError("provider returned duplicate model IDs")
    return sorted(models, key=lambda model: model["id"])


def get_display_name(model):
    name = model.get("name")
    return name if isinstance(name, str) and name else model["id"]


def filter_models(models, mode="default", price_class=None):
    if price_class:
        return [
            model
            for model in models
            if model["id"].startswith(f"{price_class}.") or model["id"].startswith(f"{price_class}/")
        ]
    return list(models)


def normalize_jsonc(text):
    result = []
    i = 0
    in_string = False
    while i < len(text):
        if in_string:
            if text[i] == "\\" and i + 1 < len(text):
                result.extend((text[i], text[i + 1]))
                i += 2
                continue
            if text[i] == '"':
                in_string = False
            result.append(text[i])
            i += 1
        elif text[i : i + 2] == "//":
            while i < len(text) and text[i] != "\n":
                i += 1
        elif text[i : i + 2] == "/*":
            i += 2
            while i < len(text) and text[i : i + 2] != "*/":
                i += 1
            i += 2
        elif text[i] == '"':
            in_string = True
            result.append(text[i])
            i += 1
        elif text[i] == ",":
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in "}]":
                i += 1
                continue
            result.append(text[i])
            i += 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def npm_name(spec):
    at = spec.rfind("@")
    return spec[:at] if at > 0 else None


def update_config(models, config_path, npm_package=None, provider_name=None, api_base_url=None):
    with open(config_path) as config_file:
        config = json.loads(normalize_jsonc(config_file.read()))

    provider_name = provider_name or PROVIDER_NAME
    models_dict = {
        model["id"]: {"name": get_display_name(model)} for model in sorted(models, key=lambda item: item["id"])
    }
    config["provider"][provider_name] = {
        "npm": npm_package or "@ai-sdk/openai-compatible",
        "name": "VSHN US AI",
        "models": models_dict,
    }
    text = json.dumps(config, indent=2) + "\n"
    directory = os.path.dirname(os.path.abspath(config_path))
    mode = os.stat(config_path).st_mode
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as temporary:
            temporary_path = temporary.name
            temporary.write(text)
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, config_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
    print(f"Updated {len(models_dict)} models in {config_path}")


def list_models(models):
    for model in models:
        print(f"{model['id']}  →  {get_display_name(model)}")


def main():
    parser = argparse.ArgumentParser(description="Update VSHN US AI models in opencode config")
    parser.add_argument("--all", action="store_true", help="Include all models")
    parser.add_argument("--list", action="store_true", help="List available models without updating config")
    parser.add_argument("--price-class", help="Only include models with this provider prefix")
    parser.add_argument("--api-key", default=os.environ.get("US_AI_API_KEY"))
    parser.add_argument("--api-base-url", default=API_BASE_URL)
    parser.add_argument("--config-path", default=CONFIG_PATH)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("US_AI_API_KEY")
    if not api_key:
        api_key = getpass.getpass("US AI API key: ")
    try:
        models = fetch_models(api_key=api_key, base_url=args.api_base_url)
        selected = filter_models(models, price_class=args.price_class)
        if not selected:
            raise ModelFetchError("no models matched the requested filter")
        if args.list:
            list_models(selected)
            return
        update_config(selected, config_path=args.config_path, api_base_url=args.api_base_url)
    except ModelFetchError as error:
        print(f"Unable to refresh models: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
