#!/bin/bash
# install.sh - 将 segway-openclaw 的 skills 部署到 openclaw workspace
#
# 用法:
#   ./scripts/install.sh                    # 默认 workspace: ~/.openclaw/workspace
#   ./scripts/install.sh /path/to/workspace # 指定 workspace 路径
#
# 部署方式: 符号链接（symlink），修改仓库代码后 workspace 自动生效

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="${1:-$HOME/.openclaw/workspace}"

echo "=== Segway OpenClaw 安装 ==="
echo "仓库路径: $REPO_DIR"
echo "Workspace: $WORKSPACE"
echo ""

# 检查 workspace 存在
if [ ! -d "$WORKSPACE" ]; then
    echo "错误: workspace 目录不存在: $WORKSPACE"
    echo "请先运行 openclaw configure 初始化 workspace"
    exit 1
fi

SKILLS_DIR="$WORKSPACE/skills"
mkdir -p "$SKILLS_DIR"

# 链接共享模块
echo "[1/4] 链接共享模块..."
for module in segway_auth.py segway_resolve.py segway_output.py segway_confirm.py; do
    src="$REPO_DIR/skills/$module"
    dst="$SKILLS_DIR/$module"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "  备份已有文件: $dst -> $dst.bak"
        mv "$dst" "$dst.bak"
    fi
    ln -sf "$src" "$dst"
    echo "  ✓ $module"
done

# 链接 skill 目录
echo "[2/4] 链接 Segway skill..."
for skill in segway-area-map segway-robot segway-task-create segway-task-manage segway-box-control segway-delivery segway-webhook; do
    src="$REPO_DIR/skills/$skill"
    dst="$SKILLS_DIR/$skill"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "  备份已有目录: $dst -> $dst.bak"
        mv "$dst" "$dst.bak"
    fi
    ln -sf "$src" "$dst"
    echo "  ✓ $skill"
done

# 部署 workspace 模板（不覆盖已有文件）
echo "[3/4] 部署 workspace 配置..."
for file in AGENTS.md SOUL.md IDENTITY.md TOOLS.md; do
    src="$REPO_DIR/workspace/$file"
    dst="$WORKSPACE/$file"
    if [ -e "$dst" ]; then
        echo "  跳过（已存在）: $file"
    else
        cp "$src" "$dst"
        echo "  ✓ $file"
    fi
done

# 初始化用户文件（从 .example 复制）
for file in USER.md MEMORY.md; do
    dst="$WORKSPACE/$file"
    if [ ! -e "$dst" ]; then
        cp "$REPO_DIR/workspace/$file.example" "$dst"
        echo "  ✓ $file（从模板创建，请编辑填写）"
    else
        echo "  跳过（已存在）: $file"
    fi
done

mkdir -p "$WORKSPACE/memory"

# 配置 .env
echo "[4/4] 检查环境变量..."
ENV_FILE="$WORKSPACE/.env"
if [ ! -e "$ENV_FILE" ]; then
    cp "$REPO_DIR/.env.example" "$ENV_FILE"
    echo "  ✓ .env 已创建，请编辑填写 Segway API 凭据"
else
    echo "  跳过（已存在）: .env"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "后续步骤:"
echo "  1. 编辑 $ENV_FILE 填写 Segway API 凭据"
echo "  2. 编辑 $WORKSPACE/USER.md 填写你的信息"
echo "  3. 重启 openclaw 使 skill 生效"
