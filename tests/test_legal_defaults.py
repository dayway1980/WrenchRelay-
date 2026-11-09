import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize('path', ['server.py', 'api-service/main.py'])
@pytest.mark.parametrize('value, expected', [
    (None, 'WrenchRelay LLC'),
    ('', 'WrenchRelay LLC'),
    ('   ', 'WrenchRelay LLC'),
    ('Configured Operator LLC', 'Configured Operator LLC'),
])
def test_legal_default_handles_empty_settings(monkeypatch, path, value, expected):
    monkeypatch.delenv('MONGO_URL', raising=False)
    monkeypatch.delenv('MONGODB_URI', raising=False)
    if value is None:
        monkeypatch.delenv('LEGAL_ENTITY_NAME', raising=False)
    else:
        monkeypatch.setenv('LEGAL_ENTITY_NAME', value)
    spec = importlib.util.spec_from_file_location('legal_default_test', Path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.LEGAL_ENTITY_NAME == expected
