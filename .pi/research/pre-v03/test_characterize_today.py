"""Characterization tests: what the UNCHANGED parent frame does today (base 5950f807).

These pin current behaviour so Plan v0.3's tests can show before/after. They assert TODAY's
outcomes, including the ones the midnight-reset feature must change. They live in .pi/ (our tree,
decision D20) and are never added to the parent's tests/.

Run (repo root, Windows needs the fcntl stand-in):
    PYTHONPATH=.pi/research/pre-v03/stubs python -m pytest .pi/research/pre-v03/test_characterize_today.py -q

Style copies the parent's own tests/test_frame_capture.py: load frame modules by path, stub
playwright for shoot.py, patch display.py's collaborators, assert on calls.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import types
import unittest
from unittest import mock

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[3]
YESTERDAY = [{"sci": "Corvus brachyrhynchos", "com": "American Crow", "n": 20}]
NOW = 1_800_000_000.0


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_module(name, **attrs):
    """A stand-in module with the given attributes (setattr keeps type checkers honest)."""
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


class Route:
    """Minimal fake of a Playwright route, like the parent's test double."""

    def __init__(self, url, payload):
        self.request = types.SimpleNamespace(url=url, headers={})
        self._payload = payload
        self.fetched_url = None
        self.result = None

    def fetch(self, url=None, **_kw):
        self.fetched_url = url
        payload = self._payload
        return types.SimpleNamespace(ok=True, status=200, json=lambda: payload)

    def fulfill(self, **kw):
        self.result = kw

    def continue_(self):
        self.result = "continued"


class TodayRun(unittest.TestCase):
    """display.run() decisions today. 'pushed' = the e-ink panel would be redrawn."""

    @classmethod
    def setUpClass(cls):
        cls.display = load("char_display", "frame/display.py")

    def setUp(self):
        fake_bundle_runtime = fake_module("bundle_runtime", active_bundle=lambda _root=None: None)
        patcher = mock.patch.dict(sys.modules, {"bundle_runtime": fake_bundle_runtime})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cfg = dict(self.display.DEFAULTS, shoot=True)  # local mode, as installed by default
        self.calls = {"obtain": [], "push": 0, "save": []}

    def run_frame(self, *, today, state, force=False, use_signature=True, quiet=False):
        d = self.display

        def obtain(_cfg, species, _bundle=None, *, capture=None):
            self.calls["obtain"].append(species)
            if capture is not None and species is not None:
                capture["species"] = species
            return Image.new("RGB", (8, 8))

        with mock.patch.object(d, "load_state", return_value=state), \
                mock.patch.object(d, "fetch_species", return_value=today) as fetch, \
                mock.patch.object(d, "obtain_image", side_effect=obtain), \
                mock.patch.object(d, "fit_panel", side_effect=lambda image: image), \
                mock.patch.object(d, "mat_and_center", side_effect=lambda image, *a: image), \
                mock.patch.object(d, "push_panel", side_effect=lambda *a: self.calls.__setitem__("push", self.calls["push"] + 1)), \
                mock.patch.object(d, "save_state", side_effect=lambda _p, sig, when: self.calls["save"].append((sig, when))), \
                mock.patch.object(d, "in_quiet_hours", return_value=quiet), \
                mock.patch.object(d.time, "time", return_value=NOW), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ok = d.run(self.cfg, force=force, use_signature=use_signature)
        return ok, fetch

    def state_showing(self, species, hours_ago=1):
        return {"signature": self.display.signature(species), "last_refresh": NOW - hours_ago * 3600}

    # --- the paths the feature must change -------------------------------------------------

    def test_today_an_empty_window_redraws_the_wall_to_the_empty_nest(self):
        """C1 (the core bug): yesterday's collage on the glass, window now empty -> panel pushed."""
        ok, _ = self.run_frame(today=[], state=self.state_showing(YESTERDAY))
        self.assertTrue(ok)
        self.assertEqual(self.calls["obtain"], [[]], "capture was asked to render an EMPTY list")
        self.assertEqual(self.calls["push"], 1, "today the wall IS redrawn (empty nest)")
        self.assertEqual(self.calls["save"], [(self.display.signature([]), NOW)])

    def test_today_force_redraws_even_when_nothing_changed(self):
        """C2: --force (README update step, birdframe-names) bypasses the gate."""
        state = self.state_showing([])
        ok, _ = self.run_frame(today=[], state=state, force=True)
        self.assertTrue(ok)
        self.assertEqual(self.calls["push"], 1)

    def test_today_no_signature_never_fetches_in_local_mode(self):
        """C3 (D16): --no-signature (bundle use/rollback) skips the fetch; capture gets species=None,
        so the page fetches `recent` itself (shoot.py) - no frame-side list exists to judge."""
        ok, fetch = self.run_frame(today=YESTERDAY, state=self.state_showing(YESTERDAY), use_signature=False)
        self.assertTrue(ok)
        fetch.assert_not_called()
        self.assertEqual(self.calls["obtain"], [None])
        self.assertEqual(self.calls["push"], 1)

    def test_today_heal_redraws_an_unchanged_empty_window(self):
        """C4 (D7): heal_hours elapsed -> refresh even with an identical (empty) signature."""
        ok, _ = self.run_frame(today=[], state=self.state_showing([], hours_ago=25))
        self.assertTrue(ok)
        self.assertEqual(self.calls["push"], 1)

    def test_today_unreadable_state_plus_empty_window_redraws(self):
        """C5 (D9, restart / boot-after-outage): load_state's error default makes [] a change."""
        ok, _ = self.run_frame(today=[], state={"signature": None, "last_refresh": 0})
        self.assertTrue(ok)
        self.assertEqual(self.calls["push"], 1)

    # --- behaviour the feature must preserve -----------------------------------------------

    def test_today_unchanged_window_skips_without_touching_state(self):
        ok, _ = self.run_frame(today=YESTERDAY, state=self.state_showing(YESTERDAY))
        self.assertTrue(ok)
        self.assertEqual((self.calls["obtain"], self.calls["push"], self.calls["save"]), ([], 0, []))

    def test_today_quiet_hours_skip_even_a_real_change(self):
        """D8: preserved behaviour - quiet hours win over a change."""
        ok, _ = self.run_frame(today=YESTERDAY, state=self.state_showing([]), quiet=True)
        self.assertTrue(ok)
        self.assertEqual(self.calls["push"], 0)

    def test_today_a_failed_push_never_saves_state(self):
        d = self.display
        with mock.patch.object(d, "load_state", return_value=self.state_showing([])), \
                mock.patch.object(d, "fetch_species", return_value=YESTERDAY), \
                mock.patch.object(d, "obtain_image", return_value=Image.new("RGB", (8, 8))), \
                mock.patch.object(d, "fit_panel", side_effect=lambda i: i), \
                mock.patch.object(d, "mat_and_center", side_effect=lambda i, *a: i), \
                mock.patch.object(d, "push_panel", side_effect=RuntimeError("SPI")), \
                mock.patch.object(d, "save_state") as save, \
                mock.patch.object(d, "in_quiet_hours", return_value=False), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(d.run(self.cfg))
        save.assert_not_called()


