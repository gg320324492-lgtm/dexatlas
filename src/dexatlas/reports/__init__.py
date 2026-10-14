"""Report generation."""

from __future__ import annotations

from dexatlas.reports.json_report import build_json_report
from dexatlas.reports.markdown import render_markdown

__all__ = ["build_json_report", "render_markdown"]
