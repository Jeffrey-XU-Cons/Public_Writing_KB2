#!/usr/bin/env python3
"""A3: Batch write A2 structure skeletons into all 43 template JSON files."""

import json
import os
import glob

# A2 structure data for each doc_type
A2_DATA = {
    "经验材料": {
        "usage_scene": "向上级汇报或向同级交流推广本单位在某项工作中形成的典型做法和经验，多在工作交流会、现场推进会或接受调研时使用。",
        "word_count_range": "1000-2500",
        "structure_skeleton": [
            {"section": "标题", "required": True, "rule": "采用'关于XXX工作的经验做法'等格式，点明交流主题和单位，不超过25字。"},
            {"section": "工作概况与成效（开篇点题）", "required": True, "rule": "首段150字以内概括本单位总体情况和主要成效（须含关键数据），避免以背景介绍开篇。"},
            {"section": "主要做法（分条展开，2-5条）", "required": True, "rule": "每条做法用简练小标题（8字以内）领起；小标题须有实质性概括，避免套话；每条须有具体举措、运作机制或案例；每条300-500字。"},
            {"section": "创新点或特色说明", "required": False, "rule": "如有创新机制，须指出与以往做法的区别；不可强行编造创新。"},
            {"section": "主要成效（数据支撑）", "required": True, "rule": "列出3-5项可量化的成效指标；数据须注明统计口径和时间范围；不得只写定性成效。"},
            {"section": "体会与思考", "required": False, "rule": "较长材料可在结尾写1-2条工作体会，须有理性反思成分；篇幅有限可省略。"}
        ],
        "constraints": [
            "做法小标题不得使用'高度重视''深入推进''扎实开展'等套话，须体现本单位的具体措施名称。",
            "每条做法必须说明'怎么做的'（机制、流程、措施），不得只说'做了什么'（结果）。",
            "成效数据须有统计时间范围，不得使用没有时间基准的绝对数字。",
            "不得将上级政策要求直接当作本单位经验（落实上级部署不等于本单位创新做法）。",
            "若有交流探讨性质，须包含客观存在的不足或待完善之处，不得回避问题。"
        ],
        "quality_checklist": [
            "检查做法小标题是否体现单位特色，将所有小标题单列出来看是否能与其他单位区分开。",
            "检查每条做法是否有'机制/制度/流程'等可复制要素描述，而非仅是结果陈述。",
            "检查开篇数据与成效部分数据是否统一，防止前后数字矛盾。",
            "检查篇幅分布是否合理：做法部分不应少于全文60%，背景和成效各不超过20%。",
            "检查成效表述是否均有数据支撑，删除所有仅有形容词的成效描述。"
        ]
    },
    "工作计划": {
        "usage_scene": "单位或部门在年初、季初或重要工作节点前，明确未来一段时期的工作目标、重点任务和实施安排，是对上呈报或内部执行的纲领性文件。",
        "word_count_range": "800-2500",
        "structure_skeleton": [
            {"section": "指导思想与总体目标", "required": True, "rule": "首段说明计划编制依据和指导思想（1-2句），重点写总体目标，须包含可量化的核心指标；不超过200字。"},
            {"section": "工作原则", "required": False, "rule": "如工作较复杂，可列2-4条工作原则；须是针对本项工作的实质性约束，不得全为套话；简单年度计划可省略。"},
            {"section": "重点工作任务（分条列项）", "required": True, "rule": "列出全年/季度重点任务，一般4-8项；每项须包含：任务名称（黑体小标题）、具体措施（2-4条）、责任主体、量化目标；任务描述须用动词开头。"},
            {"section": "实施步骤或时间安排", "required": True, "rule": "按季度或月份列出工作节点；时间节点须明确到月份，不得只写'上半年''年内'等模糊表述；可用表格呈现。"},
            {"section": "保障措施", "required": False, "rule": "列出组织保障、经费保障、考核机制等，须有具体操作内容；部门内部执行的计划可省略或简写。"}
        ],
        "constraints": [
            "每项重点工作必须有量化目标，不得全部使用'进一步加强''持续推进'等无法衡量完成情况的表述。",
            "时间节点必须明确到月份，不得全篇只用'年内''适时''按时'等模糊表述。",
            "责任主体必须明确到具体部门或岗位，不得只写'相关部门'。",
            "不得将上年遗留问题作为新年度新任务包装，延续性工作须注明'续推'或'持续'。",
            "工作计划不得夹带对上级的请示或资金请求，须单独行文。"
        ],
        "quality_checklist": [
            "检查总体目标中的量化指标是否有数据来源依据，防止目标数字脱离实际。",
            "检查每项重点工作的时间节点是否与总体部署协调，防止任务节点冲突或堆积。",
            "检查责任分工是否覆盖所有重点任务，是否存在有任务无主体的情况。",
            "逐条检查重点工作描述是否使用动词开头的行动导向表述，替换所有名词短语式标题。",
            "检查全年任务量是否与本单位人力资源匹配，防止计划虚高失去执行可能性。"
        ]
    },
    "实施方案": {
        "usage_scene": "将上级决策部署或本单位工作计划转化为可执行的具体行动方案，适用于需要多部门协作、有明确任务节点和考核要求的系统性工作部署。",
        "word_count_range": "1500-4000",
        "structure_skeleton": [
            {"section": "总体要求（含指导思想、基本原则、工作目标）", "required": True, "rule": "指导思想1-2句说明依据的上级文件和工作方向，不超过100字；基本原则列2-4条，须有实质性约束；工作目标须包含量化指标，明确到年度或阶段。"},
            {"section": "主要任务（分条列项，3-8条）", "required": True, "rule": "每条任务采用'（一）标题：……'格式，标题不超过12字；每条须包含：任务内容、实施路径、完成标准、牵头单位；各条任务有内在逻辑顺序，不可随意排列。"},
            {"section": "职责分工", "required": True, "rule": "单独列出所有参与单位及其在本方案中的具体职责，采用'×单位负责……'表述；分工须覆盖所有主要任务；总协调单位单独列明。"},
            {"section": "实施步骤（分阶段）", "required": True, "rule": "一般分启动准备、全面推进、总结验收三个阶段，每阶段明确起止时间（精确到月份）和主要工作内容；不得少于两个阶段。"},
            {"section": "保障措施", "required": True, "rule": "从组织保障、经费保障、制度保障等维度列写，每条须有具体操作内容，不得全为套话。"},
            {"section": "督查考核", "required": True, "rule": "说明督导主体、督查频次和方式，明确考核结果运用（纳入绩效、追责问责等）；不得只说'加强督查'而无具体机制。"}
        ],
        "constraints": [
            "不得缺少量化工作目标，所有目标须有可测量的完成标准，不接受'基本实现''大幅提升'等模糊表述。",
            "每项主要任务必须有明确的牵头单位，不得出现'相关单位''各单位''有关部门'等模糊责任主体。",
            "每个阶段的时间节点须精确到月份，不得使用'上半年''年内''适时'等表述。",
            "督查考核部分不得虚设，须有具体的考核主体和结果运用机制。",
            "方案不得将上级政策照抄作为本单位的工作任务，须转化为本单位的具体行动。"
        ],
        "quality_checklist": [
            "检查工作目标中的量化指标是否有对应的任务条款支撑其实现路径。",
            "检查职责分工中是否每个参与单位都有实质性职责，删除无实际分工内容的单位。",
            "检查实施步骤中各阶段时间节点是否连贯，不存在时间断档或交叉重叠。",
            "检查保障措施中是否有切实可操作的内容，将套话替换为具体机制描述。",
            "检查全方案各部分逻辑自洽：目标→任务→分工→步骤→保障，每个环节均有对应。"
        ]
    },
    "管理制度": {
        "usage_scene": "规范单位内部某类工作或行为的长效性制度文件，适用于人事管理、财务管理、业务流程、安全规范等需要建立固定规则的场景。",
        "word_count_range": "800-3000",
        "structure_skeleton": [
            {"section": "第一章 总则", "required": True, "rule": "依次包含：制度目的、适用范围（明确到人员类别或业务类别）、制度依据；目的须聚焦本制度解决的具体问题，不得泛泛而谈。"},
            {"section": "第二章 职责分工", "required": True, "rule": "明确主管部门和执行部门的各自职责，以及相关岗位人员的职责边界；须说明'谁主管''谁执行''谁监督'，不得将所有职责集中于一个部门。"},
            {"section": "第三章 具体规定（核心条款，可分多章）", "required": True, "rule": "按逻辑顺序列出管理规则和操作规范，每条规定须明确：适用情形、操作要求或禁止行为、时限要求；条款表述用'应''须''不得''禁止'等规范性词语；每章聚焦一类事项。"},
            {"section": "第四章 监督与考核", "required": True, "rule": "规定制度执行的监督主体、检查方式和频次；明确违规的认定标准和处理方式，处罚力度须与违规性质相称；不得只说'将追究责任'而无具体追责机制。"},
            {"section": "第五章 附则", "required": True, "rule": "注明制度解释权归属、生效日期和废止的原有制度；有配套附件须列明；生效日期须明确到具体日期。"}
        ],
        "constraints": [
            "每条规定必须有明确的行为主体，不得使用'相关人员''有关部门'等无法落实的主体表述。",
            "条款中须区分'应（义务性要求）''可（授权性规定）''不得（禁止性规定）'，三者不得混用。",
            "处罚条款须有具体的处罚措施和量级，不得只写'视情处理''予以追究'等无法执行的表述。",
            "制度的适用范围不得与现行其他制度重叠，须在附则中明确废止或修订旧制度。",
            "条款内容不得超出制定单位的职权范围，不得设定超出法律授权的惩处内容。"
        ],
        "quality_checklist": [
            "检查每章每条是否有明确的行为主体，逐条识别并替换模糊主体表述。",
            "检查条款中'应''须''可''不得'的使用是否准确区分义务、授权和禁止三种规范类型。",
            "检查处罚条款是否与违规行为的严重程度相匹配。",
            "检查制度生效条款是否明确废止了被本制度替代的旧制度。",
            "检查制度中引用的其他规定是否为现行有效文件。"
        ]
    },
    "会议纪要": {
        "usage_scene": "记录和反映会议主要议题、讨论结论、决定事项和责任分工，具有法定效力，作为贯彻执行会议决定和追溯会议决策的正式依据。",
        "word_count_range": "500-2000",
        "structure_skeleton": [
            {"section": "纪要标识（文头）", "required": True, "rule": "按GB/T 9704标准，'×××××纪要'居中排布；纪要字号不小于发文机关标识。"},
            {"section": "基本信息（会议要素）", "required": True, "rule": "依次注明：会议名称（正式全称）、时间（精确到时分）、地点、主持人姓名及职务、出席人员名单（按职级排序，含姓名职务）、列席人员、缺席及请假人员、记录人。"},
            {"section": "会议议程或议题", "required": True, "rule": "列出本次会议审议或讨论的事项，有多个议题时逐一列编号；议题名称须与实际讨论内容一致。"},
            {"section": "会议内容（分议题记录）", "required": True, "rule": "按议题顺序分别记录各方发言要点、争议焦点、最终决议；决议须明确表述（'会议一致同意……''会议决定……'），不得模糊化处理；有表决事项须注明票数。"},
            {"section": "决定事项与责任分工", "required": True, "rule": "单独列出'决定事项'部分，逐项注明：事项内容、责任单位/责任人、完成时限；此部分是纪要执行核心，须清晰完整，不得仅散在正文中。"},
            {"section": "纪要印发说明", "required": False, "rule": "如纪要需报送上级或抄送相关单位，注明印发范围；须经主持人或授权人审核签发后方可印发。"}
        ],
        "constraints": [
            "不得将讨论过程中未形成共识的意见表述为'会议决定'，争议意见须如实记录并注明未达成一致。",
            "不得在纪要中新增会议未讨论的事项，纪要内容须严格限于实际会议内容。",
            "出席人员名单须与实际签到记录一致，不得将未出席人员记入出席名单。",
            "决定事项的完成时限不得比实际会议商定的更宽松，且须有责任人而非仅有责任部门。",
            "涉及组织人事、资金使用等敏感事项的纪要，须按保密规定控制印发范围。"
        ],
        "quality_checklist": [
            "检查决定事项部分是否与正文中每项决议一一对应，防止遗漏。",
            "检查有表决事项的决议是否记录了表决票数，防止将有异议决议写成'一致同意'。",
            "检查出席人员名单与签到表是否一致，职务信息是否准确。",
            "检查决定事项中每条是否都有明确的责任人（非部门）和具体完成时限。",
            "检查纪要文字是否经主持人或指定负责人审阅确认。"
        ]
    }
}

