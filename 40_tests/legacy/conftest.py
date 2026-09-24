"""
conftest.py - pytest 配置与公共 Fixtures
==========================================
公文写作AI系统 E2E 测试公共配置。
pytest 会在运行 06_testing/ 目录下的任意测试时自动加载本文件。

覆盖内容：
  1. 环境变量读取与校验
  2. DifyWorkflowClient session 级别 fixture
  3. 全局测试报告 fixture（session 结束后写入 JSON）
  4. 自定义 pytest markers 注册
  5. 测试日志配置
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import pytest

# 将项目根目录加入 sys.path，方便导入其他模块
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 延迟导入，避免 conftest 加载时触发网络请求
from test_e2e_workflow import DifyWorkflowClient  # noqa: E402

# ─────────────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("e2e_test")

REPORTS_DIR = Path(__file__).parent / "reports"


# ─────────────────────────────────────────────────────
# pytest markers 注册
# ─────────────────────────────────────────────────────
def pytest_configure(config):
    """注册自定义 markers，避免 PytestUnknownMarkWarning。"""
    config.addinivalue_line("markers", "speech: 讲话类文体测试用例")
    config.addinivalue_line("markers", "plan: 计划类文体测试用例")
    config.addinivalue_line("markers", "scheme: 方案类文体测试用例")
    config.addinivalue_line("markers", "report: 报告类文体测试用例")
    config.addinivalue_line("markers", "planning: 规划类文体测试用例")
    config.addinivalue_line("markers", "briefing: 汇报类文体测试用例")
    config.addinivalue_line("markers", "slow: 字数要求较大、耗时较长的测试")
    config.addinivalue_line("markers", "smoke: 冒烟测试，每种文体各取一个代表用例")


# ─────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def dify_api_url() -> str:
    """
    从环境变量 DIFY_API_URL 读取 Dify 服务地址。
    若未设置，跳过整个 session（pytest.skip 在 session fixture 中会跳过所有测试）。

    设置方式：
      Linux/macOS: export DIFY_API_URL=http://your-dify-server/v1
      Windows CMD: set DIFY_API_URL=http://your-dify-server/v1
      Windows PS:  $Env:DIFY_API_URL="http://your-dify-server/v1"
    """
    url = os.getenv("DIFY_API_URL", "").strip()
    if not url:
        pytest.skip(
            "环境变量 DIFY_API_URL 未设置，跳过所有E2E测试。"
            "请设置后重新运行: export DIFY_API_URL=http://your-server/v1"
        )
    logger.info(f"Dify API URL: {url}")
    return url


@pytest.fixture(scope="session")
def dify_api_key() -> str:
    """
    从环境变量 DIFY_API_KEY 读取 API 密钥。
    若未设置，跳过整个 session。

    设置方式：
      export DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    """
    key = os.getenv("DIFY_API_KEY", "").strip()
    if not key:
        pytest.skip(
            "环境变量 DIFY_API_KEY 未设置，跳过所有E2E测试。"
            "请设置后重新运行: export DIFY_API_KEY=app-xxxx"
        )
    return key


@pytest.fixture(scope="session")
def dify_app_id() -> Optional[str]:
    """
    从环境变量 DIFY_APP_ID 读取工作流应用 ID（可选）。
    部分 API 端点需要 App ID，不设置则返回 None。
    """
    return os.getenv("DIFY_APP_ID", "").strip() or None


@pytest.fixture(scope="session")
def workflow_client(
    dify_api_url: str,
    dify_api_key: str,
    dify_app_id: Optional[str],
) -> DifyWorkflowClient:
    """
    Session 级别的 DifyWorkflowClient 实例，所有测试共享。
    在返回前会执行一次健康检查；若服务不可达则跳过所有测试。
    """
    client = DifyWorkflowClient(
        api_url=dify_api_url,
        api_key=dify_api_key,
        app_id=dify_app_id,
    )

    logger.info("正在检查 Dify 服务健康状态...")
    if not client.health_check():
        pytest.skip(
            f"Dify 服务不可达: {dify_api_url}，"
            "请确认服务已启动且网络连通。"
        )

    logger.info("Dify 服务健康检查通过")
    return client


@pytest.fixture(scope="session", autouse=True)
def test_report() -> Generator:
    """
    Session 级别自动使用的测试报告 fixture。
    - yield 前：初始化报告数据结构，记录开始时间
    - yield 后：汇总结果，写入 JSON 报告文件

    报告文件路径：06_testing/reports/e2e_report_<timestamp>.json
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    session_data = {
        "session_start": datetime.now().isoformat(),
        "session_end": None,
        "environment": {
            "dify_api_url": os.getenv("DIFY_API_URL", "NOT_SET"),
            "dify_app_id": os.getenv("DIFY_APP_ID", "NOT_SET"),
            "python_version": sys.version,
        },
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration_seconds": 0.0,
        },
        "test_items": [],
    }

    start_time = time.monotonic()

    yield session_data

    # ── teardown ──────────────────────────────────────
    session_data["session_end"] = datetime.now().isoformat()
    session_data["summary"]["duration_seconds"] = round(
        time.monotonic() - start_time, 2
    )

    report_path = REPORTS_DIR / (
        f"e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    logger.info(f"测试报告已写入: {report_path}")
    logger.info(
        f"测试汇总: "
        f"总计={session_data['summary']['total']} "
        f"通过={session_data['summary']['passed']} "
        f"失败={session_data['summary']['failed']} "
        f"跳过={session_data['summary']['skipped']}"
    )


# ─────────────────────────────────────────────────────
# 钩子：收集每个测试项结果写入 test_report
# ─────────────────────────────────────────────────────

def pytest_runtest_logreport(report):
    """
    pytest 内置钩子：每个测试阶段（setup/call/teardown）结束后触发。
    仅在 call 阶段记录测试结果，避免重复计数。
    """
    if report.when != "call":
        return

    # 这里无法直接访问 fixture，通过 stash 或全局列表记录
    # 实际项目中推荐使用 pytest-json-report 插件替代手动收集
    pass


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    测试会话结束后在终端追加自定义摘要信息。
    """
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    skipped = len(terminalreporter.stats.get("skipped", []))
    total = passed + failed + skipped

    terminalreporter.write_sep("=", "公文写作AI系统 E2E 测试汇总")
    terminalreporter.write_line(f"  文体覆盖: 讲话 / 计划 / 方案 / 报告 / 规划 / 汇报")
    terminalreporter.write_line(f"  测试用例: 总计={total}  通过={passed}  失败={failed}  跳过={skipped}")
    terminalreporter.write_line(f"  报告目录: {REPORTS_DIR}")
    if failed == 0 and total > 0:
        terminalreporter.write_line("  结论: 全部通过 PASS")
    elif failed > 0:
        terminalreporter.write_line(f"  结论: 存在 {failed} 个失败用例，请查看详细报告")
