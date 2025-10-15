# backend/app.py
import os, uuid, datetime, json, hashlib
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai  # or your LLM SDK

load_dotenv(".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATA_DIR = os.getenv("DATA_DIR", "./data")
REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

openai.api_key = OPENAI_API_KEY

app = FastAPI(title="Code Review Assistant")

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

@app.post("/review")
async def review(files: list[UploadFile] = File(...), language: str = Form(None)):
    saved = []
    file_texts = []
    for f in files:
        content = await f.read()
        fname = f.filename
        path = os.path.join(DATA_DIR, f"{uuid.uuid4().hex}_{fname}")
        with open(path, "wb") as fh:
            fh.write(content)
        saved.append({"filename": fname, "path": path, "sha256": sha256_bytes(content), "size": len(content)})
        try:
            text = content.decode("utf-8")
        except:
            text = ""
        file_texts.append({"filename": fname, "content": text})

    # Build system + user prompt (concise)
    system = ("You are an expert senior software engineer and code reviewer. "
              "Analyze the given files for readability, modularity, correctness, potential bugs, and security issues. "
              "Return JSON with keys: summary (string), findings (list), suggested_changes (list).")
    files_payload = []
    for ft in file_texts:
        content = ft["content"]
        if len(content) > 4000:
            content = content[:4000] + "\n\n/* TRUNCATED */"
        files_payload.append(f"--- {ft['filename']} ---\n{content}")

    user_prompt = "FILES:\n\n" + "\n\n".join(files_payload) + "\n\nProduce JSON: {summary, findings[], suggested_changes[]}."

    # Call OpenAI Chat Completions (example)
    resp = openai.ChatCompletion.create(
        model="gpt-5-thinking-mini",
        messages=[{"role":"system","content":system}, {"role":"user","content":user_prompt}],
        max_tokens=1500,
        temperature=0.0,
    )
    llm_text = resp.choices[0].message["content"]

    # Try to extract JSON
    import re
    try:
        m = re.search(r'\{.*\}', llm_text, flags=re.DOTALL)
        report_json = json.loads(m.group(0))
    except Exception:
        report_json = {"raw": llm_text}

    report = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "language": language or "unknown",
        "files": saved,
        "report": report_json,
        "llm_raw": llm_text
    }
    out_path = os.path.join(REPORTS_DIR, report["id"] + ".json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return JSONResponse({"report_id": report["id"], "summary": report_json.get("summary", "")})
