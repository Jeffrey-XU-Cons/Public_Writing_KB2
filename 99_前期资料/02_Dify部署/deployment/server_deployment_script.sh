#!/bin/bash

#################################################################
# Dify 系统部署脚本
# 适用于: 阿里云 Ubuntu 24.04 LTS
# 服务器: 47.90.148.108
# 部署日期: 2026-03-16
#################################################################

set -e

# 色彩定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

#################################################################
# 第一步: 环境检查
#################################################################

log_info "========== Phase 1: 环境检查 =========="

# 检查系统版本
OS_VERSION=$(lsb_release -d | cut -f2)
log_info "系统版本: $OS_VERSION"

if [[ ! "$OS_VERSION" == *"24.04"* ]]; then
    log_warn "系统版本不是 Ubuntu 24.04，但脚本会继续尝试"
fi

# 检查磁盘空间
DISK_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
log_info "可用磁盘空间: ${DISK_SPACE}GB"

if [ "$DISK_SPACE" -lt 50 ]; then
    log_error "磁盘空间不足！需要至少 50GB，当前仅 ${DISK_SPACE}GB"
    read -p "是否继续? (y/n)" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
log_success "磁盘空间检查通过"

# 检查内存
MEMORY_MB=$(free -m | grep Mem | awk '{print $2}')
log_info "可用内存: ${MEMORY_MB}MB"

if [ "$MEMORY_MB" -lt 2048 ]; then
    log_warn "内存较少 (${MEMORY_MB}MB)，Dify 运行可能受影响"
fi
log_success "内存检查通过"

# 检查网络连接
log_info "检查网络连接..."
if ping -c 1 8.8.8.8 &> /dev/null; then
    log_success "外网连接正常"
else
    log_error "无法连接外网，部分操作可能失败"
fi

#################################################################
# 第二步: Docker 安装与验证
#################################################################

log_info "========== Phase 2: Docker 检查与安装 =========="

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker 已安装: $DOCKER_VERSION"
else
    log_warn "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    log_success "Docker 安装完成"
fi

# 检查 Docker Compose
if command -v docker-compose &> /dev/null; then
    DC_VERSION=$(docker-compose --version)
    log_success "Docker Compose 已安装: $DC_VERSION"
else
    log_warn "Docker Compose 未安装，正在使用 Docker plugin..."
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p $DOCKER_CONFIG/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
    log_success "Docker Compose 安装完成"
fi

# 测试 Docker 连接
if sudo docker ps &> /dev/null; then
    log_success "Docker 进程运行正常"
else
    log_error "无法访问 Docker daemon，请验证权限"
    exit 1
fi

#################################################################
# 第三步: 检查现有服务冲突
#################################################################

log_info "========== Phase 3: 检查端口占用 =========="

# 检查常用端口
check_port() {
    local port=$1
    local service=$2
    if ss -tlnp 2>/dev/null | grep -q ":$port "; then
        local process=$(ss -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}')
        log_warn "端口 $port 已被占用 ($service): $process"
        return 1
    else
        log_success "端口 $port 空闲 ($service)"
        return 0
    fi
}

check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 5001 "Dify API"
check_port 5173 "Dify WebUI"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 8080 "Weaviate"

# 提示用户处理 Nginx 冲突
if ps aux | grep -q "[n]ginx"; then
    log_warn "已检测到运行中的 Nginx 进程"
    log_info "选项:"
    log_info "1) 停止现有 Nginx 并使用 Dify 的 Nginx"
    log_info "2) 保持现有 Nginx，使用 Dify 的内部端口（需手动反向代理配置）"
    read -p "请选择 (1 或 2): " nginx_choice
    
    if [ "$nginx_choice" = "1" ]; then
        log_info "停止 Nginx..."
        sudo systemctl stop nginx
        sudo systemctl disable nginx || true
        log_success "Nginx 已停止"
    fi
fi

# 提示用户清理 Xray
if command -v xray &> /dev/null || ps aux | grep -q "[x]ray"; then
    log_warn "已检测到 Xray 服务，建议在部署前清理"
    log_info "执行: sudo systemctl stop xray && sudo systemctl disable xray"
fi

#################################################################
# 第四步: 创建部署目录
#################################################################

log_info "========== Phase 4: 创建目录结构 =========="

DEPLOY_DIR="/opt/dify"
DATA_DIR="/data/dify"

# 创建部署目录
if [ ! -d "$DEPLOY_DIR" ]; then
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown -R $USER:$USER "$DEPLOY_DIR"
    log_success "创建部署目录: $DEPLOY_DIR"
else
    log_warn "部署目录已存在: $DEPLOY_DIR"
fi

# 创建数据目录
sudo mkdir -p "$DATA_DIR"/{postgres,redis,weaviate,storage,logs}
sudo chown -R 999:999 "$DATA_DIR"
log_success "创建数据目录: $DATA_DIR"

# 显示目录结构
log_info "目录结构:"
tree -L 2 "$DATA_DIR" 2>/dev/null || find "$DATA_DIR" -maxdepth 2 | sort

#################################################################
# 第五步: 配置文件上传指导
#################################################################

log_info "========== Phase 5: 配置文件准备 =========="

log_info "需要上传以下文件到服务器"
log_info "从本地执行:"
echo ""
echo "  scp docker-compose.yml root@47.90.148.108:$DEPLOY_DIR/"
echo "  scp .env.template root@47.90.148.108:$DEPLOY_DIR/.env"
echo "  scp nginx.conf root@47.90.148.108:$DEPLOY_DIR/"
echo ""

if [ -f "$DEPLOY_DIR/docker-compose.yml" ]; then
    log_success "docker-compose.yml 已存在"
else
    log_warn "docker-compose.yml 未找到，请先上传"
fi

if [ -f "$DEPLOY_DIR/.env" ]; then
    log_success ".env 已存在"
else
    log_warn ".env 配置未找到"
fi

#################################################################
# 第六步: 验证配置文件
#################################################################

log_info "========== Phase 6: 验证配置 =========="

if [ -f "$DEPLOY_DIR/docker-compose.yml" ]; then
    log_info "验证 docker-compose.yml..."
    cd "$DEPLOY_DIR"
    if docker-compose config > /dev/null 2>&1; then
        log_success "docker-compose.yml 格式正确"
    else
        log_error "docker-compose.yml 格式有误，请检查"
        docker-compose config
        exit 1
    fi
else
    log_warn "跳过 docker-compose.yml 验证（文件不存在）"
fi

#################################################################
# 第七步: 系统状态报告
#################################################################

log_info "========== Phase 7: 环境检查完成 =========="

echo ""
log_success "✓ 环境检查通过"
echo ""
echo "系统信息:"
echo "  操作系统: $OS_VERSION"
echo "  磁盘空间: ${DISK_SPACE}GB"
echo "  内存大小: ${MEMORY_MB}MB"
echo "  Docker: $(docker --version)"
echo "  Docker Compose: $(docker-compose --version 2>&1 | head -1 || echo 'v2.x (plugin)')"
echo ""
echo "部署目录: $DEPLOY_DIR"
echo "数据目录: $DATA_DIR"
echo ""
echo "下一步:"
echo "  1) 上传配置文件到 $DEPLOY_DIR"
echo "  2) 编辑 .env 文件设置必要的环境变量"
echo "  3) 运行 deploy_start.sh 启动系统"
echo ""

log_success "准备工作完成！"
