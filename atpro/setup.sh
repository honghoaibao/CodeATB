#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║           AT PRO v1.4.6 — SETUP SCRIPT                   ║
# ║   Cài đặt thông minh, đa môi trường, đa fallback                ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Hỗ trợ:                                                         ║
# ║   ✅ Ubuntu native                                               ║
# ║   ✅ Ubuntu proot-distro trong Termux                            ║
# ║   ✅ Termux trực tiếp (không qua proot)                          ║
# ║   ✅ Debian / Kali / Parrot (proot)                              ║
# ║   ✅ ARM64 / ARM32 / x86_64                                      ║
# ║   ✅ Root / Non-root / sudo                                       ║
# ║   ✅ Offline partial fallback                                     ║
# ║   ✅ PEP 668 (externally-managed) protection                     ║
# ╚══════════════════════════════════════════════════════════════════╝

# Không dùng set -e để tự xử lý lỗi từng bước
set -uo pipefail

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════
readonly TOOL_VERSION="1.4.6"
readonly TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="$TOOL_DIR/setup.log"
readonly MARKER_FILE="$TOOL_DIR/.setup_done"
readonly RETRY_MAX=3
readonly RETRY_DELAY=3

# PyPI mirrors — thử theo thứ tự nếu mạng chậm / bị block
readonly -a PYPI_MIRRORS=(
    ""                                          # PyPI chính thức (mặc định)
    "--index-url https://pypi.tuna.tsinghua.edu.cn/simple"  # Tsinghua (China)
    "--index-url https://mirrors.aliyun.com/pypi/simple"    # Aliyun
    "--index-url https://pypi.mirrors.ustc.edu.cn/simple"   # USTC
)

# ═══════════════════════════════════════════════════════════════════
# ANSI COLORS
# ═══════════════════════════════════════════════════════════════════
RED='\033[0;31m';   GREEN='\033[0;32m';  YELLOW='\033[1;33m'
CYAN='\033[0;36m';  MAGENTA='\033[0;35m'; BLUE='\033[0;34m'
BOLD='\033[1m';     DIM='\033[2m';        NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════
_ts()   { date '+%H:%M:%S'; }
log()   { echo -e "${DIM}[$(_ts)]${NC} $*"                  | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}  ✅ $*${NC}"                     | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}  ⚠️  $*${NC}"                   | tee -a "$LOG_FILE"; }
err()   { echo -e "${RED}  ❌ $*${NC}"                       | tee -a "$LOG_FILE"; }
info()  { echo -e "${CYAN}  ℹ️  $*${NC}"                     | tee -a "$LOG_FILE"; }
step()  { echo -e "\n${BOLD}${MAGENTA}▶ $* ${NC}"           | tee -a "$LOG_FILE"; }
sub()   { echo -e "${BLUE}    ↳ $*${NC}"                    | tee -a "$LOG_FILE"; }
skip()  { echo -e "${DIM}  ⏭  $* (đã có, bỏ qua)${NC}"     | tee -a "$LOG_FILE"; }

