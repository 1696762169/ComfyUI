"""Integration tests for cursor-based pagination on GET /api/assets.

Wire contract is shared with cloud's Go implementation (BE-893). These tests
exercise the handler/service/query path end-to-end; cursor-encoding-level
tests live in tests-unit/assets_test/services/test_cursor.py.
"""
import requests


def _seed(asset_factory, make_asset_bytes, count: int, tag: str) -> list[str]:
    names = [f"cursor_{i:02d}.safetensors" for i in range(count)]
    for n in names:
        asset_factory(
            n,
            ["models", "checkpoints", "unit-tests", tag],
            {},
            make_asset_bytes(n, size=2048),
        )
    return sorted(names)


def test_cursor_pages_all_items_in_order(http: requests.Session, api_base: str, asset_factory, make_asset_bytes):
    names = _seed(asset_factory, make_asset_bytes, count=5, tag="cursor-walk")

    params = {
        "include_tags": "unit-tests,cursor-walk",
        "sort": "name",
        "order": "asc",
        "limit": "2",
    }

    seen: list[str] = []
    after: str | None = None
    pages = 0
    while True:
        page_params = dict(params)
        if after is not None:
            page_params["after"] = after
        r = http.get(api_base + "/api/assets", params=page_params, timeout=120)
        assert r.status_code == 200, r.text
        body = r.json()
        seen.extend(a["name"] for a in body["assets"])
        pages += 1
        after = body.get("next_cursor")
        if after is None:
            break
        assert body["has_more"] is True
        assert pages < 10, "guard against runaway cursor loop"

    assert seen == names, f"expected {names}, got {seen}"
    # Last page should have has_more False
    assert body["has_more"] is False
    assert "next_cursor" not in body


def test_cursor_invalid_returns_400(http: requests.Session, api_base: str):
    r = http.get(
        api_base + "/api/assets",
        params={"after": "not-a-real-cursor", "sort": "created_at"},
        timeout=120,
    )
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"]["code"] == "INVALID_CURSOR"


def test_cursor_sort_mismatch_returns_400(http: requests.Session, api_base: str, asset_factory, make_asset_bytes):
    _seed(asset_factory, make_asset_bytes, count=2, tag="cursor-mismatch")

    # Take a real cursor minted for sort=name.
    r = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-mismatch",
            "sort": "name",
            "order": "asc",
            "limit": "1",
        },
        timeout=120,
    )
    assert r.status_code == 200
    cursor = r.json()["next_cursor"]
    assert cursor is not None

    # Replay against sort=created_at — should fail with INVALID_CURSOR.
    r2 = http.get(
        api_base + "/api/assets",
        params={"after": cursor, "sort": "created_at"},
        timeout=120,
    )
    assert r2.status_code == 400, r2.text
    assert r2.json()["error"]["code"] == "INVALID_CURSOR"


def test_cursor_wins_over_offset(http: requests.Session, api_base: str, asset_factory, make_asset_bytes):
    names = _seed(asset_factory, make_asset_bytes, count=4, tag="cursor-vs-offset")

    # Take a cursor that points past the first item.
    r = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-vs-offset",
            "sort": "name",
            "order": "asc",
            "limit": "1",
        },
        timeout=120,
    )
    cursor = r.json()["next_cursor"]
    assert cursor is not None

    # Pass both 'after' and a large offset. Cursor must win; offset is ignored.
    r2 = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-vs-offset",
            "sort": "name",
            "order": "asc",
            "limit": "1",
            "after": cursor,
            "offset": "999",
        },
        timeout=120,
    )
    assert r2.status_code == 200
    body = r2.json()
    # Should land on the second name in sorted order — not skip ahead by 999.
    assert [a["name"] for a in body["assets"]] == [names[1]]


def test_next_cursor_absent_when_no_more_results(http: requests.Session, api_base: str, asset_factory, make_asset_bytes):
    _seed(asset_factory, make_asset_bytes, count=2, tag="cursor-exhaust")

    r = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-exhaust",
            "sort": "name",
            "order": "asc",
            "limit": "50",
        },
        timeout=120,
    )
    body = r.json()
    assert body["has_more"] is False
    assert "next_cursor" not in body


def test_cursor_pagination_stable_after_delete(http: requests.Session, api_base: str, asset_factory, make_asset_bytes):
    names = _seed(asset_factory, make_asset_bytes, count=4, tag="cursor-delete")

    # Page 1.
    r = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-delete",
            "sort": "name",
            "order": "asc",
            "limit": "2",
        },
        timeout=120,
    )
    assert r.status_code == 200
    body = r.json()
    page1_names = [a["name"] for a in body["assets"]]
    cursor = body["next_cursor"]
    assert cursor is not None
    assert page1_names == names[:2]

    # Delete an item from page 1 (already returned) — cursor should still
    # locate the next page from where it was minted, not re-index.
    target_id = body["assets"][0]["id"]
    d = http.delete(api_base + f"/api/assets/{target_id}", timeout=120)
    assert d.status_code in (200, 204), d.text

    # Page 2 via cursor.
    r2 = http.get(
        api_base + "/api/assets",
        params={
            "include_tags": "unit-tests,cursor-delete",
            "sort": "name",
            "order": "asc",
            "limit": "2",
            "after": cursor,
        },
        timeout=120,
    )
    body2 = r2.json()
    assert [a["name"] for a in body2["assets"]] == names[2:]
