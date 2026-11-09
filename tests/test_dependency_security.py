from pathlib import Path

import httptools
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def test_urlencoded_field_limit_is_enforced():
    app = FastAPI()

    @app.post('/form')
    async def form(request: Request):
        values = await request.form(max_fields=2)
        return {'count': len(values)}

    with TestClient(app) as client:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        assert client.post('/form', content='a=1&b=2', headers=headers).json() == {'count': 2}
        assert client.post('/form', content='a=1&b=2&c=3', headers=headers).status_code == 400


def test_optional_parser_never_silently_truncates_long_path():
    path = b'/' + b'a' * 70000
    try:
        parsed = httptools.parse_url(b'http://example.test' + path)
    except (httptools.HttpParserInvalidURLError, ValueError):
        return  # Explicit rejection is safe; silent truncation is not.
    assert parsed.path == path


def test_deployment_manifests_use_the_same_dependencies():
    assert Path('requirements.txt').read_bytes() == Path('api-service/requirements.txt').read_bytes()
