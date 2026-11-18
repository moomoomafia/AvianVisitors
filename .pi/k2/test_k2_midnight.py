"""K2: the midnight scenarios end to end (Plan v0.5 §6, decisions D26/D27). Lives in .pi/ only (D20).

Real frame/display.py run() + real frame/shoot.py headless Chromium + the real station `recent`
endpoint (php -r, as in tests/test_midnight_reset.py) against a synthetic birds.db. The station's
clock is moved per request with a POSIX TZ offset (D27); a fake Inky (.pi/k2/fake_inky) counts panel
pushes. The static frontend is served like the parent's `station` fixture in
tests/test_frame_capture_browser.py. Run with .pi/k2/run.sh (inside the K1 image).
"""
import functools
import http.server
import importlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

inky = importlib.import_module("inky")  # the fake from .pi/k2/fake_inky, put on PYTHONPATH by run.sh

ROOT = Path(__file__).resolve().parents[2]
BASE_ROOT = Path(os.environ.get("K2_BASE_ROOT", "/base"))  # parent base 5950f807: the "outdated station"
ILLUSTRATIONS = ROOT / "avian/assets/illustrations"
CROW, JAY = ("Corvus brachyrhynchos", "American Crow"), ("Cyanocitta cristata", "Blue Jay")


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def tz_for(local):
    """POSIX TZ whose local time is `local` right now (local = UTC - offset)."""
    offset = round((utc_now() - local).total_seconds())
    sign = "-" if offset < 0 else ""
    hours, rest = divmod(abs(offset), 3600)
    return f"XXX{sign}{hours}:{rest // 60:02d}:{rest % 60:02d}"


def day(offset_days=0):
    """The station's 'today' D (or D +/- n) for this test run, as a date."""
    return (utc_now() - timedelta(minutes=10)).date() + timedelta(days=offset_days)


def at(d, clock):
    return datetime.combine(d, datetime.strptime(clock, "%H:%M:%S").time())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def station(tmp_path):
    (tmp_path / "educators.lock").write_text("")
    (tmp_path / "educators.state").write_text("v1\t0\t7\n")
    db = sqlite3.connect(tmp_path / "birds.db")
    db.execute("CREATE TABLE detections (Date TEXT, Time TEXT, Sci_Name TEXT NOT NULL, Com_Name TEXT NOT NULL, "
               "Confidence REAL, Lat REAL, Lon REAL, Cutoff REAL, Week INTEGER, Sens REAL, Overlap REAL, "
               "File_Name TEXT NOT NULL)")
    db.commit()
    db.close()
    state = {"root": ROOT, "clock": [], "recent": []}

    def seed(*rows):
        db = sqlite3.connect(tmp_path / "birds.db")
        db.executemany("INSERT INTO detections (Date, Time, Sci_Name, Com_Name, Confidence, File_Name) "
                       "VALUES (?, ?, ?, ?, 0.9, 'x.mp3')",
                       [(d.isoformat(), clock, sci, com) for d, clock, (sci, com) in rows])
        db.commit()
        db.close()

    def recent(query):
        local = state["clock"].pop(0) if len(state["clock"]) > 1 else state["clock"][0]
        environment = {**os.environ, "TZ": tz_for(local),
                       "AV_EDUCATOR_LOCK_FILE": str(tmp_path / "educators.lock"),
                       "AV_EDUCATOR_STATE_FILE": str(tmp_path / "educators.state"),
                       "AV_EDUCATOR_BIRDS_DB": str(tmp_path / "birds.db"),
                       "AV_EDUCATOR_MAINTENANCE_FILE": str(tmp_path / "educators.maintenance"),
                       "AV_EDUCATOR_STATE_TEST_METADATA": "1", "AV_EDUCATOR_STORE_TEST_METADATA": "1"}
        api = state["root"] / "avian/api/birdnet-api.php"
        code = ("$_SERVER=['REQUEST_METHOD'=>'GET','REMOTE_ADDR'=>'203.0.113.40','HTTP_HOST'=>'birds.example.com'];"
                "parse_str('" + query.replace("'", "") + "', $_GET);"
                f"require {json.dumps(str(api))};")
        result = subprocess.run(["php", "-r", code], cwd=state["root"], env=environment, text=True,
                                capture_output=True, timeout=20, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        body = json.loads(result.stdout)
        state["recent"].append({"query": query, "local": local, "species": [s["sci"] for s in body["species"]],
                                "clamped": body.get("midnight_clamped")})
        return result.stdout.encode()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 - matches the base signature
            pass

        def send(self, data, kind):
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            if url.path == "/":
                html = (ROOT / "avian/frontend/index.html").read_text()
                html = html.replace("</head>", "<script>Math.random=()=>0.9;</script></head>")
                return self.send(html.encode(), "text/html")
            if url.path == "/avian/api/birdnet-api.php" and query.get("action") == ["recent"]:
                return self.send(recent(url.query), "application/json")
            if url.path == "/avian/api/bundle-assets.php":
                return self.send_error(404)  # included artwork uses the legacy table path
            if url.path == "/avian/api/cutout.php":
                name = query["sci"][0].lower().replace(" ", "-") + ("-2" if query.get("pose") == ["2"] else "")
                return self.send((ILLUSTRATIONS / (name + ".png")).read_bytes(), "image/png")
            if url.path.startswith("/avian/api/"):
                return self.send(b"{}", "application/json")
            self.path = self.path.removeprefix("/avian/frontend")
            return super().do_GET()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(
        Handler, directory=str(ROOT / "avian/frontend")))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", state, seed
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


