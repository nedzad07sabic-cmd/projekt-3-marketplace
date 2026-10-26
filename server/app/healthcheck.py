"""Probe the private application port without following redirects or proxies."""
from __future__ import annotations
import json
import os
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(site_url: str, *, port: int = 8000) -> bool:
    try:
        site = urlsplit(site_url)
        if (site.scheme != 'https' or not site.hostname or site.username
                or site.password or site.port not in (None, 443)):
            return False
        request = Request(f'http://127.0.0.1:{port}/health/', headers={
            'Host': site.netloc, 'X-Forwarded-Proto': 'https',
        })
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=3) as response:
            payload = response.read(4097)
            return (response.status == 200 and len(payload) <= 4096
                    and json.loads(payload) == {'status': 'ok'})
    except (ValueError, OSError, URLError):
        return False


if __name__ == '__main__':
    raise SystemExit(0 if probe(os.environ.get('SITE_URL', '')) else 1)
