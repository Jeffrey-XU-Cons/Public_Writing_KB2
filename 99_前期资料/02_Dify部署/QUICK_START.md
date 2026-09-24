# 🚀 快速参考指南

## 立即可执行的操作

### ✅ 本地已完成

```bash
# 查看数据准备结果
cd data_prep/
dir *.jsonl          # 查看所有生成的JSONL文件
type validation_report.json  # 查看验证报告
```

**数据统计：**
- ✅ 模板库：151个（72 KB）
- ✅ 词典库：534个（116 KB）
- ✅ 语料库：615项（304 KB）
- ✅ 验证通过率：100%

---

## ⏳ 下一步行动

### 1️⃣ 准备服务器（1-2天）

```bash
# 在阿里云服务器上执行：
ssh root@your-server-ip

# 安装Docker
curl -fsSL https://get.docker.com | sh

# 验证
docker --version  # 应该 >= 24.0
```

### 2️⃣ 上传配置文件（1小时）

```bash
# 从本地机器：
scp docker-compose.yml root@server:/opt/dify/
scp .env.template root@server:/opt/dify/
scp nginx.conf root@server:/opt/dify/
scp data_prep/*.jsonl root@server:/opt/dify/data_prep/
```

### 3️⃣ 启动系统（30分钟）

```bash
# 在服务器上：
cd /opt/dify

# 配置环境变量
cp .env.template .env
nano .env  # 编辑并设置：
  # - DEEPSEEK_API_KEY（必须！）
  # - POSTGRES_PASSWORD
  # - REDIS_PASSWORD
  # - WEAVIATE_API_KEY

# 创建数据目录
mkdir -p /data/dify/{postgres,redis,weaviate,storage,logs}

# 启动容器
docker-compose up -d

# 验证
docker-compose ps       # 应显示所有容器 "Up"
curl http://localhost:5001/api/health
```

### 4️⃣ 导入知识库（2-3小时）

1. 打开 http://your-server-ip/studio
2. 创建知识库并导入 data_prep/ 下的JSONL文件
3. 等待向量化完成

---

## 🔧 常用命令

### Docker相关
```bash
# 查看容器日志
docker-compose logs dify-api

# 重启某个容器
docker-compose restart dify-api

# 进入容器
docker-compose exec dify-api bash

# 停止所有服务
docker-compose down

# 启动所有服务  
docker-compose up -d
```

### 数据库操作
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U postgres dify > backup.sql

# 恢复数据库
docker-compose exec postgres psql -U postgres dify < backup.sql

# 查看数据库大小
docker-compose exec postgres psql -U postgres -d dify -c "\l"
```

### 监控
```bash
# 实时监控容器资源
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

---

## 📋 检查清单

### 前置条件
- [ ] 获取DeepSeek API密钥
- [ ] 服务器SSH连接正常
- [ ] 至少100GB磁盘空间
- [ ] 至少8GB内存

### 部署前
- [ ] 已编辑.env文件（设置所有密钥）
- [ ] 已上传所有配置文件到服务器
- [ ] 已创建/data/dify目录
- [ ] 已备份原有数据（如有）

### 部署后
- [ ] [ ] 所有容器状态为"Up"
- [ ] [ ] API健康检查通过
- [ ] [ ] WebUI可访问
- [ ] [ ] 知识库导入成功

---

## 🎯 关键时间表

| 步骤 | 预计时间 | 关键点 |
|------|---------|--------|
| 准备服务器 | 2-4小时 | Docker安装/验证 |
| 上传文件 | 1小时 | 检查SCP连接 |
| 启动系统 | 10-15分钟 | 等待容器初始化 |
| 知识库导入 | 30-60分钟 | 向量化处理 |
| Agent工作流开发 | 40-80小时 | 主要开发工作 |
| 集成测试 | 20-30小时 | 验证质量 |
| **总计** | **6周** | 完整项目周期 |

---

## ⚠️ 常见问题速查

**Q: DeepSeek API连接失败？**
```
A: 1. 检查API密钥是否正确
   2. 检查网络连接：curl api.deepseek.com
   3. 查看日志：docker-compose logs dify-api
```

**Q: 容器无法启动？**
```
A: 1. 检查磁盘空间：df -h
   2. 检查内存：free -h
   3. 查看错误：docker-compose logs
   4. 重建镜像：docker-compose build --no-cache
```

**Q: 向量化很慢？**
```
A: 1. 检查Weaviate内存：docker stats weaviate
   2. 增加批处理大小：编辑.env中的EMBEDDING_BATCH_SIZE
   3. 分批导入知识库
```

**Q: WebUI访问不了？**
```
A: 1. 检查Nginx：docker-compose logs nginx
   2. 检查防火墙：sudo iptables -L (或在阿里云安全组)
   3. 检查地址：http://server-ip 而不是 localhost
```

---

## 📚 详细文档位置

| 内容 | 文件 | 用途 |
|------|------|------|
| 完整任务规划 | 详细项目任务.md | 了解所有24个任务 |
| 逐步部署 | DEPLOYMENT_GUIDE.md | 分阶段部署说明 |
| Docker配置 | docker-compose.yml | 容器编排 |
| 环境变量 | .env.template | 配置参考 |
| 反向代理 | nginx.conf | Web服务器配置 |

---

## 💡 建议

1. **首次部署**：按DEPLOYMENT_GUIDE.md逐步执行，不要跳步
2. **错误处理**：遇到错误先查看Docker日志，再查常见问题
3. **性能测试**：部署完成后运行基准测试（详见详细任务文档）
4. **监控**：生产环境配置告警，定期检查日志
5. **备份**：定期备份PostgreSQL和Weaviate数据

---

## 📞 支持与帮助

- 🔍 查看日志：`docker-compose logs -f service-name`
- 📖 完整文档：见各个.md文件
- ❓ 常见问题：详见DEPLOYMENT_GUIDE.md Q&A部分

---

**准备好了吗？开始部署！** 🚀

下一步：`scp docker-compose.yml 你的服务器`
