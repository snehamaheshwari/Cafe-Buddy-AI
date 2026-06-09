"""
Audit Logging Store — Cafe Buddy RBAC

Appends every user action to  data/audit.jsonl  (JSON Lines, one object per
line).  A small in-memory deque caches the most recent _MAX_MEM entries for
fast reads; full history is read from disk for export / deep filters.

Thread-safety: _lock serialises all file writes so concurrent FastAPI
handlers never interleave partial lines.

Performance targets (single-node):
  - log_action()   <  2 ms   (append-only write)
  - get_logs(100)  <  5 ms   (in-memory)
  - get_logs(10k)  < 50 ms   (disk scan)
"""
from __future__ import annotations

import csv
import io
import json
import os
import threading
import uuid
from collections import deque
from datetime import datetime
from typing import Optional

# ─── Paths (resolved dynamically so tests can override DATA_DIR) ──────────────
def _audit_file() -> str:
    data_dir = os.environ.get(
        "DATA_DIR",
        os.path.join(os.path.dirname(__file__), "data"),
    )
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "audit.jsonl")


_MAX_ENTRIES = 50_000   # max lines kept on disk (oldest trimmed)
_MAX_MEM     =  5_000   # recent entries kept in memory
_lock        = threading.Lock()
_mem: deque  = deque(maxlen=_MAX_MEM)
_mem_loaded  = False

# ─── Metadata ─────────────────────────────────────────────────────────────────
MODULE_LABELS: dict[str, str] = {
    "auth":            "Authentication",
    "upload_data":     "Upload My Data",
    "reports":         "Reports & Insights",
    "analytics":       "Smart Analytics",
    "decision_engine": "What To Do Next",
    "auto_pilot":      "Auto-Pilot Mode",
    "chatbot":         "Ask Cafe Buddy",
    "market_radar":    "Market Radar",
    "whatsapp_alerts": "WhatsApp Alerts",
    "role_management": "Role Management",
    "audit_logs":      "Audit Logs",
    "system":          "System",
}

ACTION_TYPES: list[str] = [
    "LOGIN", "LOGOUT",
    "FILE_UPLOAD", "FILE_CLEAR",
    "DATA_VIEW", "FORECAST_REQUEST",
    "DECISION_APPROVE", "DECISION_REJECT",
    "ROLE_CREATE", "ROLE_UPDATE", "ROLE_DELETE",
    "USER_CREATE", "USER_UPDATE", "USER_DELETE",
    "PEER_ANALYSIS", "EXPORT",
    "CHAT_QUERY", "AUTOPILOT_ACTION",
    "AUDIT_VIEW", "PERMISSION_DENIED",
]

STATUS_SUCCESS = "success"
STATUS_ERROR   = "error"
STATUS_WARNING = "warning"


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _load_mem() -> None:
    """Populate the in-memory deque from the last _MAX_MEM lines on disk."""
    global _mem_loaded
    path = _audit_file()
    if not os.path.exists(path):
        _mem_loaded = True
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-_MAX_MEM:]:
            line = line.strip()
            if line:
                try:
                    _mem.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    _mem_loaded = True


def _ensure_mem() -> None:
    global _mem_loaded
    if not _mem_loaded:
        with _lock:
            if not _mem_loaded:
                _load_mem()


