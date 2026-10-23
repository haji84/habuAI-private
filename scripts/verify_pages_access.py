#!/usr/bin/env python3
"""Fail closed unless production and preview Pages hosts redirect to Cloudflare Access.

This unauthenticated check is necessary but not sufficient: an owner must also
test successful sign-in and verify that the Access policy only allows them.
"""
from __future__ import annotations

import argparse
import urllib.error
import urllib.parse
import urllib.request


class AccessGateError(RuntimeError):
    pass


def assert_url(value: str, *, preview: bool) -> str:
    p = urllib.parse.urlsplit(value)
    if p.scheme != "https" or p.port is not None or p.username or p.password:
        raise AccessGateError("Expected HTTPS pages.dev URL with no userinfo or port")
    host = (p.hostname or "").lower()
    if not p.path in ("", "/") or p.query or p.fragment:
        raise AccessGateError("Expected origin URL without path, query or fragment")
    production = "hub-natural-private.pages.dev"
    if preview:
        if not host.endswith("." + production) or len(host) <= len(production) + 1:
            raise AccessGateError("Expected a real preview subdomain of the production host")
    elif host != production:
        raise AccessGateError("Expected the canonical production pages.dev host")
    return value.rstrip("/") + "/"


def check_redirect(*, code: int, location: str | None, expected_host: str = '') -> None:
    if code not in (301, 302, 303, 307, 308):
        raise AccessGateError(f"Unauthenticated response HTTP {code}, not proven to be Access-protected")
    if not location:
        raise AccessGateError("Missing Access redirect location")
    parsed = urllib.parse.urlsplit(location)
    domain = (parsed.hostname or "").lower()
    access_domain = domain.endswith(".cloudflareaccess.com")
    access_path = parsed.path.startswith("/cdn-cgi/access/login") and domain == expected_host
    if not access_domain and not access_path:
        raise AccessGateError("Redirect does not identify a Cloudflare Access login")
    if parsed.scheme != "https" and not location.startswith("/cdn-cgi/access/login"):
        raise AccessGateError("Insecure Access login redirect")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


def verify(url: str) -> None:
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={
        "User-Agent": "HUB-NATURAL-Preflight/1.0",
        "Cache-Control": "no-store",
    })
    try:
        with opener.open(request, timeout=15) as response:
            code, location = response.status, response.headers.get("Location")
    except urllib.error.HTTPError as exc:
        code, location = exc.code, exc.headers.get("Location")
    except urllib.error.URLError as exc:
        raise AccessGateError(f"Host unavailable: {exc.reason}") from exc
    check_redirect(code=code, location=location, expected_host=urllib.parse.urlsplit(url).hostname or "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--preview", help="Optional existing preview hostname")
    args = parser.parse_args()
    production = assert_url(args.production, preview=False)
    urls = [production]
    if args.preview:
        preview = assert_url(args.preview, preview=True)
        if production == preview:
            raise AccessGateError("Production and preview cannot be identical")
        urls.append(preview)
    for url in urls:
        verify(url)
        print("Access gate PASS (unauthenticated redirect):", url)


if __name__ == "__main__":
    main()
