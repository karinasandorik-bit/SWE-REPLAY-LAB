"""Two concurrent recovery workers after real SIGKILL before/after SQLite COMMIT.
PostgreSQL verification is separate and MUST NOT be claimed by this test.
"""
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER = r'''
import os,sys,sqlite3,time
p,phase,mark=sys.argv[1:]
c=sqlite3.connect(p,timeout=10,isolation_level=None)
c.execute("PRAGMA journal_mode=WAL")
c.execute("CREATE TABLE IF NOT EXISTS outcomes (id TEXT PRIMARY KEY, value TEXT)")
c.execute("BEGIN IMMEDIATE")
c.execute("INSERT OR IGNORE INTO outcomes VALUES ('canary','verified')")
if phase=="before_commit":
 open(mark,"w").write("ready");os.kill(os.getpid(),9)
c.commit()
if phase=="after_commit":
 open(mark,"w").write("ready");os.kill(os.getpid(),9)
if phase=="race":time.sleep(.05)
c.close()
'''

class ConcurrentRecovery(unittest.TestCase):
    def test_two_workers_before_and_after_commit(self):
        for phase, expected_pre in (("before_commit", 0), ("after_commit", 1)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                db, marker = str(Path(td)/"db"), str(Path(td)/"marker")
                killed = subprocess.run([sys.executable, "-c", WORKER, db, phase, marker], capture_output=True)
                self.assertEqual(killed.returncode, -signal.SIGKILL)
                with sqlite3.connect(db) as c:
                    self.assertEqual(c.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0], expected_pre)
                workers = [subprocess.Popen([sys.executable, "-c", WORKER, db, "race", marker]) for _ in range(2)]
                self.assertEqual([w.wait(timeout=15) for w in workers], [0,0])
                with sqlite3.connect(db) as c:
                    self.assertEqual(c.execute("SELECT * FROM outcomes").fetchall(), [("canary", "verified")])

if __name__ == "__main__":
    unittest.main()
