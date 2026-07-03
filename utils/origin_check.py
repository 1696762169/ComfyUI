"""Host/Origin CSRF check for the loopback dev server.

Extracted verbatim from ``server.create_origin_only_middleware`` so the decision
logic is importable and unit-testable without standing up the full
PromptServer/aiohttp app (importing ``server`` pulls in ``nodes``/``execution``/
torch and has global side effects). The wiring lives in ``server.py``; the
regression guard for GHSA-779p-m5rp-r4h4 finding #1 (CSRF bypass via
``Origin: null``) lives in
``tests-unit/security_test/test_ghsa_779p_01_origin_csrf.py``.

Only ``urllib.parse``/``ipaddress``/``socket`` (stdlib) are imported here, so the
module stays cheap to import from a unit test.
"""

import ipaddress
import socket
import urllib.parse


def is_loopback(host):
    if host is None:
        return False
    try:
        if ipaddress.ip_address(host).is_loopback:
            return True
        else:
            return False
    except ValueError:
        # Not an IP literal (ip_address raises ValueError); fall through to DNS
        # resolution below. Narrowed from a bare except so genuine interrupts
        # (KeyboardInterrupt/SystemExit) aren't swallowed.
        pass

    loopback = False
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            r = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in r:
                if not ipaddress.ip_address(sockaddr[0]).is_loopback:
                    return loopback
                else:
                    loopback = True
        except socket.gaierror:
            pass

    return loopback


def is_cross_origin_forbidden(host, origin):
    """Return True if a request with these ``Host``/``Origin`` headers must be rejected (403).

    This prevents the case where a random website can queue Comfy workflows by
    making a POST to 127.0.0.1, which browsers don't prevent. In that case the
    Host and Origin hostnames won't match. The check is intentionally limited to
    when the Host resolves to a loopback address; for non-loopback hosts it
    returns False (it is a localhost-CSRF mitigation, not a general same-origin
    enforcer).

    GHSA-779p-m5rp-r4h4 #1 fix: an opaque origin (e.g. ``"null"`` sent by a
    sandboxed iframe or a ``data:``/``file:`` document) parses to an empty/None
    host. Previously such requests skipped the comparison entirely, which let an
    attacker bypass the host/origin CSRF check with ``Origin: null``. A missing
    or empty origin host is now treated as a mismatch and rejected.
    """
    host_domain = host.lower()
    parsed = urllib.parse.urlparse(origin)
    origin_domain = parsed.netloc.lower()
    host_domain_parsed = urllib.parse.urlsplit('//' + host_domain)

    # A non-numeric or out-of-range port (e.g. Origin: http://127.0.0.1:99999)
    # makes urllib raise ValueError on .port access. Treat a malformed port as a
    # rejected request rather than letting it surface as an uncaught 500 in the
    # middleware — it fails closed, consistent with the CSRF stance.
    try:
        origin_port = parsed.port
        host_port = host_domain_parsed.port
    except ValueError:
        return True

    loopback = is_loopback(host_domain_parsed.hostname)

    if origin_port is None:  # if origin doesn't have a port strip it from the host to handle weird browsers, same for host
        host_domain = host_domain_parsed.hostname
    if host_port is None:
        origin_domain = parsed.hostname

    if loopback and host_domain is not None and len(host_domain) > 0:
        if origin_domain is None or len(origin_domain) == 0 or host_domain != origin_domain:
            return True

    return False
