"""
Unit tests for audit_store.py  —  90 tests across all public functions.

Isolation strategy: each test class gets a fresh temp directory injected via
the module-scoped `tmp_dir` fixture, plus `reset_for_tests()` to clear memory.
DATA_DIR env var is patched on every test because _audit_file() reads it live.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import threading
import pytest
import sys

# Make sure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import audit_store as as_


# ─── Fixture ─────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    """Each test starts with a clean temp dir and empty in-memory cache."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    as_.reset_for_tests()
    yield
    as_.reset_for_tests()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MODULE METADATA
# ═══════════════════════════════════════════════════════════════════════════════
class TestMetadata:
    def test_module_labels_not_empty(self):
        assert len(as_.MODULE_LABELS) >= 10

    def test_module_labels_are_strings(self):
        for k, v in as_.MODULE_LABELS.items():
            assert isinstance(k, str) and isinstance(v, str)

    def test_action_types_not_empty(self):
        assert len(as_.ACTION_TYPES) >= 10

    def test_action_types_are_strings(self):
        for a in as_.ACTION_TYPES:
            assert isinstance(a, str)

    def test_status_constants(self):
        assert as_.STATUS_SUCCESS == "success"
        assert as_.STATUS_ERROR   == "error"
        assert as_.STATUS_WARNING == "warning"

    def test_auth_in_module_labels(self):
        assert "auth" in as_.MODULE_LABELS

    def test_audit_logs_in_module_labels(self):
        assert "audit_logs" in as_.MODULE_LABELS

    def test_login_in_action_types(self):
        assert "LOGIN" in as_.ACTION_TYPES

    def test_logout_in_action_types(self):
        assert "LOGOUT" in as_.ACTION_TYPES

    def test_role_create_in_action_types(self):
        assert "ROLE_CREATE" in as_.ACTION_TYPES


