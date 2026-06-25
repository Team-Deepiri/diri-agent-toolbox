import json
from pathlib import Path

from diri_agent_toolbox.monitoring import MetricsCollector


def test_record(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.record("predict", {"latency_ms": 150, "model": "bert"})
    assert mc.current["total_operations"] == 1
    lines = list(tmp_path.joinpath("metrics.jsonl").open())
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["operation"] == "predict"
    assert entry["latency_ms"] == 150


def test_record_error(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.record_error("predict", "timeout", retry=True)
    assert mc.current["total_errors"] == 1
    lines = list(tmp_path.joinpath("metrics.jsonl").open())
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["operation"] == "predict"
    assert entry["error"] == "timeout"


def test_alert(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.alert("high_latency", "critical", {"latency_ms": 5000})
    lines = list(tmp_path.joinpath("alerts.jsonl").open())
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["alert_type"] == "high_latency"
    assert entry["severity"] == "critical"
    assert entry["resolved"] is False


def test_get_analytics(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.record("op1", {})
    mc.record("op2", {})
    mc.record_error("op1", "fail")
    analytics = mc.get_analytics(days=1)
    assert analytics["operation_counts"]["op1"] >= 1
    assert analytics["operation_counts"]["op2"] >= 1
    assert len(analytics["errors"]) >= 1


def test_get_recent_alerts(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.alert("a1", "low", {})
    mc.alert("a2", "high", {})
    alerts = mc.get_recent_alerts(hours=24)
    assert len(alerts) == 2
    assert alerts[0]["alert_type"] == "a1"


def test_get_summary(tmp_path):
    mc = MetricsCollector(log_dir=str(tmp_path))
    mc.record("op1", {})
    mc.record_error("op2", "err")
    mc.alert("test", "low", {})
    summary = mc.get_summary()
    assert summary["operations_today"] >= 1
    assert summary["errors_today"] >= 1
    assert summary["recent_alerts"] >= 1


def test_creates_log_dir():
    mc = MetricsCollector(log_dir="/tmp/_test_monitoring_dir")
    assert Path("/tmp/_test_monitoring_dir").exists()
    mc.record("cleanup", {})
    import shutil

    shutil.rmtree("/tmp/_test_monitoring_dir", ignore_errors=True)
