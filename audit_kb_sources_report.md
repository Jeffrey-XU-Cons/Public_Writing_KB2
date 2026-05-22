# 01-05 知识库源文件质量核查报告

**生成时间：** 2026-05-22 09:58
**项目路径：** `D:\projects\Public_Writing_KB`

**问题总览：** 🔴 21 个错误 ｜ ⚠️ 9 个警告

---

## 01_templates

### 统计
- **实际存在的 JSON 模板数：** 45
- **by_usage_index 声称的模板总数：** 130
- **by_usage_index 引用的唯一文件路径数：** 130
- **各场景声称数量：** `{"其他": {"declared": 92, "actual": 92}, "方案类": {"declared": 21, "actual": 21}, "汇报类": {"declared": 1, "actual": 1}, "计划类": {"declared": 13, "actual": 13}, "讲话类": {"declared": 3, "actual": 3}}`
- **索引引用但文件缺失数：** 87
- **system_prompt 为空：** 0 / 45
- **content 字段为空：** 0 / 45
- **缺失 structure_skeleton 字段：** 0 / 45
- **字段分布：** `{"template_id": 45, "title": 45, "doc_type": 45, "sub_type": 45, "scenario": 45, "applicable_industry": 45, "usage_scene": 45, "word_count_range": 45, "structure_skeleton": 45, "constraints": 45, "quality_checklist": 45, "prompt_system": 45, "prompt_template": 45, "variables": 45, "output_structure": 45, "source": 45}`
- **骨架文件 A2_审核草稿_11种文体骨架.yaml 文档数：** 9
- **骨架文件 A2_补充骨架_修订版.yaml 文档数：** 2

### 🔴 错误（12）
- by_usage_index 引用了 87 个不存在的模板文件（占索引 130 个的 67%）
-   缺失: publicity/briefing/publicity-briefing-36.json
-   缺失: norm/detail/norm-detail-34.json
-   缺失: publicity/briefing/publicity-briefing-27.json
-   缺失: plan/activity/plan-activity-14.json
-   缺失: publicity/news/publicity-news-49.json
-   缺失: publicity/news/publicity-news-30.json
-   缺失: publicity/briefing/publicity-briefing-39.json
-   缺失: plan/emergency/plan-emergency-34.json
-   缺失: norm/procedure/norm-procedure-23.json
-   缺失: plan/emergency/plan-emergency-32.json
-   …（还有 77 个）

### ⚠️ 警告（3）
- 实际存在但未在索引中的模板：2 个
-   孤儿: report/briefing/report-briefing-01.json
-   孤儿: report/briefing/report-briefing-02.json

---

## 02_rules

### 统计
- **YAML 文件数：** 13
- **JSON 文件数：** 1
- **MD 文件数：** 1
- **rules_master.yaml 声称规则总数：** 345
- **rules_master.yaml 实际规则总数：** 345
- **rules_master.yaml 声称分布：** `{"FORMAT": 28, "TERM": 82, "LOGIC": 154, "STYLE": 80, "GENRE": 5}`
- **rules_master.yaml 实际分布：** `{"FORMAT": 28, "TERM": 82, "LOGIC": 153, "STYLE": 77, "GENRE": 5}`
- **字段缺失统计：** `{"content_summary": 3}`
- **book_principles/合并_全书知识条目.yaml：** `{"top_keys": 4, "max_list_len": 93}`
- **book_principles/笔杆子炼成.yaml：** `{"top_keys": 1, "max_list_len": 25}`
- **book_principles/胡森林_公文写作底层心法.yaml：** `{"top_keys": 2, "max_list_len": 45}`
- **book_principles/胡森林_公文写作心法笔杆.yaml：** `{"top_keys": 2, "max_list_len": 30}`

### 🔴 错误（1）
- rules_master.yaml: ID 重复 21 个: ['LR-001', 'LR-003', 'LR-002', 'MT-001', 'MT-005']

### ⚠️ 警告（3）
- rules_master.yaml: LOGIC 声称 154 vs 实际 153
- rules_master.yaml: STYLE 声称 80 vs 实际 77
- rules_master.yaml: content_summary 为空 3 条

---

## 03_dictionary

