#!/bin/bash

#################################################################
# Dify 系统启动脚本
# 要求: 已完成 server_deployment_script.sh
#################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
# 初始化
#################################################################

DEPLOY_DIR="/opt/dify"
DATA_DIR="/data/dify"

if [ ! -d "$DEPLOY_DIR" ]; then
    log_error "部署目录不存在: $DEPLOY_DIR"
    log_info "请先运行: server_deployment_script.sh"
    exit 1
fi

cd "$DEPLOY_DIR"

#################################################################
# 第一步: 验证 .env 配置
#################################################################

log_info "========== Phase 1: 验证环境配置 =========="

if [ ! -f ".env" ]; then
    log_error ".env 文件不存在"
    exit 1
fi

# 检查必要的环境变量
check_env_var() {
    local var=$1
    if grep -q "^${var}=" .env || grep -q "^${var}=" .env.template; then
        local value=$(grep "^${var}=" .env | cut -d'=' -f2- || echo "未设置")
        if [ "$value" = "未设置" ]; then
            log_warn "$var 未设置，可能影响功能"
            return 1
        else
            log_success "$var 已配置"
            return 0
        fi
    fi
}

if grep -q "DEEPSEEK_API_KEY" .env; then
    KEY_VALUE=$(grep "DEEPSEEK_API_KEY" .env | cut -d'=' -f2)
    if [ -z "$KEY_VALUE" ] || [ "$KEY_VALUE" = "your_deepseek_api_key_here" ]; then
        log_error "DEEPSEEK_API_KEY 未正确设置！"
        log_info "请编辑 .env 文件并设置真实的 API 密钥"
        exit 1
    else
        log_success "DEEPSEEK_API_KEY 已配置"
    fi
fi

#################################################################
# 第二步: 启动 Docker 容器
#################################################################

log_info "========== Phase 2: 启动 Docker 容器 =========="

log_info "拉取最新镜像..."
docker-compose pull 2>&1 | grep -E "(Pulling|Downloaded|Digest)" || true

log_info "启动所有容器..."
docker-compose up -d

log_success "容器启动命令已执行"

#################################################################
# 第三步: 等待容器初始化
#################################################################

log_info "========== Phase 3: 等待容器初始化 =========="

# 等待 PostgreSQL 启动
log_info "等待 PostgreSQL 就绪..."
POSTGRES_READY=0
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        log_success "PostgreSQL 已就绪"
        POSTGRES_READY=1
        break
    fi
    echo -n "."
    sleep 2
done

if [ $POSTGRES_READY -eq 0 ]; then
    log_warn "PostgreSQL 初始化超时"
fi

# 等待 Redis 启动
log_info "等待 Redis 就绪..."
REDIS_READY=0
for i in {1..30}; do
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis 已就绪"
        REDIS_READY=1
        break
    fi
    echo -n "."
    sleep 2
done

if [ $REDIS_READY -eq 0 ]; then
    log_warn "Redis 初始化超时"
fi

# 等待 Weaviate 启动
log_info "等待 Weaviate 就绪..."
for i in {1..30}; do
    if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
        log_success "Weaviate 已就绪"
        break
    fi
    echo -n "."
    sleep 2
done

sleep 10

#################################################################
# 第四步: 容器验证
#################################################################

log_info "========== Phase 4: 容器状态检查 =========="

docker-compose ps

# 检查容器是否都在运行
if docker-compose ps | grep -q "Exit"; then
    log_error "有容器异常退出，请查看日志"
    docker-compose logs
    exit 1
fi

#################################################################
# 第五步: 健康检查
#################################################################

log_info "========== Phase 5: 系统健康检查 =========="

# 检查 Dify API
log_info "检查 Dify API..."
for i in {1..30}; do
    if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
        API_HEALTH=$(curl -s http://localhost:5001/api/health)
        log_success "Dify API 响应: $API_HEALTH"
        break
    fi
    echo -n "."
    sleep 2
done

# 检查 WebUI
log_info "检查 Dify WebUI..."
if curl -s http://localhost/studio > /dev/null 2>&1; then
    log_success "WebUI 可访问"
else
    log_warn "WebUI 暂无响应，可能仍在初始化"
fi

# 检查 Weaviate
log_info "检查 Weaviate..."
if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
    log_success "Weaviate 就绪"
fi

#################################################################
# 第六步: 日志导出
#################################################################

log_info "========== Phase 6: 记录系统日志 =========="

log_file="startup_logs_$(date +%Y%m%d_%H%M%S).txt"
log_info "导出日志到: $log_file"

{
    echo "======== Docker Compose 状态 ========"
    docker-compose ps
    echo ""
    echo "======== 容器日志 ========"
    docker-compose logs --tail=50
} > "$log_file"

log_success "日志已保存: $log_file"

#################################################################
# 第七步: 完成提示
#################################################################

log_info "========== 启动完成 =========="

echo ""
log_success "✓ Dify 系统启动成功！"
echo ""
echo "访问地址:"
echo "  WebUI: http://47.90.148.108/studio"
echo "  API: http://47.90.148.108:5001"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f dify-api"
echo "  停止系统: docker-compose down"
echo "  重启系统: docker-compose restart"
echo "  进入容器: docker-compose exec dify-api bash"
echo ""
echo "下一步:"
echo "  1) 打开 WebUI 创建默认管理员账户"
echo "  2) 配置 LLM (DeepSeek) 和向量化模型"
echo "  3) 创建知识库并导入数据"
echo ""