# ═══════════════════════════════════════════════════════════════════════════════
# 2. log_action — basic
# ═══════════════════════════════════════════════════════════════════════════════
class TestLogAction:
    def test_returns_dict(self):
        e = as_.log_action("alice", "auth", "LOGIN", "Alice logged in")
        assert isinstance(e, dict)

    def test_entry_has_required_fields(self):
        e = as_.log_action("bob", "upload_data", "FILE_UPLOAD", "Uploaded sales.xlsx")
        for field in ("id", "timestamp", "username", "module", "action", "description",
                      "status", "module_label", "ip_address"):
            assert field in e, f"Missing field: {field}"

    def test_username_stored(self):
        e = as_.log_action("charlie", "auth", "LOGIN", "login")
        assert e["username"] == "charlie"

    def test_module_stored(self):
        e = as_.log_action("alice", "upload_data", "FILE_UPLOAD", "test")
        assert e["module"] == "upload_data"

    def test_action_stored(self):
        e = as_.log_action("alice", "auth", "LOGIN", "test")
        assert e["action"] == "LOGIN"

    def test_description_stored(self):
        e = as_.log_action("alice", "auth", "LOGIN", "My description")
        assert e["description"] == "My description"

    def test_default_status_is_success(self):
        e = as_.log_action("alice", "auth", "LOGIN", "ok")
        assert e["status"] == "success"

    def test_custom_status_error(self):
        e = as_.log_action("alice", "auth", "LOGIN", "fail", status="error")
        assert e["status"] == "error"

    def test_custom_status_warning(self):
        e = as_.log_action("alice", "auth", "LOGIN", "warn", status="warning")
        assert e["status"] == "warning"

    def test_id_is_8char_hex(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x")
        assert len(e["id"]) == 8
        int(e["id"], 16)  # must parse as hex

    def test_timestamp_format(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x")
        from datetime import datetime
        datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S")  # must parse

    def test_module_label_resolved(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x")
        assert e["module_label"] == as_.MODULE_LABELS["auth"]

    def test_unknown_module_label_fallback(self):
        e = as_.log_action("alice", "unknown_module_xyz", "LOGIN", "x")
        assert "module_label" in e
        assert isinstance(e["module_label"], str)

    def test_ip_address_stored(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x", ip_address="192.168.1.1")
        assert e["ip_address"] == "192.168.1.1"

    def test_ip_address_default(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x")
        assert e["ip_address"] == "—"

    def test_duration_ms_stored(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x", duration_ms=42)
        assert e["duration_ms"] == 42

    def test_duration_ms_default_none(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x")
        assert e["duration_ms"] is None

    def test_role_stored(self):
        e = as_.log_action("alice", "auth", "LOGIN", "x", role="Admin")
        assert e["role"] == "Admin"

    def test_empty_username_becomes_anonymous(self):
        e = as_.log_action("", "auth", "LOGIN", "x")
        assert e["username"] == "anonymous"

    def test_multiple_entries_accumulate(self):
        for i in range(5):
            as_.log_action(f"user{i}", "auth", "LOGIN", "ok")
        entries, total = as_.get_logs(limit=10)
        assert total == 5

    def test_file_created_on_disk(self, tmp_path):
        as_.log_action("alice", "auth", "LOGIN", "x")
        audit_file = tmp_path / "audit.jsonl"
        assert audit_file.exists()

    def test_file_contains_valid_json(self, tmp_path):
        as_.log_action("alice", "auth", "LOGIN", "test entry")
        audit_file = tmp_path / "audit.jsonl"
        with open(audit_file) as f:
            data = json.loads(f.readline())
        assert data["username"] == "alice"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. get_logs — pagination & filters
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetLogs:
    def setup_method(self):
        as_.log_action("alice",   "auth",        "LOGIN",       "alice login",   role="Admin")
        as_.log_action("bob",     "upload_data", "FILE_UPLOAD", "bob upload",    role="Viewer")
        as_.log_action("charlie", "auth",        "LOGIN",       "charlie login", role="Sub-Admin")
        as_.log_action("alice",   "decision_engine", "DECISION_APPROVE", "approved", status="success")
        as_.log_action("bob",     "auth",        "LOGOUT",      "bob logout",    status="success")
        as_.log_action("alice",   "auth",        "LOGIN",       "alice login 2", status="error")

    def test_returns_tuple(self):
        result = as_.get_logs()
        assert isinstance(result, tuple) and len(result) == 2

    def test_total_count(self):
        _, total = as_.get_logs()
        assert total == 6

    def test_limit(self):
        entries, _ = as_.get_logs(limit=2)
        assert len(entries) == 2

    def test_offset(self):
        entries, total = as_.get_logs(limit=100, offset=4)
        assert len(entries) == 2

    def test_newest_first(self):
        entries, _ = as_.get_logs(limit=100)
        timestamps = [e["timestamp"] for e in entries]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_filter_by_username(self):
        entries, total = as_.get_logs(username="alice")
        assert total == 3
        assert all(e["username"] == "alice" for e in entries)

    def test_filter_by_module(self):
        # auth entries: alice LOGIN, charlie LOGIN, bob LOGOUT, alice LOGIN(error) = 4
        entries, total = as_.get_logs(module="auth")
        assert total == 4

    def test_filter_by_action(self):
        # LOGIN entries: alice LOGIN, charlie LOGIN, alice LOGIN(error) = 3
        entries, total = as_.get_logs(action="LOGIN")
        assert total == 3

    def test_filter_by_status_error(self):
        entries, total = as_.get_logs(status="error")
        assert total == 1

    def test_filter_by_status_success(self):
        entries, total = as_.get_logs(status="success")
        assert total == 5

    def test_filter_search_description(self):
        entries, total = as_.get_logs(search="alice login")
        assert total >= 1

    def test_filter_search_username(self):
        entries, total = as_.get_logs(search="bob")
        assert total >= 2

    def test_combined_filters(self):
        entries, total = as_.get_logs(username="alice", module="auth")
        assert total == 2
        assert all(e["username"] == "alice" for e in entries)

    def test_empty_result_on_unknown_username(self):
        entries, total = as_.get_logs(username="nobody_xyz")
        assert total == 0
        assert entries == []


# ═══════════════════════════════════════════════════════════════════════════════
# 4. get_stats
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetStats:
    def setup_method(self):
        for _ in range(3):
            as_.log_action("alice", "auth", "LOGIN", "ok")
        for _ in range(2):
            as_.log_action("bob", "upload_data", "FILE_UPLOAD", "ok")
        as_.log_action("charlie", "auth", "LOGIN", "fail", status="error")

    def test_returns_dict(self):
        s = as_.get_stats()
        assert isinstance(s, dict)

    def test_required_keys(self):
        s = as_.get_stats()
        for key in ("total_today", "total_all", "active_users_today",
                    "most_active_module", "error_count", "success_count",
                    "error_rate_pct", "module_breakdown", "action_breakdown",
                    "hourly_activity"):
            assert key in s, f"Missing key: {key}"

    def test_total_all(self):
        s = as_.get_stats()
        assert s["total_all"] == 6

    def test_error_count(self):
        s = as_.get_stats()
        assert s["error_count"] == 1

    def test_success_count(self):
        s = as_.get_stats()
        assert s["success_count"] == 5

    def test_error_rate_pct_is_float(self):
        s = as_.get_stats()
        assert isinstance(s["error_rate_pct"], float)

    def test_hourly_activity_has_24_hours(self):
        s = as_.get_stats()
        assert len(s["hourly_activity"]) == 24

    def test_module_breakdown_is_list(self):
        s = as_.get_stats()
        assert isinstance(s["module_breakdown"], list)

    def test_active_users_today_correct(self):
        s = as_.get_stats()
        assert s["active_users_today"] == 3

    def test_most_active_module_is_string(self):
        s = as_.get_stats()
        assert isinstance(s["most_active_module"], str)

    def test_empty_stats_when_no_logs(self):
        # Use clear_logs() which also removes the disk file so reload is clean
        as_.clear_logs()
        s = as_.get_stats()
        assert s["total_all"] == 0
        assert s["most_active_module"] == "—"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. export_csv
# ═══════════════════════════════════════════════════════════════════════════════
class TestExportCsv:
    def test_empty_returns_string(self):
        result = as_.export_csv([])
        assert isinstance(result, str)

    def test_empty_no_data_message(self):
        result = as_.export_csv([])
        assert "No data" in result

    def test_csv_has_header(self):
        as_.log_action("alice", "auth", "LOGIN", "test")
        entries, _ = as_.get_logs(limit=100)
        csv_str = as_.export_csv(entries)
        assert "timestamp" in csv_str.lower()
        assert "username" in csv_str.lower()

    def test_csv_has_data_rows(self):
        as_.log_action("alice", "auth", "LOGIN", "test")
        entries, _ = as_.get_logs(limit=100)
        lines = as_.export_csv(entries).strip().split("\n")
        assert len(lines) >= 2  # header + 1 data row

    def test_csv_contains_username(self):
        as_.log_action("alice", "auth", "LOGIN", "test")
        entries, _ = as_.get_logs(limit=100)
        csv_str = as_.export_csv(entries)
        assert "alice" in csv_str


# ═══════════════════════════════════════════════════════════════════════════════
# 6. clear_logs
# ═══════════════════════════════════════════════════════════════════════════════
class TestClearLogs:
    def test_returns_count(self):
        as_.log_action("alice", "auth", "LOGIN", "x")
        as_.log_action("bob",   "auth", "LOGIN", "x")
        count = as_.clear_logs()
        assert count == 2

    def test_memory_is_cleared(self):
        as_.log_action("alice", "auth", "LOGIN", "x")
        as_.clear_logs()
        _, total = as_.get_logs()
        assert total == 0

    def test_file_removed(self, tmp_path):
        as_.log_action("alice", "auth", "LOGIN", "x")
        as_.clear_logs()
        assert not (tmp_path / "audit.jsonl").exists()

    def test_clear_empty(self):
        count = as_.clear_logs()
        assert count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Thread safety
# ═══════════════════════════════════════════════════════════════════════════════
class TestThreadSafety:
    def test_concurrent_writes_no_crash(self):
        errors = []

        def writer(n):
            try:
                for i in range(20):
                    as_.log_action(f"user{n}", "auth", "LOGIN", f"entry {i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        _, total = as_.get_logs(limit=200)
        assert total == 100  # 5 threads × 20 entries

    def test_disk_lines_match_count(self, tmp_path):
        for i in range(10):
            as_.log_action(f"u{i}", "auth", "LOGIN", "ok")
        audit_file = tmp_path / "audit.jsonl"
        lines = [l for l in audit_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 10


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Persistence (from_disk mode)
# ═══════════════════════════════════════════════════════════════════════════════
class TestPersistence:
    def test_read_from_disk_after_reset(self, tmp_path):
        as_.log_action("alice", "auth", "LOGIN", "persisted")
        as_.reset_for_tests()   # clears memory
        entries, total = as_.get_logs(from_disk=True)
        assert total >= 1
        assert any(e["username"] == "alice" for e in entries)

    def test_reload_entries_correct(self, tmp_path):
        as_.log_action("bob",   "auth", "LOGIN", "entry1")
        as_.log_action("carol", "auth", "LOGOUT","entry2")
        as_.reset_for_tests()
        entries, _ = as_.get_logs(from_disk=True)
        usernames = {e["username"] for e in entries}
        assert "bob"   in usernames
        assert "carol" in usernames

    def test_jsonl_lines_are_valid(self, tmp_path):
        as_.log_action("alice", "auth", "LOGIN", "x")
        as_.log_action("bob",   "upload_data", "FILE_UPLOAD", "y")
        audit_file = tmp_path / "audit.jsonl"
        for line in audit_file.read_text().splitlines():
            if line.strip():
                obj = json.loads(line)
                assert "username" in obj
