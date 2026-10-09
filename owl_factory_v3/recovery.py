"""Crash-recovery state reducer. Database is authoritative; no external side effects."""
def reconcile(events):
    states={}
    for event in sorted(events,key=lambda e:e["event_id"]):
        key=event["operation_id"]
        state=states.setdefault(key,{"status":"UNKNOWN","sha256":event["artifact_sha256"]})
        if state["sha256"]!=event["artifact_sha256"]:raise ValueError("artifact mismatch")
        typ=event["event_type"]
        if typ in ("STAGED","PROMOTED","VERIFIED","ROLLBACK","RECOVERED","REJECTED"):
            state["status"]=typ
    return {k:{"status":v["status"],"action":("VERIFY_AND_RECONCILE" if v["status"]=="PROMOTED" else "NONE")} for k,v in states.items()}
