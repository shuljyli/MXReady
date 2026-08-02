"""MXReady 基本并发扫描负载脚本（本地 fixture + mock Git，不依赖公网）。

配套启动本地 mock 服务（克隆阶段直接复制本地 fixture，不访问公网）：
    python tests/load/serve_mock.py

另开终端运行压测（headless：10 用户 / 每秒 5 个 / 持续 30 秒）：
    locust -f tests/load/locustfile.py --host http://127.0.0.1:8100 ^
        --users 10 --spawn-rate 5 --run-time 30s --headless

或启动 Web 界面（默认 http://localhost:8089）：
    locust -f tests/load/locustfile.py --host http://127.0.0.1:8100

覆盖路径：
    GET  /api/health                存活检查
    GET  /api/rules                 规则目录
    POST /api/scans                 提交扫描（202）
    GET  /api/scans/{id}            轮询任务状态
    GET  /api/scans/{id}/report     读取完成后的报告
"""

from __future__ import annotations

import time

from locust import HttpUser, between, task

# serve_mock.py 会用 MockGitClient 接管克隆阶段，地址只需格式合法
MOCK_REPO_URL = "https://github.com/mxready/mock-fixture"

_POLL_ATTEMPTS = 40
_POLL_INTERVAL_S = 0.2


class HealthUser(HttpUser):
    """存活探针：验证基础服务可用性。"""

    wait_time = between(0.1, 0.5)

    @task
    def health(self) -> None:
        with self.client.get("/api/health", name="health") as response:
            if response.status_code != 200:
                response.failure(f"health 期望 200，实际 {response.status_code}")


class RulesUser(HttpUser):
    """规则目录读取：验证只读接口在高并发下稳定。"""

    wait_time = between(0.5, 1.5)

    @task
    def rules(self) -> None:
        with self.client.get("/api/rules", name="rules") as response:
            if response.status_code != 200:
                response.failure(f"rules 期望 200，实际 {response.status_code}")


class ScanUser(HttpUser):
    """提交扫描并轮询到终态：覆盖 202 / 轮询 / 报告读取的完整链路。"""

    wait_time = between(1, 3)

    @task
    def submit_and_poll(self) -> None:
        with self.client.post(
            "/api/scans",
            name="scan.submit",
            json={"repo_url": MOCK_REPO_URL},
        ) as response:
            if response.status_code == 429:
                # 开启限流或并发上限时属预期防护行为，不计为失败
                return
            if response.status_code != 202:
                response.failure(f"scan.submit 期望 202，实际 {response.status_code}")
                return
        scan_id = response.json().get("id")
        if not scan_id:
            response.failure("scan.submit 响应缺少 id")
            return

        for _ in range(_POLL_ATTEMPTS):
            poll = self.client.get(f"/api/scans/{scan_id}", name="scan.poll")
            if poll.status_code != 200:
                poll.failure(f"scan.poll 期望 200，实际 {poll.status_code}")
                return
            status = poll.json().get("status")
            if status in {"completed", "failed"}:
                self._read_report(scan_id)
                return
            time.sleep(_POLL_INTERVAL_S)

        # 轮询超时未进入终态（mock 服务本地扫描极快，理论上不应发生）
        self.client.get(f"/api/scans/{scan_id}", name="scan.poll.timeout").failure(
            "轮询超时未进入终态"
        )

    def _read_report(self, scan_id: str) -> None:
        with self.client.get(
            f"/api/scans/{scan_id}/report",
            name="scan.report",
        ) as report:
            if report.status_code not in (200, 409):
                report.failure(
                    f"scan.report 期望 200/409，实际 {report.status_code}"
                )
