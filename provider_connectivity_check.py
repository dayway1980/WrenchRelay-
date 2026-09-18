#!/usr/bin/env python3
"""Read-only provider connectivity validation harness.

Purpose:
    Verify that OpenAI and (optionally) Gemini/XAI are reachable and
    correctly configured in a NON-PRODUCTION test environment, using only
    environment variable references that Railway injects (never copied
    secret values). This script performs no mutations and touches no
    customer data.

Safety guarantees:
    - Uses only the standard library (urllib.request); no third-party deps.
    - Never prints API key values, model identifiers beyond what is
      explicitly allowed by the output contract, full response bodies, or
      any customer data.
    - All network requests are capped at a 10 second timeout.
    - Missing/empty credentials are reported as FAIL/UNCONFIGURED without
      attempting a network call.

Output contract (one line per provider tested):
    PROVIDER [OpenAI|Gemini|XAI] STATUS [SUCCESS|FAIL] HTTP_CODE [<code>|UNCONFIGURED] MODEL [<model>|UNKNOWN]
"""

import json
import os
import urllib.error
import urllib.request

REQUEST_TIMEOUT_SECONDS = 10

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def _redact_presence(value):
    """Never log the value itself; only whether it is present."""
    return "[REDACTED]" if value else "[ABSENT]"


def _emit(provider, status, http_code, model):
    print(f"PROVIDER {provider} STATUS {status} HTTP_CODE {http_code} MODEL {model}")


def _post_json(url, payload, headers, timeout=REQUEST_TIMEOUT_SECONDS):
    """Minimal POST helper using urllib. Returns (status_code, parsed_json_or_none)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            raw = resp.read()
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                parsed = None
            return status_code, parsed
    except urllib.error.HTTPError as e:
        raw = None
        try:
            raw = e.read()
        except Exception:
            pass
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                parsed = None
        return e.code, parsed
    except urllib.error.URLError as e:
        raise ConnectionError(str(e.reason)) from e


def check_openai():
    provider = "OpenAI"
    model = os.environ.get("OPENAI_MODEL")
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or OPENAI_DEFAULT_BASE_URL

    if not api_key or not model:
        _emit(provider, "FAIL", "UNCONFIGURED", "UNKNOWN")
        return

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5,
    }

    try:
        status_code, parsed = _post_json(url, payload, headers)
    except ConnectionError:
        _emit(provider, "FAIL", "ConnectionError", "UNKNOWN")
        return
    except TimeoutError:
        _emit(provider, "FAIL", "Timeout", "UNKNOWN")
        return
    except Exception as e:
        _emit(provider, "FAIL", type(e).__name__, "UNKNOWN")
        return

    resolved_model = "UNKNOWN"
    if isinstance(parsed, dict):
        resolved_model = parsed.get("model") or "UNKNOWN"

    status = "SUCCESS" if 200 <= status_code < 300 else "FAIL"
    _emit(provider, status, status_code, resolved_model)


def check_gemini():
    provider = "Gemini"
    model = os.environ.get("GEMINI_MODEL")
    api_key = os.environ.get("GEMINI_API_KEY")
    base_url = os.environ.get("GEMINI_BASE_URL")

    if not api_key or not model or not base_url:
        _emit(provider, "FAIL", "UNCONFIGURED", "UNKNOWN")
        return

    # Gemini REST API expects the model + API key in the URL path/query;
    # key is passed as a query parameter, not logged anywhere.
    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": "test"}]}
        ],
        "generationConfig": {"maxOutputTokens": 5},
    }

    try:
        status_code, parsed = _post_json(url, payload, headers)
    except ConnectionError:
        _emit(provider, "FAIL", "ConnectionError", "UNKNOWN")
        return
    except TimeoutError:
        _emit(provider, "FAIL", "Timeout", "UNKNOWN")
        return
    except Exception as e:
        _emit(provider, "FAIL", type(e).__name__, "UNKNOWN")
        return

    resolved_model = "UNKNOWN"
    if isinstance(parsed, dict):
        resolved_model = parsed.get("modelVersion") or model or "UNKNOWN"

    status = "SUCCESS" if 200 <= status_code < 300 else "FAIL"
    _emit(provider, status, status_code, resolved_model)


def check_xai():
    provider = "XAI"
    model = os.environ.get("XAI_MODEL")
    base_url = os.environ.get("XAI_BASE_URL")
    api_key = os.environ.get("XAI_API_KEY")

    # XAI is optional; only run the check if all inputs are present.
    if not model and not base_url and not api_key:
        return

    if not api_key or not model or not base_url:
        _emit(provider, "FAIL", "UNCONFIGURED", "UNKNOWN")
        return

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5,
    }

    try:
        status_code, parsed = _post_json(url, payload, headers)
    except ConnectionError:
        _emit(provider, "FAIL", "ConnectionError", "UNKNOWN")
        return
    except TimeoutError:
        _emit(provider, "FAIL", "Timeout", "UNKNOWN")
        return
    except Exception as e:
        _emit(provider, "FAIL", type(e).__name__, "UNKNOWN")
        return

    resolved_model = "UNKNOWN"
    if isinstance(parsed, dict):
        resolved_model = parsed.get("model") or "UNKNOWN"

    status = "SUCCESS" if 200 <= status_code < 300 else "FAIL"
    _emit(provider, status, status_code, resolved_model)


def main():
    # Never print raw credential values; presence-only diagnostics if needed
    # for local debugging can be enabled by uncommenting the following lines.
    # print("OPENAI_API_KEY:", _redact_presence(os.environ.get("OPENAI_API_KEY")))
    # print("GEMINI_API_KEY:", _redact_presence(os.environ.get("GEMINI_API_KEY")))

    check_openai()
    check_gemini()
    check_xai()


if __name__ == "__main__":
    main()
