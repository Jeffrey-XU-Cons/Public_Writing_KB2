---
name: gw-search
description: 公文库检索——查公文 QA 方法库（ThinkBook 经 Kb-RAG，7050 退回本地直查）、术语词典、范文库，按“答没答所问”分 A/B 级，给单点答复（F6）或素材包。触发：「查公文素材」「检索公文库」「公文库里有没有XX」「找写法/例句/模板」「找同类范文」「XX这个词怎么搭配」，或由 gongwen、gw-draft、gw-review 派来补检。不响应：咨询报告段落的烟草知识库召回（归 draft）、网页搜索、写整篇稿（归 gongwen）、萃取或入库（归 gw-extract、gw-ingest）。
---

# gw-search · 公文库检索

依据：04 章§4.5（检索机制）、gw-draft「检索」节（本 skill 照搬其 Kb-RAG 命令与判读规则，两处须同步改；本地直查命令与 gw-draft 同版、都打印 status，见路线 B 第 1 条）、`30_engine/runs/P3.7_检索接入_ThinkBook操作清单.md`。
本 skill 只读，不改任何库文件。

## 铁律：说法跟着实际跑了什么走

| 实际做了什么 | 只能这样说 |
|---|---|
| 真跑了 Kb-RAG 的 search.py | “已检索公文库（Kb-RAG）” |
| 在 7050 上跑了下面的本地直查命令 | “本地库直查、覆盖有限”（关键词字面匹配，换个说法就查不到） |
| 两样都没跑 | 不提检索；凭公理作答时注明“不是来自库” |

只有真跑了 Kb-RAG search.py 才能说“已检索公文库”。这条是 CLAUDE.md §4.4 的红线，没有例外。

## 第 1 步 · 判机器

- **ThinkBook（Windows）**：走路线 A。
- **dell-7050（Linux）**：路线 A 跑不了（无 GPU、无模型、不装 torch/lancedb），走路线 B，不要尝试安装绕过。

## 路线 A · ThinkBook 经 Kb-RAG

公文 QA 已注册为 Kb-RAG 只读库 `public_writing_qa`（只读索引，真源仍是本项目 `20_knowledge/qa/`）：
```
D:/ai-runtime/venv-cuda/Scripts/python.exe D:/projects/Kb-RAG/tools/search.py --q "问题" --kb public_writing_qa --tags gw:W2 --json
```
- 按写作层过滤 `--tags gw:W1`…`gw:W5`，按大类 `gw:C1`…`gw:C6`，“为什么”类加 `gw:depth=axiom`。
- 标签是**召回后过滤**：先召回候选再筛标签，不保证返回该标签的全部条目（P5 收尾实测库内 rule 14 条只回 10 条）。要“全部某类”时改用路线 B 的本地列表命令。
- 结果 id 与本库原 id 一致（QA-C3-00001），回本库按 id 取全文核对。
- 索引会过时：公文库入库或改条目后，要在 ThinkBook 重跑 `kb_import.py public_writing_qa` 与 `kb_index.py public_writing_qa`，否则查到的是旧数据。怀疑新条目没进索引时，按 id 走路线 B 核对。

### 命中判读（分数高不等于答对）

P3.7 实测：问“‘高度重视’能不能用”，Top1 是讲数据说服力的 QA-C6-00010，分数 0.854，沾边但答不了所问。所以：

1. 采用前先核对：答案回答的是不是所问的那一件事。只沾边的不用，不能拿分数当依据。
2. Top1 分数低于 0.4，按“库里没有可靠答案”处理。
3. 下面两类问题库里目前没有对应内容，**先说明“库里没有”**，再给出基于六条公理的一般判断，并注明不是来自库：
   - 措辞分寸：“XX 能不能用”“这里用 XX 合不合适”
   - 要例子：“有没有范文”“给个例段”。例外：范文库已收的文种去范文库查（路线 B 第 4 条）；收了哪些文种以 `articles.jsonl` 实际内容为准，查前先跑第 4 条下的文种分布命令，不凭记忆说“已建”（2026-10-07 核查时库内只有讲话稿，其他文种的批次尚未并入）。段落库未建，“给个例段”仍按库里没有处理
4. 以上三种情况都算“查不到/查到没用”，写作任务里记进 review_report 第六节，单点问答直接告诉用户。

## 路线 B · 7050 本地直查（两台机器都能跑，纯标准库）

在项目根目录执行；Windows 上把 `python3` 换成 `python`。

