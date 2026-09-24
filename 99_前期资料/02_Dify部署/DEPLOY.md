# 部署操作手册 (DEPLOY.md)

> 这是可以反复执行的操作清单，不靠记忆。

---

## 当前状态速查

| 服务 | 端口 | 状态 |
|------|------|------|
| Nginx | 80, 443 | ⏳ 未启动（OOM中断）|
| Dify Web | 3000 | ⏳ 未启动 |
| Dify API | 5001 | ⏳ 未启动 |
| Dify Worker | - | ⏳ 未启动 |
| PostgreSQL | 5432 | ⏳ 未启动 |
| Redis | 6379 | ⏳ 未启动 |
| Weaviate | 8080 | ⏳ 未启动 |

访问地址：`http://47.90.148.108`（暂无域名，用IP访问）

---

## A. OOM问题解决（首要任务）

### 第一步：确认服务器内存

```bash
ssh admin@47.90.148.108
free -h
```

**根据结果判断：**

| 实际内存 | 方案 |
|---------|------|
| ≥ 12GB | 直接按顺序启动（方案1） |
| 8-12GB | 加内存限制再启动（方案2） |
| < 8GB | 移除Weaviate，改用Chroma（方案3）|

---

### 方案1：内存充足 → 顺序启动（推荐先试这个）

```bash
cd /mnt/gdrive/projects/Public_Writing_KB

# 确保有.env文件（首次需要）
cp .env.template .env
nano .env   # 填入真实的密码和API Key

# 停止残留容器
docker-compose down

# 按依赖顺序分批启动
docker-compose up -d postgres redis
sleep 15
docker-compose up -d weaviate
sleep 15
docker-compose up -d dify-api dify-worker
sleep 30
docker-compose up -d dify-web nginx

# 检查状态
docker-compose ps
```

---

### 方案2：内存8-12GB → 加内存限制

在 `docker-compose.yml` 每个耗内存的服务下加 `deploy` 限制：

```yaml
# 在 weaviate 服务下添加：
deploy:
  resources:
    limits:
      memory: 2G

# 在 dify-api 服务下添加：
deploy:
  resources:
    limits:
      memory: 2G

# 在 postgres 服务下添加：
deploy:
  resources:
    limits:
      memory: 1G
```

然后按方案1的顺序启动。

---

### 方案3：内存 < 8GB → 移除Weaviate，改用Chroma

这是最快能跑通的方案。

**步骤1**：在 `docker-compose.yml` 中注释掉 `weaviate` 服务和其他服务对它的 `depends_on`

**步骤2**：修改 `.env` 文件：
```bash
# 将以下两行
WEAVIATE_ENABLED=true
WEAVIATE_ENDPOINT=http://weaviate:8080

# 改为
WEAVIATE_ENABLED=false
# Dify将自动使用内置Chroma向量存储
```

**步骤3**：启动其余6个服务（同方案1，跳过weaviate）

**注意**：用Chroma后，Dify WebUI里知识库的向量配置不同，导入知识库时选 "Built-in" 向量存储而非Weaviate。

---

## B. 首次部署（从零到跑通）

### 前提条件检查

```bash
# SSH连接
ssh admin@47.90.148.108

# 检查Docker
docker --version        # 需要 20.x+
docker-compose --version

# 检查rclone挂载
ls /mnt/gdrive/projects/Public_Writing_KB/docker-compose.yml
# 如果报错，先重新挂载：
rclone mount obsidian:/ /mnt/gdrive --vfs-cache-mode writes --daemon

# 检查data目录（Docker volume挂载点需要在本地磁盘，不能在rclone）
sudo mkdir -p /data/dify/{storage,logs,postgres,postgres_backup,redis,weaviate,weaviate_backups,nginx_logs}
sudo chown -R admin:admin /data/dify/
```

### 配置 .env 文件

```bash
cd /mnt/gdrive/projects/Public_Writing_KB
cp .env.template .env

# 编辑，必须填写以下字段：
nano .env
```

