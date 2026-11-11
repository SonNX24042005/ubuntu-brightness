#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
launcher_only=false
video_group_changed=false
case "${1:-}" in
    "") ;;
    --launcher-only) launcher_only=true ;;
    *) printf 'Cách dùng: %s [--launcher-only]\n' "$0" >&2; exit 2 ;;
esac

if [[ "$EUID" -eq 0 ]]; then
    printf 'Chạy script bằng tài khoản desktop thông thường; script sẽ dùng sudo khi cần.\n' >&2
    exit 1
fi

if [[ "$launcher_only" == false ]]; then
    if ! command -v apt-get >/dev/null; then
        printf 'Script này dành cho Ubuntu/Debian có apt-get.\n' >&2
        exit 1
    fi
    sudo apt-get update
    sudo apt-get install -y python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 x11-xserver-utils ddcutil brightnessctl brightness-udev
    sudo modprobe i2c-dev
    printf 'i2c-dev\n' | sudo tee /etc/modules-load.d/ubuntu-brightness-i2c.conf >/dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=i2c-dev
    sudo udevadm trigger --action=add --subsystem-match=backlight
    if [[ " $(id -nG) " != *" video "* ]]; then
        sudo usermod -aG video "$(id -un)"
        video_group_changed=true
    fi
fi

/usr/bin/python3 - "$project_root" <<'PY'
import os
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
data_root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
applications = data_root / "applications"
applications.mkdir(parents=True, exist_ok=True)
path_value = str(project_root).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
desktop = applications / "io.github.ubuntubrightness.desktop"
desktop.write_text(
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=Độ sáng màn hình\n"
    "Comment=Chọn màn hình và điều chỉnh độ sáng riêng\n"
    "Exec=/usr/bin/python3 -m ubuntu_brightness\n"
    f"Path={path_value}\n"
    "Icon=display-brightness-symbolic\n"
    "Terminal=false\n"
    "Categories=Settings;HardwareSettings;\n"
    "Keywords=brightness;monitor;display;độ sáng;màn hình;\n"
    "StartupNotify=true\n",
    encoding="utf-8",
)
print(f"Đã tạo biểu tượng ứng dụng: {desktop}")
PY

printf 'Mở ứng dụng bằng ./run.sh hoặc tìm “Độ sáng màn hình” trong menu ứng dụng.\n'
if [[ "$launcher_only" == false ]]; then
    printf 'Nếu báo thiếu quyền, xem mục quyền truy cập trong README.md.\n'
fi
if [[ "$video_group_changed" == true ]]; then
    printf 'Đã thêm tài khoản vào nhóm video. Đăng xuất rồi đăng nhập lại trước khi điều chỉnh đèn nền.\n'
fi
