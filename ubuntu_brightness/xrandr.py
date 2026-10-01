"""Làm tối hình ảnh trên từng đầu ra X11 bằng xrandr."""

import math
import os
import re
import shutil
from dataclasses import replace
from typing import Callable, Mapping

from .backends import CommandResult, require_success, run_command
from .models import Brightness, BrightnessError, Discovery, Display, validate_percent


def is_wayland(environment: Mapping[str, str]) -> bool:
    return environment.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
        environment.get("WAYLAND_DISPLAY")
    )


def _monitor_name(block: str, target: str) -> str:
    match = re.search(r"(?m)^\s*EDID:\s*\n((?:[ \t]+[0-9a-fA-F]{32}[ \t]*\n)+)", block)
    if match:
        edid = bytes.fromhex(match[1])
        for offset in (54, 72, 90, 108):
            descriptor = edid[offset:offset + 18]
            if len(descriptor) == 18 and descriptor[:5] == b"\x00\x00\x00\xfc\x00":
                name = descriptor[5:].decode("ascii", errors="replace").strip("\n\x00 ")
                if name:
                    return name
    return "Màn hình laptop" if target.startswith(("eDP", "LVDS", "DSI")) else target


def parse_xrandr(output: str) -> Discovery:
    """Đọc đầu ra verbose, giữ nguyên tên output và bỏ các cổng không kết nối."""
    displays = []
    notices = []
    controllers: dict[str, list[str]] = {}
    blocks = re.split(r"(?m)^(?=\S+ (?:connected|disconnected|unknown connection)\b)", output)
    for block in blocks:
        header = re.match(r"(\S+) connected\b([^\n]*)", block)
        if header is None:
            continue
        target = header[1]
        active = bool(re.search(r"\b\d+x\d+[+-]\d+[+-]\d+\b", header[2]))
        error = ""
        brightness = None
        if not active:
            error = "Màn hình đang tắt. Bật màn hình trong cài đặt hiển thị rồi quét lại."
        else:
            match = re.search(r"(?m)^\s*Brightness:\s*(\S+)", block)
            try:
                value = float(match[1]) if match else math.nan
                if not math.isfinite(value) or value < 0:
                    raise ValueError
                brightness = Brightness(int(min(value, 1) * 100 + 0.5), 100)
                if value > 1:
                    notices.append(f"{target} đang sáng trên 100%; thanh trượt giới hạn ở 100%.")
            except ValueError:
                error = "Không đọc được độ sáng xrandr. Kiểm tra driver đồ họa rồi quét lại."
            crtc = re.search(r"(?m)^\s*CRTC:\s*(\d+)\s*$", block)
            if crtc:
                controllers.setdefault(crtc[1], []).append(target)
        displays.append(Display(
            f"xrandr:{target}", _monitor_name(block, target), target,
            "xrandr", target, brightness, error,
        ))

    # Các đầu ra dùng cùng CRTC có chung bảng màu, không thể chỉnh riêng.
    for targets in controllers.values():
        if len(targets) > 1:
            displays = [
                replace(item, error=(
                    f"Các màn hình {', '.join(targets)} dùng chung bộ điều khiển màu. "
                    "Chuyển sang chế độ mở rộng trong cài đặt hiển thị để điều chỉnh riêng."
                )) if item.target in targets else item
                for item in displays
            ]
    return Discovery(tuple(displays), tuple(notices))


class XrandrBackend:
    mode = "software"

    def __init__(
        self,
        runner: Callable[..., CommandResult] = run_command,
        which: Callable[[str], str | None] = shutil.which,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.runner = runner
        self.which = which
        self.environment = os.environ if environment is None else environment

    def discover(self) -> Discovery:
        if is_wayland(self.environment):
            raise BrightnessError(
                "Làm tối bằng xrandr cần phiên X11. Đăng nhập bằng Ubuntu on Xorg "
                "hoặc dùng --mode hardware để điều chỉnh đèn nền trên Wayland."
            )
        if not self.environment.get("DISPLAY"):
            raise BrightnessError("Không có phiên X11. Chạy ứng dụng trong desktop Ubuntu.")
        if self.which("xrandr") is None:
            raise BrightnessError("Chưa cài xrandr. Chạy ./scripts/install.sh để cài phụ thuộc.")
        result = self.runner(["xrandr", "--current", "--verbose"])
        return parse_xrandr(require_success(result, "xrandr"))

    def _current(self, display: Display) -> Display:
        if display.backend != "xrandr" or display.identifier != f"xrandr:{display.target}":
            raise BrightnessError("Mã màn hình không thuộc chế độ xrandr.")
        current = next(
            (item for item in self.discover().displays if item.identifier == display.identifier),
            None,
        )
        if current is None:
            raise BrightnessError("Màn hình đã bị ngắt kết nối. Quét lại để chọn màn hình hiện tại.")
        if not current.available:
            raise BrightnessError(current.error)
        return current

    def read(self, display: Display) -> Brightness:
        return self._current(display).brightness

    def set(self, display: Display, percent: int) -> Brightness:
        validate_percent(percent)
        current = self._current(display)
        result = self.runner([
            "xrandr", "--output", current.target, "--brightness", f"{percent / 100:.2f}",
        ])
        require_success(result, "xrandr")
        return self.read(current)
