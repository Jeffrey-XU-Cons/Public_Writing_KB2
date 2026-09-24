#!/usr/bin/env pwsh

#################################################################
# PowerShell 上传脚本 - 用于 Windows 系统
# 功能: 上传配置文件到阿里云服务器
#################################################################

# 配置
$ServerIP = "47.90.148.108"
$ServerUser = "root"
$DeployDir = "/opt/dify"
$DataPrepDir = "/opt/dify/data_prep"

# 色彩定义
function Write-Green($text) { Write-Host $text -ForegroundColor Green }
function Write-Red($text) { Write-Host $text -ForegroundColor Red }
function Write-Blue($text) { Write-Host $text -ForegroundColor Cyan }
function Write-Yellow($text) { Write-Host $text -ForegroundColor Yellow }

Write-Blue "========== Dify 配置文件上传脚本 (PowerShell) =========="
Write-Host "服务器: $ServerIP"
Write-Host "部署目录: $DeployDir"
Write-Host ""

# 检查本地文件
Write-Blue "[检查本地文件]"

$filesToUpload = @(
    @{source="docker-compose.yml"; target="$DeployDir/"},
    @{source=".env.template"; target="$DeployDir/.env"},
    @{source="nginx.conf"; target="$DeployDir/"}
)

$jsonlFiles = @(
    "data_prep/templates_import.jsonl",
    "data_prep/dictionary_unified.jsonl",
    "data_prep/corpus_segments.jsonl",
    "data_prep/corpus_documents.jsonl",
    "data_prep/corpus_paragraphs.jsonl"
)

$allExist = $true

foreach ($file in $filesToUpload) {
    if (Test-Path $file.source) {
        Write-Green "✓ $($file.source) 存在"
    } else {
        Write-Red "✗ $($file.source) 不存在"
        $allExist = $false
    }
}

foreach ($jsonl in $jsonlFiles) {
    if (Test-Path $jsonl) {
        $size = (Get-Item $jsonl).Length / 1KB
        Write-Green "✓ $jsonl ($([Math]::Round($size, 2)) KB)"
    } else {
        Write-Yellow "⚠ $jsonl 不存在"
    }
}

if (-not $allExist) {
    Write-Red "错误: 部分必要文件不存在"
    exit 1
}

Write-Host ""
Write-Blue "[准备上传]"

# 测试 SSH 连接
Write-Host "1. 测试 SSH 连接..."
try {
    ssh $ServerUser@$ServerIP "echo 'SSH连接正常'"
    Write-Green "✓ SSH 连接正常"
} catch {
    Write-Red "✗ 无法连接到服务器"
    exit 1
}

# 创建远程目录
Write-Host "2. 创建远程目录..."
ssh $ServerUser@$ServerIP "mkdir -p $DeployDir $DataPrepDir && chown -R root:root $DeployDir"
Write-Green "✓ 远程目录创建完成"

# 上传主配置文件
Write-Host "3. 上传主配置文件..."
foreach ($file in $filesToUpload) {
    Write-Host "  上传 $($file.source) ... " -NoNewline
    scp $file.source "$ServerUser@$ServerIP`:`$($file.target)"
    Write-Green "✓"
}

# 上传数据文件
Write-Host "4. 上传数据文件..."
foreach ($jsonl in $jsonlFiles) {
    if (Test-Path $jsonl) {
        Write-Host "  上传 $(Split-Path $jsonl -Leaf) ... " -NoNewline
        scp $jsonl "$ServerUser@$ServerIP`:`$DataPrepDir/"
        Write-Green "✓"
    }
}

# 上传脚本
Write-Host "5. 上传部署脚本..."
if (Test-Path "deployment") {
    Get-ChildItem deployment/*.sh | ForEach-Object {
        Write-Host "  上传 $($_.Name) ... " -NoNewline
        scp $_.FullName "$ServerUser@$ServerIP`:`$DeployDir/"
        Write-Green "✓"
    }
    ssh $ServerUser@$ServerIP "chmod +x $DeployDir/*.sh"
}

# 验证
Write-Host ""
Write-Blue "[验证远程文件]"
Write-Host "远程文件列表:"
ssh $ServerUser@$ServerIP "ls -lh $DeployDir/ | grep -E '\.(yml|sh|conf|env)'"

Write-Host ""
Write-Green "========== 上传完成 =========="
Write-Host ""
Write-Yellow "后续步骤:"
Write-Host "1. SSH 到服务器:   ssh root@$ServerIP"
Write-Host "2. 编辑 .env:     nano $DeployDir/.env"
Write-Host "3. 运行脚本:      bash $DeployDir/server_deployment_script.sh"
Write-Host "4. 启动系统:      bash $DeployDir/deploy_start.sh"
Write-Host ""