# ═══════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════
print_banner() {
    [[ "${NONINTERACTIVE:-0}" == "1" ]] && clear || clear 2>/dev/null || true
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       🎯  AT TOOL v${TOOL_VERSION} — SMART SETUP SCRIPT  🎯         ║"
    echo "║       Cài đặt tự động • Đa môi trường • Đa fallback         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ═══════════════════════════════════════════════════════════════════
# ENVIRONMENT DETECTION
# ═══════════════════════════════════════════════════════════════════
detect_env() {
    step "Phát hiện môi trường"

    # ── Flags ──────────────────────────────────────────────────────
    IS_TERMUX=false
    IS_PROOT=false          # Ubuntu/Debian trong proot-distro
    IS_UBUNTU=false
    IS_DEBIAN=false
    IS_NATIVE_LINUX=false
    IS_ARM64=false
    IS_ARM32=false
    IS_X86_64=false
    IS_ROOT=false
    HAS_SUDO=false
    HAS_APT=false
    HAS_PKG=false           # Termux pkg
    HAS_INTERNET=false
    HAS_UNZIP=false
    HAS_WGET=false
    HAS_CURL=false
    OS_NAME="Unknown"
    OS_VER="?"
    DISTRO_ID=""

    # ── Running as root? ───────────────────────────────────────────
    [[ "$(id -u)" == "0" ]] && IS_ROOT=true

    # ── Architecture ───────────────────────────────────────────────
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) IS_ARM64=true ;;
        armv7l|armv8l) IS_ARM32=true ;;
        x86_64|amd64)  IS_X86_64=true ;;
    esac

    # ── Termux detection ───────────────────────────────────────────
    if [[ -d "/data/data/com.termux" ]] \
    || [[ -n "${TERMUX_VERSION:-}" ]] \
    || [[ -n "${PREFIX:-}" && "$PREFIX" == *"termux"* ]]; then
        IS_TERMUX=true
    fi

    # ── proot / distro detection ───────────────────────────────────
    # Khi ở trong proot-distro, /proc/1/cmdline chứa "proot" hoặc
    # /run/container-id tồn tại, hoặc đơn giản là có /etc/os-release
    if [[ -f "/etc/os-release" ]]; then
        # shellcheck disable=SC1091
        source /etc/os-release 2>/dev/null || true
        DISTRO_ID="${ID:-}"
        OS_NAME="${NAME:-Unknown}"
        OS_VER="${VERSION_ID:-?}"

        case "${DISTRO_ID}" in
            ubuntu) IS_UBUNTU=true ;;
            debian|kali|parrot) IS_DEBIAN=true ;;
        esac

        # Nếu đang trong Termux nhưng có /etc/os-release → proot
        $IS_TERMUX && IS_PROOT=true
    fi

    # Native Linux (không phải Termux, không phải proot)
    if ! $IS_TERMUX && [[ -f "/etc/os-release" ]]; then
        IS_NATIVE_LINUX=true
    fi

    # ── Package managers ───────────────────────────────────────────
    command -v apt-get &>/dev/null && HAS_APT=true
    command -v pkg     &>/dev/null && $IS_TERMUX && HAS_PKG=true
    command -v unzip   &>/dev/null && HAS_UNZIP=true
    command -v wget    &>/dev/null && HAS_WGET=true
    command -v curl    &>/dev/null && HAS_CURL=true

    # ── sudo ───────────────────────────────────────────────────────
    if $IS_ROOT; then
        HAS_SUDO=true   # Root không cần sudo
    elif command -v sudo &>/dev/null; then
        # Test sudo không cần password
        sudo -n true 2>/dev/null && HAS_SUDO=true || true
        # proot thường có sudo wrapper giả
        $IS_PROOT && HAS_SUDO=true
    fi

    # ── Internet check ─────────────────────────────────────────────
    if $HAS_CURL; then
        curl -s --max-time 5 --head "https://pypi.org" &>/dev/null \
            && HAS_INTERNET=true || true
    elif $HAS_WGET; then
        wget -q --spider --timeout=5 "https://pypi.org" &>/dev/null \
            && HAS_INTERNET=true || true
    fi

    # ── Print summary ──────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}OS:${NC}        ${OS_NAME} ${OS_VER}"
    echo -e "  ${BOLD}Arch:${NC}      ${ARCH}"
    echo -e "  ${BOLD}Termux:${NC}    ${IS_TERMUX}"
    echo -e "  ${BOLD}proot:${NC}     ${IS_PROOT}"
    echo -e "  ${BOLD}Root:${NC}      ${IS_ROOT}"
    echo -e "  ${BOLD}sudo:${NC}      ${HAS_SUDO}"
    echo -e "  ${BOLD}apt:${NC}       ${HAS_APT}"
    echo -e "  ${BOLD}Internet:${NC}  ${HAS_INTERNET}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# APT WRAPPER — tự chọn sudo hay không
# ═══════════════════════════════════════════════════════════════════
_apt() {
    local cmd="$1"; shift
    export DEBIAN_FRONTEND=noninteractive

    local apt_cmd="apt-get"
    command -v apt &>/dev/null && apt_cmd="apt"

    if $IS_ROOT || ($IS_PROOT && ! command -v sudo &>/dev/null); then
        $apt_cmd "$cmd" -y -qq "$@" >> "$LOG_FILE" 2>&1
    elif $HAS_SUDO; then
        sudo $apt_cmd "$cmd" -y -qq "$@" >> "$LOG_FILE" 2>&1
    else
        $apt_cmd "$cmd" -y -qq "$@" >> "$LOG_FILE" 2>&1
    fi
}

apt_install() {
    local pkg="$1"
    # Skip nếu đã có
    if dpkg -l "$pkg" &>/dev/null 2>&1 | grep -q "^ii"; then
        skip "$pkg"
        return 0
    fi
    log "apt install $pkg..."
    if _apt install "$pkg"; then
        ok "$pkg"
        return 0
    fi
    warn "Không cài được $pkg qua apt"
    return 1
}

apt_update() {
    log "apt update..."
    _apt update -qq || warn "apt update thất bại (tiếp tục)"
}

