#!/usr/bin/env bash
set -euo pipefail

# Multi-architecture CLI build script for MiMinions
# Supports ARM64, x86_64, and universal binaries on macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create architecture-specific spec file
create_spec_for_arch() {
    local arch="$1"
    local spec_file="miminions-cli-${arch}.spec"

    cat > "$spec_file" << EOF
# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(SPEC), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Core dependencies
        'miminions',
        'miminions.cli',
        'miminions.interface.cli.main',
        'miminions.interface.cli.gateway',
        'miminions.core.gateway',
        'miminions.core.gateway.bus',
        'miminions.core.gateway.events',
        'miminions.core.gateway.orchestrator',
        'miminions.core.gateway.session',
        'miminions.core.gateway.services',
        'miminions.core.gateway.channel',
        # Pydantic AI and related
        'pydantic_ai',
        'pydantic_ai.agent',
        'pydantic_ai.models',
        'pydantic_ai.tools',
        # Click and CLI
        'click',
        'click.core',
        'click.formatting',
        'click.parser',
        'click.termui',
        'click.types',
        'click.utils',
        # Async and networking
        'asyncio',
        'uvloop',
        'aiohttp',
        'httpx',
        # Data processing
        'numpy',
        'numpy.core',
        'numpy.lib',
        'sentence_transformers',
        'transformers',
        'torch',
        'torch.nn',
        'torch.nn.functional',
        # Database and vector stores
        'sqlite3',
        'faiss',
        'faiss.swigfaiss',
        # MCP and FastMCP
        'mcp',
        'mcp.server',
        'mcp.server.fastmcp',
        'fastmcp',
        # Logging and utilities
        'logfire',
        'logfire.integrations.pydantic',
        'werkzeug',
        'werkzeug.utils',
        'werkzeug.security',
        # Auth and security
        'authlib',
        'authlib.integrations.base_client',
        'authlib.integrations.httpx_client',
        'jwt',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
        # File processing
        'pdfplumber',
        'pdfplumber.page',
        'PIL',
        'PIL.Image',
        # Web and HTTP
        'starlette',
        'starlette.applications',
        'starlette.responses',
        'starlette.routing',
        'urllib3',
        'urllib3.util',
        'urllib3.connection',
        # Additional utilities
        'filelock',
        'python_multipart',
        'python_multipart.multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules
        'pytest',
        'pytest_asyncio',
        'pytest_cov',
        '_pytest',
        'unittest',
        # Exclude development tools
        'setuptools',
        'pip',
        'wheel',
        'build',
        # Exclude unnecessary stdlib modules for size
        'tkinter',
        'turtle',
        'turtledemo',
        'idlelib',
        'test',
        'tests',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='miminions-cli-${arch}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='${arch}',
    codesign_identity=None,
    entitlements_file=None,
)
EOF

    print_status "Created spec file: $spec_file"
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

# Detect current architecture
detect_arch() {
    case "$(uname -m)" in
        arm64|aarch64)
            echo "arm64"
            ;;
        x86_64|amd64)
            echo "x86_64"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Check if we're on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS. For Linux/Windows, use separate build environments."
        exit 1
    fi
}

# Build for specific architecture
build_for_arch() {
    local arch="$1"
    local output_name="miminions-cli-${arch}"

    print_status "Building for architecture: $arch"

    # Set environment variables for cross-compilation
    case "$arch" in
        arm64)
            export PYINSTALLER_TARGET_ARCH="arm64"
            ;;
        x86_64)
            export PYINSTALLER_TARGET_ARCH="x86_64"
            # On ARM64 macOS, this requires Rosetta
            if [[ "$(detect_arch)" == "arm64" ]]; then
                print_warning "Building x86_64 on ARM64 macOS requires Rosetta 2"
                print_warning "Make sure Rosetta 2 is installed: softwareupdate --install-rosetta"
            fi
            ;;
        *)
            print_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac

    # Sync dependencies
    uv sync --extra cli-build

# Build with PyInstaller using spec file
    # Create architecture-specific spec file
    create_spec_for_arch "$arch"

    uv run pyinstaller \
        --clean \
        --noconfirm \
        "miminions-cli-${arch}.spec"

    print_success "Built binary: dist/$output_name"
}

# Create universal binary (macOS only)
create_universal_binary() {
    local arm64_binary="dist/miminions-cli-arm64"
    local x86_64_binary="dist/miminions-cli-x86_64"
    local universal_binary="dist/miminions-cli"

    if [[ -f "$arm64_binary" && -f "$x86_64_binary" ]]; then
        print_status "Creating universal binary..."
        lipo -create -output "$universal_binary" "$arm64_binary" "$x86_64_binary"
        print_success "Universal binary created: $universal_binary"
    else
        print_warning "Cannot create universal binary - missing architecture binaries"
        print_warning "Available binaries:"
        ls -la dist/miminions-cli-* 2>/dev/null || true
    fi
}

# Main build function
main() {
    local build_arch="${1:-}"
    local current_arch
    current_arch="$(detect_arch)"

    check_macos

    print_status "MiMinions CLI Multi-Architecture Build"
    print_status "Current architecture: $current_arch"

    # Clean previous builds
    rm -rf build dist *.spec

    case "$build_arch" in
        "")
            # Build for current architecture only
            print_status "Building for current architecture: $current_arch"
            build_for_arch "$current_arch"
            mv "dist/miminions-cli-${current_arch}" "dist/miminions-cli"
            ;;
        "universal")
            # Build universal binary (ARM64 + x86_64)
            print_status "Building universal binary (ARM64 + x86_64)"
            build_for_arch "arm64"
            build_for_arch "x86_64"
            create_universal_binary
            ;;
        "arm64"|"x86_64")
            # Build for specific architecture
            build_for_arch "$build_arch"
            ;;
        "all")
            # Build for both architectures separately
            print_status "Building for all architectures"
            build_for_arch "arm64"
            build_for_arch "x86_64"
            ;;
        *)
            print_error "Usage: $0 [arm64|x86_64|universal|all]"
            print_error "  (no arg) - build for current architecture"
            print_error "  arm64    - build for ARM64 only"
            print_error "  x86_64   - build for x86_64 only"
            print_error "  universal- build universal binary (ARM64 + x86_64)"
            print_error "  all      - build separate binaries for all architectures"
            exit 1
            ;;
    esac

    print_success "Build completed!"
    print_status "Output location: $PROJECT_DIR/dist/"
    ls -la dist/miminions-cli* 2>/dev/null || true
}

# Run main function with all arguments
main "$@"