"""
Module 10 Solution — A URL-Shortener Service, Layered
=====================================================
Run: python3 solution.py
"""
from dataclasses import dataclass
from typing import Callable, Protocol


# ============================================================================
# DOMAIN
# ============================================================================
class DomainError(Exception):
    pass


class NotFound(DomainError):
    pass


class DuplicateSlug(DomainError):
    pass


@dataclass(frozen=True)
class ShortSlug:
    text: str

    def __post_init__(self):
        if not (3 <= len(self.text) <= 12) or not self.text.isalnum():
            raise ValueError("slug must be 3-12 alphanumeric characters")


class ShortLink:
    def __init__(self, slug: ShortSlug, target_url: str):
        if not target_url.startswith(("http://", "https://")):
            raise ValueError("target must be http(s)")
        self.slug = slug
        self.target_url = target_url
        self.hits = 0

    def record_hit(self):
        self.hits += 1

    def __eq__(self, other):
        if not isinstance(other, ShortLink):
            return NotImplemented
        return self.slug == other.slug      # entity: identity, not state

    def __hash__(self):
        return hash(self.slug)

    def __repr__(self):
        return f"ShortLink({self.slug.text!r} -> {self.target_url!r}, hits={self.hits})"


# ============================================================================
# REPOSITORY
# ============================================================================
class LinkRepo(Protocol):
    def add(self, link: ShortLink) -> None: ...
    def get(self, slug_text: str) -> ShortLink: ...
    def list_all(self) -> list[ShortLink]: ...


class InMemoryLinkRepo:
    def __init__(self):
        self._links: dict[str, ShortLink] = {}

    def add(self, link: ShortLink) -> None:
        if link.slug.text in self._links:
            raise DuplicateSlug(f"slug {link.slug.text!r} taken")
        self._links[link.slug.text] = link

    def get(self, slug_text: str) -> ShortLink:
        try:
            return self._links[slug_text]
        except KeyError:
            raise NotFound(f"slug {slug_text!r} not found") from None

    def list_all(self) -> list[ShortLink]:
        return list(self._links.values())


# Stretch 1: a drop-in persistent repo — same contract, nothing above changes.
class JsonFileLinkRepo:
    def __init__(self, path):
        import json
        import pathlib
        self._path = pathlib.Path(path)
        self._json = json
        self._links: dict[str, ShortLink] = {}
        if self._path.exists():
            for slug, rec in json.loads(self._path.read_text()).items():
                link = ShortLink(ShortSlug(slug), rec["target"])
                link.hits = rec["hits"]
                self._links[slug] = link

    def _flush(self):
        data = {s: {"target": l.target_url, "hits": l.hits}
                for s, l in self._links.items()}
        self._path.write_text(self._json.dumps(data))

    def add(self, link: ShortLink) -> None:
        if link.slug.text in self._links:
            raise DuplicateSlug(f"slug {link.slug.text!r} taken")
        self._links[link.slug.text] = link
        self._flush()

    def get(self, slug_text: str) -> ShortLink:
        try:
            return self._links[slug_text]
        except KeyError:
            raise NotFound(f"slug {slug_text!r} not found") from None

    def list_all(self) -> list[ShortLink]:
        return list(self._links.values())


# ============================================================================
# SERVICE
# ============================================================================
class SlugGenerator(Protocol):
    def next_slug(self) -> ShortSlug: ...


class CounterSlugs:
    def __init__(self):
        self._n = 0

    def next_slug(self) -> ShortSlug:
        self._n += 1
        return ShortSlug(f"link{self._n}")


class ShortenerService:
    def __init__(self, repo: LinkRepo, slugs: SlugGenerator):
        self._repo = repo
        self._slugs = slugs

    def shorten(self, target_url: str,
                custom_slug: str | None = None) -> ShortLink:
        slug = ShortSlug(custom_slug) if custom_slug else self._slugs.next_slug()
        link = ShortLink(slug, target_url)
        self._repo.add(link)
        return link

    def resolve(self, slug_text: str) -> str:
        link = self._repo.get(slug_text)
        link.record_hit()
        return link.target_url

    def stats(self, slug_text: str) -> dict:
        link = self._repo.get(slug_text)
        return {"slug": link.slug.text, "target": link.target_url,
                "hits": link.hits}

    # Stretch 3: a domain rule enforced in the service
    def delete(self, slug_text: str) -> None:
        link = self._repo.get(slug_text)
        if link.hits > 0:
            raise DomainError(f"slug {slug_text!r} has hits; cannot delete")
        # (InMemory-only for brevity)
        self._repo._links.pop(slug_text)          # type: ignore[attr-defined]