**必须修改的字段：**
```
SECRET_KEY=       # 随机32+字符，可用：openssl rand -hex 32
POSTGRES_PASSWORD=# 强密码
REDIS_PASSWORD=   # 强密码
WEAVIATE_API_KEY= # 强密码
DEEPSEEK_API_KEY= # 从 https://platform.deepseek.com 获取
```

### 启动并验证

```bash
# 按A节方案启动后，验证：
docker-compose ps                          # 全部显示 Up
curl http://localhost:5001/api/health      # 返回{"status":"ok"}
curl http://localhost:3000                 # 返回HTML页面
curl http://localhost                      # 经过Nginx的入口
```

---

## C. Dify WebUI 初始配置（启动成功后）

浏览器访问 `http://47.90.148.108` 或 `http://47.90.148.108/console`

### 1. 配置 DeepSeek API
- Settings → Model Providers → 添加 DeepSeek
- API Key：填入 .env 中的 DEEPSEEK_API_KEY
- 默认模型：`deepseek-v3` / `deepseek-chat`
- 点击 Test → 验证通过

### 2. 配置嵌入模型
- Settings → Embedding Model
- 选 HuggingFace → BGE-large-zh-v1.5（维度1024）
- 或用 DeepSeek 自带嵌入（维度1536，精度稍低但更简单）

### 3. 配置向量数据库连接
- Settings → Vector Store
- 如用Weaviate：端点 `http://weaviate:8080`，API Key 填 WEAVIATE_API_KEY
- 如用Chroma（方案3降级）：选 Built-in，无需额外配置

---

## D. 知识库导入（Dify WebUI操作，约3-4小时）

先把JSONL文件上传到服务器：
```bash
# 在本地Windows执行：
scp D:\projects\Public_Writing_KB\data_prep\*.jsonl admin@47.90.148.108:/tmp/dify_import/
```

然后在Dify WebUI → Knowledge Base，依次创建5个知识库：

| 知识库名称 | 文件 | 记录数 |
|-----------|------|--------|
| PublicWriting_Prompts_Library | templates_import.jsonl | 151条 |
| PublicWriting_Dictionary | dictionary_unified.jsonl | 534条 |
| PublicWriting_Exemplars | corpus_documents.jsonl | 285条 |
| PublicWriting_Paragraphs | corpus_paragraphs.jsonl | 330条 |
| PublicWriting_GoldenSentences | corpus_golden_sentences.jsonl | 387条 |

每个知识库：Upload File → 等待向量化（5-15分钟） → Test查询验证

---

## E. 日常更新代码

```bash
ssh admin@47.90.148.108
cd /mnt/gdrive/projects/Public_Writing_KB
git pull

# 如果改了prompts/或code/，在Dify WebUI手动更新对应节点
# 如果改了docker-compose.yml或nginx.conf：
docker-compose restart nginx   # 或对应服务名

# 如果改了.env：
docker-compose down && docker-compose up -d
```

---

## F. 验证健康状态

```bash
# 容器状态
docker-compose ps

# 各服务日志（最后30行）
docker-compose logs --tail=30 dify-api
docker-compose logs --tail=30 dify-worker

# 接口健康检查
curl http://localhost:5001/api/health
curl http://localhost:8080/v1/.well-known/ready   # Weaviate

# 内存使用
free -h
docker stats --no-stream
```

---

## G. 回滚方法

```bash
# 找到上一个好的提交
git log --oneline -10

# 回滚到指定提交
git checkout <commit_id>

# 重启受影响的服务
docker-compose restart dify-api dify-worker
```

---

## H. 下一步：HTTPS配置（暂缓，有域名后执行）

```bash
# 安装certbot
sudo apt-get install certbot python3-certbot-nginx

# 申请证书（需要先有域名，DNS解析到47.90.148.108）
sudo certbot --nginx -d your-domain.com

# 修改nginx.conf中的server_name为实际域名
# 重启nginx
docker-compose restart nginx
```

---

*更新时间：2026-03-17*
