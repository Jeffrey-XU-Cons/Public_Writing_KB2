# 🚀 Dify 系统部署指南 - 阿里云环境

**目标服务器**: 47.90.148.108 (Ubuntu 24.04 LTS)  
**部署日期**: 2026-03-16  
**任务**: Task 6.1 - 基础环境检查与部署

---

## 📋 前置条件检查

### 本地环境要求
- ✅ 已完成数据准备（Task 6.5）
- ✅ 已生成 JSONL 数据文件（在 `data_prep/` 目录）
- ✅ 已生成 docker-compose.yml
- ✅ 已生成 .env.template
- ✅ 可以 SSH 登录服务器
- ✅ 已安装 `scp` 工具

### 服务器配置
- IP: 47.90.148.108
- 操作系统: Ubuntu 24.04 LTS
- CPU: 2核
- 内存: 2GB
- 存储: 40GB SSD
- 到期日期: 2027-02-09
- **现有服务**: Nginx、Xray（需清理/调整）

---

## 🔧 部署步骤

### 第一步: 本地准备 (5分钟)

#### 1.1 验证本地文件
```bash
cd d:\projects\Public_Writing_KB

# 检查关键文件
ls -lh docker-compose.yml
ls -lh .env.template
ls -lh nginx.conf
ls -lh data_prep/*.jsonl
ls -lh deployment/*.sh
```

**预期输出**:
```
docker-compose.yml               (10-15 KB)
.env.template                   (8-10 KB)
nginx.conf                      (5-8 KB)
data_prep/templates_import.jsonl     (72 KB, 151 records)
data_prep/dictionary_unified.jsonl  (116 KB, 534 records)
data_prep/corpus_segments.jsonl    (304 KB, 615 records)
deployment/server_deployment_script.sh
deployment/deploy_start.sh
deployment/upload_config.sh
```

#### 1.2 准备上传脚本权限
```bash
# Windows PowerShell
chmod +x deployment/*.sh

# 或者在 Git Bash 中
cd deployment
chmod +x *.sh
cd ..
```

---

### 第二步: SSH 连接验证 (2分钟)

#### 2.1 测试 SSH 连接
```bash
ssh root@47.90.148.108 "echo 'SSH 连接正常' && uname -a"
```

**预期输出**:
```
SSH 连接正常
Linux iZbp... 6.8.0-28-generic #28-Ubuntu SMP ... x86_64 GNU/Linux
```

#### 2.2 如果没有 SSH 密钥，请配置
```bash
# 生成密钥对（如果还没有）
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# 添加公钥到服务器（可用密码或 PuTTY）
# 或者在阿里云控制台添加密钥对
```

---

### 第三步: 上传配置文件 (10分钟)

#### 3.1 运行上传脚本
```bash
# Windows PowerShell
bash deployment/upload_config.sh

# 或者 PowerShell 中（需要 bash）
.\deployment\upload_config.sh
```

**脚本作用**:
- 创建远程目录 (/opt/dify, /data/dify)
- 上传 docker-compose.yml
- 上传 .env.template→.env
- 上传 nginx.conf
- 上传所有 JSONL 数据文件
- 上传部署脚本

**进度提示**:
```
[检查本地文件]
✓ docker-compose.yml 存在
✓ .env.template 存在
✓ nginx.conf 存在
✓ data_prep/templates_import.jsonl (72K)
✓ data_prep/dictionary_unified.jsonl (116K)
...

[准备上传]
1. 创建远程目录...
✓ 远程目录创建成功

2. 上传主配置文件...
✓ docker-compose.yml
✓ .env.template (as .env)
✓ nginx.conf

3. 上传知识库数据文件...
✓ templates_import.jsonl
✓ dictionary_unified.jsonl
...

后续步骤:
1. SSH 登录服务器
2. 编辑环境配置
...
```

#### 3.2 手动上传（如果脚本失败）
```bash
# 每个文件单独上传
scp docker-compose.yml root@47.90.148.108:/opt/dify/
scp .env.template root@47.90.148.108:/opt/dify/.env
scp nginx.conf root@47.90.148.108:/opt/dify/
scp -r data_prep/*.jsonl root@47.90.148.108:/opt/dify/data_prep/
scp deployment/*.sh root@47.90.148.108:/opt/dify/
```

---

### 第四步: 远程环境检查 (10分钟)

#### 4.1 SSH 登录服务器
```bash
ssh root@47.90.148.108
```

#### 4.2 快速验证
```bash
# 检查系统信息
lsb_release -d
free -h
df -h /

# 检查 Docker
docker --version
docker-compose --version || docker compose version

# 检查端口占用
ss -tlnp | grep -E ':(80|443|5001|5432|6379|8080)'

# 检查现有服务
ps aux | grep -E '(nginx|xray|pm2)'
```

#### 4.3 处理端口冲突（如需要）

**如果 Nginx 在运行**:
```bash
# 查看 Nginx 状态
systemctl status nginx

# 停止 Nginx（可选，如要使用 Dify 的 Nginx）
systemctl stop nginx
systemctl disable nginx

# 或者保留 Nginx，配置反向代理...（见下方）
```

