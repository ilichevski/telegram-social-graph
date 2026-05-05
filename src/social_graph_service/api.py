from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .pipeline import run_analysis


app = FastAPI(title="Social Graph Service", version="0.1.0")


class AnalyzeRequest(BaseModel):
    export_path: str
    output_path: str
    self_name: Optional[str] = None
    as_of_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cadence_days: int = 7
    window_days: int = 90
    short_window_days: int = 30
    with_llm: bool = False
    with_voice_asr: bool = False


@app.get("/healthz")
def healthcheck() -> dict:
    return {"ok": True}


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    return run_analysis(
        Path(request.export_path),
        Path(request.output_path),
        self_name=request.self_name,
        as_of_date=request.as_of_date,
        start_date=request.start_date,
        end_date=request.end_date,
        cadence_days=request.cadence_days,
        window_days=request.window_days,
        short_window_days=request.short_window_days,
        with_llm=request.with_llm,
        with_voice_asr=request.with_voice_asr,
    )