# ═══════════════════════════════════════════════════════════════════
# NETWORK — retry với backoff
# ═══════════════════════════════════════════════════════════════════
wait_for_internet() {
    if $HAS_INTERNET; then return 0; fi

    warn "Không có internet. Chờ tối đa 30s..."
    for i in $(seq 1 6); do
        sleep 5
        if $HAS_CURL && curl -s --max-time 5 --head "https://pypi.org" &>/dev/null; then
            HAS_INTERNET=true; ok "Đã có internet"; return 0
        fi
        sub "Thử lại $i/6..."
    done
    warn "Vẫn không có internet. Một số package có thể không cài được."
    return 1
}

# ═══════════════════════════════════════════════════════════════════
# DISK SPACE CHECK
# ═══════════════════════════════════════════════════════════════════
check_disk_space() {
    local min_mb=300
    local avail_mb
    avail_mb=$(df "$TOOL_DIR" 2>/dev/null | awk 'NR==2{print int($4/1024)}' || echo 9999)
    if [[ "$avail_mb" -lt "$min_mb" ]]; then
        warn "Dung lượng trống thấp: ${avail_mb}MB (khuyến nghị >300MB)"
    else
        ok "Dung lượng: ${avail_mb}MB trống"
    fi
}

# ═══════════════════════════════════════════════════════════════════
# PYTHON DETECTION & INSTALL
# ═══════════════════════════════════════════════════════════════════
find_python() {
    step "Python"

    PYTHON=""
    PY_MAJOR=0; PY_MINOR=0

    # Termux native: python = python3 (không có python3.x symlink)
    local search_cmds=()
    if $IS_TERMUX && ! $IS_PROOT; then
        search_cmds=(python python3)
    else
        search_cmds=(python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3 python)
    fi

    for cmd in "${search_cmds[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then continue; fi
        if ! "$cmd" -c "import sys" &>/dev/null 2>&1; then continue; fi  # broken install

        local maj min
        maj=$("$cmd" -c "import sys;print(sys.version_info.major)" 2>/dev/null) || continue
        min=$("$cmd" -c "import sys;print(sys.version_info.minor)" 2>/dev/null) || continue

        if [[ "$maj" -ge 3 && "$min" -ge 8 ]]; then
            PYTHON="$cmd"
            PY_MAJOR=$maj; PY_MINOR=$min
            ok "Python: $cmd ($maj.$min)"
            break
        fi
    done

    # Chưa có → thử cài
    if [[ -z "$PYTHON" ]]; then
        warn "Python 3.8+ chưa có, đang cài..."
        if $HAS_APT; then
            apt_update
            for pkg in python3.12 python3.11 python3.10 python3 python3-minimal; do
                apt_install "$pkg" && break || continue
            done
            apt_install "python3-dev" || true
        elif $HAS_PKG; then
            pkg install -y python 2>>"$LOG_FILE" || true
        fi
        # Thử lại sau khi cài
        for cmd in python3.12 python3.11 python3.10 python3; do
            command -v "$cmd" &>/dev/null && PYTHON="$cmd" && break
        done
    fi

    if [[ -z "$PYTHON" ]]; then
        err "Không tìm được Python 3.8+!"
        err "Chạy thủ công: apt install python3"
        exit 1
    fi

    # Kiểm tra SSL (cần thiết cho pip)
    if ! "$PYTHON" -c "import ssl" &>/dev/null 2>&1; then
        warn "Python thiếu SSL support, đang cài libssl-dev..."
        $HAS_APT && apt_install "libssl-dev" || true
        $HAS_APT && apt_install "python3-dev" || true
    fi

    # PEP 668: detect externally-managed
    IS_EXTERNALLY_MANAGED=false
    if "$PYTHON" -m pip install --dry-run pip &>/dev/null 2>&1 | grep -q "externally-managed"; then
        IS_EXTERNALLY_MANAGED=true
        info "Phát hiện PEP 668 (externally-managed-environment)"
    fi
    # Cũng detect bằng file
    local py_prefix
    py_prefix=$("$PYTHON" -c "import sys;print(sys.prefix)" 2>/dev/null)
    [[ -f "${py_prefix}/lib/python${PY_MAJOR}.${PY_MINOR}/EXTERNALLY-MANAGED" ]] \
        && IS_EXTERNALLY_MANAGED=true
    [[ -f "/usr/lib/python${PY_MAJOR}/EXTERNALLY-MANAGED" ]] \
        && IS_EXTERNALLY_MANAGED=true

    $IS_EXTERNALLY_MANAGED && info "PEP 668: dùng --break-system-packages tự động"
}

