import json
import logging
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# ---- CHANGE THIS to the email from your assignment ----
EMAIL = "23f2005623@ds.study.iitm.ac.in"

START_TIME = time.monotonic()

# Counter shows up in /metrics as `http_requests_total`
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

# Keep the last 1000 log entries in memory so /logs/tail can return them
LOG_BUFFER = deque(maxlen=1000)

# Also print each log as one JSON line (what real servers do)
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = str(uuid.uuid4())
    REQUESTS.inc()  # counts EVERY request, any endpoint
    start = time.monotonic()
    response = await call_next(request)
    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": round((time.monotonic() - start) * 1000, 2),
    }
    LOG_BUFFER.append(entry)
    logger.info(json.dumps(entry))
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = 1):
    n = max(0, min(n, 1_000_000))  # keep it safe
    total = 0
    for i in range(n):  # "K units of work"
        total += i
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.monotonic() - START_TIME)}


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    limit = max(0, limit)
    return list(LOG_BUFFER)[-limit:] if limit else []
