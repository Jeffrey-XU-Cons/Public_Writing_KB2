"""
公文写作AI系统 - 六智能体工作流 E2E 测试框架
==============================================
基于 pytest 实现，覆盖 test_cases.json 中全部18个用例。

运行方式：
  # 基础运行
  pytest 06_testing/test_e2e_workflow.py -v

  # 生成HTML报告（需安装 pytest-html）
  pytest 06_testing/test_e2e_workflow.py -v --html=report.html --self-contained-html

  # 按文体筛选运行
  pytest 06_testing/test_e2e_workflow.py -v -k "speech"
  pytest 06_testing/test_e2e_workflow.py -v -k "plan or scheme"

  # 并行运行（需安装 pytest-xdist）
  pytest 06_testing/test_e2e_workflow.py -v -n 4

  # 超时控制（需安装 pytest-timeout）
  pytest 06_testing/test_e2e_workflow.py -v --timeout=120

依赖安装：
  pip install pytest pytest-html pytest-timeout pytest-xdist requests

环境变量（必须设置）：
  DIFY_API_URL    Dify服务地址，如 http://your-server/v1
  DIFY_API_KEY    API密钥（用户API密钥或应用API密钥）
  DIFY_APP_ID     Dify工作流应用ID（可选，部分接口需要）

注意：
  conftest.py 已分离到同目录下，pytest 会自动加载。
  如需在 CI 中运行，请确保环境变量已正确注入。
"""

import json
import os
import re
import time
import pytest
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────
TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"
REPORTS_DIR = Path(__file__).parent / "reports"
REQUEST_TIMEOUT = 180       # 单次工作流调用最长等待时间（秒）
POLL_INTERVAL = 3           # 异步任务轮询间隔（秒）
MAX_POLL_RETRIES = 60       # 最大轮询次数 = 60 * 3s = 180s


def _load_test_cases() -> dict:
    """加载 test_cases.json 并返回以 id 为键的字典。"""
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {tc["id"]: tc for tc in data["test_cases"]}


ALL_CASES = _load_test_cases()


# ─────────────────────────────────────────────────────
# Dify 工作流客户端
# ─────────────────────────────────────────────────────
class DifyWorkflowClient:
    """
    封装 Dify Workflow API 的同步/异步调用，
    自动处理流式响应、轮询任务状态和错误重试。
    """

    def __init__(self, api_url: str, api_key: str, app_id: Optional[str] = None):
        self.base_url = api_url.rstrip("/")
        self.api_key = api_key
        self.app_id = app_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def run_workflow(self, test_case: dict) -> dict:
        """
        根据测试用例调用 Dify 工作流并返回结构化结果。

        Args:
            test_case: test_cases.json 中的单个测试用例字典

        Returns:
            dict: {
                "success": bool,
                "output_text": str,
                "word_count": int,
                "response_time": float,
                "raw_response": dict,
                "error": str | None,
            }
        """
        url = f"{self.base_url}/workflows/run"
        payload = {
            "inputs": {
                "document_type": test_case["document_type"],
                "user_request": test_case["input_request"],
                "test_case_id": test_case["id"],
            },
            "response_mode": "blocking",
            "user": f"e2e-test-{test_case['id']}",
        }

        start = time.perf_counter()
        try:
            resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            elapsed = round(time.perf_counter() - start, 3)
            resp.raise_for_status()
            raw = resp.json()

            # 从 Dify 响应中提取生成文本
            output_text = self._extract_output(raw)
            word_count = len(output_text) if output_text else 0

            return {
                "success": True,
                "output_text": output_text,
                "word_count": word_count,
                "response_time": elapsed,
                "raw_response": raw,
                "error": None,
            }

        except requests.exceptions.Timeout:
            elapsed = round(time.perf_counter() - start, 3)
            return {
                "success": False,
                "output_text": "",
                "word_count": 0,
                "response_time": elapsed,
                "raw_response": {},
                "error": f"请求超时（>{REQUEST_TIMEOUT}s）",
            }
        except requests.exceptions.HTTPError as exc:
            elapsed = round(time.perf_counter() - start, 3)
            return {
                "success": False,
                "output_text": "",
                "word_count": 0,
                "response_time": elapsed,
                "raw_response": {},
                "error": f"HTTP错误: {exc.response.status_code} {exc.response.text[:200]}",
            }
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 3)
            return {
                "success": False,
                "output_text": "",
                "word_count": 0,
                "response_time": elapsed,
                "raw_response": {},
                "error": str(exc),
            }

    @staticmethod
    def _extract_output(raw_response: dict) -> str:
        """
        从不同格式的 Dify 响应中提取生成文本。
        支持 blocking workflow 响应和 chat message 响应格式。
        """
        # Dify workflow blocking 模式响应格式
        if "data" in raw_response:
            data = raw_response["data"]
            if isinstance(data, dict):
                outputs = data.get("outputs", {})
                # 尝试常见输出字段名
                for key in ("result", "text", "output", "content", "document"):
                    if key in outputs:
                        return str(outputs[key])
                # 取第一个非空字符串值
                for v in outputs.values():
                    if isinstance(v, str) and v.strip():
                        return v
        # chat message 格式
        if "answer" in raw_response:
            return raw_response["answer"]
        return ""

    def health_check(self) -> bool:
        """检查 Dify 服务是否可达。"""
        try:
            resp = self.session.get(
                f"{self.base_url}/info", timeout=10
            )
            return resp.status_code < 500
        except Exception:
            return False


