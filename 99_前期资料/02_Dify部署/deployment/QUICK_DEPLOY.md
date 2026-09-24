# ⚡ Task 6.1 快速执行指南

**目标**: 部署 Dify 系统到阿里云服务器 47.90.148.108

**预计时间**: 60 分钟

---

## 📌 三步快速部署

### 步骤 1: 上传配置文件 (10 分钟)

**在本地机器执行:**

```powershell
# PowerShell 方式（Windows）
cd d:\projects\Public_Writing_KB
.\deployment\upload_config.ps1

# 或 Git Bash
bash deployment/upload_config.sh
```

✅ **检查点**: 所有文件上传成功，看到"上传完成"提示

---

### 步骤 2: 远程环境检查与启动 (30 分钟)

**SSH 登录服务器:**

```bash
ssh root@47.90.148.108
cd /opt/dify
```

**运行检查脚本:**

```bash
chmod +x server_deployment_script.sh deploy_start.sh
bash server_deployment_script.sh
```

✅ **检查点**: 脚本完成，无重大错误

---

### 步骤 3: 远程系统启动 (20 分钟)

**编辑环境配置:**

```bash
nano .env
```

**必须设置的项** (找到并修改):

```
DEEPSEEK_API_KEY=sk_xxxxxxxxxxxx  # ← 必须设置！
POSTGRES_PASSWORD=YourStrongPassword123!  # 自定义强密码
REDIS_PASSWORD=YourRedisPassword456!
```

**保存** (Ctrl+O, Enter, Ctrl+X)

---

**启动系统:**

```bash
bash deploy_start.sh
```

✅ **检查点**: 看到"✓ Dify 系统启动成功！"并显示访问地址

---

## 🎯 验证成功

打开浏览器访问:

```
http://47.90.148.108/studio
```

或使用 SSH 端口转发:

```bash
ssh -L 8080:localhost:80 root@47.90.148.108
# 浏览器访问: http://localhost:8080/studio
```

**首次使用**:
1. 设置管理员邮箱
2. 设置管理员密码
3. 完成初始化

---

## 📝 完整步骤清单

### 本地准备 (5分钟)

- [ ] 确认 docker-compose.yml 存在
- [ ] 确认 .env.template 存在
- [ ] 确认 nginx.conf 存在
- [ ] 确认 data_prep/*.jsonl 文件存在（6个文件）
- [ ] 确认 deployment/*.sh 脚本存在（3个脚本）

### SSH 连接

- [ ] 可以 SSH 登录: `ssh root@47.90.148.108`
- [ ] 系统版本是 Ubuntu 24.04

### 文件上传

- [ ] 执行上传脚本成功
- [ ] 远程 /opt/dify 目录包含所有配置文件
- [ ] 远程 /opt/dify/data_prep 包含所有 JSONL 文件

### 环境检查

```bash
ssh root@47.90.148.108
cd /opt/dify

# 运行:
bash server_deployment_script.sh
```

- [ ] 系统版本: Ubuntu 24.04 LTS ✓
- [ ] 磁盘空间: ≥50GB ✓
- [ ] Docker 已安装 ✓
- [ ] Docker Compose 已安装 ✓
- [ ] 网络连接正常 ✓
- [ ] 无关键端口冲突 ✓

### 配置与启动

- [ ] 编辑 .env，设置 DEEPSEEK_API_KEY
- [ ] 编辑 .env，设置强密码 (POSTGRES, REDIS)
- [ ] 运行: `bash deploy_start.sh`
- [ ] 所有容器状态显示 "Up"
- [ ] API 响应正常: `curl http://localhost:5001/api/health`

### WebUI 验证

- [ ] 可以访问 http://47.90.148.108/studio
- [ ] 可以创建管理员账户
- [ ] 登录成功

---

## 🆘 常见问题

### Q: 上传脚本失败
A: 确保已安装 SSH 和 SCP，或使用手动上传:
```bash
scp docker-compose.yml root@47.90.148.108:/opt/dify/
# 逐个上传其他文件...
```

### Q: 无法连接 SSH
A: 检查阿里云密钥对配置或 IP 地址是否正确

### Q: Docker 镜像拉取超时
A: 配置阿里云镜像加速（见完整部署指南）

### Q: 端口已被占用
A: 停止现有服务:
```bash
systemctl stop nginx  # 如果在运行 Nginx
systemctl stop xray   # 如果在运行 Xray
```

### Q: 内存或磁盘不足
A: 删除不需要的镜像或数据，或升级服务器配置

---

## 📚 详细文档

更多信息请查看: [DEPLOYMENT_GUIDE_v2.md](./DEPLOYMENT_GUIDE_v2.md)

---

## ✨ 完成后的下一步

Task 6.1 完成后:

1. **Task 6.3** - Dify 系统启动和容器健康检查
   - 验证所有服务就绪
   - 测试 API 调用

2. **Task 6.4** - LLM/向量化/Weaviate 配置
   - 在 WebUI 配置 DeepSeek API
   - 配置向量化模型
   - 测试混合检索

3. **Task 7.x** - 知识库导入
   - 导入 Prompt 模板库（151个）
   - 导入词典库（534个）
   - 导入语料库（814项）

---

**当前状态**: 🟡 等待执行  
**优先级**: 🔴 高（阻挡其他所有任务）  
**工时**: 4小时  
**最后更新**: 2026-03-16