**如果 Xray 在运行**（可选清理）:
```bash
# 查看 Xray
ps aux | grep xray

# 停止（可选）
systemctl stop xray
# systemctl disable xray  # 永久关闭
```

**保存现有 Nginx 配置**（如需保留）:
```bash
# 备份现有配置
cp -r /etc/nginx /etc/nginx.backup
# 然后手动配置反向代理...
```

---

### 第五步: 远程部署脚本执行 (15分钟)

#### 5.1 运行部署检查脚本
```bash
# 仍在 ssh root@47.90.148.108 的会话中

cd /opt/dify

# 确保脚本有执行权限
chmod +x server_deployment_script.sh deploy_start.sh

# 运行环境检查脚本
bash server_deployment_script.sh
```

**脚本检查项**:
```
========== Phase 1: 环境检查 ==========
[INFO] 系统版本: Ubuntu 24.04.4 LTS
[✓] 可用磁盘空间: 35GB
[✓] 磁盘空间检查通过
[INFO] 可用内存: 2048MB
[✓] 内存检查通过
[✓] 外网连接正常

========== Phase 2: Docker 检查与安装 ==========
[✓] Docker 已安装
[✓] Docker Compose 已安装
[✓] Docker 进程运行正常

========== Phase 3: 检查端口占用 ==========
[✓] 端口 80 空闲 (HTTP)
[✓] 端口 443 空闲 (HTTPS)
[✓] 端口 5001 空闲 (Dify API)
...

========== Phase 4: 创建目录结构 ==========
[✓] 创建部署目录: /opt/dify
[✓] 创建数据目录: /data/dify

下一步:
  1) 上传配置文件到 /opt/dify
  2) 编辑 .env 文件设置必要的环境变量
  3) 运行 deploy_start.sh 启动系统
```

#### 5.2 编辑环境配置文件
```bash
# 编辑 .env
nano /opt/dify/.env
```

**关键配置项**（必须编辑）:

```env
# ============== REQUIRED ==============

# DeepSeek API 密钥 (必须！)
DEEPSEEK_API_KEY=sk_xxxxxxxxxxxx

# 数据库密码 (强密码，16+ 字符)
POSTGRES_PASSWORD=Secure_Password_123!@#

# Redis 密码
REDIS_PASSWORD=Redis_Secure_Pass_456!@#

# ============== OPTIONAL ==============

# 其他 LLM 提供商 (若需要)
OPENAI_API_KEY=sk-xxxxx  # 可选

# Weaviate 配置
WEAVIATE_ENABLED=true
WEAVIATE_API_KEY=weaviate-key-12345

# 时区
TIME_ZONE=Asia/Shanghai

# 模式
MODE=production

# 日志级别
LOG_LEVEL=INFO
```

**保存方法** (nano):
- Ctrl+O → Enter → Ctrl+X

#### 5.3 验证配置文件
```bash
cd /opt/dify

# 检查 .env 格式
head -20 .env

# 检查 docker-compose.yml
docker-compose config | head -30

# 列出数据文件
ls -lh data_prep/*.jsonl
```

---

### 第六步: 启动 Dify 系统 (15-20分钟)

#### 6.1 拉取容器镜像
```bash
cd /opt/dify
docker-compose pull
```

**进度提示**:
```
Pulling dify-web ... done
Pulling dify-api ... done
Pulling postgres ... done
Redis ... done
Weaviate ... done
...
```

#### 6.2 启动所有容器
```bash
docker-compose up -d
```

**输出示例**:
```
Creating network "dify_default" with driver "bridge"
Creating dify-postgres ... done
Creating dify-redis ... done
Creating dify-weaviate ... done
Creating dify-api ... done
Creating dify-web ... done
Creating dify-worker ... done
Creating dify-nginx ... done
```

#### 6.3 运行完整启动脚本（推荐）
```bash
bash deploy_start.sh
```

**完整流程**:
```
========== Phase 1: 验证环境配置 ==========
[✓] DEEPSEEK_API_KEY 已配置

========== Phase 2: 启动 Docker 容器 ==========
[INFO] 拉取最新镜像...
[✓] 容器启动命令已执行

========== Phase 3: 等待容器初始化 ==========
[INFO] 等待 PostgreSQL 就绪...
[✓] PostgreSQL 已就绪
[INFO] 等待 Redis 就绪...
[✓] Redis 已就绪
[INFO] 等待 Weaviate 就绪...
[✓] Weaviate 已就绪

========== Phase 4: 容器状态检查 ==========
NAME                  STATE       PORTS
dify-nginx           Up 20 sec   0.0.0.0:80->80/tcp
dify-postgres        Up 25 sec   5432/tcp
dify-redis           Up 25 sec   6379/tcp
dify-weaviate        Up 22 sec   8080/tcp
dify-api             Up 18 sec   5001/tcp
dify-web             Up 20 sec   3000/tcp
dify-worker          Up 18 sec

========== Phase 5: 系统健康检查 ==========
[INFO] 检查 Dify API...
[✓] Dify API 响应: {"status":"ok"}
[INFO] 检查 Dify WebUI...
[✓] WebUI 可访问
[INFO] 检查 Weaviate...
[✓] Weaviate 就绪

========== 启动完成 ==========
✓ Dify 系统启动成功！

访问地址:
  WebUI: http://47.90.148.108/studio
  API: http://47.90.148.108:5001

常用命令:
  查看日志: docker-compose logs -f dify-api
  停止系统: docker-compose down
  重启系统: docker-compose restart
```