# ═══════════════════════════════════════════════════════════════════
# PIP DETECTION & BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════
find_pip() {
    step "pip"

    PIP="$PYTHON -m pip"

    # Test pip hiện tại
    if $PYTHON -m pip --version &>/dev/null 2>&1; then
        ok "pip: $($PYTHON -m pip --version 2>/dev/null | head -1)"
        return 0
    fi

    warn "pip chưa có, đang bootstrap..."

    # Thử 1: apt
    if $HAS_APT; then
        apt_install "python3-pip" && \
            $PYTHON -m pip --version &>/dev/null 2>&1 && \
            ok "pip qua apt" && return 0
    fi

    # Thử 2: ensurepip
    "$PYTHON" -m ensurepip --upgrade &>>"$LOG_FILE" && \
        ok "pip qua ensurepip" && return 0 || true

    # Thử 3: tải get-pip.py
    local get_pip_url="https://bootstrap.pypa.io/get-pip.py"
    local get_pip_file="/tmp/get-pip.py"
    if $HAS_CURL; then
        curl -sSL "$get_pip_url" -o "$get_pip_file" &>>"$LOG_FILE"
    elif $HAS_WGET; then
        wget -qO "$get_pip_file" "$get_pip_url" &>>"$LOG_FILE"
    fi

    if [[ -f "$get_pip_file" ]]; then
        "$PYTHON" "$get_pip_file" &>>"$LOG_FILE" && \
            ok "pip qua get-pip.py" && return 0 || true
    fi

    # Thử 4: Termux pkg
    if $HAS_PKG && $IS_TERMUX && ! $IS_PROOT; then
        pkg install -y python-pip &>>"$LOG_FILE" && \
            ok "pip qua Termux pkg" && return 0 || true
    fi

    err "Không bootstrap được pip!"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# PIP INSTALL — đa tầng fallback
# ═══════════════════════════════════════════════════════════════════

# Build PIP_FLAGS dựa trên môi trường
_build_pip_flags() {
    PIP_FLAGS=()

    # PEP 668 / Ubuntu 23.04+
    # Termux native KHÔNG cần --break-system-packages (env riêng biệt)
    if $IS_EXTERNALLY_MANAGED     || ( [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 11 ]] && ! $IS_TERMUX ); then
        PIP_FLAGS+=("--break-system-packages")
    fi
}

# Thực sự cài 1 package với 1 mirror
_pip_try() {
    local pkg="$1"; shift
    local flags=("$@")
    $PYTHON -m pip install "${flags[@]}" "$pkg" >> "$LOG_FILE" 2>&1
}

# Kiểm tra package đã import được chưa
_can_import() {
    local mod="$1"
    "$PYTHON" -c "import $mod" &>/dev/null 2>&1
}

pip_install() {
    local pkg="$1"
    local display="${2:-$pkg}"
    local required="${3:-false}"   # "true" = exit nếu thất bại

    local base_pkg="${pkg%%[>=<!@]*}"   # bỏ version constraint
    local import_mod="${4:-$base_pkg}"  # tên module để import test

    # Kiểm tra đã có chưa (nếu biết tên import)
    if [[ -n "$import_mod" ]] && _can_import "$import_mod"; then
        skip "$display"
        return 0
    fi

    log "pip install $display..."

    _build_pip_flags

    local tried=0
    local succeeded=false

    # ── Vòng lặp thử từng mirror ─────────────────────────────────
    for mirror in "${PYPI_MIRRORS[@]}"; do
        [[ "$tried" -gt 0 ]] && sub "Thử mirror: ${mirror:-pypi.org}..."

        # Mảng mirror flags
        local mirror_flags=()
        [[ -n "$mirror" ]] && IFS=' ' read -ra mirror_flags <<< "$mirror"

        for attempt in $(seq 1 $RETRY_MAX); do
            [[ $attempt -gt 1 ]] && sub "Retry $attempt/$RETRY_MAX..." && sleep $RETRY_DELAY

            # Thử 1: Cài bình thường
            if _pip_try "$pkg" "${PIP_FLAGS[@]}" "${mirror_flags[@]}"; then
                succeeded=true; break 2
            fi

            # Thử 2: --user
            if _pip_try "$pkg" "--user" "${PIP_FLAGS[@]}" "${mirror_flags[@]}"; then
                succeeded=true; break 2
            fi

            # Thử 3: bỏ version constraint
            if [[ "$base_pkg" != "$pkg" ]]; then
                if _pip_try "$base_pkg" "${PIP_FLAGS[@]}" "${mirror_flags[@]}"; then
                    succeeded=true; break 2
                fi
            fi

            # Thử 4: --no-deps (với package phức tạp)
            if _pip_try "$pkg" "--no-deps" "${PIP_FLAGS[@]}" "${mirror_flags[@]}"; then
                # Cài deps riêng sau
                _pip_try "$pkg" "--only-binary=:all:" "${PIP_FLAGS[@]}" "${mirror_flags[@]}" || true
                succeeded=true; break 2
            fi
        done
        tried=$((tried + 1))

        # Không thử mirror tiếp nếu offline
        $HAS_INTERNET || break
    done

    # Apt fallback cho một số package phổ biến
    if ! $succeeded && $HAS_APT; then
        local apt_alt=""
        case "$base_pkg" in
            Pillow|pillow)     apt_alt="python3-pil" ;;
            numpy)             apt_alt="python3-numpy" ;;
            requests)          apt_alt="python3-requests" ;;
            pytz)              apt_alt="python3-tz" ;;
            rich)              apt_alt="python3-rich" ;;
            uiautomator2)      apt_alt="" ;;   # không có apt
        esac
        if [[ -n "$apt_alt" ]]; then
            sub "Thử apt fallback: $apt_alt..."
            apt_install "$apt_alt" && succeeded=true
        fi
    fi

    if $succeeded; then
        ok "$display"
        return 0
    fi

    if [[ "$required" == "true" ]]; then
        err "$display là bắt buộc! Dừng setup."
        exit 1
    fi
    warn "$display không cài được (optional, bỏ qua)"
    return 1
}

