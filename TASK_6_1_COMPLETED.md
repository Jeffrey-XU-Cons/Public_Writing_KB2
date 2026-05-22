# Task 6.1 部署环境检查清单

**任务编号**: T-6.1
**执行日期**: 2026-03-16
**执行状态**: ✅ 完成
**执行耗时**: ~45分钟

---

## 服务器基本信息

| 项目 | 值 | 状态 |
|------|-----|------|
| 服务器IP | 47.90.148.108 | ✅ |
| 操作系统 | Ubuntu 24.04.4 LTS | ✅ |
| 主机名 | iZ0xi5n2o3pe28r8uqbun7Z | ✅ |
| 登录用户 | root | ✅ |
| SSH访问 | 正常 | ✅ |

---

## 一、系统版本检查

| 检查项 | 要求 | 实际值 | 状态 |
|--------|------|--------|------|
| 操作系统 | Ubuntu 24.04 LTS | Ubuntu 24.04.4 LTS | ✅ |
| 内核版本 | 任意 | Linux 6.x | ✅ |
| Python | ≥ 3.8 | Python 3.12.3 | ✅ |
| pip | 已安装 | pip 24.0 | ✅ |

---

## 二、Docker 安装状态

| 检查项 | 要求 | 实际值 | 状态 |
|--------|------|--------|------|
| Docker CE | ≥ 20.x | Docker 29.3.0 | ✅ |
| Docker Compose | v2.x | v5.1.0 (plugin) | ✅ |
| Docker 服务 | active | active (running) | ✅ |
| docker ps 权限 | 可执行 | 正常 | ✅ |

**安装方式**: 通过 Docker 官方仓库安装（apt）
**镜像加速**: 已配置阿里云 + 中科大加速镜像

```json
{
  "registry-mirrors": [
    "https://registry.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

---

## 三、磁盘空间检查

| 检查项 | 要求 | 实际值 | 状态 |
|--------|------|--------|------|
| 磁盘总量 | ≥ 50GB（建议） | 40GB | ⚠️ |
| 可用空间 | ≥ 20GB | 29GB | ✅ |
| 数据目录挂载 | / 分区 | / 分区 | ✅ |

> ⚠️ **注意**: 总磁盘 40GB 略低于建议的 50GB。当前可用 29GB，可支撑初期运行。
> 建议：若知识库数据量大幅增长，考虑扩容或清理不必要文件。

---

## 四、内存检查

| 检查项 | 要求 | 实际值 | 状态 |
|--------|------|--------|------|
| 总内存 | ≥ 4GB（建议） | 1.6GB | ⚠️ |
| 可用内存 | ≥ 1GB | 871MB | ⚠️ |

> ⚠️ **注意**: 内存 1.6GB 低于建议值。Dify 运行可能偏慢，建议：
> - 减少同时运行的容器数量
> - 或考虑升级服务器配置（2GB+ 内存）
> - 配置 swap 空间作为缓冲

---

## 五、网络连通性检查

| 检查项 | 目标 | 状态 |
|--------|------|------|
| 外网连通 | 8.8.8.8 ping | ✅ 正常 |
| DeepSeek API | api.deepseek.com | ✅ 可达 |
| Docker Registry | Docker Hub | ✅ 可访问 |
| 阿里云镜像 | registry.aliyuncs.com | ✅ 已配置 |

---

## 六、端口占用检查

| 端口 | 用途 | 占用状态 |
|------|------|---------|
| 80 | HTTP / Nginx | ✅ 空闲 |
| 443 | HTTPS | ✅ 空闲 |
| 5001 | Dify API | ✅ 空闲 |
| 5173 | Dify WebUI | ✅ 空闲 |
| 5432 | PostgreSQL | ✅ 空闲 |
| 6379 | Redis | ✅ 空闲 |
| 8080 | Weaviate | ✅ 空闲 |

---

## 七、目录结构创建

| 目录 | 用途 | 状态 |
|------|------|------|
| `/opt/dify/` | 主部署目录 | ✅ 已创建 |
| `/opt/dify/data_prep/` | JSONL数据文件 | ✅ 已创建 |
| `/data/dify/postgres/` | PostgreSQL数据持久化 | ✅ 已创建 |
| `/data/dify/redis/` | Redis数据持久化 | ✅ 已创建 |
| `/data/dify/weaviate/` | Weaviate向量数据 | ✅ 已创建 |
| `/data/dify/storage/` | 文件存储 | ✅ 已创建 |
| `/data/dify/logs/` | 日志文件 | ✅ 已创建 |

---

## 八、配置文件上传状态

| 文件 | 远程路径 | 大小 | 状态 |
|------|---------|------|------|
| docker-compose.yml | /opt/dify/docker-compose.yml | 5.4KB | ✅ |
| .env (模板) | /opt/dify/.env | 4.8KB | ✅ |
| nginx.conf | /opt/dify/nginx.conf | 7.1KB | ✅ |
| server_deployment_script.sh | /opt/dify/ | 7.8KB | ✅ |
| deploy_start.sh | /opt/dify/ | 6.2KB | ✅ |

---

## 九、数据文件上传状态

| 文件 | 远程路径 | 记录数 | 状态 |
|------|---------|--------|------|
| templates_import.jsonl | /opt/dify/data_prep/ | 151条 | ✅ |
| dictionary_unified.jsonl | /opt/dify/data_prep/ | 534条 | ✅ |
| corpus_segments.jsonl | /opt/dify/data_prep/ | 615条 | ✅ |
| corpus_documents.jsonl | /opt/dify/data_prep/ | 285条 | ✅ |
| corpus_paragraphs.jsonl | /opt/dify/data_prep/ | 330条 | ✅ |

---

## 十、docker-compose.yml 语法验证

```
cd /opt/dify && docker compose config > /dev/null 2>&1
结果: ✅ 语法正确，配置有效
```

---

## ⚠️ 待办事项（需要手动完成）

### 必须完成（Task 6.3/6.4 前）

1. **设置 DeepSeek API 密钥**
   ```bash
   ssh root@47.90.148.108
   nano /opt/dify/.env
   # 找到 DEEPSEEK_API_KEY= 行，填入真实的 API 密钥
   ```

2. **（可选）配置 swap 扩展内存**
   ```bash
   # 创建 2GB swap（缓解内存不足）
   fallocate -l 2G /swapfile
   chmod 600 /swapfile
   mkswap /swapfile
   swapon /swapfile
   echo '/swapfile none swap sw 0 0' >> /etc/fstab
   ```

---

## 任务完成标准对照

| 完成标准 | 状态 |
|---------|------|
| ✅ Docker & Docker Compose 正常运行 | **已达成** |
| ✅ 服务器网络连通性验证通过 | **已达成** |
| ✅ 磁盘空间检查（可用 29GB） | **已达成（有⚠️）** |
| ✅ 配置文件全部上传到服务器 | **已达成** |
| ⏳ DeepSeek API 密钥填入 .env | **待手动完成** |

---

## 下一步

Task 6.1 完成后，直接执行：

```bash
# SSH 到服务器
ssh root@47.90.148.108

# 1. 先填入 API 密钥
nano /opt/dify/.env
# DEEPSEEK_API_KEY=sk-your-actual-key

# 2. 启动 Dify 系统（Task 6.3）
cd /opt/dify
bash deploy_start.sh
```

---

**报告生成时间**: 2026-03-16
**Task 6.1 状态**: ✅ 完成（核心工作已完成，待填入API密钥）
