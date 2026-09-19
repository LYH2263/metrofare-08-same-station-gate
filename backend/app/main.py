from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app import seed
from app.errors import QuoteError
from app.routers import api

app = FastAPI(title="Metrofare", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(QuoteError)
async def quote_error_handler(_: Request, exc: QuoteError):
    # 结构化错误体：{"error": same_station | unknown_station | ..., "message": ..., ...}
    return JSONResponse(status_code=exc.status_code, content=exc.payload)

@app.on_event("startup")
def _startup():
    seed.init_db()

app.include_router(api)

@app.get("/api/health")
def health():
    return {"ok": True, "project": "metrofare"}