# ═══════════════════════════════════════════════════════════════════
# SYSTEM DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════
install_system_deps() {
    step "System dependencies"

    # ── Termux native (không qua proot) ─────────────────────────
    if $IS_TERMUX && ! $IS_PROOT; then
        sub "Termux native: cài qua pkg..."
        pkg update -y >> "$LOG_FILE" 2>&1 || true
        local termux_pkgs=(
            "python" "python-pip"
            "libandroid-support"
            "libjpeg-turbo" "libpng" "libtiff" "libwebp"
            "freetype" "harfbuzz"
            "zlib" "openssl"
            "curl" "wget" "unzip" "git"
        )
        for pkg_t in "${termux_pkgs[@]}"; do
            pkg install -y "$pkg_t" >> "$LOG_FILE" 2>&1 && ok "$pkg_t" || true
        done
        ok "Termux deps hoàn tất"
        return 0
    fi

    if ! $HAS_APT; then
        info "Không có apt-get, bỏ qua system deps"
        return 0
    fi

    apt_update

    # Cơ bản
    local core_sys=(
        "python3" "python3-dev" "python3-pip" "python3-venv"
        "build-essential" "gcc" "g++"
        "libffi-dev" "libssl-dev"
        "curl" "wget" "git" "unzip" "zip"
        "ca-certificates"
    )

    # Image processing (Pillow deps)
    local img_sys=(
        "libjpeg-dev" "libjpeg8-dev" "libjpeg-turbo8-dev"
        "zlib1g-dev" "libpng-dev"
        "libtiff-dev" "libtiff5-dev"
        "libopenjp2-7-dev"
        "libwebp-dev"
        "libfreetype6-dev" "libharfbuzz-dev" "libfribidi-dev"
    )

    # ADB
    local adb_sys=("adb" "android-tools-adb")

    echo -e "${BOLD}  Core:${NC}"
    for pkg in "${core_sys[@]}"; do
        apt_install "$pkg" || true
    done

    echo -e "${BOLD}  Image deps (Pillow):${NC}"
    for pkg in "${img_sys[@]}"; do
        apt_install "$pkg" 2>/dev/null || true
    done

    echo -e "${BOLD}  ADB:${NC}"
    for pkg in "${adb_sys[@]}"; do
        apt_install "$pkg" && break || true
    done

    ok "System deps hoàn tất"
}

