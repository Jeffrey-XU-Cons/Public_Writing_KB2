#!/bin/bash
#################################################################
# Dify 最小化启动脚本（针对低内存服务器 <2GB）
# 策略：先启动基础组件，等稳定后再启动 Web/Worker
#################################################################

set -e
DEPLOY_DIR="/opt/dify"
cd "$DEPLOY_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }

echo ""
log_info "====== Dify 分阶段启动（低内存模式）======"
log_info "当前内存状态:"
free -m | grep -E 'Mem|Swap'
echo ""

# ── 阶段1：先启动基础数据服务 ──────────────────────────────
log_info "阶段1: 启动 PostgreSQL + Redis + Weaviate"
docker compose up -d postgres redis weaviate
log_success "基础数据服务已启动"

log_info "等待 PostgreSQL 就绪 (最多60秒)..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        log_success "PostgreSQL 已就绪 (${i}次检查)"
        break
    fi
    sleep 2
done

log_info "等待 Redis 就绪..."
for i in $(seq 1 20); do
    if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        log_success "Redis 已就绪"
        break
    fi
    sleep 2
done

echo ""
log_info "阶段1 内存状态:"
free -m | grep -E 'Mem|Swap'
echo ""

# ── 阶段2：启动 Dify API ──────────────────────────────────
log_info "阶段2: 启动 Dify API"
docker compose up -d dify-api
log_info "等待 Dify API 就绪 (最多120秒)..."
for i in $(seq 1 60); do
    if curl -s http://localhost:5001/api/health 2>/dev/null | grep -q ok; then
        log_success "Dify API 已就绪 (${i}次检查)"
        break
    fi
    sleep 2
done

echo ""
log_info "阶段2 内存状态:"
free -m | grep -E 'Mem|Swap'
echo ""

# ── 阶段3：启动其余服务 ───────────────────────────────────
log_info "阶段3: 启动 Worker + Web + Nginx"
docker compose up -d dify-worker dify-web nginx
sleep 20

# ── 最终状态 ──────────────────────────────────────────────
log_info "====== 最终容器状态 ======"
docker compose ps

echo ""
log_info "====== 健康检查 ======"
API_STATUS=$(curl -s http://localhost:5001/api/health 2>/dev/null)
echo "  Dify API:   ${API_STATUS:-无响应}"
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/studio 2>/dev/null)
echo "  WebUI:      HTTP ${WEB_STATUS:-无响应}"
WEAV_STATUS=$(curl -s http://localhost:8080/v1/.well-known/ready 2>/dev/null)
echo "  Weaviate:   ${WEAV_STATUS:-无响应}"

echo ""
log_success "====== 启动完成 ======"
echo "  WebUI:  http://47.90.148.108/studio"
echo "  API:    http://47.90.148.108:5001"
