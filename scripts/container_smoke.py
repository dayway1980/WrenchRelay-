"""Run inside the candidate image only; never connect to production services."""
import importlib.util
import os
from pathlib import Path
import time

from fastapi.testclient import TestClient


def main():
    expected = Path('/app/backend/production.py')
    spec = importlib.util.find_spec('production')
    assert spec and Path(spec.origin) == expected, 'Wrong production entrypoint'
    import production
    import server

    assert server.FRONTEND_URL == os.environ['FRONTEND_URL']
    assert server.LEGAL_ENTITY_NAME == 'WrenchRelay LLC'
    with TestClient(production.app) as client:
        assert client.get('/api/health/live').status_code == 200
        for path in ['/', '/industrial', '/automotive']:
            response = client.get(path)
            assert response.status_code == 200, path
            assert '<html' in response.text.lower(), path
        assets = list(Path('/app/frontend/build/static').rglob('*.js'))
        assert assets, 'Compiled JavaScript is missing'
        asset_url = '/' + assets[0].relative_to('/app/frontend/build').as_posix()
        assert client.get(asset_url).status_code == 200
        assert client.get('/api/unknown-container-smoke-route').status_code == 404
        origin = 'https://custom.example.invalid'
        response = client.options('/api/config', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'GET',
        })
        assert response.headers.get('access-control-allow-origin') == origin
        assert client.get('/api/config').json()['legal_entity'] == 'WrenchRelay LLC'

        require_database = os.environ.get('SMOKE_REQUIRE_DATABASE') == '1'
        if require_database:
            for attempt in range(20):
                response = client.get('/api/health/ready')
                if response.status_code == 200:
                    break
                time.sleep(1)
            assert response.status_code == 200, 'Test database never became ready'
            assert response.json()['database'] == 'ok'
        else:
            assert not server.MONGO_URL, 'Offline smoke must have no database URL'
            assert client.get('/api/health/ready').status_code == 503
    print('PASS container entrypoint, assets, routes, CORS, legal identity, readiness')


if __name__ == '__main__':
    main()
