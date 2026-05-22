# Agent② 知识检索 — 配置文档

## 文档说明

| 属性 | 值 |
|------|-----|
| 用于节点 | Dify 并行知识检索节点组（T-2.x） |
| 节点类型 | Knowledge Retrieval Node × 5 + Code Node × 1 |
| 并行执行 | 5路检索同时进行，Code Node等待全部完成后聚合 |
| 上游输入 | `intent_result`（来自Agent①的JSON字符串） |
| 输出变量 | `knowledge_context`（聚合后的知识上下文字典） |

---

## 5路并行检索配置详情

### 检索路 1：模板库检索

| 配置项 | 值 |
|--------|-----|
| 知识库名称 | `public_writing_templates` |
| Dify知识库ID | `kb_templates_001`（部署时替换为实际ID） |
| 检索模式 | 混合检索（语义+关键词） |
| Top-K | 3 |
| 相似度阈值 | 0.65 |
| 输出变量名 | `template_results` |

**查询语句构建：**
```
{{doc_type_cn}}结构模板 {{occasion}}
```
示例：`讲话稿结构模板 年度工作会议`

**检索目标：** 获取与当前文体类型匹配的标准结构模板，包含各级标题框架和段落组织方式。

---

### 检索路 2：词典库检索

| 配置项 | 值 |
|--------|-----|
| 知识库名称 | `term_dictionary` |
| Dify知识库ID | `kb_dict_001` |
| 检索模式 | 关键词检索 |
| Top-K | 10 |
| 相似度阈值 | 0.60 |
| 输出变量名 | `dict_results` |

**查询语句构建：**
```
{{topic}} {{core_content}} 规范术语 禁用词
```
示例：`专卖打假 假冒烟草制品 规范术语 禁用词`

**检索目标：** 获取与主题相关的规范术语对照表、禁用词列表、行业专业词汇。

---

### 检索路 3：示范文档检索

| 配置项 | 值 |
|--------|-----|
| 知识库名称 | `sample_documents` |
| Dify知识库ID | `kb_samples_001` |
| 检索模式 | 语义检索 |
| Top-K | 2 |
| 相似度阈值 | 0.70 |
| 输出变量名 | `sample_results` |

**查询语句构建：**
```
{{doc_type_cn}} {{topic}} 优秀范文
```
示例：`工作报告 市场开拓工作 优秀范文`

**检索目标：** 获取同类型、相近主题的高质量历史公文样本，供起草参考。

---

### 检索路 4：段落库检索

| 配置项 | 值 |
|--------|-----|
| 知识库名称 | `paragraph_library` |
| Dify知识库ID | `kb_paragraphs_001` |
| 检索模式 | 语义检索 |
| Top-K | 8 |
| 相似度阈值 | 0.68 |
| 输出变量名 | `paragraph_results` |

**查询语句构建：**
```
{{doc_type_cn}} {{core_content}} 段落片段
```
示例：`实施方案 专项整治措施 段落片段`

**检索目标：** 获取可复用的标准段落片段，包括开头段、过渡段、措施段、结尾段等。

---

### 检索路 5：金句库检索

| 配置项 | 值 |
|--------|-----|
| 知识库名称 | `golden_sentences` |
| Dify知识库ID | `kb_golden_001` |
| 检索模式 | 语义检索 |
| Top-K | 6 |
| 相似度阈值 | 0.62 |
| 输出变量名 | `golden_results` |

**查询语句构建：**
```
{{topic}} {{tone_style}} 金句 排比句
```
示例：`党建工作部署 庄重 金句 排比句`

**检索目标：** 获取适合当前主题和语气风格的精彩句子，用于开头、结尾或重点段落的润色。

---

## Code Node 聚合脚本

**节点名称：** `agent2_knowledge_aggregator`
**节点类型：** Code Node（Python）
**触发条件：** 5路检索全部完成后执行

### 输入变量

