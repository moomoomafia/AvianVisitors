"""R5: do installable bundles actually contain species without a base-pose illustration?

Scans every catalog a frame installs from, mirroring frame/bundle_runtime.py:
  * the vendored official catalog  frame/vendor/catalog-v1.json   (_vendor_catalog)
  * the LIVE community feed         CATALOG_URL                    (refresh_catalog, :1152)
and, for reference only, the station UI snapshot (not a frame install source).
Every manifest is fetched over HTTPS from avianvisitors.com, verified against the catalog's
SHA-256 pin, and its species' pose sets are classified against what renderCollage can draw
(avian/frontend/apt.js:3164-3186: base slug, or "-2"; nothing else).

Fails loudly (exit 1) on fetch errors, SHA-256 mismatches, a manifest without a `species`
list, or a species count that disagrees with the catalog row. Read-only.

Usage (repo root): python .pi/research/r5/manifest_scan.py
"""
import hashlib
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
# Same origin policy and feed as the frame's bundle runtime (frame/bundle_runtime.py:46-50).
ALLOWED_HOSTS = frozenset({"avianvisitors.com"})
COMMUNITY_URL = "https://avianvisitors.com/api/bundles/catalog/community-v1.json"
SOURCES = [
    ("vendored official catalog (frame install source)", ROOT / "frame" / "vendor" / "catalog-v1.json"),
    ("LIVE community feed (frame install source)", COMMUNITY_URL),
    ("station UI snapshot (reference only, not a frame install source)",
     ROOT / "avian" / "frontend" / "assets" / "bundle-catalog" / "catalog-snapshot.js"),
]
BASE_POSES = {"perched", "variant-1"}  # both map to the unsuffixed slug (_pose_suffix, :1241-1245)
SECOND_POSES = {"flight", "variant-2"}  # the "-2" slug the collage may roll (FLY_PROB = 0.15)


def fetch(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"refusing non-https or unexpected host: {url}")
    # SAFETY: scheme is pinned to https and the host to ALLOWED_HOSTS just above, so file: and
    # custom schemes can never reach urlopen (the audit rule can't see that guard).
    req = urllib.request.Request(url, headers={"User-Agent": "AvianVisitors-research/R5"})  # noqa: S310  # nosec B310
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310  # nosec B310
        return response.read(8 * 1024 * 1024)


def load_catalog(source):
    if isinstance(source, str):
        return json.loads(fetch(source))
    text = source.read_text(encoding="utf-8")
    if source.suffix == ".js":
        text = text[text.index("{"): text.rindex("}") + 1]
    return json.loads(text)


def classify(bird):
    ids = {pose["id"] for pose in bird.get("poses", [])}
    if ids & BASE_POSES:
        return "always"
    if ids & SECOND_POSES:
        return "about-15pct"
    return "never"


def scan_pack(pack, seen):
    """Print one pack's classification; return the number of problems (0 or 1)."""
    manifest = pack["manifest"]
    if manifest["sha256"] in seen:
        print(f"  {pack['id']}: same manifest as {seen[manifest['sha256']]} (already counted)")
        return 0
    seen[manifest["sha256"]] = pack["id"]
    try:
        raw = fetch(manifest["url"])
    except Exception as error:
        print(f"  {pack['id']}: MANIFEST FETCH FAILED ({type(error).__name__}: {error})")
        return 1
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        print(f"  {pack['id']}: SHA-256 MISMATCH")
        return 1
    data = json.loads(raw)
    birds = data.get("species")
    if not isinstance(birds, list):
        print(f"  {pack['id']}: MANIFEST HAS NO `species` LIST")
        return 1
    expected = pack.get("species_count")
    mismatch = expected not in (None, len(birds))
    buckets = {"always": [], "about-15pct": [], "never": []}
    hist = {}
    for bird in birds:
        buckets[classify(bird)].append(bird["scientific_name"])
        for pose in bird.get("poses", []):
            hist[pose["id"]] = hist.get(pose["id"], 0) + 1
    top = ", ".join(f"{k}:{v}" for k, v in sorted(hist.items(), key=lambda kv: -kv[1])[:6])
    note = f"  COUNT MISMATCH (catalog says {expected})" if mismatch else ""
    print(f"  {pack['id']} [review={pack.get('review')}, availability={pack.get('availability')}] "
          f"manifest v{data.get('format_version')}, sha256 ok, {len(birds)} species{note}")
    print(f"     poses [{top}]")
    print(f"     base pose (always drawn): {len(buckets['always'])} | "
          f"only -2 (drawn ~15%): {len(buckets['about-15pct'])} | "
          f"neither (never drawn): {len(buckets['never'])}")
    for bucket in ("about-15pct", "never"):
        for sci in buckets[bucket]:
            print(f"       - [{bucket}] {sci}")
    return 1 if mismatch else 0


def main():
    problems = 0
    seen = {}
    for label, source in SOURCES:
        name = source if isinstance(source, str) else source.relative_to(ROOT).as_posix()
        try:
            catalog = load_catalog(source)
        except Exception as error:
            print(f"== {label}: {name}\n  CATALOG FETCH/PARSE FAILED ({type(error).__name__}: {error})")
            problems += 1
            continue
        packs = catalog.get("packs", [])
        with_manifest = [p for p in packs if p.get("manifest")]
        avail = sorted({str(p.get("availability")) for p in packs})
        print(f"== {label}: {name}\n   format={catalog.get('format')} v{catalog.get('format_version')}, "
              f"{len(packs)} packs, {len(with_manifest)} with a manifest, availability values {avail}")
        for pack in with_manifest:
            problems += scan_pack(pack, seen)
    print(f"\nunique manifests scanned: {len(seen)}; problems: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
