from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from diri_agent_toolbox.logging import get_logger

logger = get_logger("diri_agent_toolbox.monitoring")


class MetricsCollector:
    def __init__(self, log_dir: str = "./logs/metrics"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.log_dir / "metrics.jsonl"
        self.alerts_file = self.log_dir / "alerts.jsonl"
        self.current: Dict[str, Any] = {
            "total_operations": 0,
            "total_errors": 0,
            "last_check": None,
        }
        self._load()

    def record(self, operation: str, data: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            **data,
        }
        self._write(self.metrics_file, entry)
        self.current["total_operations"] += 1
        logger.info("Metric recorded", operation=operation)

    def record_error(self, operation: str, error: str, **kwargs: Any) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "error": error,
            **kwargs,
        }
        self._write(self.metrics_file, entry)
        self.current["total_errors"] += 1
        logger.error("Error recorded", operation=operation, error=error)

    def alert(self, alert_type: str, severity: str, data: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "data": data,
            "resolved": False,
        }
        self._write(self.alerts_file, entry)
        logger.warning("Alert created", type=alert_type, severity=severity)

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        analytics: Dict[str, Any] = {
            "period_days": days,
            "operations": [],
            "errors": [],
            "operation_counts": {},
        }
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        ts = datetime.fromisoformat(entry["timestamp"])
                        if ts >= cutoff:
                            op = entry.get("operation", "unknown")
                            analytics["operation_counts"][op] = (
                                analytics["operation_counts"].get(op, 0) + 1
                            )
                            if "error" in entry:
                                analytics["errors"].append(entry)
                            else:
                                analytics["operations"].append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        return analytics

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        if self.alerts_file.exists():
            with open(self.alerts_file) as f:
                for line in f:
                    try:
                        alert = json.loads(line.strip())
                        ts = datetime.fromisoformat(alert["timestamp"])
                        if ts >= cutoff:
                            alerts.append(alert)
                    except (json.JSONDecodeError, KeyError):
                        continue
        return alerts[-10:]

    def get_summary(self) -> Dict[str, Any]:
        analytics = self.get_analytics(days=1)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operations_today": sum(analytics["operation_counts"].values()),
            "errors_today": len(analytics["errors"]),
            "recent_alerts": len(self.get_recent_alerts(hours=24)),
        }

    def _write(self, path: Path, entry: Dict[str, Any]) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _load(self) -> None:
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    for line in f:
                        if '"operation"' in line:
                            self.current["total_operations"] += 1
                        if '"error"' in line:
                            self.current["total_errors"] += 1
            except Exception:
                pass
