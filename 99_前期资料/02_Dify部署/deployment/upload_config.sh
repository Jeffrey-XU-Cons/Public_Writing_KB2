#!/bin/bash

#################################################################
# 配置文件远程上传脚本
# 用途: 将必要配置文件上传到阿里云服务器
#################################################################

# 配置
SERVER_IP="47.90.148.108"
SERVER_USER="root"
DEPLOY_DIR="/opt/dify"
DATA_PREP_DIR="/opt/dify/data_prep"

# 色彩定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========== Dify 配置文件上传脚本 ==========${NC}"
echo "服务器: $SERVER_IP"
echo "部署目录: $DEPLOY_DIR"
echo ""

# 检查本地文件是否存在
echo -e "${BLUE}[检查本地文件]${NC}"

files_to_upload=(
    "docker-compose.yml:$DEPLOY_DIR/"
    ".env.template:$DEPLOY_DIR/.env"
    "nginx.conf:$DEPLOY_DIR/"
)

jsonl_files=(
    "data_prep/templates_import.jsonl"
    "data_prep/dictionary_unified.jsonl"
    "data_prep/corpus_segments.jsonl"
    "data_prep/corpus_documents.jsonl"
    "data_prep/corpus_paragraphs.jsonl"
)

# 检查主配置文件
all_exist=true
for file_entry in "${files_to_upload[@]}"; do
    IFS=':' read -r source_file _ <<< "$file_entry"
    if [ -f "$source_file" ]; then
        echo -e "${GREEN}✓${NC} $source_file 存在"
    else
        echo -e "${RED}✗${NC} $source_file 不存在"
        all_exist=false
    fi
done

# 检查数据文件
for jsonl_file in "${jsonl_files[@]}"; do
    if [ -f "$jsonl_file" ]; then
        size_kb=$(du -h "$jsonl_file" | cut -f1)
        echo -e "${GREEN}✓${NC} $jsonl_file ($size_kb)"
    else
        echo -e "${RED}✗${NC} $jsonl_file 不存在"
    fi
done

if [ "$all_exist" = false ]; then
    echo -e "${RED}错误: 部分文件不存在，请先检查${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}[准备上传]${NC}"

# 创建远程目录
echo "1. 创建远程目录..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOY_DIR $DATA_PREP_DIR && chown -R root:root $DEPLOY_DIR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 远程目录创建成功${NC}"
else
    echo -e "${RED}✗ 无法连接到服务器，请检查 SSH 配置${NC}"
    exit 1
fi

# 上传主配置文件
echo ""
echo "2. 上传主配置文件..."
for file_entry in "${files_to_upload[@]}"; do
    IFS=':' read -r source_file remote_path <<< "$file_entry"
    echo -n "  上传 $source_file ... "
    scp "$source_file" $SERVER_USER@$SERVER_IP:"$remote_path"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
done

# 上传数据文件
echo ""
echo "3. 上传知识库数据文件..."
for jsonl_file in "${jsonl_files[@]}"; do
    if [ -f "$jsonl_file" ]; then
        echo -n "  上传 $(basename $jsonl_file) ... "
        scp "$jsonl_file" $SERVER_USER@$SERVER_IP:"$DATA_PREP_DIR/"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
done

# 上传部署脚本
echo ""
echo "4. 上传部署脚本..."

if [ -d "deployment" ]; then
    echo -n "  上传 deployment/* ... "
    scp deployment/*.sh $SERVER_USER@$SERVER_IP:"$DEPLOY_DIR/"
    ssh $SERVER_USER@$SERVER_IP "chmod +x $DEPLOY_DIR/*.sh"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
fi

# 验证远程文件
echo ""
echo -e "${BLUE}[验证远程文件]${NC}"
echo "远程文件列表:"
ssh $SERVER_USER@$SERVER_IP "ls -lh $DEPLOY_DIR/ | grep -E '\.(yml|sh|conf|env)'" || true
echo ""
ssh $SERVER_USER@$SERVER_IP "ls -lh $DATA_PREP_DIR/ | grep '.jsonl'" || true

echo ""
echo -e "${GREEN}========== 上传完成 ==========${NC}"
echo ""
echo "后续步骤:"
echo "1. SSH 登录服务器: ssh root@$SERVER_IP"
echo "2. 编辑环境配置: nano $DEPLOY_DIR/.env"
echo "   (必须设置 DEEPSEEK_API_KEY)"
echo "3. 运行部署脚本: bash $DEPLOY_DIR/server_deployment_script.sh"
echo "4. 运行启动脚本: bash $DEPLOY_DIR/deploy_start.sh"
echo ""
