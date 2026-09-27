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
    if any(
        not isinstance(model, dict)
        or not isinstance(model.get("id"), str)
        or not model["id"].strip()
        for model in models
    ):
        raise ModelFetchError("provider returned an invalid model response")
    ids = [model["id"] for model in models]
    if len(ids) != len(set(ids)):
        raise ModelFetchError("provider returned duplicate model IDs")
    return sorted(models, key=lambda model: model["id"])


def get_display_name(model):
    name = model.get("name")
    return name if isinstance(name, str) and name.strip() else model["id"]


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


def _skip_jsonc(text, position):
    while position < len(text):
        if text[position].isspace():
            position += 1
        elif text[position : position + 2] == "//":
            newline = text.find("\n", position + 2)
            position = len(text) if newline == -1 else newline + 1
        elif text[position : position + 2] == "/*":
            end = text.find("*/", position + 2)
            position = len(text) if end == -1 else end + 2
        else:
            break
    return position


def _string_end(text, position):
    position += 1
    while position < len(text):
        if text[position] == "\\":
            position += 2
        elif text[position] == '"':
            return position + 1
        else:
            position += 1
    raise ValueError("unterminated JSON string")


def _matching_end(text, position):
    pairs = {"{": "}", "[": "]"}
    stack = [pairs[text[position]]]
    position += 1
    while position < len(text) and stack:
        if text[position] == '"':
            position = _string_end(text, position)
        elif text[position : position + 2] == "//":
            position = _skip_jsonc(text, position)
        elif text[position : position + 2] == "/*":
            position = _skip_jsonc(text, position)
        elif text[position] in pairs:
            stack.append(pairs[text[position]])
            position += 1
        elif text[position] == stack[-1]:
            stack.pop()
            position += 1
        else:
            position += 1
    if stack:
        raise ValueError("unterminated JSON value")
    return position


def _property_value_span(text, object_start, property_name):
    if text[object_start] != "{":
        raise ValueError("expected JSON object")
    position = object_start + 1
    depth = 0
    while position < len(text):
        position = _skip_jsonc(text, position)
        if position >= len(text) or (text[position] == "}" and depth == 0):
            break
        if text[position] == '"':
            string_start = position
            position = _string_end(text, position)
            if depth:
                continue
            if json.loads(text[string_start:position]) != property_name:
                continue
            colon = _skip_jsonc(text, position)
            if colon >= len(text) or text[colon] != ":":
                continue
            value_start = _skip_jsonc(text, colon + 1)
            if value_start >= len(text):
                break
            if text[value_start] in "[{":
                return value_start, _matching_end(text, value_start)
            value_end = value_start
            while value_end < len(text) and text[value_end] not in ",}":
                value_end += 1
            return value_start, value_end
        if text[position] in "[{":
            depth += 1
        elif text[position] in "]}":
            depth -= 1
        position += 1
    raise ValueError(f"missing JSON property: {property_name}")


def npm_name(spec):
    at = spec.rfind("@")
    return spec[:at] if at > 0 else None


def update_config(models, config_path, npm_package=None, provider_name=None, api_base_url=None):
    with open(config_path) as config_file:
        text = config_file.read()

    json.loads(normalize_jsonc(text))
    provider_name = provider_name if provider_name and provider_name.strip() else PROVIDER_NAME
    models_dict = {
        model["id"]: {"name": get_display_name(model)} for model in sorted(models, key=lambda item: item["id"])
    }
    model_text = json.dumps(models_dict, indent=2)
    lines = model_text.splitlines()
    provider_start, _ = _property_value_span(text, 0, "provider")
    provider_model_start, provider_model_end = _property_value_span(text, provider_start, provider_name)
    try:
        models_start, models_end = _property_value_span(text, provider_model_start, "models")
    except ValueError:
        closing = provider_model_end - 1
        line_start = text.rfind("\n", 0, provider_model_start) + 1
        provider_indentation = text[line_start:provider_model_start]
        provider_indentation = provider_indentation[: len(provider_indentation) - len(provider_indentation.lstrip())]
        before = text[:closing].rstrip()
        separator = "" if before.endswith(("{", ",")) else ","
        replacement = (
            before
            + separator
            + "\n"
            + provider_indentation
            + "  \"models\": "
            + lines[0]
            + "\n"
            + "\n".join(provider_indentation + "  " + line for line in lines[1:])
            + "\n"
            + provider_indentation
        )
        text = replacement + text[closing:]
    else:
        line_start = text.rfind("\n", 0, models_start) + 1
        indentation = text[line_start:models_start]
        indentation = indentation[: len(indentation) - len(indentation.lstrip())]
        replacement = lines[0] + "\n" + "\n".join(indentation + line for line in lines[1:])
        text = text[:models_start] + replacement + text[models_end:]
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
