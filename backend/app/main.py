"""FastAPI app for the KMITL web-automation demo (LLM Lecture 12).

Routes:
  GET  /api/health              -> config sanity (which keys are set)
  POST /api/search-agent        -> SSE stream of the agentic search→fetch→cite loop
  POST /api/browser/render      -> plain-GET vs browser-render comparison
  POST /api/browser/automate    -> scripted login flow with an ACT/OBS trace
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent import run_search_agent
from .browser import BrowserUnavailable, JS_DEMO_URL, automate_login, render_vs_fetch
from .config import get_settings

app = FastAPI(title="KMITL Web Automation Demo")

# Dev: the Svelte dev server (Vite) calls us cross-origin; allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


class AgentIn(BaseModel):
    question: str
    defended: bool = True


class RenderIn(BaseModel):
    url: str = JS_DEMO_URL


class AutomateIn(BaseModel):
    username: str = "student"
    password: str = "kmitl-demo"


@app.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {
        "llm_key_set": bool(s.llm_api_key),
        "tavily_key_set": bool(s.tavily_api_key),
        "model": s.model,
        "llm_base_url": s.llm_base_url,
    }


def _sse(events: Iterator[dict]) -> StreamingResponse:
    def gen() -> Iterator[str]:
        for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/search-agent")
def search_agent(body: AgentIn) -> StreamingResponse:
    settings = get_settings()
    return _sse(run_search_agent(body.question, body.defended, settings))


@app.post("/api/browser/render")
async def browser_render(body: RenderIn) -> dict:
    try:
        return await render_vs_fetch(body.url, get_settings())
    except BrowserUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/browser/automate")
async def browser_automate(body: AutomateIn) -> dict:
    try:
        return await automate_login(body.username, body.password, get_settings())
    except BrowserUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