@pytest.fixture
def frame(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "frame"))
    monkeypatch.setitem(sys.modules, "shoot", load("k2_shoot", ROOT / "frame/shoot.py"))
    display = load("k2_display", ROOT / "frame/display.py")
    state_file = tmp_path / "state.json"

    def run(url, *, reset=True, force=False, use_signature=True):
        state_file.write_text(json.dumps({"signature": "before-midnight", "last_refresh": time.time()}))
        before = state_file.read_bytes()
        inky.PUSHES.clear()
        cfg = dict(display.DEFAULTS, shoot=True, base_url=url, cache=str(tmp_path), state=str(state_file),
                   timeout=60, reset_at_midnight=reset)
        ok = display.run(cfg, force=force, use_signature=use_signature)
        return ok, len(inky.PUSHES), state_file.read_bytes() != before

    return run


@pytest.mark.parametrize("force,use_signature", [(False, True), (True, True), (True, False)],
                         ids=["timer", "force", "bundle-use"])
def test_quiet_night_keeps_yesterdays_collage(station, frame, force, use_signature):
    url, state, seed = station
    seed((day(-1), "20:00:00", CROW))
    state["clock"] = [at(day(), "00:05:00")]
    ok, pushes, saved = frame(url, force=force, use_signature=use_signature)
    assert (ok, pushes, saved) == (True, 0, False)
    assert state["recent"][0]["clamped"] is True and state["recent"][0]["species"] == []


def test_first_bird_after_midnight_draws_only_today(station, frame):
    url, state, seed = station
    seed((day(-1), "20:00:00", CROW), (day(), "00:03:00", JAY))
    state["clock"] = [at(day(), "00:05:00")]
    ok, pushes, saved = frame(url)
    assert (ok, pushes, saved) == (True, 1, True)
    assert len(state["recent"]) >= 2  # the frame's decision fetch, then the page's own request
    assert all(r["species"] == [JAY[0]] and r["clamped"] is True for r in state["recent"])


def test_capture_that_crosses_midnight_keeps_the_panel(station, frame):
    """Review R, F1: decided on 23:59:50's list, captured after midnight -> never push the empty nest."""
    url, state, seed = station
    seed((day(-1), "20:00:00", CROW))
    state["clock"] = [at(day(-1), "23:59:50"), at(day(), "00:00:10")]
    ok, pushes, saved = frame(url)
    assert state["recent"][0]["species"] == [CROW[0]]  # the frame saw a bird and decided to draw
    assert state["recent"][-1]["species"] == []  # the page asked again after the station's midnight
    assert (ok, pushes, saved) == (True, 0, False)


def test_control_flag_off_pushes_the_empty_nest(station, frame):
    """Control: without the flag the parent redraws an empty window, so the fake panel can see a blank push."""
    url, state, _seed = station
    state["clock"] = [at(day(), "00:05:00")]
    ok, pushes, saved = frame(url, reset=False)
    assert (ok, pushes, saved) == (True, 1, True)
    assert state["recent"][-1]["species"] == []


def test_outdated_station_holds_and_reports_failure(station, frame):
    """D14: a station without the per-request param never clamps; hold the panel and exit 1."""
    assert (BASE_ROOT / "avian/api/birdnet-api.php").is_file(), "K2_BASE_ROOT must hold the parent base tree"
    url, state, seed = station
    state["root"] = BASE_ROOT
    seed((day(), "00:03:00", JAY))
    state["clock"] = [at(day(), "00:05:00")]
    ok, pushes, saved = frame(url)
    assert (ok, pushes, saved) == (False, 0, False)
    assert state["recent"][0]["clamped"] is False
