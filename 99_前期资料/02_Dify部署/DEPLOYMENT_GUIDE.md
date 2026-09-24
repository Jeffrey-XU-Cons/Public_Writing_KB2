# 公文写作AI系统 Dify工作流部署指南

## 项目概述

本项目是一个基于Dify的公文写作AI系统，包含6个Agent工作流，用于自动化生成、审核和优化公文文稿。

**系统架构：**
- 前端UI: Dify WebUI (React)
- 后端API: Dify API (Python)
- 数据库: PostgreSQL（业务数据）
- 缓存: Redis（会话和消息队列）
- 向量库: Weaviate（向量化数据）
- LLM提供商: DeepSeek API

**项目数据规模：**
- 模板库: 151个模板
- 词典库: 534个条目（官方用语、金句等）
- 语料库: 615项（范文90、段落330、金句为补充）

---

## 部署前准备

### 1. 环境需求检查清单

**服务器要求（阿里云 Ubuntu 24.04.4 LTS）：**
- [ ] CPU: 4核或以上
- [ ] 内存: 8GB或以上
- [ ] 磁盘: 100GB或以上（用于Dify和数据存储）
- [ ] 网络: 公网访问，能访问DeepSeek API
- [ ] SSH: 能远程连接

**本地开发环境（可选）：**
- [ ] Docker 22.0+
- [ ] Docker Compose 2.0+
- [ ] Python 3.10+ (仅用于本地数据准备)
- [ ] 2-4GB可用磁盘空间

### 2. 注册API密钥

在开始部署前，需要获取以下密钥：

**DeepSeek API密钥：**
1. 访问 https://platform.deepseek.com
2. 登录或注册账户
3. 进入API控制面板
4. 创建新的API密钥
5. 将密钥保存到安全位置

**其他API（可选）：**
- OpenAI/Claude: 作为备选LLM提供商
- Hugging Face: 用于嵌入模型下载

### 3. 数据准备

数据准备脚本已在本地执行完成。生成的文件位于 `data_prep/` 目录：

```
data_prep/
├── templates_import.jsonl           (151个模板)
├── dictionary_unified.jsonl         (534个词典条目)
├── corpus_segments.jsonl            (615个语料库条目)
└── 验证报告和统计信息
```

这些文件已验证通过，总体有效率100%，可直接用于导入。

---

## 部署步骤

### 第一阶段：基础环境部署（第1-2周）

#### Step 1：连接阿里云服务器

```bash
# 使用SSH连接到服务器
ssh root@your-server-ip

# 验证系统版本
lsb_release -a
# 预期输出: Ubuntu 24.04.4 LTS
```

#### Step 2：安装Docker和Docker Compose

```bash
# 更新系统包
apt-get update && apt-get upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 验证Docker版本
docker --version
# 预期: Docker version 24.0+

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证Docker Compose版本
docker-compose --version
# 预期: Docker Compose version 2.x+
```

#### Step 3：准备部署文件

```bash
# 创建Dify部署目录
mkdir -p /opt/dify
cd /opt/dify

# 上传以下文件到服务器：
# - docker-compose.yml
# - .env.template
# - nginx.conf (可选)
# - data_prep/中的所有.jsonl文件

# 从模板创建.env文件
cp .env.template .env

# 编辑.env文件，设置所有必需的密钥和密码
nano .env
# 重点设置：
# - DEEPSEEK_API_KEY
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - WEAVIATE_API_KEY
```

#### Step 4：创建数据存储目录

```bash
# 创建持久化存储目录
mkdir -p /data/dify/{postgres,redis,weaviate,storage,logs,nginx_logs}

# 设置正确的权限
chmod -R 755 /data/dify
```

#### Step 5：启动Dify系统

```bash
# 在docker-compose.yml所在目录执行
cd /opt/dify

# 启动所有容器
docker-compose up -d

# 验证容器启动状态
docker-compose ps
# 预期：所有容器状态为 "Up"

# 查看API日志
docker-compose logs dify-api | tail -20
```

#### Step 6：验证系统健康状态

```bash
# 检查API健康状态
curl -s http://localhost:5001/api/health | python -m json.tool

# 检查前端访问
curl -s http://localhost:3000 | head

# 检查Weaviate连接
curl -s http://localhost:8080/v1/.well-known/ready

# 查看PostgreSQL连接
docker-compose exec postgres psql -U postgres -d dify -c "SELECT 1"
```

---

### 第二阶段：知识库导入（第2-3周）

#### Step 7：访问Dify WebUI

1. 打开浏览器访问：http://your-server-ip/studio
2. 完成初始化（创建管理员账户）
3. 进入系统

#### Step 8：配置LLM提供商

1. 导航到：Settings → Model Providers
2. 添加 DeepSeek 提供商：
   - Provider: DeepSeek
   - API Key: 粘贴你的DEEPSEEK_API_KEY
   - Model: deepseek-v3
   - 点击 "Test" 验证连接
3. 设置为默认模型

#### Step 9：配置嵌入模型

1. 导航到：Settings → Vector Store
2. 配置嵌入模型：
   - Model: BGE-large-zh-v1.5
   - Dimension: 1024
   - Batch Size: 32

#### Step 10：导入知识库

将生成的JSONL文件上传到Dify的Knowledge Base模块：

**知识库1 - 模板库：**
- File: `data_prep/templates_import.jsonl`
- Name: PublicWriting_Prompts_Library
- 预期: 151个模板导入

**知识库2 - 词典库：**
- File: `data_prep/dictionary_unified.jsonl`
- Name: PublicWriting_Dictionary
- 预期: 534个条目导入

