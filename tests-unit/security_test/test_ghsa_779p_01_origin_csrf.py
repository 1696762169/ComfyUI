"""CI unit guard for FIX #1 of GHSA-779p-m5rp-r4h4 — the Origin: null CSRF bypass.

Vuln #1 was a CSRF bypass: the loopback host/origin guard in
``server.create_origin_only_middleware`` skipped the comparison entirely whenever
the origin host parsed to an empty string. An opaque ``Origin: null`` (sent by a
sandboxed iframe or a ``data:``/``file:`` document) parses to exactly that, so an
attacker could forge cross-origin state-mutating requests against a victim's
loopback ComfyUI — the entry primitive for the [CISA-1] CSRF -> stored-XSS ->
client-side RCE chain.

The decision logic was extracted verbatim from the middleware closure into
``utils.origin_check`` precisely so it can be exercised here: ``server.py`` cannot
be imported in a unit test (importing it spins up the full PromptServer/aiohttp
app and its global side effects), which is why finding #1 previously had no
server-free CI coverage and only a live-server POC
(``.security/pocs/test_security_ghsa_779p.py::TestOriginNullCsrf``, skipped
unless a server is running on 127.0.0.1:8188). This file is the fast, hermetic
guard so the Origin: null bypass cannot silently reopen.

Cases use IP literals so the loopback determination does not depend on DNS; the
one name-based case ("localhost") relies only on standard loopback resolution.
"""

from utils.origin_check import is_cross_origin_forbidden, is_loopback


# ---------------------------------------------------------------------------
# The regression: an opaque/empty Origin against a loopback Host MUST be a 403.
# Each of these returned False (allowed) before the fix — that is the bug.
# ---------------------------------------------------------------------------
OPAQUE_ORIGIN_ON_LOOPBACK = [
    ("127.0.0.1:8188", "null"),     # the exact reported bypass
    ("127.0.0.1:8188", ""),         # empty Origin header, same empty-host path
    ("127.0.0.1", "null"),          # host without an explicit port
    ("[::1]:8188", "null"),         # IPv6 loopback host
]


def test_origin_null_is_forbidden():
    """Origin: null against a loopback host must be rejected (the #1 fix)."""
    assert is_cross_origin_forbidden("127.0.0.1:8188", "null") is True, (
        "Origin: null was treated as allowed — this is exactly the "
        "GHSA-779p-m5rp-r4h4 #1 CSRF bypass reopening."
    )


def test_all_opaque_origins_on_loopback_forbidden():
    for host, origin in OPAQUE_ORIGIN_ON_LOOPBACK:
        assert is_cross_origin_forbidden(host, origin) is True, (host, origin)


# ---------------------------------------------------------------------------
# False-positive guards: legitimate same-origin requests must stay allowed, or
# the fix would break the dev server. The port-stripping cases preserve the
# original "handle weird browsers" behaviour (origin without a port matches a
# host with one, and vice versa).
# ---------------------------------------------------------------------------
MATCHING_ORIGINS = [
    ("127.0.0.1:8188", "http://127.0.0.1:8188"),
    ("127.0.0.1:8188", "http://127.0.0.1"),   # origin has no port -> host port stripped for compare
    ("127.0.0.1", "http://127.0.0.1"),
    ("localhost:8188", "http://localhost:8188"),
]


def test_matching_origins_allowed():
    for host, origin in MATCHING_ORIGINS:
        assert is_cross_origin_forbidden(host, origin) is False, (host, origin)


# ---------------------------------------------------------------------------
# Genuine cross-origin requests against a loopback host must be forbidden.
# ---------------------------------------------------------------------------
MISMATCHED_ORIGINS_ON_LOOPBACK = [
    ("127.0.0.1:8188", "http://evil.com"),
    ("127.0.0.1:8188", "https://127.0.0.1:9999"),  # same host, different port
    ("127.0.0.1:8188", "http://localhost.evil.com"),
]


def test_mismatched_origins_on_loopback_forbidden():
    for host, origin in MISMATCHED_ORIGINS_ON_LOOPBACK:
        assert is_cross_origin_forbidden(host, origin) is True, (host, origin)


# ---------------------------------------------------------------------------
# Scope guard: the check is deliberately limited to loopback hosts. A
# non-loopback Host must NOT trip the guard (even on a mismatch / opaque
# origin) — this preserves the original behaviour and documents that the
# mitigation is localhost-only by design.
# ---------------------------------------------------------------------------
NON_LOOPBACK_HOSTS = [
    ("203.0.113.5:8188", "http://evil.com"),   # public IP literal -> not loopback
    ("203.0.113.5:8188", "null"),
    ("10.0.0.5:8188", "null"),                 # private but not loopback
]


def test_non_loopback_host_not_subject_to_check():
    for host, origin in NON_LOOPBACK_HOSTS:
        assert is_cross_origin_forbidden(host, origin) is False, (host, origin)


# ---------------------------------------------------------------------------
# is_loopback — the predicate the scoping above depends on.
# ---------------------------------------------------------------------------
def test_is_loopback_true_for_loopback_addresses():
    for host in ("127.0.0.1", "::1", "localhost"):
        assert is_loopback(host) is True, host


def test_is_loopback_false_for_non_loopback_and_none():
    for host in ("203.0.113.5", "10.0.0.5", None):
        assert is_loopback(host) is False, host
