"""Crash recovery experiment with a real SIGKILL and SQLite persistence.

Runs only in disposable temporary directories. No secrets or network calls.
"""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER = r'''
import os, sqlite3, sys
db, marker, mode = sys.argv[1:]
con = sqlite3.connect(db, isolation_level=None)
con.execute("PRAGMA journal_mode=WAL")
con.execute("CREATE TABLE IF NOT EXISTS outcomes (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
con.execute("INSERT OR IGNORE INTO outcomes VALUES (?, ?)", ("canary-001", "verified"))
con.close()
if mode == "crash":
    open(marker, "w").write("committed")
    os.kill(os.getpid(), 9)
print("recovered")
'''

class CrashRecovery(unittest.TestCase):
    def test_sigkill_then_replay_exactly_one_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "ledger.sqlite")
            marker = str(Path(tmp) / "committed")
            crashed = subprocess.run([sys.executable, "-c", WORKER, db, marker, "crash"], capture_output=True, text=True)
            self.assertEqual(crashed.returncode, -signal.SIGKILL)
            self.assertEqual(Path(marker).read_text(), "committed")
            recovered = subprocess.run([sys.executable, "-c", WORKER, db, marker, "recover"], capture_output=True, text=True)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            con = sqlite3.connect(db)
            rows = con.execute("SELECT id, payload FROM outcomes").fetchall()
            con.close()
            self.assertEqual(rows, [("canary-001", "verified")])
            print(json.dumps({"event": "SIGKILL_RECOVERY_VERIFIED", "crash_returncode": crashed.returncode, "replay_returncode": recovered.returncode, "outcomes": len(rows)}))

if __name__ == "__main__":
    unittest.main()