### 统计
- **YAML 文件数：** 16
- **总条目数（扫描所有列表）：** 1150
- **各文件条目数：** `{"C1_审核草稿_官方术语结构化样本.yaml": {"entries": 20, "ids": 20}, "golden_sentences/石头哥_金句素材.yaml": {"entries": 45, "ids": 45}, "official_terms.yaml": {"entries": 0, "ids": 0}, "official_terms_v2.yaml": {"entries": 0, "ids": 0}, "sentence_patterns/固定句式模板.yaml": {"entries": 96, "ids": 92}, "sentence_patterns/开头结尾句式库.yaml": {"entries": 78, "ids": 78}, "title_patterns/石头哥_标题结构.yaml": {"entries": 32, "ids": 32}, "title_patterns/词句应用大全_标题库.yaml": {"entries": 67, "ids": 67}, "tobacco_terms/01_组织术语.yaml": {"entries": 35, "ids": 35}, "tobacco_terms/02_业务术语.yaml": {"entries": 90, "ids": 85}, "tobacco_terms/03_政策术语.yaml": {"entries": 66, "ids": 62}, "tobacco_terms/04_管理成熟度术语.yaml": {"entries": 137, "ids": 128}, "tobacco_terms/05_十五五规划术语.yaml": {"entries": 90, "ids": 88}, "金句库(P4).yaml": {"entries": 394, "ids": 0}}`
- **tobacco_terms/01_组织术语.yaml：** `{"top_keys": ["meta", "terms"], "size_kb": 22}`
- **tobacco_terms/02_业务术语.yaml：** `{"top_keys": ["meta", "biz_terms"], "size_kb": 42}`
- **tobacco_terms/03_政策术语.yaml：** `{"top_keys": ["meta", "policy_terms"], "size_kb": 37}`
- **tobacco_terms/04_管理成熟度术语.yaml：** `{"top_keys": ["meta", "mme_terms"], "size_kb": 69}`
- **tobacco_terms/05_十五五规划术语.yaml：** `{"top_keys": ["meta", "p15_terms"], "size_kb": 55}`

### 🔴 错误（3）
- YAML 解析失败 golden_sentences/词句应用大全_排比句库.yaml: while parsing a block mapping
  in "D:\projects\Public_Writing_KB\03_dictionary\golden_sentences\词句应用大全_排比句库.yaml", line 869, column 5
expected <block end>, but found '<scalar>'
  in "D:\projects\Public_Writing_KB\03_dictionary\golden_sentences\词句应用大全_排比句库.yaml", line 871, column 20
- YAML 解析失败 golden_sentences/词句应用大全_比喻词库.yaml: while parsing a block mapping
  in "D:\projects\Public_Writing_KB\03_dictionary\golden_sentences\词句应用大全_比喻词库.yaml", line 486, column 5
expected <block end>, but found '<scalar>'
  in "D:\projects\Public_Writing_KB\03_dictionary\golden_sentences\词句应用大全_比喻词库.yaml", line 488, column 19
- official_terms_v2.yaml: 是纯文本包装在 content: | 中（共 9179 字符），未结构化为可检索条目 —— 这是已知缺陷（见 今日工作计划 C1 任务）

---

## 04_corpus

### 统计
- **顶层文件/目录数：** 11
- **优质范文库(P3).yaml 条目数：** 90
- **个人历史交付物元数据索引.yaml 条目数：** 90
- **个人历史交付物元数据索引_评分版.yaml 条目数：** 90
- **高价值文件清单.yaml 条目数：** 30
- **selected_articles TA-*.md 文件数：** 264
- **selected_articles 索引文件数：** 4
- **article_index.json 索引条目数：** 264
- **段落库(P4).yaml 条目数：** 330
- **段落库 字段分布：** `{"file_title": 330, "category": 330, "file_path": 330, "paragraph_type": 330, "paragraph_index": 330, "content": 330, "word_count": 330, "quality_score": 330}`

### 🔴 错误（5）
- 优质范文库(P3).yaml 中引用的原始文件缺失: 4 个
-   缺失: 00_raw_materials/个人历史交付物/方案类/陕西 中烟 智慧 物流数字化转型实施方案 2.md
-   缺失: 00_raw_materials/个人历史交付物/规划类/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md
-   缺失: 00_raw_materials/个人历史交付物/规划类/1-1河南中烟工业有限责任公司南阳卷烟厂数字化转型中长期规划.md
-   缺失: 00_raw_materials/个人历史交付物/规划类/长株潭公司十四五战略规划（意见修订稿）-20210220.md

---

## 05_metadata

### 统计
- **JSON 文件数：** 3
- **声称 01_templates：** `{"name": "Prompt Template Library", "count": 152, "size_kb": 367.6044921875, "status": "完成", "coverage": "151个模板，5个场景"}`
- **声称 02_rules：** `{"name": "Rule Engine & Extracted Knowledge", "count": 19, "status": "完成", "coverage": "15个文件，8本书籍提炼"}`
- **声称 03_dictionary：** `{"name": "Dictionary Library", "files": 2, "status": "完成 (扩展中)", "coverage": "12个YAML文件 + official_terms_v2.yaml(150+词条)"}`
- **声称 04_corpus：** `{"name": "Corpus Library", "count": 274, "size_kb": 3916.03125, "status": "高级阶段", "metadata_files": 2, "high_value_files": 30, "total_documents": 90}`
- **声称 05_metadata：** `{"name": "Metadata & Integration Index", "status": "进行中", "planned_files": ["knowledge_base_stats.json (此文件)", "cross_library_index.json (跨库检索)", "integration_test_report.json (测试报告)"]}`
- **声称全库实体数：** 418
- **声称就绪度：** 95% - 待最终测试
- **cross_library_index 顶层 keys：** `["metadata", "keyword_mappings"]`
- **测试用例数：** 0

### ⚠️ 警告（3）
- cross_library_index.json 已 67 天未更新（最后修改 2026-03-16）
- integration_test_report.json 已 67 天未更新（最后修改 2026-03-16）
- knowledge_base_stats.json 已 67 天未更新（最后修改 2026-03-16）

---