**知识库3 - 语料库（统一）：**
- File: `data_prep/corpus_segments.jsonl`
- Name: PublicWriting_Corpus
- 预期: 615项导入

---

### 第三阶段：Agent工作流实现（第3-5周）

#### Step 11：创建Workflow

在Dify中逐步实现6个Agent工作流（参考详细任务文档）：

1. **Agent ① - 意图识别**
   - LLM节点：意图分析和元数据提取
   - 输出：JSON格式的文档类型和参数

2. **Agent ② - 知识检索**
   - 5路并行检索节点
   - 检索对象：模板库、词典库、范文、段落、金句
   - 输出：聚合的知识上下文

3. **Agent ③ - 起草**
   - 核心LLM节点：文稿生成
   - 输入：意图分析 + 知识上下文
   - 输出：初稿文本

4. **Agent ④ - 格式审核**
   - LLM节点：GB/T 9704标准检查
   - 自动修复或回环到Agent ③

5. **Agent ⑤ - 术语校对**
   - LLM节点：禁用词、搭配规范检查
   - 自动替换或回环

6. **Agent ⑥ - 润色**
   - LLM节点：文采提升
   - 金句插入、排比句等

#### Step 12：发布Workflow

- 名称: PublicWriting_SixAgentPipeline_v1.0
- 健康检查：运行3个测试用例确保正常工作
- 记录 Workflow ID 供后续调用

---

### 第四阶段：测试与优化（第5-6周）

#### Step 13：端到端测试

准备18个典型测试用例：
- 讲话稿：3个（工作会议、竣工仪式、表彰大会）
- 方案：3个（实施方案、改革方案、应急方案）
- 计划：3个（年度、季度、部门）
- 报告：3个（总结、调研、工作汇报）
- 规划：3个（发展、战略、五年规划）
- 汇报：3个（定期、工作、专项）

#### Step 14：性能优化

- 目标：平均响应时间 < 30秒
- 精度：生成质量评分 ≥ 8/10
- 并发：支持 10+ 并发请求

---

### 第五阶段：生产部署（第6周+）

#### Step 15：生产环境配置

```bash
# 配置HTTPS（使用Let's Encrypt）
certbot certonly --standalone -d your-domain.com

# 配置Nginx反向代理和SSL
cp nginx.conf /etc/nginx/sites-available/dify
ln -s /etc/nginx/sites-available/dify /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
```

#### Step 16：备份与恢复方案

```bash
# 每日备份PostgreSQL
docker-compose exec postgres pg_dump -U postgres dify > /backup/dify_$(date +%Y%m%d).sql

# 备份向量数据库
docker-compose exec weaviate tar czf /backup/weaviate_$(date +%Y%m%d).tar.gz /var/lib/weaviate
```

#### Step 17：监控告警

- 设置容器健康检查监控
- 配置日志聚合（可选：ELK Stack）
- 设置性能告警阈值

#### Step 18：文档与培训

- 生成API文档（Swagger/OpenAPI）
- 准备系统管理员手册
- 编写用户使用指南
- 录制系统演示视频

---

## 常见问题排查

### Q1：API连接失败

```bash
# 检查容器日志
docker-compose logs dify-api

# 检查网络连接
docker-compose exec dify-api curl -v http://weaviate:8080/v1/.well-known/ready

# 检查环境变量
docker-compose exec dify-api env | grep DEEPSEEK
```

### Q2：向量化速度慢

**可能原因：**
- Weaviate配置不足内存
- 批处理大小过大

**解决方案：**
```bash
# 增加Weaviate内存配置
docker-compose down
# 编辑docker-compose.yml中Weaviate的内存限制
docker-compose up -d
```

### Q3：文稿生成质量不达标

**调整方案：**
1. 检查DeepSeek API是否正常
2. 优化System Prompt（参考任务文档）
3. 增加检索结果数量（Top K: 5 → 7）
4. 降低相似度阈值（0.5 → 0.45）

### Q4：知识库检索不准

**改进步骤：**
1. 验证嵌入模型是否正确加载
2. 检查向量化是否完成
3. 调整混合检索权重

```bash
# 查看Weaviate向量统计
docker-compose exec weaviate curl http://localhost:8080/v1/graphql \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "{Aggregate{PublicWritingCorpus{meta{count}}}}"}'
```

---

## 性能基准

**预期指标（在标准配置下）：**

| 指标 | 预期值 | 备注 |
|------|--------|------|
| 意图识别 | 1-2秒 | Agent ① |
| 知识检索 | 2-3秒 | Agent ② (5路并行) |
| 文稿初稿生成 | 8-15秒 | Agent ③ |
| 格式审核 | 2-3秒 | Agent ④ |
| 术语校对 | 2-3秒 | Agent ⑤ |
| 润色优化 | 5-8秒 | Agent ⑥ |
| **总流程** | **20-45秒** | 端到端 |
| 检索精度 | ≥85% | RAG评估 |
| 生成质量 | ≥8/10 | 人工评分 |

---

## 后续维护

### 定期任务

- **每周**：检查系统日志，验证备份
- **每月**：性能评估，更新API密钥
- **每季**：知识库更新，Agent Prompt优化
- **每年**：大版本升级，架构评估

### 扩展方向

1. 支持更多LLM提供商（Claude、Llama等）
2. 集成更多领域的专业知识库
3. 构建用户反馈闭环优化样本
4. 多语言支持
5. 企业级权限和审计系统

---

## 技术支持

**文档位置：**
- 详细任务文档：`详细项目任务.md`
- Prompt模板：`Agent System Prompts/`
- 测试用例：`test_cases/`

**联系方式：**
- 提交Issue或PR到项目仓库
- 邮件：support@example.com

---

**最后更新：2026-03-16**