class TodayFetch(unittest.TestCase):
    """What the frame learns from the station today."""

    @classmethod
    def setUpClass(cls):
        cls.display = load("char_display_fetch", "frame/display.py")

    def test_today_local_mode_ignores_the_drawable_filter(self):
        """C6 (D12/R5): fetch_species passes `drawable` only in BirdWeather mode."""
        cfg = dict(self.display.DEFAULTS, shoot=True)
        undrawable = [{"sci": "Ardea herodias", "com": "Great Blue Heron", "n": 3}]
        with mock.patch.object(self.display, "fetch_recent", return_value=undrawable) as recent:
            got = self.display.fetch_species(cfg, None, drawable=frozenset({"corvus-brachyrhynchos"}))
        self.assertEqual(got, undrawable, "local mode returns the station list unfiltered")
        recent.assert_called_once_with(cfg["base_url"], 24, cfg["timeout"], None)

    def test_today_fetch_recent_returns_only_the_species_list(self):
        """C7 (D14): the response's window metadata (midnight_clamped, ...) is discarded today."""
        payload = {"species": YESTERDAY, "midnight_clamped": True, "window_start": "2026-09-02 00:00:00"}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc) -> None:
                return None

        with mock.patch.object(self.display.urllib.request, "urlopen",
                               return_value=Response(json.dumps(payload).encode())) as urlopen:
            got = self.display.fetch_recent("http://station", 24, 5)
        self.assertEqual(got, YESTERDAY)
        url = urlopen.call_args[0][0].full_url
        self.assertEqual(url, "http://station/avian/api/birdnet-api.php?action=recent&hours=24")


class TodayCaptureRewrite(unittest.TestCase):
    """Item 5: the capture's single rewrite point for the page's own `recent` request."""

    @classmethod
    def setUpClass(cls):
        api = fake_module("playwright.sync_api", TimeoutError=TimeoutError, sync_playwright=lambda: None)
        with mock.patch.dict(sys.modules, {"playwright.sync_api": api}):
            cls.shoot = load("char_shoot", "frame/shoot.py")

    def handle(self, url, window_hours: int | None = 24):
        route = Route(url, {"species": YESTERDAY})
        self.shoot._make_api_handler(0.04, window_hours, None)(route)
        return route

    def test_today_hours_is_substituted_and_the_rest_of_the_query_survives(self):
        """C8: the rewrite is a substitution of hours=\\d+; every other param is preserved verbatim,
        so a param appended next to it (v0.3) reaches the station unchanged."""
        url = "http://s/avian/api/birdnet-api.php?action=recent&hours=12&edu=saved&reset_at_midnight=1"
        route = self.handle(url)
        self.assertEqual(route.fetched_url,
                         "http://s/avian/api/birdnet-api.php?action=recent&hours=24&edu=saved&reset_at_midnight=1")

    def test_today_non_recent_actions_pass_through_untouched(self):
        route = self.handle("http://s/avian/api/birdnet-api.php?action=stats")
        self.assertEqual(route.result, "continued")
        self.assertIsNone(route.fetched_url)

    def test_today_no_window_hours_means_the_url_is_not_rewritten(self):
        url = "http://s/avian/api/birdnet-api.php?action=recent&hours=168"
        self.assertEqual(self.handle(url, window_hours=None).fetched_url, url)


if __name__ == "__main__":
    unittest.main()
