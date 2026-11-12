"""Điểm vào giao diện hoặc công cụ dòng lệnh."""

import argparse
import json
import os
import sys

from . import __version__
from .backends import DemoBackend, HardwareBackend
from .models import BrightnessError, validate_percent
from .xrandr import XrandrBackend, is_wayland


APP_IDS = ("io.github.ubuntubrightness", "io.github.ubuntubrightness.hardware")


def _activate_running_app(app_id: str, action: str, parameters: list) -> bool:
    try:
        from gi.repository import Gio, GLib
    except ImportError:
        return False
    object_path = "/" + app_id.replace(".", "/")
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            app_id,
            object_path,
            "org.gtk.Actions",
            "Activate",
            GLib.Variant("(sava{sv})", (action, parameters, {})),
            None,
            Gio.DBusCallFlags.NO_AUTO_START,
            500,
            None,
        )
    except GLib.Error:
        return False
    return True


def _notify_running_app(mode: str, identifier: str, percent: int) -> None:
    try:
        from gi.repository import GLib
    except ImportError:
        return
    app_id = APP_IDS[1] if mode == "hardware" else APP_IDS[0]
    _activate_running_app(app_id, "external-set", [GLib.Variant("(si)", (identifier, percent))])


def _reset_all(mode: str, demo: bool) -> int:
    # Ứng dụng đang chạy tự áp dụng để không tranh chấp với cơ chế giữ mức sáng.
    if not demo:
        handled = [app_id for app_id in APP_IDS if _activate_running_app(app_id, "reset-all", [])]
        if handled:
            print("Đã yêu cầu ứng dụng đang chạy đưa tất cả màn hình về 100%.")
            return 0
    backend = create_backend(mode, demo)
    failed = 0
    for item in backend.discover().displays:
        if not item.available:
            continue
        try:
            brightness = backend.set(item, 100)
        except BrightnessError as exc:
            failed += 1
            print(f"{item.name}: {exc}", file=sys.stderr)
        else:
            print(f"{item.name}: {brightness.percent}%")
    return 1 if failed else 0


def _shortcut(options) -> int:
    try:
        from . import shortcut
    except (ImportError, ValueError) as exc:
        raise BrightnessError(
            "Thiếu GTK 4 hoặc PyGObject. Chạy ./scripts/install.sh trước."
        ) from exc
    if options.set is not None:
        state = shortcut.write(options.set)
    elif options.disable:
        state = shortcut.write("")
    elif options.default:
        state = shortcut.write(shortcut.DEFAULT_BINDING)
    elif options.ensure:
        state = shortcut.ensure()
    else:
        state = shortcut.read()
    if not state.installed:
        print("Chưa tạo phím tắt. Chạy lệnh với --default để tạo phím mặc định.")
        return 0
    print(f"Phím tắt đưa tất cả màn hình về 100%: {shortcut.display_label(state.binding)}")
    if state.lock_screen:
        print("Dùng được ở màn hình khóa qua extension GNOME Shell.")
    else:
        print(f"Chưa dùng được ở màn hình khóa. {shortcut.extension_status()}")
    if state.binding:
        for name in shortcut.conflicts(state.binding):
            print(f"Trùng với phím tắt khác: {name}", file=sys.stderr)
    return 0


def _quit_running_app() -> int:
    try:
        from gi.repository import Gio, GLib
    except ImportError as exc:
        raise BrightnessError(
            "Thiếu PyGObject để kết nối phiên desktop. Chạy ./scripts/install.sh trước."
        ) from exc
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    except GLib.Error as exc:
        raise BrightnessError("Không thể kết nối D-Bus của phiên desktop hiện tại.") from exc

    stopped = 0
    for app_id in APP_IDS:
        try:
            has_owner = bus.call_sync(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "NameHasOwner",
                GLib.Variant("(s)", (app_id,)),
                GLib.VariantType.new("(b)"),
                Gio.DBusCallFlags.NONE,
                500,
                None,
            ).unpack()[0]
            if not has_owner:
                continue
            object_path = "/" + app_id.replace(".", "/")
            actions = bus.call_sync(
                app_id,
                object_path,
                "org.gtk.Actions",
                "List",
                None,
                GLib.VariantType.new("(as)"),
                Gio.DBusCallFlags.NO_AUTO_START,
                500,
                None,
            ).unpack()[0]
            action_name = "full-quit" if "full-quit" in actions else "quit"
            bus.call_sync(
                app_id,
                object_path,
                "org.gtk.Actions",
                "Activate",
                GLib.Variant("(sava{sv})", (action_name, [], {})),
                None,
                Gio.DBusCallFlags.NO_AUTO_START,
                1000,
                None,
            )
            stopped += 1
        except GLib.Error:
            continue

    if stopped:
        print("Đã gửi lệnh thoát hẳn tới ứng dụng đang chạy.")
    else:
        print("Không có ứng dụng nào đang chạy ngầm.")
    return 0


def create_backend(mode: str, demo: bool = False):
    if demo:
        return DemoBackend()
    if mode == "auto":
        mode = "software" if os.environ.get("DISPLAY") and not is_wayland(os.environ) else "hardware"
    return XrandrBackend() if mode == "software" else HardwareBackend()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Điều chỉnh độ sáng riêng cho từng màn hình trên Ubuntu.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--quit", action="store_true", help="Dừng hẳn ứng dụng đang chạy ngầm"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Dùng màn hình giả lập, không truy cập phần cứng"
    )
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
    commands.add_parser("reset", help="Đưa tất cả màn hình về 100%, dùng cho phím tắt toàn cục")
    keys = commands.add_parser("shortcut", help="Xem hoặc đổi phím tắt toàn cục của GNOME")
    choice = keys.add_mutually_exclusive_group()
    choice.add_argument("--set", metavar="PHÍM", help="Tổ hợp phím mới, ví dụ '<Super><Alt>0'")
    choice.add_argument("--disable", action="store_true", help="Tắt phím tắt toàn cục")
    choice.add_argument("--default", action="store_true", help="Dùng lại phím mặc định Super+Alt+0")
    choice.add_argument("--ensure", action="store_true", help="Tạo phím mặc định nếu chưa có")
    options = parser.parse_args(argv)
    # Xác thực trước khi dò phần cứng để giá trị sai không gây truy cập thiết bị.
    try:
        if options.quit:
            return _quit_running_app()
        if options.command == "set":
            validate_percent(options.percent)
        if options.command == "reset":
            return _reset_all(options.mode, options.demo)
        if options.command == "shortcut":
            return _shortcut(options)
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
        if not options.demo:
            _notify_running_app(
                getattr(backend, "mode", ""), selected.identifier, brightness.percent
            )
        print(f"{selected.name}: {brightness.percent}%")
        return 0
    except BrightnessError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
