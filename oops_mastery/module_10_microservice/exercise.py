"""
Module 10 Exercise: A URL-Shortener Service, Layered
====================================================
Goal
----
Build a URL-shortener microservice with the exact four-layer shape from
concepts.py: domain -> repository -> service -> API, wired in a composition
root. Same rules: imports point inward, status codes only at the boundary.

Complete the TODOs, then run:  python3 exercise.py
"""
from dataclasses import dataclass
from typing import Callable, Protocol


# ---------------------------------------------------------------------------
# TODO 1 — DOMAIN
# ---------------------------------------------------------------------------
# * exceptions: DomainError(Exception), NotFound(DomainError),
#   DuplicateSlug(DomainError)
# * value object ShortSlug (frozen dataclass, field: text)
#     invariant in __post_init__: 3 <= len(text) <= 12, alphanumeric only
#     (text.isalnum()); raise ValueError otherwise
# * entity ShortLink:
#     __init__(self, slug: ShortSlug, target_url: str)
#       - raise ValueError("target must be http(s)") unless target_url
#         startswith "http://" or "https://"
#       - self.hits = 0
#     method record_hit() -> increments hits
#     equality + hash by slug (entities: identity, not state)


# ---------------------------------------------------------------------------
# TODO 2 — REPOSITORY
# ---------------------------------------------------------------------------
# * protocol LinkRepo: add(link), get(slug_text) -> ShortLink, list_all()
# * InMemoryLinkRepo implementing it:
#     - add raises DuplicateSlug(f"slug {text!r} taken") on collision
#     - get raises NotFound(f"slug {text!r} not found")


# ---------------------------------------------------------------------------
# TODO 3 — SERVICE
# ---------------------------------------------------------------------------
# * protocol SlugGenerator: next_slug() -> ShortSlug
# * CounterSlugs: generates "link1", "link2", ... as ShortSlug
# * ShortenerService(repo: LinkRepo, slugs: SlugGenerator):
#     shorten(target_url, custom_slug: str | None = None) -> ShortLink
#         - custom_slug given -> use ShortSlug(custom_slug)
#         - else -> slugs.next_slug()
#     resolve(slug_text) -> str
#         - looks up the link, records a hit, returns target_url
#     stats(slug_text) -> dict {"slug":..., "target":..., "hits":...}


# ---------------------------------------------------------------------------
# TODO 4 — API
# ---------------------------------------------------------------------------
# Reuse this Response DTO:
@dataclass
class Response:
    status: int
    body: dict


# * Router with route(method, path) decorator + handle(method, path, body)
#     - unknown route -> 404
#     - NotFound -> 404 {"error": str(e)}
#     - ValueError / DomainError -> 400 {"error": str(e)}
# * build_api(service) registering:
#     POST /links     body {"url": ..., "slug": optional} -> 201
#                     {"slug":..., "target":...}
#     GET  /links     body {"slug": ...} -> 200 {"target":...} (records a hit!)
#     GET  /stats     body {"slug": ...} -> 200 stats dict


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # domain invariants
    try:
        ShortSlug("ab")
        raise SystemExit("FAIL: short slug must be rejected")
    except ValueError:
        pass
    try:
        ShortSlug("has space")
        raise SystemExit("FAIL: non-alnum slug must be rejected")
    except ValueError:
        pass
    try:
        ShortLink(ShortSlug("okay1"), "ftp://nope")
        raise SystemExit("FAIL: non-http target must be rejected")
    except ValueError:
        pass
    assert ShortLink(ShortSlug("same1"), "http://a.com") == \
           ShortLink(ShortSlug("same1"), "http://b.com"), "entity eq is by slug"

    # wiring (your composition root in miniature)
    service = ShortenerService(InMemoryLinkRepo(), CounterSlugs())
    api = build_api(service)

    r = api.handle("POST", "/links", {"url": "https://example.com/very/long"})
    assert (r.status, r.body["slug"]) == (201, "link1"), (r.status, r.body)

    r = api.handle("POST", "/links", {"url": "https://py.org", "slug": "py"})
    assert r.status == 400, "custom slug 'py' is too short -> invariant -> 400"

    r = api.handle("POST", "/links", {"url": "https://py.org", "slug": "python"})
    assert (r.status, r.body["slug"]) == (201, "python")

    r = api.handle("POST", "/links", {"url": "https://other.org", "slug": "python"})
    assert r.status == 400 and "taken" in r.body["error"]

    r = api.handle("GET", "/links", {"slug": "python"})
    assert (r.status, r.body["target"]) == (200, "https://py.org")
    api.handle("GET", "/links", {"slug": "python"})

    r = api.handle("GET", "/stats", {"slug": "python"})
    assert r.status == 200 and r.body["hits"] == 2, r.body

    r = api.handle("GET", "/links", {"slug": "ghost99"})
    assert r.status == 404

    r = api.handle("PATCH", "/links", {})
    assert r.status == 404

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add a JsonFileLinkRepo persisting to disk; swap it in and rerun —
#    nothing above the repo layer may change.
# 2. Add an EventEmitter; emit "link.resolved" and subscribe an audit list.
# 3. Add DELETE /links with a 204 response and a domain rule: only links
#    with zero hits may be deleted (409 otherwise — extend the Router).

# Cleanup: nothing to clean up (unless you built the file repo — delete its file).