```yaml
inputs:
  - template_results    # 来自检索路1
  - dict_results        # 来自检索路2
  - sample_results      # 来自检索路3
  - paragraph_results   # 来自检索路4
  - golden_results      # 来自检索路5
  - intent_result       # 来自Agent①（JSON字符串）
```

### 完整 Python 代码

```python
import json

def main(
    template_results,
    dict_results,
    sample_results,
    paragraph_results,
    golden_results,
    intent_result
) -> dict:
    """
    Agent② 知识检索结果聚合器
    将5路并行检索结果整合为统一的knowledge_context字典
    供Agent③起草节点使用
    """

    # ── 1. 解析意图识别结果 ─────────────────────────────────────
    try:
        intent = json.loads(intent_result) if isinstance(intent_result, str) else intent_result
    except (json.JSONDecodeError, TypeError):
        intent = {
            "doc_type": "report",
            "doc_type_cn": "工作报告",
            "topic": "未知主题",
            "word_count_min": 1500,
            "word_count_max": 3000
        }

    # ── 2. 标准化检索结果处理函数 ────────────────────────────────
    def normalize_retrieval(raw_results, source_name, max_items=None):
        """将Dify知识库检索结果标准化为文本列表"""
        items = []
        if not raw_results:
            return items

        # Dify知识库检索结果通常是列表格式
        if isinstance(raw_results, list):
            for idx, item in enumerate(raw_results):
                if max_items and idx >= max_items:
                    break
                if isinstance(item, dict):
                    content = item.get("content", item.get("text", item.get("page_content", "")))
                    score = item.get("score", item.get("similarity", 0.0))
                    metadata = item.get("metadata", {})
                    doc_name = metadata.get("doc_name", metadata.get("source", f"{source_name}_{idx+1}"))
                    if content:
                        items.append({
                            "source": doc_name,
                            "content": content.strip(),
                            "score": round(float(score), 4)
                        })
                elif isinstance(item, str) and item.strip():
                    items.append({
                        "source": f"{source_name}_{idx+1}",
                        "content": item.strip(),
                        "score": 0.0
                    })
        elif isinstance(raw_results, str) and raw_results.strip():
            items.append({
                "source": source_name,
                "content": raw_results.strip(),
                "score": 0.0
            })

        return items

    # ── 3. 处理各路检索结果 ──────────────────────────────────────
    templates = normalize_retrieval(template_results, "模板库", max_items=3)
    dictionary = normalize_retrieval(dict_results, "词典库", max_items=10)
    samples = normalize_retrieval(sample_results, "示范文档", max_items=2)
    paragraphs = normalize_retrieval(paragraph_results, "段落库", max_items=8)
    golden = normalize_retrieval(golden_results, "金句库", max_items=6)

    # ── 4. 构建结构化文本摘要（供LLM直接阅读） ───────────────────
    def build_text_block(items, title, max_chars=800):
        """将检索结果列表格式化为可读文本块"""
        if not items:
            return f"【{title}】\n（暂无相关内容）\n"

        lines = [f"【{title}】"]
        total_chars = 0
        for item in items:
            content = item["content"]
            if total_chars + len(content) > max_chars:
                # 截断以控制总token数
                remaining = max_chars - total_chars
                if remaining > 50:
                    content = content[:remaining] + "..."
                else:
                    break
            source_label = f"（来源：{item['source']}）" if item["source"] else ""
            lines.append(f"- {content}{source_label}")
            total_chars += len(content)

        return "\n".join(lines) + "\n"

    # ── 5. 构建knowledge_context字典 ────────────────────────────
    knowledge_context = {
        # 结构化数据（供代码节点使用）
        "structured": {
            "templates": templates,
            "dictionary": dictionary,
            "samples": samples,
            "paragraphs": paragraphs,
            "golden_sentences": golden
        },

        # 文本化摘要（直接注入LLM提示词）
        "text_summary": "\n".join([
            "=" * 50,
            "以下是从知识库检索到的参考内容，请在起草时合理参考：",
            "=" * 50,
            build_text_block(templates, "结构模板参考", max_chars=600),
            build_text_block(samples, "优秀范文参考", max_chars=1000),
            build_text_block(paragraphs, "可用段落片段", max_chars=1200),
            build_text_block(golden, "推荐金句参考", max_chars=400),
            build_text_block(dictionary, "规范术语与禁用词", max_chars=500),
        ]),

        # 禁用词快速索引（供校对节点使用）
        "forbidden_words": _extract_forbidden_words(dictionary),

        # 统计信息
        "stats": {
            "template_count": len(templates),
            "dict_count": len(dictionary),
            "sample_count": len(samples),
            "paragraph_count": len(paragraphs),
            "golden_count": len(golden),
            "total_retrieved": len(templates) + len(dictionary) + len(samples) + len(paragraphs) + len(golden)
        },

        # 透传意图信息
        "intent": intent
    }

    return {"knowledge_context": json.dumps(knowledge_context, ensure_ascii=False)}


def _extract_forbidden_words(dict_items):
    """从词典检索结果中提取禁用词列表"""
    forbidden = []
    for item in dict_items:
        content = item.get("content", "")
        # 简单规则：含"禁用"、"不得使用"、"错误写法"字样的条目
        if any(kw in content for kw in ["禁用", "不得使用", "错误写法", "×", "禁止"]):
            # 提取禁用词（简化处理，实际可用正则）
            forbidden.append(content)
    return forbidden
```

