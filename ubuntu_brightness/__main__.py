"""Điểm vào giao diện hoặc công cụ dòng lệnh."""

import argparse
import json
import os
import sys

from . import __version__
from .backends import DemoBackend, HardwareBackend
from .models import BrightnessError, validate_percent
from .xrandr import XrandrBackend, is_wayland


def create_backend(mode: str, demo: bool = False):
    if demo:
        return DemoBackend()
    if mode == "auto":
        mode = "software" if os.environ.get("DISPLAY") and not is_wayland(os.environ) else "hardware"
    return XrandrBackend() if mode == "software" else HardwareBackend()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Điều chỉnh độ sáng riêng cho từng màn hình trên Ubuntu.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--demo", action="store_true", help="Dùng màn hình giả lập, không truy cập phần cứng")
    parser.add_argument(
        "--mode", choices=("auto", "software", "hardware"), default="auto",
        help="auto: dùng xrandr trên X11, đèn nền trên Wayland; software: xrandr; hardware: đèn nền",
    )
    commands = parser.add_subparsers(dest="command")
    listing = commands.add_parser("list", help="Liệt kê màn hình và mã dùng để điều chỉnh")
    listing.add_argument("--json", action="store_true", help="Xuất kết quả dưới dạng JSON")
    setting = commands.add_parser("set", help="Điều chỉnh một màn hình theo mã từ lệnh list")
    setting.add_argument("display", help="Mã màn hình, ví dụ xrandr:HDMI-1")
    setting.add_argument("percent", type=int, help="Độ sáng từ 0 đến 100%")
    options = parser.parse_args(argv)
    # Xác thực trước khi dò phần cứng để giá trị sai không gây truy cập thiết bị.
    try:
        if options.command == "set":
            validate_percent(options.percent)
        backend = create_backend(options.mode, options.demo)
        if options.command is None:
            try:
                from .gui import launch
            except (ImportError, ValueError) as exc:
                raise BrightnessError(
                    "Thiếu GTK 4 hoặc PyGObject. Chạy ./scripts/install.sh rồi dùng ./run.sh."
                ) from exc
            return launch(backend, demo=options.demo)

        discovery = backend.discover()
        if options.command == "list":
            if options.json:
                print(json.dumps({
                    "displays": [{
                        "id": item.identifier,
                        "name": item.name,
                        "connection": item.connection,
                        "backend": item.backend,
                        "brightness": item.brightness.percent if item.brightness else None,
                        "available": item.available,
                        "error": item.error,
                    } for item in discovery.displays],
                    "notices": discovery.notices,
                }, ensure_ascii=False, indent=2))
            else:
                for item in discovery.displays:
                    value = f"{item.brightness.percent}%" if item.brightness else "—"
                    print(f"{item.identifier}\t{item.name}\t{value}\t{item.connection}")
                    if item.error:
                        print(f"  {item.error}", file=sys.stderr)
                for notice in discovery.notices:
                    print(notice, file=sys.stderr)
                if not discovery.displays:
                    print("Không tìm thấy màn hình. Kiểm tra kết nối và quyền truy cập.", file=sys.stderr)
            return 0

        selected = next((item for item in discovery.displays if item.identifier == options.display), None)
        if selected is None:
            raise BrightnessError("Không tìm thấy mã màn hình. Chạy lệnh list để lấy danh sách hiện tại.")
        brightness = backend.set(selected, options.percent)
        print(f"{selected.name}: {brightness.percent}%")
        return 0
    except BrightnessError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
