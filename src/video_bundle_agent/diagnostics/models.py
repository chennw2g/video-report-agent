from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error"]
Status = Literal["ok", "warning", "error"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DiagnosticRecord(BaseModel):
    code: str
    severity: Severity
    message: str
    stage: str
    created_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticLog(BaseModel):
    schema_version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    records: list[DiagnosticRecord] = Field(default_factory=list)

    @property
    def status(self) -> Status:
        if any(record.severity == "error" for record in self.records):
            return "error"
        if any(record.severity == "warning" for record in self.records):
            return "warning"
        return "ok"

    def add(
        self,
        *,
        code: str,
        severity: Severity,
        message: str,
        stage: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.records.append(
            DiagnosticRecord(
                code=code,
                severity=severity,
                message=message,
                stage=stage,
                details=details or {},
            )
        )

    def summary(self) -> dict[str, int | str]:
        warnings = sum(1 for record in self.records if record.severity == "warning")
        errors = sum(1 for record in self.records if record.severity == "error")
        return {
            "status": self.status,
            "record_count": len(self.records),
            "warning_count": warnings,
            "error_count": errors,
        }


class ToolCheck(BaseModel):
    name: str
    required: bool
    available: bool
    status: Status
    version: str | None = None
    path: str | None = None
    message: str


class DoctorReport(BaseModel):
    schema_version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    status: Status
    tools: list[ToolCheck]
