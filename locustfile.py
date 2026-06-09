"""
Locust Load Test — Cafe Buddy API
====================================
Simulates realistic user behaviour including login, data browsing,
decision engine interaction, audit log viewing, and role management.

Run:
    locust -f locustfile.py --host=https://aicafebuddy.com
    # or local:
    locust -f locustfile.py --host=http://localhost:8000

Web UI:  http://localhost:8089
    Set: Number of users = 1000, Ramp-up = 50 users/sec, Host = your URL

CLI (headless):
    locust -f locustfile.py --host=https://aicafebuddy.com \\
           --users 1000 --spawn-rate 50 --run-time 120s --headless

Target metrics:
    - Requests/s  : ≥ 500
    - P95 latency : < 500 ms
    - Error rate  : < 1 %
"""
import random
from locust import HttpUser, task, between, events

# ─── Credential pool ─────────────────────────────────────────────────────────
_VALID_CREDS = [
    ("admin", "cafe123"),
    ("owner", "buddy@2024"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Base user — handles login / logout lifecycle
# ═══════════════════════════════════════════════════════════════════════════════
class CafeBuddyBase(HttpUser):
    abstract = True
    wait_time = between(1, 3)   # think time between tasks

    def on_start(self):
        """Login once on session start."""
        username, password = random.choice(_VALID_CREDS)
        with self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            catch_response=True,
            name="POST /api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self._username = data.get("username", username)
                self._role     = data.get("role", "Admin")
                self._token    = data.get("token", "")
                resp.success()
            else:
                self._username = username
                self._role     = "Admin"
                self._token    = ""
                resp.failure(f"Login failed: {resp.status_code}")

    def _headers(self) -> dict:
        return {
            "X-Username": self._username,
            "X-Role":     self._role,
        }

    def on_stop(self):
        """Logout on session end."""
        self.client.post(
            "/api/auth/logout",
            headers=self._headers(),
            name="POST /api/auth/logout",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Viewer — read-only tasks (80% of users)
# ═══════════════════════════════════════════════════════════════════════════════
class ViewerUser(CafeBuddyBase):
    weight = 80   # 80% of total users
    wait_time = between(2, 5)

    @task(5)
    def view_dashboard(self):
        self.client.get("/api/dashboard/overview",
                        headers=self._headers(), name="GET /api/dashboard/overview")

    @task(4)
    def view_layer1_summary(self):
        self.client.get("/api/layer1/summary",
                        headers=self._headers(), name="GET /api/layer1/summary")

    @task(3)
    def view_decisions(self):
        self.client.get("/api/layer4/decisions",
                        headers=self._headers(), name="GET /api/layer4/decisions")

    @task(3)
    def view_forecast(self):
        self.client.get("/api/layer3/forecast",
                        headers=self._headers(), name="GET /api/layer3/forecast")

    @task(2)
    def view_processed_data(self):
        self.client.get("/api/layer2/processed-data",
                        headers=self._headers(), name="GET /api/layer2/processed-data")

    @task(2)
    def view_pipeline_status(self):
        self.client.get("/api/layer2/pipeline-status",
                        headers=self._headers(), name="GET /api/layer2/pipeline-status")

    @task(2)
    def view_autonomous_actions(self):
        self.client.get("/api/layer5/autonomous-actions",
                        headers=self._headers(), name="GET /api/layer5/autonomous-actions")

    @task(1)
    def view_peer_cities(self):
        self.client.get("/api/peers/cities",
                        headers=self._headers(), name="GET /api/peers/cities")

    @task(1)
    def view_upload_status(self):
        self.client.get("/api/upload/status",
                        headers=self._headers(), name="GET /api/upload/status")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="GET /health")


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — includes role/audit management tasks (15% of users)
# ═══════════════════════════════════════════════════════════════════════════════
class AdminUser(CafeBuddyBase):
    weight = 15
    wait_time = between(1, 4)
    _role_counter = 0

    @task(4)
    def view_audit_logs(self):
        self.client.get("/api/audit/logs?limit=25",
                        headers=self._headers(), name="GET /api/audit/logs")

    @task(3)
    def view_audit_stats(self):
        self.client.get("/api/audit/stats",
                        headers=self._headers(), name="GET /api/audit/stats")

    @task(3)
    def view_roles(self):
        self.client.get("/api/roles",
                        headers=self._headers(), name="GET /api/roles")

    @task(3)
    def view_users(self):
        self.client.get("/api/users",
                        headers=self._headers(), name="GET /api/users")

    @task(2)
    def view_dashboard(self):
        self.client.get("/api/dashboard/overview",
                        headers=self._headers(), name="GET /api/dashboard/overview (admin)")

    @task(1)
    def view_audit_modules(self):
        self.client.get("/api/audit/modules",
                        headers=self._headers(), name="GET /api/audit/modules")

    @task(1)
    def view_decisions(self):
        self.client.get("/api/layer4/decisions",
                        headers=self._headers(), name="GET /api/layer4/decisions (admin)")


# ═══════════════════════════════════════════════════════════════════════════════
# ChatBot — frequent chat queries (5% of users)
# ═══════════════════════════════════════════════════════════════════════════════
SAMPLE_QUERIES = [
    "What are my top selling items?",
    "Show me today's revenue",
    "Which platform generates the most orders?",
    "What should I promote this weekend?",
    "Analyse my food cost",
]

class ChatUser(CafeBuddyBase):
    weight = 5
    wait_time = between(3, 8)

    @task(3)
    def send_chat(self):
        q = random.choice(SAMPLE_QUERIES)
        self.client.post(
            "/api/chat",
            json={"message": q},
            headers=self._headers(),
            name="POST /api/chat",
        )

    @task(1)
    def view_dashboard(self):
        self.client.get("/api/dashboard/overview",
                        headers=self._headers(), name="GET /api/dashboard/overview (chat)")


# ═══════════════════════════════════════════════════════════════════════════════
# Event hooks — print summary at end
# ═══════════════════════════════════════════════════════════════════════════════
@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    stats = environment.runner.stats
    total = stats.total
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Requests total : {total.num_requests:,}")
    print(f"Failures       : {total.num_failures:,} ({total.fail_ratio*100:.2f}%)")
    print(f"Avg resp time  : {total.avg_response_time:.1f} ms")
    print(f"P95 resp time  : {total.get_response_time_percentile(0.95):.1f} ms")
    print(f"P99 resp time  : {total.get_response_time_percentile(0.99):.1f} ms")
    print(f"Requests/s     : {total.current_rps:.1f}")
    print("=" * 60)

    # Fail the test if targets not met
    if total.fail_ratio > 0.01:
        print(f"❌ Error rate {total.fail_ratio*100:.2f}% > 1% — FAIL")
        environment.process_exit_code = 1
    if total.get_response_time_percentile(0.95) > 500:
        print(f"❌ P95 {total.get_response_time_percentile(0.95):.1f}ms > 500ms — FAIL")
        environment.process_exit_code = 1
    if environment.process_exit_code == 0:
        print("✅ All performance targets met!")