# ============================================================================
# API
# ============================================================================
@dataclass
class Response:
    status: int
    body: dict


class Router:
    def __init__(self):
        self._routes: dict[tuple[str, str], Callable] = {}

    def route(self, method: str, path: str):
        def deco(handler):
            self._routes[(method, path)] = handler
            return handler
        return deco

    def handle(self, method: str, path: str, body: dict | None = None) -> Response:
        handler = self._routes.get((method, path))
        if handler is None:
            return Response(404, {"error": f"no route {method} {path}"})
        try:
            return handler(body or {})
        except NotFound as e:
            return Response(404, {"error": str(e)})
        except (ValueError, DomainError) as e:
            return Response(400, {"error": str(e)})


def build_api(service: ShortenerService) -> Router:
    router = Router()

    @router.route("POST", "/links")
    def create_link(body: dict) -> Response:
        link = service.shorten(body["url"], body.get("slug"))
        return Response(201, {"slug": link.slug.text, "target": link.target_url})

    @router.route("GET", "/links")
    def resolve_link(body: dict) -> Response:
        return Response(200, {"target": service.resolve(body["slug"])})

    @router.route("GET", "/stats")
    def link_stats(body: dict) -> Response:
        return Response(200, service.stats(body["slug"]))

    return router


# ============================================================================
# COMPOSITION ROOT + checks
# ============================================================================
if __name__ == "__main__":
    try:
        ShortSlug("ab")
        raise SystemExit("FAIL")
    except ValueError:
        pass
    try:
        ShortSlug("has space")
        raise SystemExit("FAIL")
    except ValueError:
        pass
    try:
        ShortLink(ShortSlug("okay1"), "ftp://nope")
        raise SystemExit("FAIL")
    except ValueError:
        pass
    assert ShortLink(ShortSlug("same1"), "http://a.com") == \
           ShortLink(ShortSlug("same1"), "http://b.com")

    service = ShortenerService(InMemoryLinkRepo(), CounterSlugs())
    api = build_api(service)

    r = api.handle("POST", "/links", {"url": "https://example.com/very/long"})
    assert (r.status, r.body["slug"]) == (201, "link1")

    r = api.handle("POST", "/links", {"url": "https://py.org", "slug": "py"})
    assert r.status == 400

    r = api.handle("POST", "/links", {"url": "https://py.org", "slug": "python"})
    assert (r.status, r.body["slug"]) == (201, "python")

    r = api.handle("POST", "/links", {"url": "https://other.org", "slug": "python"})
    assert r.status == 400 and "taken" in r.body["error"]

    r = api.handle("GET", "/links", {"slug": "python"})
    assert (r.status, r.body["target"]) == (200, "https://py.org")
    api.handle("GET", "/links", {"slug": "python"})

    r = api.handle("GET", "/stats", {"slug": "python"})
    assert r.status == 200 and r.body["hits"] == 2

    r = api.handle("GET", "/links", {"slug": "ghost99"})
    assert r.status == 404
    r = api.handle("PATCH", "/links", {})
    assert r.status == 404

    # Stretch 1: swap in the file-backed repo — zero changes above the repo.
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "links.json")
        file_service = ShortenerService(JsonFileLinkRepo(path), CounterSlugs())
        file_service.shorten("https://persist.me", "keeper")
        # a "restart": a fresh repo instance reads the same file
        reborn = ShortenerService(JsonFileLinkRepo(path), CounterSlugs())
        assert reborn.resolve("keeper") == "https://persist.me"
        assert reborn.stats("keeper")["hits"] == 1
        # (note: hits aren't flushed on resolve — persisting mutations
        #  needs a save()/unit-of-work method; a great extra exercise)

    # Stretch 3: delete rule
    service.shorten("https://fresh.io", "fresh")
    service.delete("fresh")                       # zero hits: ok
    try:
        service.delete("python")                  # has hits: refused
        raise SystemExit("FAIL")
    except DomainError:
        pass

    print("All solution checks passed ✔")
