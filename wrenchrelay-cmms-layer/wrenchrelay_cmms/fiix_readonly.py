"""Prepare Fiix sandbox FindRequest only. No transport or write methods.

Wire convention: official Fiix No-SDK guide. Live acceptance is outstanding.
"""
from dataclasses import dataclass, field
import hashlib
import hmac
import json
from urllib.parse import urlencode, urlsplit


@dataclass(frozen=True)
class Credentials:
    app_key: str = field(repr=False)
    access_key: str = field(repr=False)
    secret: str = field(repr=False)


@dataclass(frozen=True, repr=False)
class PreparedRead:
    url: str
    headers: dict
    body: bytes
    method: str = 'POST'

    def __repr__(self):
        return 'PreparedRead(method=POST, credentials=REDACTED, transport=DISABLED)'


def prepare_find(*, base_url, credentials, object_class, timestamp_ms, offset=0, limit=50):
    parsed = urlsplit(base_url)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
            or parsed.query or parsed.fragment or parsed.path != '/api/'
            or not host.endswith('.fiixsandbox.com')
            or host.count('.') != 2 or not host.split('.')[0].replace('-', '').isalnum()):
        raise ValueError('An explicit HTTPS Fiix sandbox /api/ URL is required')
    if object_class not in ('Asset', 'WorkOrder'):
        raise ValueError('Only Asset and WorkOrder FindRequest preparation allowed')
    if type(timestamp_ms) is not int or timestamp_ms <= 0:
        raise ValueError('Explicit epoch-millisecond timestamp required')
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Bounded paging required')
    if not all(isinstance(v, str) and v for v in (credentials.app_key, credentials.access_key, credentials.secret)):
        raise ValueError('Credentials required; never use production keys')
    params = {'service': 'cmms', 'timestamp': timestamp_ms, 'appKey': credentials.app_key,
              'accessKey': credentials.access_key, 'signatureMethod': 'HmacSHA256', 'signatureVersion': 1}
    url = base_url + '?' + urlencode(params)
    signature = hmac.new(credentials.secret.encode(), url.removeprefix('https://').encode(), hashlib.sha256).hexdigest()
    body = {'_maCn': 'FindRequest', 'className': object_class,
            'fields': 'id,strName' if object_class == 'Asset' else 'id,strCode',
            'offset': offset, 'limit': limit, 'requestSentUnixTime': timestamp_ms}
    return PreparedRead(url, {'Content-Type': 'text/plain', 'Authorization': signature},
                        json.dumps(body, separators=(',', ':')).encode())
