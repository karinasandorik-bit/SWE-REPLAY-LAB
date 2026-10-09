"""PostgreSQL crash/recovery integration test, requires OWL_TEST_DATABASE_URL.
Writes only rows with generated identifiers to owl_ablation_004.outcomes.
"""
import os
import signal
import subprocess
import sys
import uuid
import psycopg

DSN = os.environ["OWL_TEST_DATABASE_URL"]
CHILD = """
import os,sys,psycopg
dsn,key,phase=sys.argv[1:]
with psycopg.connect(dsn) as conn:
 with conn.cursor() as cur:
  cur.execute("INSERT INTO owl_ablation_004.outcomes(decision_id,payload) VALUES (%s,'verified') ON CONFLICT DO NOTHING",(key,))
  if phase=="before":
   os.kill(os.getpid(),9)
  conn.commit()
  if phase=="after":
   os.kill(os.getpid(),9)
"""
RECOVER = """
import sys,psycopg
with psycopg.connect(sys.argv[1]) as conn:
 with conn.cursor() as cur:
  cur.execute("INSERT INTO owl_ablation_004.outcomes(decision_id,payload) VALUES (%s,'verified') ON CONFLICT DO NOTHING",(sys.argv[2],))
"""

def inspect(key):
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*), min(payload) FROM owl_ablation_004.outcomes WHERE decision_id=%s", (key,))
            return cur.fetchone()

for phase in ("before", "after"):
    key = "owl-recovery-" + uuid.uuid4().hex
    crash = subprocess.run([sys.executable, "-c", CHILD, DSN, key, phase], timeout=30)
    assert crash.returncode == -signal.SIGKILL, crash.returncode
    assert inspect(key)[0] == (0 if phase == "before" else 1)
    workers = [subprocess.Popen([sys.executable, "-c", RECOVER, DSN, key]) for _ in range(2)]
    assert [p.wait(timeout=30) for p in workers] == [0, 0]
    assert inspect(key) == (1, "verified")
    print("PASS", phase, "SIGKILL", crash.returncode, "outcomes=1")