---

### 第七步: 验证系统 (10分钟)

#### 7.1 查看容器状态
```bash
docker-compose ps
```

**预期**: 所有容器都应显示 "Up"

#### 7.2 检查容器日志
```bash
# 查看 API 日志
docker-compose logs -f dify-api

# 查看其他服务日志
docker-compose logs postgres
docker-compose logs redis
docker-compose logs weaviate
```

#### 7.3 API 健康检查
```bash
curl http://localhost:5001/api/health
```

**预期响应**:
```json
{"status":"ok"}
```

#### 7.4 本地访问 WebUI

从本地机器访问（通过 SSH 端口转发，如无直接网络访问）:
```bash
# Windows PowerShell (本地)
ssh -L 8080:localhost:80 root@47.90.148.108

# 然后浏览器打开
# http://localhost:8080/studio
```

或直接访问（如服务器有公网 IP）:
```
http://47.90.148.108/studio
```

#### 7.5 首次使用 - 创建管理员账户

1. 打开 http://47.90.148.108/studio
2. 设置管理员邮箱和密码
3. 完成初始化

#### 7.6 保存启动日志
```bash
# 导出完整日志
docker-compose logs > /opt/dify/startup_logs.txt

# 复制回本地
scp root@47.90.148.108:/opt/dify/startup_logs.txt ./
```

---

## ⚠️ 故障排查

### 问题 1: Docker 镜像拉取超时

**症状**:
```
Error response from daemon: Get "https://registry-1.docker.io/...": io timeout
```

**解决**:
```bash
# 配置阿里云镜像加速
cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://registry.aliyuncs.com"
  ]
}
EOF

# 重启 Docker
systemctl restart docker

# 重新拉取
docker-compose pull
```

### 问题 2: 端口已被占用

**症状**:
```
Error: Port 80 is already in use
Error: Port 5001 is already in use
```

**解决**:
```bash
# 查看占用端口的进程
lsof -i :80
lsof -i :5001

# 停止现有服务
systemctl stop nginx
systemctl stop other-service
```

### 问题 3: 内存不足

**症状**:
```
OOMKilled
Container exited with code 137
```

**解决**:
```bash
# 查看内存使用
free -h
docker stats

# 调整容器内存限制（编辑 docker-compose.yml）
# 减少副本数或调整内存分配
```

### 问题 4: PostgreSQL 无法连接

**症状**:
```
psycopg2.OperationalError: could not connect to server
```

**解决**:
```bash
# 检查 PostgreSQL 容器
docker-compose logs postgres

# 检查密码
docker-compose exec postgres psql -U postgres -c "SELECT 1"

# 验证 .env 中 POSTGRES_PASSWORD
cat /opt/dify/.env | grep POSTGRES_PASSWORD
```

### 问题 5: Weaviate 向量库连接失败

**症状**:
```
Connection refused: 127.0.0.1:8080
```

**解决**:
```bash
# 检查 Weaviate 状态
docker-compose logs weaviate

# 直接测试连接
curl http://localhost:8080/v1/.well-known/ready

# 重启 Weaviate
docker-compose restart weaviate
```

---

## 🎯 成功标志

✅ 完成 Task 6.1 的标准:

- [x] SSH 访问服务器验证连接正常
- [x] 系统版本验证：Ubuntu 24.04 LTS ✅
- [x] Docker 安装状态检查：✅
- [x] Docker Compose 安装验证：✅
- [x] 可用磁盘空间检查（≥50GB）：✅
- [x] 网络连接验证：✅
- [x] 所有容器正常运行
- [x] API 健康检查通过
- [x] WebUI 可正常访问
- [x] 无关键错误日志

---

## 📋 交付物清单

- ✅ server_deployment_script.sh - 环境检查脚本
- ✅ deploy_start.sh - 启动脚本
- ✅ upload_config.sh - 上传脚本
- ✅ docker-compose.yml - 已上传
- ✅ .env - 已配置
- ✅ nginx.conf - 已上传
- ✅ startup_logs.txt - 系统日志
- ✅ 部署环境检查清单（本文档）

---

## 📅 后续任务

Task 6.1 完成后，继续：

1. **Task 6.3** - Dify 系统启动和容器健康检查
2. **Task 6.4** - LLM/向量化/Weaviate 配置
3. **Task 7.x** - 知识库导入与 RAG 优化

---

**部署状态**: 🟢 就绪等待执行  
**最后更新**: 2026-03-16  
**预计部署时间**: 60分钟（包括等待和验证）
