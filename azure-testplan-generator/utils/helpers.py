"""Shared helper functions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

import pandas as pd

from models.entities import ReportRecord


def ensure_directories(paths: Sequence[str]) -> None:
    """Create required directories when missing."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def build_iteration_path(base_iteration: str, sprint: int) -> str:
    """Build dynamic iteration path from sprint number."""
    return f"{base_iteration}\\Sprint {sprint}"


def build_test_plan_name(sprint: int) -> str:
    """Build test plan name using expected format."""
    return f"Atendido 2.0_Sprint {sprint}"


def export_csv_report(records: list[ReportRecord], reports_dir: str = "reports") -> Path:
    """Generate report CSV file in reports directory."""
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(reports_dir) / f"suite_creation_report_{timestamp}.csv"

    frame = pd.DataFrame(
        [record.to_dict() for record in records],
        columns=["id", "titulo", "suite_creada", "resultado", "fecha", "mensaje"],
    )
    frame.columns = ["ID", "Título", "Suite creada", "Resultado", "Fecha", "Mensaje"]
    frame.to_csv(report_path, index=False, encoding="utf-8-sig")
    return report_path