# ═══════════════════════════════════════════════════════════════════
# ADB SETUP
# ═══════════════════════════════════════════════════════════════════
setup_adb() {
    step "ADB"

    # Đã có rồi
    if command -v adb &>/dev/null; then
        ok "ADB đã có: $(adb version 2>/dev/null | head -1)"
        # Thử khởi động ADB server
        adb start-server &>/dev/null 2>&1 || true
        return 0
    fi

    # Termux native (không qua proot)
    if $IS_TERMUX && ! $IS_PROOT; then
        sub "Thử pkg install android-tools (Termux)..."
        pkg install -y android-tools >> "$LOG_FILE" 2>&1 \
            && ok "ADB qua Termux pkg" && return 0 || true
    fi

    # apt
    if $HAS_APT; then
        for pkg in "adb" "android-tools-adb" "android-sdk-platform-tools-common"; do
            apt_install "$pkg" \
                && command -v adb &>/dev/null \
                && ok "ADB qua apt ($pkg)" && return 0 || true
        done
    fi

    # Tải platform-tools thủ công
    if ! $HAS_INTERNET; then
        warn "Không có internet, không tải được ADB"
        return 1
    fi

    sub "Tải platform-tools từ Google..."

    # Chọn URL theo arch
    local pt_url="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
    local pt_zip="/tmp/platform-tools.zip"
    local pt_dir="$HOME/platform-tools"

    local dl_ok=false
    if $HAS_CURL; then
        curl -sSL "$pt_url" -o "$pt_zip" >> "$LOG_FILE" 2>&1 && dl_ok=true
    elif $HAS_WGET; then
        wget -qO "$pt_zip" "$pt_url" >> "$LOG_FILE" 2>&1 && dl_ok=true
    fi

    if $dl_ok && $HAS_UNZIP; then
        rm -rf "$pt_dir"
        unzip -q "$pt_zip" -d "$HOME/" >> "$LOG_FILE" 2>&1
        chmod +x "${pt_dir}/adb" 2>/dev/null || true
        export PATH="$pt_dir:$PATH"
        command -v adb &>/dev/null \
            && ok "ADB tải thủ công: $pt_dir/adb" \
            && return 0
    fi

    warn "Không cài được ADB tự động"
    warn "→ Cài thủ công: apt install adb  hoặc  pkg install android-tools"
}

# ═══════════════════════════════════════════════════════════════════
# PYTHON PACKAGES
# ═══════════════════════════════════════════════════════════════════
install_python_pkgs() {
    step "Python packages"

    # ──────────────────────────────────────────────────────────────
    # 1. Core bắt buộc
    # ──────────────────────────────────────────────────────────────
    echo -e "\n${BOLD}  [1/5] Core packages (bắt buộc):${NC}"

    pip_install "uiautomator2"  "uiautomator2"  "true"  "uiautomator2"
    pip_install "rich>=10.0"    "rich"           "true"  "rich"
    pip_install "pytz"          "pytz"           "true"  "pytz"
    pip_install "requests"      "requests"       "true"  "requests"

    # ──────────────────────────────────────────────────────────────
    # 2. Image processing (cho AI vision)
    # ──────────────────────────────────────────────────────────────
    echo -e "\n${BOLD}  [2/5] Image processing:${NC}"

    # Pillow — thử nhiều cách do ARM thường lỗi
    local pillow_ok=false
    if _can_import "PIL"; then
        skip "Pillow"
        pillow_ok=true
    else
        # Thử binary wheel trước (nhanh, không cần build)
        if _pip_try "Pillow" "--only-binary=:all:" "${PIP_FLAGS[@]}"; then
            ok "Pillow (binary wheel)"
            pillow_ok=true
        # Thử với version cụ thể cho ARM
        elif $IS_ARM64 && _pip_try "Pillow==10.4.0" "${PIP_FLAGS[@]}"; then
            ok "Pillow 10.4.0 (ARM64)"
            pillow_ok=true
        elif $IS_ARM64 && _pip_try "Pillow==9.5.0" "${PIP_FLAGS[@]}"; then
            ok "Pillow 9.5.0 (ARM64)"
            pillow_ok=true
        elif _pip_try "Pillow" "${PIP_FLAGS[@]}"; then
            ok "Pillow"
            pillow_ok=true
        # Fallback apt
        elif $HAS_APT && apt_install "python3-pil"; then
            ok "Pillow (qua apt python3-pil)"
            pillow_ok=true
        else
            warn "Pillow không cài được — AI vision TẮT"
        fi
    fi

    # NumPy
    if _can_import "numpy"; then
        skip "numpy"
    elif _pip_try "numpy" "--only-binary=:all:" "${PIP_FLAGS[@]}"; then
        ok "numpy (binary wheel)"
    elif _pip_try "numpy" "${PIP_FLAGS[@]}"; then
        ok "numpy"
    elif $HAS_APT && apt_install "python3-numpy"; then
        ok "numpy (apt)"
    else
        warn "numpy không cài được (optional)"
    fi

    # ──────────────────────────────────────────────────────────────
    # 3. Gemini AI SDK — NEW (google-genai) ưu tiên
    # ──────────────────────────────────────────────────────────────
    echo -e "\n${BOLD}  [3/5] Gemini AI SDK:${NC}"

    if _can_import "google.genai"; then
        skip "google-genai (new SDK)"
    elif pip_install "google-genai" "google-genai (new SDK)" "false" "google.genai"; then
        ok "google-genai ✅ AI popup detection sẵn sàng"
    else
        warn "google-genai thất bại, thử fallback sdk cũ..."
        if _can_import "google.generativeai"; then
            skip "google-generativeai (legacy)"
        elif pip_install "google-generativeai" "google-generativeai (legacy)" "false" "google.generativeai"; then
            ok "google-generativeai (legacy) ✅"
        else
            warn "Không cài được Gemini SDK — AI popup detection TẮT"
        fi
    fi

    # protobuf (cần cho google-genai trên ARM)
    if ! _can_import "google.protobuf"; then
        _pip_try "protobuf" "${PIP_FLAGS[@]}" >> "$LOG_FILE" 2>&1 || true
    fi

    # ──────────────────────────────────────────────────────────────
    # 4. AI optional
    # ──────────────────────────────────────────────────────────────
    echo -e "\n${BOLD}  [4/5] AI optional (OpenAI / Anthropic):${NC}"

    pip_install "openai"    "OpenAI"    "false" "openai"
    pip_install "anthropic" "Anthropic" "false" "anthropic"

    # ──────────────────────────────────────────────────────────────
    # 5. uiautomator2 init (khởi tạo ATX agent)
    # ──────────────────────────────────────────────────────────────
    echo -e "\n${BOLD}  [5/5] uiautomator2 init:${NC}"
    _init_uiautomator2
}