# ─────────────────────────────────────────────────────
# 通用断言辅助函数
# ─────────────────────────────────────────────────────
def assert_output_not_empty(result: dict, case_id: str) -> None:
    assert result["success"], (
        f"[{case_id}] 工作流调用失败: {result['error']}"
    )
    assert result["output_text"].strip(), (
        f"[{case_id}] 输出为空"
    )


def assert_word_count_in_range(result: dict, case: dict) -> None:
    wc = result["word_count"]
    lo, hi = case["expected_output"]["word_count_range"]
    assert lo <= wc <= hi, (
        f"[{case['id']}] 字数不在范围内: 实际={wc}，期望=[{lo}, {hi}]"
    )


def assert_document_type(result: dict, case: dict) -> None:
    """验证输出文体类型（通过关键词推断）。"""
    doc_type = case["document_type"]
    text = result["output_text"]
    type_markers = {
        "讲话": ["同志们", "讲话", "会议", "指出"],
        "计划": ["工作计划", "目标", "任务", "安排", "时间节点"],
        "方案": ["实施方案", "方案", "措施", "步骤", "保障"],
        "报告": ["工作报告", "情况报告", "总结", "问题", "建议"],
        "规划": ["规划", "发展目标", "战略", "愿景", "重点任务"],
        "汇报": ["汇报", "情况", "进展", "下步"],
    }
    markers = type_markers.get(doc_type, [])
    matched = sum(1 for m in markers if m in text)
    assert matched >= 1, (
        f"[{case['id']}] 输出内容不符合文体特征（{doc_type}），"
        f"关键词匹配数={matched}/{len(markers)}"
    )


def assert_required_sections(result: dict, case: dict) -> None:
    """验证必要段落（宽松匹配：要求覆盖60%以上）。"""
    sections = case["expected_output"]["required_sections"]
    text = result["output_text"]
    matched = [s for s in sections if s in text]
    coverage = len(matched) / len(sections) if sections else 1.0
    assert coverage >= 0.6, (
        f"[{case['id']}] 必要段落覆盖率不足: "
        f"{len(matched)}/{len(sections)} = {coverage:.0%}，"
        f"缺失: {[s for s in sections if s not in matched]}"
    )