1. **QA 关键词直查**（问法＋答案字面包含关键词；输出 id、status、depth、写作层、首问）：
```
python3 -c "import json,glob,sys;kw=sys.argv[1];[print(r['id'],r['status'],r.get('depth'),r.get('w_layer'),r['question'][:50]) for f in glob.glob('20_knowledge/qa/*.jsonl') for r in map(json.loads,open(f,encoding='utf-8')) if kw in r['question']+r['answer']]" 结论先行
```
   本条与 gw-draft「检索」节的同名命令一致（2026-10-07 起两处都打印 `status`）：合并去重后废弃的条目仍留在库里（例：查“结论先行”第一条就是已废弃的 QA-C6-00001），`deprecated` 的一律不用。
   一个说法查不到，换两三个同义说法再查（“开头”“开篇”“帽段”），都查不到才算库里没有。

2. **按 id 取全文**（核对答案、看出处）：
```
python3 -c "import json,glob,sys;[print(json.dumps(r,ensure_ascii=False,indent=1)) for f in glob.glob('20_knowledge/qa/*.jsonl') for r in map(json.loads,open(f,encoding='utf-8')) if r['id']==sys.argv[1]]" QA-C3-00001
```

3. **按小类列全部条目**（替代路线 A 的标签过滤；第 1 个参数是大类文件，第 2 个是 category_l2）：
```
python3 -c "import json,sys;[print(r['id'],r['status'],r.get('depth',''),r['question'].split(' / ')[0][:40]) for r in map(json.loads,open(sys.argv[1],encoding='utf-8')) if r['category_l2']==sys.argv[2]]" 20_knowledge/qa/c3_结构与逻辑.jsonl 模块写法
```
   `status` 为 deprecated 的已废弃，不用。

4. **范文库**（`20_knowledge/articles/articles.jsonl`，未进 Kb-RAG 索引，两台机器都直读；关键词匹配标题、摘要、文种、子类）：
```
python3 -c "import json,sys;kw=sys.argv[1];[print(r['id'],r['grade'],r['doc_type'],r['subtype'],r['org_level'],r['title'][:40]) for r in map(json.loads,open('20_knowledge/articles/articles.jsonl',encoding='utf-8')) if kw in r['title']+r['summary']+r['doc_type']+r['subtype']]" 现场会
```
   先看库里收了哪些文种（只认已并入 articles.jsonl 的，批次目录里没合并的不算）：
```
python3 -c "import json,collections;print(collections.Counter(json.loads(l)['doc_type'] for l in open('20_knowledge/articles/articles.jsonl',encoding='utf-8') if l.strip()))"
```
   要某篇的要件、骨架、好在哪，按 id 读该行的 `must_haves`、`skeleton`、`why_good`。起草时的范文对照走 gw-draft W2-0，不在这里展开。

5. **术语与搭配**（`20_knowledge/terms/terms.jsonl`，未进索引；`kind=术语` 带 T1 定义与 T2 搭配，`kind=官方规则` 是官方词表规则）：
```
python3 -c "import json,sys;kw=sys.argv[1];[print(r['id'],r['kind'],r['term'],str(r.get('t1_definition') or r.get('rule') or '')[:60].replace(chr(10),''),(r.get('t2_collocation') or {}).get('典型搭配','')) for r in map(json.loads,open('20_knowledge/terms/terms.jsonl',encoding='utf-8')) if kw in r['term']]" 专卖
```
   T1 定义为空的是待写条目；带 `t1_status: draft` 的是未经人工审的草稿定义，引用时注明“草稿”。

## 第 2 步 · 分级与交付

逐条判，不按分数排：

| 级 | 判据 | 怎么用 |
|---|---|---|
| A | 直接回答所问的那一件事，且条目 active | 可引用，写明 id |
| B | 沾边：同主题但答的是相邻问题，或只覆盖一部分 | 只作参考，说明差在哪 |
| 不用 | 答非所问、已废弃、分数低于 0.4 | 不进素材包；计入“查不到/没用” |

- **F6 单点问答**：先给结论（一两句），再列依据 id；库里没有就照判读第 3 条说。
- **素材包（gw-draft／gw-review 派来补检）**：按“所问 → A 级 id＋一句要点 → B 级 id＋差在哪 → 查不到的”四栏交回，不替对方写正文。
- 范文、段落、示例来自不同客户：**只学写法，不搬数据与名称**；范文 `source_path` 指向本机脱敏批次，不外流。

## 回归（ThinkBook）

F6 八条问答的检索验收：
```
D:/ai-runtime/venv-cuda/Scripts/python.exe 40_tests/cases/run_f6_kbrag.py D:/projects/Kb-RAG
```
用例在 `40_tests/cases/scenarios/batch1_F6单点问答.jsonl`；应命中 4 条须 Top5 命中，另 4 条是已知缺口，只看 Top1 是不是在硬凑。不要为过验收改 QA 文本或放宽期望。