def _trim_file(path: str) -> None:
    """Keep only the last _MAX_ENTRIES lines in the JSONL file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > _MAX_ENTRIES:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[-_MAX_ENTRIES:])
    except Exception:
        pass


# ─── Public API ───────────────────────────────────────────────────────────────

def log_action(
    username:    str,
    module:      str,
    action:      str,
    description: str,
    *,
    role:        str = "",
    status:      str = STATUS_SUCCESS,
    ip_address:  str = "",
    duration_ms: Optional[int] = None,
) -> dict:
    """
    Append one audit entry to disk and to the in-memory cache.
    Returns the entry dict.  Never raises — audit failure must not crash
    the main request.
    """
    _ensure_mem()
    entry: dict = {
        "id":           uuid.uuid4().hex[:8],
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username":     username or "anonymous",
        "role":         role,
        "module":       module,
        "module_label": MODULE_LABELS.get(module, module.replace("_", " ").title()),
        "action":       action,
        "description":  description,
        "status":       status,
        "ip_address":   ip_address or "—",
        "duration_ms":  duration_ms,
    }
    try:
        path = _audit_file()
        with _lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            _mem.append(entry)
            # Trim disk file occasionally (every 1000 writes)
            if len(_mem) % 1000 == 0:
                _trim_file(path)
    except Exception:
        pass   # audit must never crash the caller
    return entry


def get_logs(
    *,
    limit:       int = 100,
    offset:      int = 0,
    username:    Optional[str] = None,
    module:      Optional[str] = None,
    action:      Optional[str] = None,
    status:      Optional[str] = None,
    date_from:   Optional[str] = None,   # "YYYY-MM-DD"
    date_to:     Optional[str] = None,   # "YYYY-MM-DD"
    search:      Optional[str] = None,   # free-text in description/username
    from_disk:   bool = False,           # read all entries from disk
) -> tuple[list[dict], int]:
    """
    Return (entries, total_matching) filtered and paginated.
    Uses in-memory deque for speed; pass from_disk=True for full history.
    """
    _ensure_mem()

    if from_disk:
        entries = _read_all_from_disk()
    else:
        entries = list(_mem)

    # Newest first
    entries = list(reversed(entries))

    # ── Filters ──
    if username:
        entries = [e for e in entries if e.get("username", "").lower() == username.lower()]
    if module:
        entries = [e for e in entries if e.get("module") == module]
    if action:
        entries = [e for e in entries if e.get("action") == action]
    if status:
        entries = [e for e in entries if e.get("status") == status]
    if date_from:
        entries = [e for e in entries if e.get("timestamp", "") >= date_from]
    if date_to:
        entries = [e for e in entries if e.get("timestamp", "") <= date_to + " 23:59:59"]
    if search:
        q = search.lower()
        entries = [
            e for e in entries
            if q in e.get("description", "").lower()
            or q in e.get("username", "").lower()
            or q in e.get("module_label", "").lower()
        ]

    total = len(entries)
    return entries[offset: offset + limit], total


def _read_all_from_disk() -> list[dict]:
    path = _audit_file()
    if not os.path.exists(path):
        return []
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return entries


def get_stats() -> dict:
    """
    Aggregate stats from recent entries (in-memory, fast).
    Returns: counts by module, action, status, hourly activity.
    """
    _ensure_mem()
    entries = list(_mem)
    today   = datetime.now().strftime("%Y-%m-%d")
    today_e = [e for e in entries if e.get("timestamp", "").startswith(today)]

    # Module breakdown
    mod_counts: dict = {}
    for e in today_e:
        mod = e.get("module_label", "Unknown")
        mod_counts[mod] = mod_counts.get(mod, 0) + 1

    # Action breakdown
    act_counts: dict = {}
    for e in entries:
        act = e.get("action", "UNKNOWN")
        act_counts[act] = act_counts.get(act, 0) + 1

    # Status breakdown
    success = sum(1 for e in entries if e.get("status") == "success")
    errors  = sum(1 for e in entries if e.get("status") == "error")

    # Unique active users today
    users_today = len(set(e.get("username") for e in today_e))

    # Hourly breakdown (last 24h)
    hourly: dict = {str(h).zfill(2): 0 for h in range(24)}
    for e in today_e:
        try:
            h = e["timestamp"][11:13]
            hourly[h] = hourly.get(h, 0) + 1
        except Exception:
            pass

    # Most active module today
    most_active = max(mod_counts, key=mod_counts.get) if mod_counts else "—"

    return {
        "total_today":      len(today_e),
        "total_all":        len(entries),
        "active_users_today": users_today,
        "most_active_module": most_active,
        "error_count":      errors,
        "success_count":    success,
        "error_rate_pct":   round(errors / max(len(entries), 1) * 100, 1),
        "module_breakdown": [
            {"module": k, "count": v}
            for k, v in sorted(mod_counts.items(), key=lambda x: -x[1])
        ],
        "action_breakdown": [
            {"action": k, "count": v}
            for k, v in sorted(act_counts.items(), key=lambda x: -x[1])[:10]
        ],
        "hourly_activity": [
            {"hour": h, "count": c} for h, c in sorted(hourly.items())
        ],
    }


def export_csv(entries: list[dict]) -> str:
    """Return a CSV string from a list of audit entries."""
    if not entries:
        return "No data to export"
    fields = ["id", "timestamp", "username", "role", "module_label",
              "action", "description", "status", "ip_address", "duration_ms"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(entries)
    return buf.getvalue()


def clear_logs() -> int:
    """Delete all audit logs (admin-only operation). Returns count deleted."""
    _ensure_mem()
    count = len(_mem)
    _mem.clear()
    path = _audit_file()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return count


def reset_for_tests() -> None:
    """Clear in-memory state (used by tests). Does NOT remove the disk file
    so persistence tests can still read entries written in the same test."""
    global _mem_loaded
    _mem.clear()
    _mem_loaded = False