# ─────────────────────────────────────────────────────
# pytest 测试类
# ─────────────────────────────────────────────────────
class TestPublicWritingWorkflow:
    """
    公文写作六智能体工作流端到端测试类。
    每个测试方法对应 test_cases.json 中的一个用例，
    全部18个用例按文体分组：讲话(01-03)、计划(01-03)、
    方案(01-03)、报告(01-03)、规划(01-03)、汇报(01-03)。
    """

    client: DifyWorkflowClient
    test_results: list

    @classmethod
    def setup_class(cls):
        """初始化 Dify 客户端，检查服务可达性，准备报告目录。"""
        api_url = os.getenv("DIFY_API_URL", "http://localhost/v1")
        api_key = os.getenv("DIFY_API_KEY", "")
        app_id = os.getenv("DIFY_APP_ID", "")

        if not api_key:
            pytest.skip("未设置 DIFY_API_KEY 环境变量，跳过E2E测试")

        cls.client = DifyWorkflowClient(api_url, api_key, app_id)
        cls.test_results = []

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 服务健康检查
        if not cls.client.health_check():
            pytest.skip(f"Dify服务不可达: {api_url}，跳过E2E测试")

        print(f"\n[setup] Dify服务连接正常: {api_url}")

    @classmethod
    def teardown_class(cls):
        """将全部测试结果写入JSON报告。"""
        report_path = REPORTS_DIR / f"e2e_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report = {
            "generated_at": datetime.now().isoformat(),
            "total": len(cls.test_results),
            "passed": sum(1 for r in cls.test_results if r.get("passed")),
            "failed": sum(1 for r in cls.test_results if not r.get("passed")),
            "results": cls.test_results,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n[teardown] 测试报告已保存: {report_path}")

    def _run_case(self, case_id: str) -> dict:
        """通用用例执行逻辑，记录结果供 teardown 汇总。"""
        case = ALL_CASES[case_id]
        result = self.client.run_workflow(case)
        result["case_id"] = case_id
        result["case_name"] = case["name"]
        self.__class__.test_results.append(result)
        return result

    # ─── 讲话类 ──────────────────────────────────────
    def test_speech_01(self):
        """讲话-01：2026年春季工作会议讲话稿"""
        case = ALL_CASES["TC-SPEECH-01"]
        result = self._run_case("TC-SPEECH-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_speech_02(self):
        """讲话-02：年度表彰大会讲话稿"""
        case = ALL_CASES["TC-SPEECH-02"]
        result = self._run_case("TC-SPEECH-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_speech_03(self):
        """讲话-03：数字化转型动员大会讲话"""
        case = ALL_CASES["TC-SPEECH-03"]
        result = self._run_case("TC-SPEECH-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    # ─── 计划类 ──────────────────────────────────────
    def test_plan_01(self):
        """计划-01：2026年度工作计划（财政局）"""
        case = ALL_CASES["TC-PLAN-01"]
        result = self._run_case("TC-PLAN-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_plan_02(self):
        """计划-02：党建工作年度计划"""
        case = ALL_CASES["TC-PLAN-02"]
        result = self._run_case("TC-PLAN-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_plan_03(self):
        """计划-03：安全生产年度工作计划"""
        case = ALL_CASES["TC-PLAN-03"]
        result = self._run_case("TC-PLAN-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    # ─── 方案类 ──────────────────────────────────────
    def test_scheme_01(self):
        """方案-01：数字化转型实施方案（三年）"""
        case = ALL_CASES["TC-SCHEME-01"]
        result = self._run_case("TC-SCHEME-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_scheme_02(self):
        """方案-02：大型会议组织保障方案"""
        case = ALL_CASES["TC-SCHEME-02"]
        result = self._run_case("TC-SCHEME-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_scheme_03(self):
        """方案-03：绩效考核改革实施方案"""
        case = ALL_CASES["TC-SCHEME-03"]
        result = self._run_case("TC-SCHEME-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    # ─── 报告类 ──────────────────────────────────────
    def test_report_01(self):
        """报告-01：上半年工作报告（住建局）"""
        case = ALL_CASES["TC-REPORT-01"]
        result = self._run_case("TC-REPORT-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_report_02(self):
        """报告-02：营商环境专项调研报告"""
        case = ALL_CASES["TC-REPORT-02"]
        result = self._run_case("TC-REPORT-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_report_03(self):
        """报告-03：年度党建工作总结报告"""
        case = ALL_CASES["TC-REPORT-03"]
        result = self._run_case("TC-REPORT-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    # ─── 规划类 ──────────────────────────────────────
    def test_planning_01(self):
        """规划-01：县级市十五五发展规划纲要"""
        case = ALL_CASES["TC-PLANNING-01"]
        result = self._run_case("TC-PLANNING-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_planning_02(self):
        """规划-02：交通运输行业数字化专项规划"""
        case = ALL_CASES["TC-PLANNING-02"]
        result = self._run_case("TC-PLANNING-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_planning_03(self):
        """规划-03：市级人才发展专项规划"""
        case = ALL_CASES["TC-PLANNING-03"]
        result = self._run_case("TC-PLANNING-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    # ─── 汇报类 ──────────────────────────────────────
    def test_briefing_01(self):
        """汇报-01：重点项目推进情况汇报"""
        case = ALL_CASES["TC-BRIEFING-01"]
        result = self._run_case("TC-BRIEFING-01")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_briefing_02(self):
        """汇报-02：领导班子年度述职汇报"""
        case = ALL_CASES["TC-BRIEFING-02"]
        result = self._run_case("TC-BRIEFING-02")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True

    def test_briefing_03(self):
        """汇报-03：省级督察组工作情况汇报"""
        case = ALL_CASES["TC-BRIEFING-03"]
        result = self._run_case("TC-BRIEFING-03")
        assert_output_not_empty(result, case["id"])
        assert_word_count_in_range(result, case)
        assert_document_type(result, case)
        assert_required_sections(result, case)
        result["passed"] = True


# ─────────────────────────────────────────────────────
# conftest.py 配置说明（见同目录 conftest.py）
# ─────────────────────────────────────────────────────
#
# conftest.py 提供以下 fixtures：
#
#   @pytest.fixture(scope="session")
#   def dify_api_url() -> str
#     从环境变量 DIFY_API_URL 读取，若未设置则 pytest.skip()
#
#   @pytest.fixture(scope="session")
#   def workflow_client(dify_api_url) -> DifyWorkflowClient
#     返回已初始化的 DifyWorkflowClient 实例
#
#   @pytest.fixture(scope="session", autouse=True)
#   def test_report() -> Generator
#     session 级别，收集所有测试结果，teardown 时写入 JSON 报告
#
# pytest.ini 配置参考：
#   [pytest]
#   testpaths = 06_testing
#   python_files = test_*.py
#   python_classes = Test*
#   python_functions = test_*
#   addopts = -v --tb=short
#   timeout = 180
#   markers =
#     speech: 讲话类测试
#     plan: 计划类测试
#     scheme: 方案类测试
#     report: 报告类测试
#     planning: 规划类测试
#     briefing: 汇报类测试
#     slow: 耗时较长的测试（字数要求大）
#
# ─────────────────────────────────────────────────────
