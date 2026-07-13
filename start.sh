#!/bin/bash
#
# Bank Audit RAG - 快速启动脚本
# 银行审计部智能检索问答系统
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                                 ║"
    echo "║     🏦   Bank Audit RAG - 银行审计部智能检索问答系统   🏦     ║"
    echo "║                                                                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 环境..."

    if ! command_exists python3; then
        print_error "未找到 python3，请先安装 Python 3.10+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "检测到 Python 版本: ${PYTHON_VERSION}"

    # 版本比较
    if python3 -c "import sys; exit(0) if sys.version_info >= (3, 10) else exit(1)"; then
        print_success "Python 版本符合要求 ✓"
    else
        print_error "需要 Python 3.10 或更高版本，当前版本: ${PYTHON_VERSION}"
        exit 1
    fi
}

# 检查 Poetry
check_poetry() {
    print_info "检查 Poetry 包管理器..."

    if command_exists poetry; then
        POETRY_VERSION=$(poetry --version | awk '{print $2}')
        print_info "检测到 Poetry 版本: ${POETRY_VERSION}"
        print_success "Poetry 已安装 ✓"
    else
        print_warning "未检测到 Poetry，正在安装..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        print_success "Poetry 安装完成 ✓"
    fi
}

# 检查环境变量配置
check_env_config() {
    print_info "检查环境变量配置..."

    if [ ! -f .env ]; then
        print_warning "未找到 .env 文件，正在从 .env.example 复制..."
        cp .env.example .env
        print_success "已创建 .env 文件 ✓"
        echo ""
        print_warning "⚠️  请配置 OpenAI API Key:"
        echo "   编辑 .env 文件，设置 ATRAG_OPENAI_API_KEY=your-api-key"
        echo ""
    else
        print_success ".env 文件已存在 ✓"

        # 检查是否配置了 API Key
        if grep -q "your-api-key-here" .env; then
            print_warning "检测到默认 API Key 配置，请记得修改为真实的 API Key"
        fi
    fi
}

# 创建数据目录
create_data_dirs() {
    print_info "创建数据目录..."

    mkdir -p data/chroma
    mkdir -p data/documents
    mkdir -p data/cache
    mkdir -p logs

    print_success "数据目录创建完成 ✓"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."

    if [ -d ".venv" ]; then
        print_info "检测到现有虚拟环境，跳过依赖安装（如需重新安装请删除 .venv 目录）"
    else
        poetry install --no-root
        print_success "依赖安装完成 ✓"
    fi
}

# 显示启动信息
show_startup_info() {
    echo ""
    print_info "启动信息:"
    echo ""
    echo -e "  ${CYAN}🌐 API 文档地址:${NC}  http://localhost:8080/docs"
    echo -e "  ${CYAN}🔍 Health 检查:${NC} http://localhost:8080/health"
    echo -e "  ${CYAN}📊 Metrics 端点:${NC} http://localhost:8080/metrics"
    echo ""
    echo -e "  ${CYAN}📁 项目目录:${NC} $(pwd)"
    echo -e "  ${CYAN}🔧 配置文件:${NC} $(pwd)/.env"
    echo ""
    echo -e "  ${YELLOW}⌨️  按 Ctrl+C 停止服务${NC}"
    echo ""
}

# 显示帮助信息
show_help() {
    print_header
    echo "用法: ./start.sh [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示此帮助信息"
    echo "  --check-only        仅检查环境，不启动服务"
    echo "  --no-deps           跳过依赖安装"
    echo "  --prod              生产模式启动"
    echo "  --docker            使用 Docker Compose 启动"
    echo ""
    echo "示例:"
    echo "  ./start.sh                    # 开发模式启动"
    echo "  ./start.sh --prod             # 生产模式启动"
    echo "  ./start.sh --docker           # Docker Compose 启动"
    echo "  ./start.sh --check-only       # 仅检查环境"
    echo ""
}

# 主程序
main() {
    local CHECK_ONLY=false
    local NO_DEPS=false
    local PROD_MODE=false
    local USE_DOCKER=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --no-deps)
                NO_DEPS=true
                shift
                ;;
            --prod)
                PROD_MODE=true
                shift
                ;;
            --docker)
                USE_DOCKER=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    print_header

    # 切换到脚本所在目录
    cd "$(dirname "$0")"

    # Docker 启动模式
    if [ "$USE_DOCKER" = true ]; then
        print_info "使用 Docker Compose 启动..."

        if ! command_exists docker-compose; then
            print_error "未找到 docker-compose，请先安装 Docker Compose"
            exit 1
        fi

        check_env_config
        docker-compose up -d

        echo ""
        print_success "Docker Compose 服务已启动 ✓"
        print_info "查看日志: docker-compose logs -f"
        print_info "停止服务: docker-compose down"
        exit 0
    fi

    # 环境检查
    check_python
    check_poetry
    check_env_config
    create_data_dirs

    # 安装依赖
    if [ "$NO_DEPS" = false ]; then
        install_dependencies
    fi

    # 仅检查模式
    if [ "$CHECK_ONLY" = true ]; then
        echo ""
        print_success "环境检查全部通过 ✓"
        print_info "运行 './start.sh' 启动服务"
        exit 0
    fi

    # 显示启动信息
    show_startup_info

    # 启动服务
    print_info "正在启动 Bank Audit RAG 服务..."

    if [ "$PROD_MODE" = true ]; then
        print_info "生产模式启动 (4 workers)..."
        export ATRAG_ENVIRONMENT=production
        poetry run uvicorn bank_audit_rag.api.main:app \
            --host 0.0.0.0 \
            --port 8080 \
            --workers 4 \
            --log-level info
    else
        print_info "开发模式启动 (自动重载)..."
        export ATRAG_ENVIRONMENT=development
        poetry run uvicorn bank_audit_rag.api.main:app \
            --host 0.0.0.0 \
            --port 8080 \
            --reload \
            --log-level debug
    fi
}

# 运行主程序
main "$@"
