import json
import logging
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

EMAIL = "24f2002298@ds.study.iitm.ac.in"

app = FastAPI()
START = time.time()

# The clicker: counts every request to every endpoint
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

# The notebook: keeps the last 1000 log entries in memory
LOGS = deque(maxlen=1000)

# Also print each log as JSON to the console (what "structured logs" means)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("app")


@app.middleware("http")
async def observe(request: Request, call_next):
    REQUESTS.inc()                       # press the clicker
    request_id = str(uuid.uuid4())       # ticket number
    response = await call_next(request)  # let the real endpoint run

    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
    }
    LOGS.append(entry)                   # write in the notebook
    logger.info(json.dumps(entry))
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = 1):
    n = max(0, min(n, 1_000_000))        # keep it safe
    total = 0
    for i in range(n):                   # "K units of work"
        total += i
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.time() - START)}


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    items = list(LOGS)
    return items[-limit:] if limit > 0 else []