import os,json,re,urllib.request,hashlib,statistics,math
ROOT="trials/TRAJECTORY-TRANSFER-TRIAL-001"
MODEL=os.getenv("OPENAI_MODEL","gpt-5.6-luna")
KEY=os.environ["OPENAI_API_KEY"]
def call(prompt):
    body=json.dumps({"model":MODEL,"input":prompt,"reasoning":{"effort":"low"},"max_output_tokens":32}).encode()
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=body,headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: data=json.load(r)
    txt=""
    for item in data.get("output",[]):
      for c in item.get("content",[]):
        if c.get("type")=="output_text": txt+=c.get("text","")
    m=re.search(r"(?:P\s*=\s*)?(0(?:\.\d+)?|1(?:\.0+)?)",txt)
    if not m: raise RuntimeError("unparseable:"+txt)
    return max(0,min(1,float(m.group(1)))),txt
with open(ROOT+"/challenge.frozen.json") as f: cfg=json.load(f)
base="You predict a hidden deterministic binary rule over 8-bit strings. Return only P=<probability y=1>, no explanation. "
history=[]
for i,z in enumerate(cfg["train"]):
    context="\n".join(history)
    p,raw=call(base+context+"\nCurrent x="+z["x"])
    history += ["x="+z["x"]+" prediction="+str(p),"observed y="+str(z["y"])]
checkpoint={"protocol":"TRAJECTORY-TRANSFER-TRIAL-001","model":MODEL,"history":history,"train":cfg["train"]}
canon=json.dumps(checkpoint,separators=(",",":"),sort_keys=True)
print("CHECKPOINT_SHA256="+hashlib.sha256(canon.encode()).hexdigest())
print("CHECKPOINT_JSON="+canon)
if os.getenv("EXECUTE_TRIAL")!="1":
    print("STATE=CHECKPOINT_READY_NOT_EVALUATED")
    raise SystemExit(0)
# evaluated branch A: full experienced trajectory
pred=[]
for z in cfg["challenge"]:
    p,_=call(base+"\n".join(history)+"\nCurrent x="+z["x"])
    pred.append((z["id"],p,z["y"]))
loss=[(p-y)**2 for _,p,y in pred]
out={"state":"OUTCOME","branch":"A","n":len(loss),"mean_brier":sum(loss)/len(loss),"predictions":pred,"checkpoint_sha256":hashlib.sha256(canon.encode()).hexdigest()}
print("OUTCOME_JSON="+json.dumps(out,separators=(",",":"),sort_keys=True))