# Find all JSON template files (exclude index files)
base_dir = "D:/projects/Public_Writing_KB/01_templates"
json_files = glob.glob(os.path.join(base_dir, "**/*.json"), recursive=True)
json_files = [f for f in json_files if "index" not in os.path.basename(f).lower()]

print(f"Found {len(json_files)} template JSON files")

updated = 0
skipped = 0
unknown_types = set()

for filepath in sorted(json_files):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    doc_type = data.get("doc_type", "")

    if doc_type not in A2_DATA:
        unknown_types.add(doc_type)
        skipped += 1
        continue

    a2 = A2_DATA[doc_type]

    # Build new ordered dict with desired field order
    new_data = {}
    new_data["template_id"] = data.get("template_id", "")
    new_data["title"] = data.get("title", "")
    new_data["doc_type"] = data.get("doc_type", "")
    new_data["sub_type"] = data.get("sub_type", "")
    new_data["scenario"] = data.get("scenario", "通用")
    new_data["applicable_industry"] = data.get("applicable_industry", ["通用"])
    new_data["usage_scene"] = a2["usage_scene"]
    new_data["word_count_range"] = a2["word_count_range"]
    new_data["structure_skeleton"] = a2["structure_skeleton"]
    new_data["constraints"] = a2["constraints"]
    new_data["quality_checklist"] = a2["quality_checklist"]
    new_data["prompt_system"] = data.get("prompt_system", "")
    new_data["prompt_template"] = data.get("prompt_template", "")
    new_data["variables"] = data.get("variables", [])
    new_data["output_structure"] = data.get("output_structure", "按照标准公文结构")
    new_data["source"] = data.get("source", "")

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    updated += 1
    print(f"  OK: {os.path.basename(filepath)} ({doc_type})")

print(f"\nUpdated: {updated} files")
print(f"Skipped: {skipped} files")
if unknown_types:
    print(f"Unknown doc_types: {unknown_types}")
