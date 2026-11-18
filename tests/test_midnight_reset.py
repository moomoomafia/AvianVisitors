import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path


class MidnightResetTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("php"), "PHP CLI is unavailable")
    def test_php_contract(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["php", str(root / "tests" / "test_midnight_reset.php")],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("midnight reset tests passed", result.stdout)

    @unittest.skipUnless(shutil.which("php"), "PHP CLI is unavailable")
    def test_recent_request_can_ask_for_the_station_midnight(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="avian-midnight-") as temporary:
            temp = Path(temporary)
            (temp / "educators.lock").write_text("", encoding="utf-8")
            (temp / "educators.state").write_text("v1\t0\t7\n", encoding="utf-8")
            db = sqlite3.connect(temp / "birds.db")
            db.execute("CREATE TABLE detections (Date TEXT, Time TEXT, Sci_Name TEXT, Com_Name TEXT, "
                       "Confidence REAL, File_Name TEXT)")
            db.close()
            environment = {**os.environ, "AV_EDUCATOR_LOCK_FILE": str(temp / "educators.lock"),
                           "AV_EDUCATOR_STATE_FILE": str(temp / "educators.state"),
                           "AV_EDUCATOR_BIRDS_DB": str(temp / "birds.db"), "AV_REQUIRE_AUTH": "0",
                           "AV_EDUCATOR_STATE_TEST_METADATA": "1", "AV_EDUCATOR_STORE_TEST_METADATA": "1"}
            windows = {}
            for flag in ("", "&reset_at_midnight=1"):
                code = ("$_SERVER=['REQUEST_METHOD'=>'GET','REMOTE_ADDR'=>'203.0.113.40','HTTP_HOST'=>'birds.example.com'];"
                        f"parse_str('action=recent&hours=24{flag}', $_GET);"
                        f"require {json.dumps(str(root / 'avian' / 'api' / 'birdnet-api.php'))};")
                result = subprocess.run(["php", "-r", code], cwd=root, env=environment, text=True,
                                        capture_output=True, timeout=10, check=False)
                windows[flag] = json.loads(result.stdout)
        # A per-request ask clamps today's window to the station's midnight; without it, rolling 24 h.
        self.assertIs(windows[""]["midnight_clamped"], False)
        self.assertIs(windows["&reset_at_midnight=1"]["midnight_clamped"], True)
        self.assertTrue(windows["&reset_at_midnight=1"]["window_start"].endswith(" 00:00:00"))


if __name__ == "__main__":
    unittest.main()