_init_uiautomator2() {
    # Không chạy u2 init nếu không có ADB hoặc không có điện thoại kết nối
    if ! command -v adb &>/dev/null; then
        info "Bỏ qua u2 init (ADB chưa có)"
        return 0
    fi

    # Kiểm tra có thiết bị không
    local devices
    devices=$(adb devices 2>/dev/null | grep -v "List of devices" | grep -c "device$" || echo 0)

    if [[ "$devices" -eq 0 ]]; then
        info "Không có thiết bị kết nối — bỏ qua u2 init"
        info "→ Cắm điện thoại rồi chạy: python3 -m uiautomator2 init"
        return 0
    fi

    sub "Tìm thấy $devices thiết bị, đang init uiautomator2..."
    if "$PYTHON" -m uiautomator2 init >> "$LOG_FILE" 2>&1; then
        ok "uiautomator2 init thành công"
    else
        warn "uiautomator2 init thất bại"
        info "→ Cắm lại điện thoại rồi chạy: python3 -m uiautomator2 init"
    fi
}

# ═══════════════════════════════════════════════════════════════════
# PATH FIX
# ═══════════════════════════════════════════════════════════════════
fix_path() {
    step "Cập nhật PATH"

    local rc_files=("$HOME/.bashrc" "$HOME/.profile" "$HOME/.bash_profile")
    local rc=""
    for f in "${rc_files[@]}"; do
        [[ -f "$f" ]] && rc="$f" && break
    done
    [[ -z "$rc" ]] && rc="$HOME/.bashrc" && touch "$rc"

    local paths=(
        "export PATH=\$HOME/.local/bin:\$PATH"
        "export PATH=\$HOME/platform-tools:\$PATH"
    )
    for line in "${paths[@]}"; do
        grep -qF "$line" "$rc" 2>/dev/null || echo "$line" >> "$rc"
    done
    export PATH="$HOME/.local/bin:$HOME/platform-tools:$PATH"

    ok "PATH cập nhật trong $rc"
}