---

## 并行检索配置方法说明

### 在 Dify 中配置并行节点

1. **创建并行分支**
   - 在意图识别节点（agent1）之后，点击"+"添加节点
   - 选择"并行分支"（Parallel Branch）模式
   - 系统将自动创建并行执行框架

2. **配置每路知识检索节点**
   - 在每个并行分支内添加"知识检索"（Knowledge Retrieval）节点
   - 按上表配置各路的知识库、Top-K、阈值参数
   - 查询变量从 `intent_result` 解析后的字段中引用

3. **查询语句变量引用**
   ```
   # Dify变量引用语法示例
   {{#agent1_intent_analysis.intent_result.doc_type_cn#}}
   {{#agent1_intent_analysis.intent_result.topic#}}
   ```
   注：需先通过Code Node或内置JSON解析器提取字段

4. **聚合节点配置**
   - 在所有并行分支汇合后添加Code Node
   - 将5个检索节点的输出变量均作为Code Node的输入
   - 代码节点输出 `knowledge_context` 供后续节点使用

5. **超时与容错**
   - 建议为每路检索设置5秒超时
   - 任一检索路超时，以空列表代替，不影响整体流程
   - 在Code Node中已处理空值情况（`normalize_retrieval`函数）

### 变量引用链路图

```
user_input
    │
    ▼
[Agent①意图识别] → intent_result (JSON)
    │
    ├──▶ [检索路1: 模板库] → template_results
    ├──▶ [检索路2: 词典库] → dict_results
    ├──▶ [检索路3: 示范文档] → sample_results
    ├──▶ [检索路4: 段落库] → paragraph_results
    └──▶ [检索路5: 金句库] → golden_results
                                    │
                                    ▼
                    [Code Node: 知识聚合器]
                                    │
                                    ▼
                          knowledge_context (JSON)
                                    │
                                    ▼
                          [Agent③ 起草节点]
```

---

## 注意事项

1. 知识库ID（`kb_xxx_001`）为占位符，部署前必须替换为Dify实际知识库ID
2. Top-K和相似度阈值可根据知识库实际内容质量调整
3. 词典库建议使用关键词检索而非语义检索，确保精确匹配禁用词
4. 若知识库尚未建立，各路返回空结果，系统仍可正常运行（降级模式）
5. `text_summary` 字段注入Agent③的System Prompt时，建议控制在2000字符以内，避免超出上下文窗口
