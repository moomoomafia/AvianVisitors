import contextlib
import importlib.util
import io
import json
import os
import pathlib
import stat
import struct
import subprocess
import sys
import tempfile
import types
import unittest
import zlib
from unittest import mock

from PIL import Image
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPECIES = [{"sci": "Corvus brachyrhynchos", "com": "American Crow", "n": 20}]
TODAY = [{"sci": "Turdus migratorius", "com": "American Robin", "n": 2}]
NOW = 1_800_000_000.0


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def midnight(species, clamped=True):
    """A station `recent` answer for reset_at_midnight=1 (clamped=False: an outdated station)."""
    return {"species": species, "hours": 24, "midnight_clamped": clamped, "window_start": "2027-01-15 00:00:00"}


class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status
        self.ok = status == 200

    def json(self):
        return self.data

    def read(self, limit):
        return json.dumps(self.data).encode()[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class Route:
    def __init__(self, payload, status=200):
        self.request = types.SimpleNamespace(
            url="http://station/avian/api/birdnet-api.php?action=recent&hours=24&edu=saved",
            headers={},
        )
        self.response = Response(payload, status)
        self.result = None
        self.continued = False

    def fetch(self, **kwargs):
        self.fetch_args = kwargs
        return self.response

    def fulfill(self, **kwargs):
        self.result = kwargs

    def continue_(self):
        self.continued = True


class CapturePage:
    def __init__(self, mode):
        self.mode = mode
        self.routes = {}
        self.screenshots = 0
        self.token = "1"
        self.revision = "1"
        self.events = {}
        self.paper = "rgb(255, 255, 255)"
        self.visible_surfaces = []
        self.context = types.SimpleNamespace(new_cdp_session=lambda _page: types.SimpleNamespace(
            send=lambda method, params: self.visible_surfaces.append((method, params))))

    def on(self, event, handler):
        self.events[event] = handler

    def route(self, pattern, handler):
        self.routes[pattern] = handler

    def add_init_script(self, *_args):
        pass

    def add_style_tag(self, **_kwargs):
        self.paper = "rgba(0, 0, 0, 0)"

    def goto(self, *_args, **_kwargs):
        self.routes["**/birdnet-api.php**"](Route({"species": SPECIES, "hours": 24}))
        self.events["response"](types.SimpleNamespace(
            request=types.SimpleNamespace(resource_type="image", redirected_from=None, url="http://station/bird.png"),
            status=200, ok=True, header_value=lambda _name: str(len(small_png())), body=small_png))
        return Response({})

    def wait_for_selector(self, *_args, **_kwargs):
        pass

    def query_selector(self, selector):
        return object() if selector == ".gtile" else None

    def wait_for_function(self, script, **_kwargs):
        if self.mode == "broken-image" or (self.mode == "old-frontend" and "frame" in script):
            raise TimeoutError("collage not ready")
        if self.mode == "decode-timeout" and "decode" in script:
            raise TimeoutError("image decode did not finish")
        if self.mode == "font-timeout" and "fonts.load" in script:
            raise TimeoutError("label font did not finish")
        return types.SimpleNamespace(json_value=lambda: {"token": self.token, "revision": self.revision})

    def evaluate(self, script, *_args):
        if "__frameImageIds" in script:
            return {"images": [{"id": 1, "src": "http://station/bird.png", "box": [10, 20, 2, 1],
                                "natural": [2, 1], "fit": "fill", "position": "50% 50%", "filter": "none"}],
                    "labels": [], "token": self.token, "revision": self.revision}
        if "backgroundColor" in script:
            return self.paper
        if "fonts.load" in script:
            return True
        if "decode" in script:
            return {"token": "1", "revision": "1"}
        if "frame" in script:
            return (all(_args[0][key] == value for key, value in
                        (("token", self.token), ("revision", self.revision)))
                    and not (self.mode == "rerender" and self.screenshots))

    def wait_for_timeout(self, *_args):
        pass

    def screenshot(self, **kwargs):
        self.screenshots += 1
        png = io.BytesIO()
        clip = kwargs["clip"]
        Image.new("RGBA", (round(clip["width"] * 2), round(clip["height"] * 2))).save(png, "PNG")
        return png.getvalue()


class FrameCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api = types.ModuleType("playwright.sync_api")
        api.TimeoutError = TimeoutError
        api.sync_playwright = lambda: None
        with mock.patch.dict(sys.modules, {"playwright.sync_api": api}):
            cls.shoot = load("capture_shoot", "frame/shoot.py")
        cls.display = load("capture_display", "frame/display.py")
        cls.bundle_runtime = load("capture_bundle_runtime", "frame/bundle_runtime.py")

    def setUp(self):
        for patcher in (
            mock.patch.dict(sys.modules, {"bundle_runtime": self.bundle_runtime}),
            mock.patch.object(self.bundle_runtime, "active_bundle", return_value=None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_recent_errors_are_not_rewritten_as_success(self):
        for payload, status in (({"error": "database unavailable"}, 503),
                                ({"error": "bad data"}, 200),
                                ({"species": None}, 200),
                                ({"species": [None]}, 200),
                                ({"species": [{"sci": "", "n": 1}]}, 200)):
            with self.subTest(payload=payload, status=status):
                route = Route(payload, status)
                self.shoot._make_api_handler(0.04, 12, None)(route)
                self.assertFalse(route.continued)
                self.assertGreaterEqual(route.result["status"], 400)

    def test_valid_empty_response_and_scope_metadata_survive(self):
        route = Route({"species": [], "hours": 12, "educator_scope": {"id": "saved"}})
        self.shoot._make_api_handler(0.04, 12, None)(route)
        self.assertEqual(route.result["status"], 200)
        body = json.loads(route.result["body"])
        self.assertEqual(body["species"], [])
        self.assertEqual(body["educator_scope"], {"id": "saved"})
        self.assertIn("hours=12", route.fetch_args["url"])
        self.assertIn("edu=saved", route.fetch_args["url"])

    def test_floor_does_not_mutate_the_species_snapshot(self):
        species = [dict(SPECIES[0]), {"sci": "Turdus migratorius", "com": "Robin", "n": 1}]
        route = Route({})
        self.shoot._make_api_handler(0.5, 24, None, species)(route)
        self.assertEqual(species[1]["n"], 1)
        self.assertEqual(json.loads(route.result["body"])["species"][1]["n"], 10)

    def test_signature_fetch_rejects_missing_species_not_as_empty(self):
        for payload in ({"error": "database unavailable"}, {"species": None}, []):
            with self.subTest(payload=payload), mock.patch.object(
                    self.display.urllib.request, "urlopen", return_value=Response(payload)):
                with self.assertRaises((ValueError, RuntimeError)):
                    self.display.fetch_recent("http://station", 24, 5)

    def test_capture_failure_preserves_panel_state_and_next_cycle_retries(self):
        cfg = dict(self.display.DEFAULTS)
        state = {"signature": "previous", "last_refresh": 1}
        panel = []
        saves = []
        with mock.patch.object(self.display, "load_state", return_value=state), \
                mock.patch.object(self.display, "fetch_species", return_value=SPECIES), \
                mock.patch.object(self.display, "obtain_image", side_effect=RuntimeError("not ready")) as capture, \
                mock.patch.object(self.display, "push_panel", side_effect=lambda *args: panel.append(args)), \
                mock.patch.object(self.display, "save_state", side_effect=lambda *args: saves.append(args)), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(self.display.run(cfg))
            self.assertFalse(self.display.run(cfg))
        self.assertEqual(capture.call_count, 2)
        self.assertEqual(panel, [])
        self.assertEqual(saves, [])

    def test_saved_signature_describes_captured_data_not_earlier_fetch(self):
        cfg = dict(self.display.DEFAULTS, shoot=True)
        captured = [{"sci": "Turdus migratorius", "com": "Robin", "n": 2}]
        saved = []

        def obtain(_cfg, _species, _bundle=None, *, capture=None):
            if capture is not None:
                capture["species"] = captured
            return Image.new("RGB", (20, 20))

        with mock.patch.object(self.display, "load_state", return_value={}), \
                mock.patch.object(self.display, "fetch_species", return_value=SPECIES), \
                mock.patch.object(self.display, "obtain_image", side_effect=obtain), \
                mock.patch.object(self.display, "fit_panel", side_effect=lambda image: image), \
                mock.patch.object(self.display, "mat_and_center", side_effect=lambda image, *args: image), \
                mock.patch.object(self.display, "push_panel"), \
                mock.patch.object(self.display, "save_state", side_effect=lambda _path, sig, _now: saved.append(sig)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.display.run(cfg)
        self.assertEqual(saved, [self.display.signature(captured)])

    def test_captured_signature_keeps_the_exact_bundle_selection(self):
        import bundle_runtime

        cfg = dict(self.display.DEFAULTS, shoot=True)
        bundle = types.SimpleNamespace(
            drawable_slugs=frozenset({"turdus-migratorius"}),
            reference={"revision": "a" * 64, "selection_revision": "b" * 64},
        )
        saved = []

        def obtain(_cfg, _species, selected, *, capture=None):
            self.assertIs(selected, bundle)
            capture["species"] = [{"sci": "Turdus migratorius", "com": "Robin", "n": 2}]
            return Image.new("RGB", (20, 20))

        with mock.patch.object(bundle_runtime, "active_bundle", return_value=bundle), \
                mock.patch.object(self.display, "load_state", return_value={}), \
                mock.patch.object(self.display, "fetch_species", return_value=SPECIES), \
                mock.patch.object(self.display, "obtain_image", side_effect=obtain), \
                mock.patch.object(self.display, "fit_panel", side_effect=lambda image: image), \
                mock.patch.object(self.display, "mat_and_center", side_effect=lambda image, *args: image), \
                mock.patch.object(self.display, "push_panel"), \
                mock.patch.object(self.display, "save_state", side_effect=lambda _path, sig, _now: saved.append(sig)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(self.display.run(cfg, force=True))
        self.assertEqual(saved, ["58d0ae600e086fb2"])

    def run_reset_frame(self, today, *, state=None, bundle=None, quiet=False, rolling=SPECIES, now=NOW, cfg=None, **options):
        """One display.run() in local mode with reset_at_midnight on (unless `cfg` says otherwise).
        `today` is the station's midnight payload, an exception the fetch raises, or None for the
        real fetch_recent_payload. `rolling` is what the rolling-window fetch_species would return."""
        cfg = {**self.display.DEFAULTS, "shoot": True, "reset_at_midnight": True, **(cfg or {})}
        if state is None:
            state = {"signature": self.display.signature(SPECIES), "last_refresh": NOW - 3600}
        if today is None:
            fetch = mock.Mock(wraps=self.display.fetch_recent_payload)
        elif isinstance(today, Exception):
            fetch = mock.Mock(side_effect=today)
        else:
            fetch = mock.Mock(return_value=today)
        result = types.SimpleNamespace(obtained=[], pushed=0, saved=[])

        def obtain(_cfg, species, _bundle=None, *, capture=None):
            result.obtained.append(species)
            if capture is not None and species is not None:
                capture["species"] = species
            return Image.new("RGB", (20, 20))

        def push(*_args):
            result.pushed += 1

        log = io.StringIO()
        quiet_hours = (contextlib.nullcontext() if quiet is None
                       else mock.patch.object(self.display, "in_quiet_hours", return_value=quiet))
        with mock.patch.object(self.bundle_runtime, "active_bundle", return_value=bundle), \
                mock.patch.object(self.display, "load_state", return_value=state), \
                mock.patch.object(self.display, "fetch_recent_payload", fetch), \
                mock.patch.object(self.display, "fetch_species", return_value=rolling) as fetch_species, \
                mock.patch.object(self.display, "obtain_image", side_effect=obtain), \
                mock.patch.object(self.display, "fit_panel", side_effect=lambda image: image), \
                mock.patch.object(self.display, "mat_and_center", side_effect=lambda image, *args: image), \
                mock.patch.object(self.display, "push_panel", side_effect=push), \
                mock.patch.object(self.display, "save_state", side_effect=lambda _path, sig, _now: result.saved.append(sig)), \
                mock.patch.object(self.display.time, "time", return_value=now), \
                quiet_hours, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            result.ok = self.display.run(cfg, **options)
        result.fetch, result.fetch_species, result.log = fetch, fetch_species, log.getvalue()
        return result

    def empty_day_paths(self):
        showing = {"signature": self.display.signature(SPECIES), "last_refresh": NOW - 3600}
        return (
            ("timer", showing, {}),
            ("--force", showing, {"force": True}),
            ("--no-signature", showing, {"use_signature": False}),
            ("avian-bundle use/rollback", showing, {"force": True, "use_signature": False}),
            ("heal due", {"signature": self.display.signature([]), "last_refresh": NOW - 25 * 3600}, {}),
            ("unreadable state", {"signature": None, "last_refresh": 0}, {}),
        )

    def test_reset_at_midnight_keeps_the_collage_on_every_path_while_today_is_empty(self):
        for path, state, options in self.empty_day_paths():
            with self.subTest(path=path):
                result = self.run_reset_frame(midnight([]), state=state, **options)
                self.assertIs(result.ok, True)
                self.assertEqual((result.obtained, result.pushed, result.saved), ([], 0, []))
                self.assertIn("no drawable bird since midnight; keeping the current collage", result.log)
                result.fetch.assert_called_once_with(
                    self.display.DEFAULTS["base_url"], 24, self.display.DEFAULTS["timeout"], None, reset_at_midnight=True)
                result.fetch_species.assert_not_called()

    def test_reset_at_midnight_off_keeps_the_empty_window_redraw(self):
        for path, state, options in self.empty_day_paths():
            with self.subTest(path=path):
                result = self.run_reset_frame(None, state=state, rolling=[], cfg={"reset_at_midnight": False}, **options)
                self.assertIs(result.ok, True)
                self.assertEqual(result.obtained, [None if options.get("use_signature") is False else []])
                self.assertEqual(result.pushed, 1)
                self.assertEqual(len(result.saved), 1)
                self.assertEqual(result.fetch_species.call_count, 0 if options.get("use_signature") is False else 1)
                result.fetch.assert_not_called()
                self.assertNotIn("reset_at_midnight", result.log)

    def test_reset_at_midnight_counts_only_birds_with_a_base_pose_in_the_frame_bundle(self):
        heron = {"sci": "Ardea herodias", "com": "Great Blue Heron", "n": 3}
        crow = dict(SPECIES[0])
        bundle = types.SimpleNamespace(
            index={"assets": {"ardea-herodias": {"flight": {}}, "corvus-brachyrhynchos": {"perched": {}},
                              "turdus-migratorius": {"variant-1": {}, "variant-2": {}}}},
            drawable_slugs=frozenset({"ardea-herodias", "corvus-brachyrhynchos", "turdus-migratorius"}),
            reference={"revision": "a" * 64},
        )
        flight_only = self.run_reset_frame(midnight([heron]), bundle=bundle)
        self.assertIs(flight_only.ok, True)
        self.assertEqual((flight_only.obtained, flight_only.pushed, flight_only.saved), ([], 0, []))
        for drawable in (crow, TODAY[0]):
            with self.subTest(drawable=drawable["sci"]):
                mixed = self.run_reset_frame(midnight([heron, drawable]), bundle=bundle,
                                             state={"signature": None, "last_refresh": NOW - 3600})
                self.assertIs(mixed.ok, True)
                self.assertEqual(mixed.obtained, [[heron, drawable]])
                self.assertEqual((mixed.pushed, len(mixed.saved)), (1, 1))

    def test_reset_at_midnight_holds_the_collage_when_the_station_ignores_the_window(self):
        for payload in ({"species": TODAY, "hours": 24}, midnight(TODAY, clamped=False), midnight([], clamped=False)):
            for options in ({}, {"force": True}, {"force": True, "use_signature": False}):
                with self.subTest(payload=payload, **options):
                    result = self.run_reset_frame(payload, **options)
                    self.assertIs(result.ok, False)
                    self.assertEqual((result.obtained, result.pushed, result.saved), ([], 0, []))
                    self.assertIn("station did not apply the midnight window", result.log)

    def test_reset_at_midnight_fetch_failure_skips_a_timer_run_and_fails_a_forced_one(self):
        for options, ok in (({}, True), ({"force": True}, False), ({"use_signature": False}, False),
                            ({"force": True, "use_signature": False}, False)):
            with self.subTest(**options):
                result = self.run_reset_frame(OSError("station unreachable"), **options)
                self.assertIs(result.ok, ok)
                self.assertEqual((result.obtained, result.pushed, result.saved), ([], 0, []))
                result.fetch_species.assert_not_called()

    def test_reset_at_midnight_first_drawable_bird_replaces_the_collage(self):
        result = self.run_reset_frame(midnight(TODAY))
        self.assertIs(result.ok, True)
        self.assertEqual(result.obtained, [TODAY])
        self.assertEqual(result.pushed, 1)
        self.assertEqual(result.saved, [self.display.signature(TODAY)])
        result.fetch.assert_called_once_with(
            self.display.DEFAULTS["base_url"], 24, self.display.DEFAULTS["timeout"], None, reset_at_midnight=True)
        result.fetch_species.assert_not_called()

    def test_reset_at_midnight_decides_and_captures_from_the_clamped_list_not_the_rolling_one(self):
        rolling = SPECIES + TODAY  # last night's crow is still inside a rolling 24 h window
        unchanged = self.run_reset_frame(midnight(TODAY), rolling=rolling,
                                         state={"signature": self.display.signature(TODAY), "last_refresh": NOW - 3600})
        self.assertIs(unchanged.ok, True)
        self.assertEqual((unchanged.obtained, unchanged.pushed), ([], 0))
        changed = self.run_reset_frame(midnight(TODAY), rolling=rolling,
                                       state={"signature": self.display.signature(rolling), "last_refresh": NOW - 3600})
        self.assertEqual(changed.obtained, [TODAY])
        self.assertEqual(changed.saved, [self.display.signature(TODAY)])
        for result in (unchanged, changed):
            result.fetch.assert_called_once()
            result.fetch_species.assert_not_called()

    def test_reset_at_midnight_first_bird_in_quiet_hours_waits_for_them_to_end(self):
        quiet = self.run_reset_frame(midnight(TODAY), quiet=True)
        self.assertIs(quiet.ok, True)
        self.assertEqual((quiet.obtained, quiet.pushed, quiet.saved), ([], 0, []))
        later = self.run_reset_frame(midnight(TODAY))
        self.assertEqual((later.obtained, later.pushed), ([TODAY], 1))

    def test_reset_at_midnight_preview_renders_but_never_touches_the_panel(self):
        for payload in (midnight([]), midnight(TODAY, clamped=False)):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                preview = pathlib.Path(directory) / "preview.png"
                result = self.run_reset_frame(payload, preview=str(preview))
                self.assertIs(result.ok, True)
                self.assertTrue(preview.is_file())
                self.assertEqual(result.obtained, [payload["species"]])
                self.assertEqual((result.pushed, result.saved), (0, []))

    def test_reset_at_midnight_is_ignored_outside_local_mode(self):
        for mode in ({"species_source": "birdweather", "zip": "49503"}, {"shoot": False, "image": "frame.png"}):
            with self.subTest(mode=mode):
                on = self.run_reset_frame(None, cfg=mode)
                off = self.run_reset_frame(None, cfg=dict(mode, reset_at_midnight=False))
                self.assertEqual((on.ok, on.obtained, on.pushed, on.saved), (off.ok, off.obtained, off.pushed, off.saved))
                self.assertEqual(on.log.count("reset_at_midnight applies only to local mode; ignored"), 1)
                self.assertNotIn("reset_at_midnight", off.log)
                on.fetch.assert_not_called()

    def test_reset_at_midnight_does_not_depend_on_the_frame_clock(self):
        class FarDatetime(self.display.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(1999, 12, 31, 23, 59)

        outcomes = {}
        for now, clock in ((NOW, self.display.datetime), (4_000_000_000.0, FarDatetime)):
            for name, payload in (("empty", midnight([])), ("bird", midnight(TODAY))):
                with mock.patch.object(self.display.urllib.request, "urlopen", return_value=Response(payload)) as urlopen, \
                        mock.patch.object(self.display, "datetime", clock):
                    result = self.run_reset_frame(None, now=now, quiet=None)
                outcomes.setdefault(name, set()).add(
                    (urlopen.call_args[0][0].full_url, result.ok, len(result.obtained), result.pushed))
        self.assertEqual(outcomes, {
            "empty": {("http://birdnet.local/avian/api/birdnet-api.php?action=recent&hours=24&reset_at_midnight=1", True, 0, 0)},
            "bird": {("http://birdnet.local/avian/api/birdnet-api.php?action=recent&hours=24&reset_at_midnight=1", True, 1, 1)},
        })

    def test_recent_payload_asks_for_the_midnight_window_and_fetch_recent_is_unchanged(self):
        payload = midnight(TODAY)
        with mock.patch.object(self.display.urllib.request, "urlopen", return_value=Response(payload)) as urlopen:
            self.assertEqual(self.display.fetch_recent_payload("http://station/", 24, 5, reset_at_midnight=True), payload)
            self.assertEqual(urlopen.call_args[0][0].full_url,
                             "http://station/avian/api/birdnet-api.php?action=recent&hours=24&reset_at_midnight=1")
            self.assertEqual(self.display.fetch_recent("http://station", 24, 5), TODAY)
            self.assertEqual(urlopen.call_args[0][0].full_url, "http://station/avian/api/birdnet-api.php?action=recent&hours=24")

    def test_api_handler_asks_the_station_for_its_midnight_window_once(self):
        base = "http://station/avian/api/birdnet-api.php?action=recent"
        for url in (f"{base}&hours=12&edu=saved", f"{base}&hours=12&edu=saved&reset_at_midnight=1"):
            with self.subTest(url=url):
                route = Route({"species": TODAY, "midnight_clamped": True})
                route.request.url = url
                self.shoot._make_api_handler(0.04, 24, None, reset_at_midnight=True)(route)
                self.assertEqual(route.fetch_args["url"], f"{base}&hours=24&edu=saved&reset_at_midnight=1")
                self.assertEqual(route.result["status"], 200)
        route = Route({"species": TODAY})
        self.shoot._make_api_handler(0.04, 24, None)(route)
        self.assertEqual(route.fetch_args["url"], f"{base}&hours=24&edu=saved")
        route = Route({})
        route.request.url = "http://station/avian/api/birdnet-api.php?action=stats"
        self.shoot._make_api_handler(0.04, 24, None, reset_at_midnight=True)(route)
        self.assertTrue(route.continued)
        self.assertFalse(hasattr(route, "fetch_args"))

    def test_capture_asks_for_the_midnight_window_only_when_reset_is_active(self):
        calls = []

        def fake_shoot(_url, out, **kwargs):
            calls.append((kwargs["window_hours"], kwargs["reset_at_midnight"]))
            Image.new("RGB", (4, 4)).save(out)

        module = types.ModuleType("shoot")
        module.shoot = fake_shoot
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(sys.modules, {"shoot": module}):
            for flag in (True, False):
                cfg = dict(self.display.DEFAULTS, shoot=True, hours=6, cache=directory, reset_at_midnight=flag)
                self.display.obtain_image(cfg)
        self.assertEqual(calls, [(24, True), (6, False)])
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(self.shoot, "_make_api_handler", wraps=self.shoot._make_api_handler) as handler:
            self.capture_page(CapturePage("ready"), str(pathlib.Path(directory) / "shot.png"),
                              window_hours=24, reset_at_midnight=True)
        self.assertEqual(handler.call_args[0][1], 24)
        self.assertIs(handler.call_args[0][5], True)

    def capture_page(self, page, output, capture=None, **options):
        browser = mock.Mock()
        browser.new_context.return_value.new_page.return_value = page
        manager = contextlib.nullcontext(types.SimpleNamespace(
            chromium=types.SimpleNamespace(launch=lambda **_kwargs: browser)))
        with mock.patch.object(self.shoot, "sync_playwright", return_value=manager):
            kwargs = {} if capture is None else {"capture": capture}
            return self.shoot.shoot("http://station", output, timeout_ms=options.pop("timeout_ms", 5000),
                                    bird_names=page.mode == "font-timeout", **kwargs, **options)

    def test_bundle_integrity_failure_during_screenshot_keeps_previous_png(self):
        page = CapturePage("ready")
        screenshot = page.screenshot

        def fail_resolve(*_args):
            raise RuntimeError("checksum mismatch")

        def capture_with_late_failure(**kwargs):
            route = Route({})
            route.request.url = "http://station/avian/api/cutout.php?sci=Corvus%20corax&pose=1"
            page.routes["**/cutout.php*"](route)
            return screenshot(**kwargs)

        page.screenshot = capture_with_late_failure
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            with self.assertRaisesRegex(RuntimeError, "collage changed during capture"):
                self.capture_page(page, str(output), cutout_resolver=fail_resolve)
            self.assertEqual(output.read_bytes(), b"previous capture")
            self.assertEqual(page.screenshots, 1, "integrity failures are not retried")

    def test_changed_recent_before_capture_retries_and_reports_the_new_species(self):
        page = CapturePage("ready")
        wait = page.wait_for_function
        newer = [{"sci": "Turdus migratorius", "com": "Robin", "n": 2}]

        def refresh_during_decode(script, **kwargs):
            if "decode" in script and page.token == "1":
                page.routes["**/birdnet-api.php**"](Route({"species": newer, "hours": 24}))
                page.token = "2"
                page.revision = "2"
            return wait(script, **kwargs)

        page.wait_for_function = refresh_during_decode
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {}
            self.capture_page(page, str(output), capture)
            with Image.open(output) as result:
                self.assertEqual(result.getpixel((20, 40)), (255, 0, 0))
            self.assertEqual(capture["species"], newer)
            self.assertEqual(page.screenshots, 16, "the invalidated pre-capture attempt takes no screenshot")

    def test_recent_response_during_final_validation_cannot_relabel_an_older_png(self):
        page = CapturePage("ready")
        evaluate = page.evaluate
        newer = [{"sci": "Turdus migratorius", "com": "Robin", "n": 2}]

        def response_during_validation(script, *args):
            unchanged = evaluate(script, *args)
            if "frame" in script and page.screenshots == 1 and page.token == "1":
                # Playwright pumps route callbacks while evaluate is in flight;
                # Python can observe a new response after the JS result was
                # computed. The successful screenshot still belongs to token 1.
                page.routes["**/birdnet-api.php**"](Route({"species": newer, "hours": 24}))
                page.token = "2"
                page.revision = "2"
            return unchanged

        page.evaluate = response_during_validation
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {}
            self.capture_page(page, str(output), capture)
            self.assertEqual(page.screenshots, 17)
            self.assertEqual(capture["species"], newer)

    def test_api_failure_during_final_validation_is_not_retried_or_published(self):
        page = CapturePage("ready")
        evaluate = page.evaluate

        def fail_during_validation(script, *args):
            unchanged = evaluate(script, *args)
            if "frame" in script and page.screenshots:
                page.routes["**/birdnet-api.php**"](Route({"error": "unavailable"}, 503))
            return unchanged

        page.evaluate = fail_during_validation
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(io.StringIO()):
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {"species": []}
            with self.assertRaises(RuntimeError):
                self.capture_page(page, str(output), capture)
            self.assertEqual(page.screenshots, 1)
            self.assertEqual(output.read_bytes(), b"previous capture")
            self.assertEqual(capture, {"species": []})

    def test_continuous_rerenders_are_bounded_and_preserve_png_and_capture_metadata(self):
        page = CapturePage("ready")
        screenshot = page.screenshot

        def rerender(**kwargs):
            png = screenshot(**kwargs)
            page.revision = str(int(page.revision) + 1)
            return png

        page.screenshot = rerender
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {"species": [{"sci": "previous snapshot"}]}
            with self.assertRaisesRegex(RuntimeError, "collage changed during capture"):
                self.capture_page(page, str(output), capture)
            self.assertEqual(page.screenshots, 3)
            self.assertEqual(output.read_bytes(), b"previous capture")
            self.assertEqual(capture, {"species": [{"sci": "previous snapshot"}]})
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [output])

    def test_capture_retries_share_one_deadline_including_the_screenshot(self):
        page = CapturePage("ready")
        screenshot = page.screenshot
        elapsed = [0.0]
        timeouts = []

        def slow_rerender(**kwargs):
            timeouts.append(kwargs.get("timeout"))
            png = screenshot(**kwargs)
            elapsed[0] += 0.003
            page.revision = str(int(page.revision) + 1)
            return png

        page.screenshot = slow_rerender
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch("time.monotonic", side_effect=lambda: elapsed[0]):
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {"species": []}
            with self.assertRaises(RuntimeError):
                self.capture_page(page, str(output), capture, timeout_ms=5)
            self.assertEqual(timeouts, [5, 2])
            self.assertEqual(output.read_bytes(), b"previous capture")
            self.assertEqual(capture, {"species": []})

    def test_incomplete_or_changed_capture_keeps_previous_png(self):
        for mode in ("broken-image", "old-frontend", "rerender", "decode-timeout", "font-timeout"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                output = pathlib.Path(directory) / "shot.png"
                output.write_bytes(b"previous capture")
                with self.assertRaises((RuntimeError, TimeoutError)):
                    self.capture_page(CapturePage(mode), str(output))
                self.assertEqual(output.read_bytes(), b"previous capture")

    def test_completed_capture_replaces_png_and_reports_its_species(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "shot.png"
            output.write_bytes(b"previous capture")
            capture = {}
            self.capture_page(CapturePage("ready"), str(output), capture)
            with Image.open(output) as result:
                self.assertEqual(result.size, (1200, 1600))
                self.assertEqual(result.getpixel((20, 40)), (255, 0, 0))
            self.assertEqual(capture["species"], SPECIES)
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [output])

    def test_typography_bounds_the_visible_compositor_surface(self):
        page = CapturePage("ready")
        with self.shoot.capture_text_overlay(page, 600, 800, 2):
            pass
        self.assertEqual(len(page.visible_surfaces), page.screenshots)
        self.assertGreater(len(page.visible_surfaces), 0)
        for method, metrics in page.visible_surfaces:
            self.assertEqual(method, "Emulation.setDeviceMetricsOverride")
            self.assertEqual((metrics["width"], metrics["height"], metrics["deviceScaleFactor"]), (600, 800, 2))
            view = metrics["viewport"]
            self.assertLessEqual(view["width"] * view["height"] * 4, 120000)

    def test_replacing_capture_preserves_existing_file_permissions(self):
        for mode in (0o644, 0o640, 0o600):
            with self.subTest(mode=oct(mode)), tempfile.TemporaryDirectory() as directory:
                output = pathlib.Path(directory) / "shot.png"
                output.write_bytes(b"previous capture")
                output.chmod(mode)
                before = output.stat()
                self.capture_page(CapturePage("ready"), str(output))
                after = output.stat()
                self.assertEqual(stat.S_IMODE(after.st_mode), mode)
                self.assertEqual((after.st_uid, after.st_gid), (before.st_uid, before.st_gid))

    def test_new_capture_respects_process_umask(self):
        for mask, mode in ((0o022, 0o644), (0o027, 0o640), (0o077, 0o600)):
            with self.subTest(mask=oct(mask)), tempfile.TemporaryDirectory() as directory:
                output = pathlib.Path(directory) / "shot.png"
                previous_mask = os.umask(mask)
                try:
                    self.capture_page(CapturePage("ready"), str(output))
                finally:
                    os.umask(previous_mask)
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), mode)

    def test_capture_does_not_follow_an_output_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "private.png"
            target.write_bytes(b"private image")
            target.chmod(0o600)
            output = pathlib.Path(directory) / "shot.png"
            output.symlink_to(target)
            with self.assertRaises(RuntimeError):
                self.capture_page(CapturePage("ready"), str(output))
            self.assertTrue(output.is_symlink())
            self.assertEqual(target.read_bytes(), b"private image")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)


def capture_art():
    return load("capture_art_test", "frame/capture_art.py")


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def small_png(color=(255, 0, 0, 255)):
    output = io.BytesIO()
    Image.new("RGBA", (2, 1), color).save(output, "PNG")
    return output.getvalue()


@pytest.mark.parametrize("damage", ["iend-crc", "missing-iend", "missing-crc", "trailing",
    "duplicate-ihdr", "oversized", "chunk-length", "idat-order", "bad-zlib", "short-zlib", "animation"])
def test_decoder_rejects_malformed_png(damage):
    art = capture_art()
    png = small_png()
    ihdr, idat, iend = png[8:33], png[33:-12], png[-12:]
    variants = {
        "iend-crc": png[:-1] + bytes([png[-1] ^ 1]),
        "missing-iend": png[:-12], "missing-crc": png[:-3], "trailing": png + b"extra",
        "duplicate-ihdr": png[:33] + ihdr + png[33:],
        "oversized": png[:8] + png_chunk(b"IHDR", struct.pack(">II", 8193, 1) + png[24:29]) + png[33:],
        "chunk-length": png[:33] + b"\xff\xff\xff\xff" + png[37:],
        "idat-order": png[:33] + idat + png_chunk(b"tEXt", b"key\0value") + idat + iend,
        "bad-zlib": png[:33] + png_chunk(b"IDAT", b"invalid") + iend,
        "short-zlib": png[:33] + png_chunk(b"IDAT", idat[8:-7]) + iend,
        "animation": png[:33] + png_chunk(b"acTL", struct.pack(">II", 1, 0)) + png[33:],
    }
    with pytest.raises(RuntimeError):
        art.decode_capture_image(variants[damage])


def test_decoder_accepts_png_and_full_empty_nest_webp():
    art = capture_art()
    with art.decode_capture_image(small_png()) as decoded:
        assert decoded.mode == "RGBA" and decoded.size == (2, 1)
        assert decoded.getpixel((0, 0)) == (255, 0, 0, 255)
    nest = (ROOT / "avian/frontend/nest.webp").read_bytes()
    with Image.open(io.BytesIO(nest)) as expected, art.decode_capture_image(nest) as decoded:
        expected.load()
        assert decoded.size == expected.size
        assert decoded.tobytes() == expected.convert("RGBA").tobytes()
    for bad in (nest[:-1], nest + b"x", nest[:12] + b"broken"):
        with pytest.raises(RuntimeError):
            art.decode_capture_image(bad)


@pytest.mark.parametrize("row_bytes", [17, 34, 51, 69])
def test_png_incomplete_or_excess_scanlines_reject(row_bytes):
    from tests.png_fixtures import scanline_png
    with pytest.raises(RuntimeError):
        capture_art().decode_capture_image(scanline_png(4, 4, 8, 6, bytes(row_bytes)))


def test_png_capture_limits_precede_inflation(monkeypatch):
    from tests.png_fixtures import scanline_png
    art = capture_art()
    data = scanline_png(4, 4, 8, 6, bytes(68))

    class ForbiddenInflater:
        def decompress(self, *_args):
            raise AssertionError("oversized capture PNG reached decompression")

    monkeypatch.setattr(art, "MAX_ASSET_PIXELS", 10)
    monkeypatch.setattr(art._png_validation.zlib, "decompressobj", ForbiddenInflater)
    with pytest.raises(RuntimeError, match="dimensions exceed limits"):
        art.decode_capture_image(data)


def test_capture_art_import_and_png_decode_from_frame_cwd():
    result = subprocess.run([sys.executable, "-c",
                             "import capture_art; from pathlib import Path; "
                             "data=Path('../avian/assets/illustrations/corvus-brachyrhynchos.png').read_bytes(); "
                             "image=capture_art.decode_capture_image(data); "
                             "assert image.width > 0; image.close()"],
                            cwd=ROOT / "frame", capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("width,height,depth,color,interlace,byte_count", [
    (3, 2, 1, 0, 0, 4),  # Each packed row is one filter plus one sample byte.
    (5, 3, 2, 0, 0, 9),
    (3, 2, 4, 0, 0, 6),
    (3, 2, 1, 3, 0, 4),
    (3, 2, 16, 0, 0, 14),
    (3, 2, 16, 2, 0, 38),
    (3, 2, 16, 4, 0, 26),
    (3, 2, 16, 6, 0, 50),
    (1, 1, 8, 6, 1, 5),  # Only Adam7 pass one is nonempty.
    (1, 2, 8, 6, 1, 10),  # Passes one and seven each contain one pixel.
    (2, 1, 8, 6, 1, 10),  # Passes one and six each contain one pixel.
    (2, 2, 8, 6, 1, 19),  # 5 + 5 + 9 bytes in passes one, six, seven.
    (3, 3, 1, 0, 1, 12),  # Six rows across five nonempty packed passes.
    (8, 8, 8, 6, 1, 271),  # 256 sample bytes plus 15 filter bytes.
])
def test_png_exact_scanline_count_across_formats(width, height, depth, color, interlace, byte_count):
    from tests.png_fixtures import scanline_png
    art = capture_art()
    good = scanline_png(width, height, depth, color, bytes(byte_count), interlace)
    with art.decode_capture_image(good) as image:
        assert image.size == (width, height)
    for wrong_count in (byte_count - 1, byte_count + 1):
        with pytest.raises(RuntimeError):
            art.decode_capture_image(scanline_png(width, height, depth, color,
                                                  bytes(wrong_count), interlace))


def small_webp(kind):
    output = io.BytesIO()
    Image.new("RGB", (2, 1), (30, 60, 90)).save(output, "WEBP", lossless=kind != b"VP8 ")
    data = output.getvalue()
    assert data[12:16] == (b"VP8L" if kind == b"VP8X" else kind)
    if kind == b"VP8X":
        # Extended canvas 2x1, with the unchanged lossless bitstream following.
        chunks = b"VP8X\x0a\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00" + data[12:]
        data = b"RIFF" + struct.pack("<I", len(chunks) + 4) + b"WEBP" + chunks
    return data


@pytest.mark.parametrize("kind,offset,dimensions", [
    (b"VP8 ", 26, b"\x00\x20\x00\x20"),  # 8192x8192 exceeds pixel budget.
    (b"VP8 ", 26, b"\x01\x20\x01\x00"),  # 8193x1 exceeds edge budget.
    (b"VP8L", 21, b"\xff\xdf\xff\x07"),
    (b"VP8L", 21, b"\x00\x20\x00\x00"),
    (b"VP8X", 24, b"\xff\x1f\x00\xff\x1f\x00"),
    (b"VP8X", 24, b"\x00\x20\x00\x00\x00\x00"),
    # A small extended canvas cannot mask an oversized inner VP8L bitstream.
    (b"VP8X", 39, b"\xff\xdf\xff\x07"),
    (b"VP8X", 39, b"\x00\x20\x00\x00"),
])
def test_webp_dimensions_reject_before_decoder_entry(monkeypatch, kind, offset, dimensions):
    art = capture_art()
    data = bytearray(small_webp(kind))
    data[offset:offset + len(dimensions)] = dimensions

    def forbidden_decoder(*_args, **_kwargs):
        raise AssertionError("Pillow entered before WebP dimensions were bounded")

    monkeypatch.setattr(art.Image, "open", forbidden_decoder)
    with pytest.raises(RuntimeError, match="dimensions exceed limits"):
        art.decode_capture_image(bytes(data))


@pytest.mark.parametrize("kind", [b"VP8 ", b"VP8L", b"VP8X"])
def test_webp_bounded_headers_still_fully_decode(kind):
    art = capture_art()
    data = small_webp(kind)
    with Image.open(io.BytesIO(data)) as expected, art.decode_capture_image(data) as decoded:
        expected.load()
        assert decoded.size == (2, 1)
        assert decoded.tobytes() == expected.convert("RGBA").tobytes()


@pytest.mark.parametrize("kind,payload", [
    (b"VP8 ", b"\x00" * 9),
    (b"VP8 ", b"\x00" * 10),  # Missing keyframe start code.
    (b"VP8 ", b"\x01\x00\x00\x9d\x01\x2a\x02\x00\x01\x00"),
    (b"VP8L", b"\x2f\x00\x00\x00"),
    (b"VP8L", b"\x00\x01\x00\x00\x00"),  # Incorrect lossless signature.
    (b"VP8L", b"\x2f\x01\x00\x00\x20"),  # Unsupported version one.
    (b"VP8X", b"\x00" * 9),
    (b"VP8X", b"\x00" * 11),
])
def test_webp_invalid_headers_reject_before_decoder_entry(monkeypatch, kind, payload):
    art = capture_art()
    chunk = kind + struct.pack("<I", len(payload)) + payload + b"\x00" * (len(payload) & 1)
    data = b"RIFF" + struct.pack("<I", len(chunk) + 4) + b"WEBP" + chunk

    def forbidden_decoder(*_args, **_kwargs):
        raise AssertionError("Pillow entered with an invalid WebP header")

    monkeypatch.setattr(art.Image, "open", forbidden_decoder)
    with pytest.raises(RuntimeError, match="invalid WebP header"):
        art.decode_capture_image(data)


@pytest.mark.parametrize("kind,header_size", [(b"VP8 ", 10), (b"VP8L", 5)])
def test_webp_valid_header_without_compressed_pixels_fails_full_decode(kind, header_size):
    art = capture_art()
    payload = small_webp(kind)[20:20 + header_size]
    chunk = kind + struct.pack("<I", len(payload)) + payload + b"\x00" * (len(payload) & 1)
    data = b"RIFF" + struct.pack("<I", len(chunk) + 4) + b"WEBP" + chunk
    with pytest.raises(RuntimeError, match="could not be fully decoded"):
        art.decode_capture_image(data)


def test_decoder_rejects_unsupported_animation_and_size_limits(monkeypatch):
    art = capture_art()
    gif = io.BytesIO()
    Image.new("RGB", (1, 1)).save(gif, "GIF")
    with pytest.raises(RuntimeError):
        art.decode_capture_image(gif.getvalue())
    frames = [Image.new("RGB", (2, 2), color) for color in ("red", "blue")]
    webp = io.BytesIO()
    frames[0].save(webp, "WEBP", save_all=True, append_images=frames[1:], duration=100)
    with pytest.raises(RuntimeError):
        art.decode_capture_image(webp.getvalue())
    with monkeypatch.context() as patch:
        patch.setattr(art, "MAX_ASSET_BYTES", 10)
        with pytest.raises(RuntimeError):
            art.decode_capture_image(small_png())
    with monkeypatch.context() as patch:
        patch.setattr(art, "MAX_ASSET_PIXELS", 1)
        with pytest.raises(RuntimeError):
            art.decode_capture_image(small_png())


def test_compositor_preserves_contain_offsets_fractional_origin_and_alpha():
    art = capture_art()
    overlay = Image.new("RGBA", (10, 10))
    overlay.putpixel((3, 4), (0, 255, 0, 128))
    records = [{"body": small_png(), "rect": [1.5, 2.5, 4, 4],
                "fit": "contain", "position": [0.5, 0.5], "shadow": None, "natural": [2, 1]}]
    output = art.compose_capture(overlay, records, (10, 10), (255, 255, 255))
    expected = Image.new("RGB", (10, 10), "white")
    for y in (4, 5):
        for x in (2, 3, 4, 5):
            expected.putpixel((x, y), (255, 0, 0))
    expected.putpixel((3, 4), (127, 128, 0))
    with Image.open(io.BytesIO(output)) as result:
        assert result.mode == "RGB"
        assert result.tobytes() == expected.tobytes()
    encoded = io.BytesIO()
    expected.save(encoded, "PNG")
    assert output == encoded.getvalue()


def test_compositor_places_measured_shadow_under_art():
    art = capture_art()
    records = [{"body": small_png(), "rect": [2, 2, 2, 1], "fit": "fill", "position": [0.5, 0.5],
                "shadow": {"offset": [0, 2], "blur": 0, "color": [0, 0, 0, 64]}, "natural": [2, 1]}]
    output = art.compose_capture(Image.new("RGBA", (8, 8)), records, (8, 8), (255, 255, 255))
    with Image.open(io.BytesIO(output)) as result:
        assert result.getpixel((2, 2)) == (255, 0, 0)
        assert result.getpixel((2, 4)) == (191, 191, 191)
        assert result.getpixel((2, 5)) == (255, 255, 255)


def test_compositor_rejects_mixed_invalid_art_and_budget_overflows(monkeypatch):
    art = capture_art()
    item = {"body": small_png(), "rect": [0, 0, 2, 1], "fit": "fill", "position": [0.5, 0.5],
            "shadow": None, "natural": [2, 1]}
    overlay = Image.new("RGBA", (2, 2))
    for items in ([item, {**item, "body": small_png()[:-12]}],
                  [item] * 513, [{**item, "natural": [1, 1]}],
                  [{**item, "rect": [0, 0, float("nan"), 1]}]):
        with pytest.raises(RuntimeError):
            art.compose_capture(overlay, items, (2, 2), (255, 255, 255))
    with pytest.raises(RuntimeError):
        art.compose_capture(overlay, [item], (4000, 4000), (255, 255, 255))
    monkeypatch.setattr(art, "MAX_RETAINED_BYTES", len(item["body"]) - 1)
    with pytest.raises(RuntimeError):
        art.compose_capture(overlay, [item], (2, 2), (255, 255, 255))


def test_response_limits_reject_before_retaining_oversized_art(monkeypatch):
    shoot = load("bounded_shoot", "frame/shoot.py")
    item = {"src": "http://station/bird", "box": [0, 0, 2, 1], "natural": [2, 1],
            "fit": "fill", "position": "50% 50%", "filter": "none"}

    def forbidden_body():
        raise AssertionError("oversized Content-Length must be rejected before body()")

    response = types.SimpleNamespace(ok=True, header_value=lambda _name: "16777217", body=forbidden_body)
    with pytest.raises(RuntimeError):
        shoot._composition_images({"images": [item]}, {item["src"]: response}, 1)
    with pytest.raises(RuntimeError):
        shoot._composition_images({"images": [item]}, {}, 1)
    response.header_value = lambda _name: "1"
    response.body = small_png
    monkeypatch.setattr(shoot.capture_art, "MAX_RETAINED_BYTES", len(small_png()) - 1)
    with pytest.raises(RuntimeError):
        shoot._composition_images({"images": [item]}, {item["src"]: response}, 1)


if __name__ == "__main__":
    unittest.main()