# ═══════════════════════════════════════════════════════════════════
# VERIFY
# ═══════════════════════════════════════════════════════════════════
verify() {
    step "Kết quả cài đặt"

    local ok_count=0
    local warn_count=0

    _check() {
        local label="$1" module="$2" required="${3:-false}"
        if "$PYTHON" -c "import $module" &>/dev/null 2>&1; then
            local ver
            ver=$("$PYTHON" -c "
import $module
for attr in ('__version__','version','VERSION','__ver__'):
    v = getattr($module, attr, None)
    if v: print(str(v)); break
else: print('ok')
" 2>/dev/null || echo "ok")
            echo -e "    ${GREEN}✅${NC} ${label} ${DIM}(${ver})${NC}"
            ok_count=$((ok_count + 1))
        else
            if [[ "$required" == "true" ]]; then
                echo -e "    ${RED}❌${NC} ${BOLD}${label}${NC} ${RED}(THIẾU - BẮT BUỘC)${NC}"
            else
                echo -e "    ${YELLOW}⚠️ ${NC} ${label} ${DIM}(optional, không có)${NC}"
            fi
            warn_count=$((warn_count + 1))
        fi
    }

    echo ""
    echo -e "  ${BOLD}━━ Bắt buộc ━━${NC}"
    _check "uiautomator2"      "uiautomator2"         "true"
    _check "rich"              "rich"                  "true"
    _check "pytz"              "pytz"                  "true"
    _check "requests"          "requests"              "true"

    echo ""
    echo -e "  ${BOLD}━━ AI ━━${NC}"
    _check "google-genai (new)" "google.genai"         "false"
    _check "google-genai (old)" "google.generativeai"  "false"
    _check "Pillow"             "PIL"                   "false"
    _check "numpy"              "numpy"                 "false"

    echo ""
    echo -e "  ${BOLD}━━ AI optional ━━${NC}"
    _check "openai"     "openai"     "false"
    _check "anthropic"  "anthropic"  "false"

    echo ""
    echo -e "  ${BOLD}━━ Tools ━━${NC}"
    if command -v adb &>/dev/null; then
        echo -e "    ${GREEN}✅${NC} adb $(adb version 2>/dev/null | head -1)"
        ok_count=$((ok_count + 1))
    else
        echo -e "    ${YELLOW}⚠️ ${NC} adb (chưa có)"
    fi

    echo ""
    echo -e "  ${CYAN}Tổng: ${GREEN}${ok_count} OK${NC} | ${YELLOW}${warn_count} cảnh báo${NC}"
}

# ═══════════════════════════════════════════════════════════════════
# MARKER
# ═══════════════════════════════════════════════════════════════════
mark_done() {
    {
        echo "SETUP_DATE=$(date '+%Y-%m-%d %H:%M:%S')"
        echo "PYTHON=$PYTHON"
        echo "PY_VERSION=$PY_MAJOR.$PY_MINOR"
        echo "ARCH=$ARCH"
        echo "OS=$OS_NAME $OS_VER"
        echo "IS_TERMUX=$IS_TERMUX"
        echo "IS_PROOT=$IS_PROOT"
        echo "IS_ROOT=$IS_ROOT"
        echo "TOOL_VERSION=$TOOL_VERSION"
    } > "$MARKER_FILE"
    ok "Marker lưu: .setup_done"
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
main() {
    print_banner

    # Reset log
    {
        echo "═══════════════════════════════════════════════════"
        echo " AT TOOL v${TOOL_VERSION} Setup Log — $(date)"
        echo "═══════════════════════════════════════════════════"
    } > "$LOG_FILE"

    # Non-interactive: gọi từ main.py hoặc stdin không phải tty
    NONINTERACTIVE="${NONINTERACTIVE:-0}"
    [[ ! -t 0 ]] && NONINTERACTIVE="1"

    # Check marker
    if [[ -f "$MARKER_FILE" && "${1:-}" != "--force" ]]; then
        echo -e "${GREEN}✅ Đã setup trước đó ($(grep SETUP_DATE "$MARKER_FILE" | cut -d= -f2))${NC}"
        if [[ "$NONINTERACTIVE" == "1" ]]; then
            info "Non-interactive: bỏ qua re-install"
            exit 0
        fi
        echo ""
        echo -e "  [1] Bỏ qua (mặc định)"
        echo -e "  [2] Cài lại toàn bộ"
        echo -e "  [3] Chỉ verify"
        read -rp $'\n  Chọn (1/2/3): ' choice 2>/dev/null || choice="1"
        case "${choice:-1}" in
            2) info "Cài lại..." ;;
            3) detect_env; find_python; verify; exit 0 ;;
            *) echo "Bỏ qua."; exit 0 ;;
        esac
    fi

    # Run steps
    detect_env
    check_disk_space
    wait_for_internet || true   # cảnh báo nhưng không dừng
    install_system_deps
    find_python
    find_pip
    setup_adb
    install_python_pkgs
    fix_path
    verify
    mark_done

    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║               ✅  SETUP HOÀN TẤT!                           ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Chạy tool  :  python3 main.py                              ║"
    echo "║  Xem log    :  cat setup.log                                ║"
    echo "║  Cài lại    :  bash setup.sh --force                        ║"
    echo "║  Chỉ verify :  bash setup.sh --verify                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    if ! command -v adb &>/dev/null; then
        echo -e "${YELLOW}⚠️  ADB chưa có. Sau khi cắm điện thoại:${NC}"
        echo -e "   ${DIM}apt install adb  hoặc  pkg install android-tools${NC}"
    fi
}

# ── Xử lý --verify flag riêng ──────────────────────────────────────
if [[ "${1:-}" == "--verify" ]]; then
    echo "=== AT TOOL Verify ===" > "$LOG_FILE"
    detect_env
    find_python
    verify
    exit 0
fi

main "$@"
