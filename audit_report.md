# 知识库核查报告
**生成时间：** 2026-03-27 22:38
**项目路径：** D:\projects\Public_Writing_KB

---

## 一、JSONL文件核查（P0 优先处理）

### 模板库
**文件：** `data_prep/templates_import.jsonl` | **总条数：** 130

- ⚠️ 字段「system_prompt」缺失或为空：130条（共130条）
- 🔴 system_prompt为空：130条（共130条）——这些模板无法正常使用，需要人工补充
- ⚠️ content字段为空：130条

### 词典库
**文件：** `data_prep/dictionary_unified.jsonl` | **总条数：** 534

- ⚠️ 字段「content」缺失或为空：139条（共534条）
- ⚠️ content字段为空：139条
- 🔴 发现重复ID：54个
-     → 行55: OTHER_000000
-     → 行56: OTHER_000001
-     → 行57: OTHER_000002
-     → 行58: OTHER_000003
-     → 行59: OTHER_000004

### 语料库_范文
**文件：** `data_prep/corpus_documents.jsonl` | **总条数：** 285

- ✅ 格式检查通过，共285条

### 段落库
**文件：** `data_prep/corpus_paragraphs.jsonl` | **总条数：** 330

- ⚠️ content过短（<10字）的条目：9条
-     → 行29: id=p_000028, 内容仅3字
-     → 行38: id=p_000037, 内容仅4字
-     → 行62: id=p_000061, 内容仅4字
-     → 行79: id=p_000078, 内容仅6字
-     → 行80: id=p_000079, 内容仅6字

### 金句库
**文件：** `data_prep/corpus_golden_sentences.jsonl` | **总条数：** 387

- ✅ 格式检查通过，共387条

### 模板库专项：usage分布统计

**按usage分类：**
- `其他`：92条 （其中system_prompt为空：92条）
- `方案类`：21条 （其中system_prompt为空：21条）
- `计划类`：13条 （其中system_prompt为空：13条）
- `讲话类`：3条 （其中system_prompt为空：3条）
- `汇报类`：1条 （其中system_prompt为空：1条）

**⚠️ 重点关注：以下usage类型与四类核心文种的对应关系**
- `汇报类` → 汇报文种
- `方案类` → 方案文种
- `讲话类` → 讲话稿文种
- `其他` → 暂不使用，数量最多，建议确认是否有遗漏归类

### 语料库专项：文种分布统计

**按doc_type分类：**
- `报告类`：130条
- `讲话类`：72条
- `方案类`：44条
- `规划类`：27条
- `待分类`：9条
- `汇报类`：3条

**按质量评分分类：**
- 评分`0.0`：90条
- 评分`5.0`：13条
- 评分`6.0`：40条
- 评分`7.0`：50条
- 评分`8.0`：92条

## 二、YAML文件核查（P0-P1）

### 规则总表
**文件：** `02_rules/rules_master.yaml` | 顶层键数：6 | 文件大小：221.7KB

- ✅ YAML格式正常

### 公文用语词典v2
**文件：** `03_dictionary/official_terms_v2.yaml` | 顶层键数：1 | 文件大小：19.9KB

- ✅ YAML格式正常

### 格式规则
**文件：** `02_rules/format_compliance/format_rules.yaml` | 顶层键数：2 | 文件大小：23.0KB

- ✅ YAML格式正常

### 质量规则
**文件：** `02_rules/content_quality/quality_rules.yaml` | 顶层键数：2 | 文件大小：23.7KB

- ✅ YAML格式正常

### 语言风格规则
**文件：** `02_rules/language_style/language_rules.yaml` | 顶层键数：2 | 文件大小：31.0KB

- ✅ YAML格式正常

### 烟草组织术语
**文件：** `03_dictionary/tobacco_terms/01_组织术语.yaml` | 顶层键数：2 | 文件大小：22.1KB

- ✅ YAML格式正常

### 烟草业务术语
**文件：** `03_dictionary/tobacco_terms/02_业务术语.yaml` | 顶层键数：2 | 文件大小：42.6KB

- ✅ YAML格式正常

### 烟草政策术语
**文件：** `03_dictionary/tobacco_terms/03_政策术语.yaml` | 顶层键数：2 | 文件大小：38.0KB

- ✅ YAML格式正常

### 烟草管理成熟度术语
**文件：** `03_dictionary/tobacco_terms/04_管理成熟度术语.yaml` | 顶层键数：2 | 文件大小：69.6KB

- ✅ YAML格式正常

### 烟草十五五规划术语
**文件：** `03_dictionary/tobacco_terms/05_十五五规划术语.yaml` | 顶层键数：2 | 文件大小：55.6KB

- ✅ YAML格式正常

### 金句库P4
**文件：** `03_dictionary/金句库(P4).yaml` | 条目数：394 | 字段列表：['file_path', 'category', 'sentence', 'quality_score', 'length', 'file_title'] | 文件大小：190.0KB

- ✅ YAML格式正常

### 段落库P4
**文件：** `04_corpus/段落库(P4).yaml` | 条目数：330 | 字段列表：['file_path', 'content', 'category', 'quality_score', 'paragraph_type', 'word_count', 'file_title', 'paragraph_index'] | 文件大小：284.7KB

- ✅ YAML格式正常

## 三、范文全文核查（P2）

- MD文件数量：264
- 索引条目数：264
- ✅ 文件完整性检查通过

---

## 四、问题汇总与处理优先级

### 🔴 必须处理（影响系统运行）
- **模板库**：🔴 system_prompt为空：130条（共130条）——这些模板无法正常使用，需要人工补充
- **词典库**：🔴 发现重复ID：54个

### ⚠️ 建议处理（影响生成质量）
- **模板库**：⚠️ 字段「system_prompt」缺失或为空：130条（共130条）
- **模板库**：⚠️ content字段为空：130条
- **词典库**：⚠️ 字段「content」缺失或为空：139条（共534条）
- **词典库**：⚠️ content字段为空：139条
- **段落库**：⚠️ content过短（<10字）的条目：9条

---

## 五、下一步操作建议

1. 先处理所有🔴问题
2. 把有⚠️问题的文件逐个粘贴到Claude Project，由架构师协助分析内容质量
3. 重点人工核查：模板库中usage=汇报类/方案类/讲话类的条目
4. 人工核查完成后，回到Claude Project确认知识库就绪，再进入T-001