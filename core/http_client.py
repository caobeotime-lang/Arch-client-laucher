"""
Minimal HTTP client built only on Python's standard library (urllib).

Why this exists instead of using `requests`: python-for-android's current
Python 3.14 recipe fails to install `requests` -- its dependency
charset-normalizer now ships a compiled wheel tagged for a platform p4a's
bundled pip doesn't recognize ("... is not a supported wheel on this
platform"), so the whole build aborts before it ever reaches our code
(see https://github.com/kivy/python-for-android/issues/3364). Using only
the standard library sidesteps that dependency chain entirely, and this
app's HTTP needs are small enough that it costs nothing.

Exposes a tiny requests-like Response so call sites barely change:
resp.status_code, resp.ok, resp.text, resp.json(), resp.headers.
"""

import json as _json
import urllib.error
import urllib.request


class Response:
    def __init__(self, status_code, headers, body_bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body_bytes

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    @property
    def text(self):
        return self._body.decode("utf-8", errors="replace")

    def json(self):
        return _json.loads(self._body.decode("utf-8"))

    def iter_content(self, chunk_size=65536):
        # Kept for API compatibility with the old requests-based call
        # sites; the body is already fully read by the time we get here.
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]


def _do_request(method, url, data_bytes=None, headers=None, timeout=15):
    req = urllib.request.Request(url, data=data_bytes, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, dict(r.headers), r.read())
    except urllib.error.HTTPError as e:
        # Same shape as a non-raising requests response: callers check
        # .ok / .status_code themselves rather than getting an exception.
        return Response(e.code, dict(e.headers or {}), e.read())


def get(url, headers=None, timeout=15):
    return _do_request("GET", url, headers=headers, timeout=timeout)


def post_json(url, json_body, headers=None, timeout=15):
    body = _json.dumps(json_body).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    merged_headers.update(headers or {})
    return _do_request("POST", url, data_bytes=body, headers=merged_headers, timeout=timeout)


def post_form(url, form_dict, headers=None, timeout=15):
    from urllib.parse import urlencode
    body = urlencode(form_dict).encode("utf-8")
    merged_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    merged_headers.update(headers or {})
    return _do_request("POST", url, data_bytes=body, headers=merged_headers, timeout=timeout)


def download_to_file(url, dest_path, timeout=30):
    """Stream a URL straight to disk. Returns (total_bytes, response_headers)."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        total = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        return total, dict(r.headers)
