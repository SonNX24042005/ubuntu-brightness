"""Đọc đèn nền Linux và điều khiển màn hình rời bằng DDC/CI."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from .models import Brightness, BrightnessError, Discovery, Display, validate_percent


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


def run_command(arguments: list[str], timeout: float = 20) -> CommandResult:
    """Chạy trực tiếp, không qua shell; cố định ngôn ngữ để phân tích đầu ra."""
    environment = os.environ.copy()
    environment.update(LC_ALL="C", LANG="C")
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=environment,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BrightnessError(
            f"Chưa cài {arguments[0]}. Hãy chạy ./scripts/install.sh trong thư mục dự án."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        hint = "Kiểm tra cáp, bật DDC/CI rồi quét lại màn hình." if arguments[0] == "ddcutil" else "Quét lại màn hình rồi thử lại."
        raise BrightnessError(
            f"{arguments[0]} phản hồi quá chậm. {hint}"
        ) from exc
    except OSError as exc:
        raise BrightnessError(f"Không chạy được {arguments[0]}: {exc}") from exc
    return CommandResult(result.returncode, result.stdout, result.stderr)


def require_success(result: CommandResult, tool: str) -> str:
    if result.returncode == 0:
        return result.stdout
    detail = (result.stderr.strip() or result.stdout.strip() or "Không có thông tin lỗi.")
    permission_denied = any(
        word in detail.lower() for word in ("permission", "permitted", "access denied")
    )
    if permission_denied:
        hint = (
            "Chưa có quyền truy cập màn hình. Xem mục quyền truy cập trong README.md "
            "và đăng xuất, đăng nhập lại sau khi thiết lập."
        )
    elif tool == "ddcutil":
        hint = "Không giao tiếp được với màn hình. Kiểm tra cáp, bật DDC/CI rồi quét lại."
    elif tool == "xrandr":
        hint = "Không điều chỉnh được hình ảnh. Kiểm tra phiên X11, driver và kết nối màn hình."
    else:
        hint = "Không điều chỉnh được đèn nền. Kiểm tra driver và quyền truy cập."
    raise BrightnessError(f"{hint}\n{detail[:1200]}")


def parse_vcp(output: str) -> Brightness:
    match = re.search(r"^\s*VCP\s+(?:0x)?10\s+C\s+(\d+)\s+(\d+)\s*$", output, re.M)
    if match is None:
        raise BrightnessError(
            "Màn hình không cung cấp điều khiển độ sáng qua DDC/CI (VCP 0x10). "
            "Thử bật DDC/CI và tắt chế độ tương phản động trong menu màn hình."
        )
    return Brightness(int(match[1]), int(match[2]))


def parse_ddc_displays(output: str) -> list[Display]:
    """Phân tích detect --brief; không chọn số thứ tự có thể thay đổi khi cắm/rút."""
    displays = []
    blocks = re.split(r"(?m)^(?=Display\s+\d+\b|Invalid display\b|Phantom display\b)", output)
    for block in blocks:
        if re.match(r"Display\s+\d+\b", block) is None:
            continue
        bus = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", block)
        usb = re.search(r"USB bus/device:\s*(\d+)[.:/](\d+)", block)
        hiddev = re.search(r"(?:Hiddev|USB device):\s*/dev/usb/hiddev(\d+)", block, re.I)
        if bus:
            target, selector, identifier = bus[1], "--bus", f"ddc:i2c-{bus[1]}"
            connection = f"I²C {bus[1]}"
        elif usb:
            target, selector = f"{usb[1]}.{usb[2]}", "--usb"
            identifier, connection = f"ddc:usb-{target}", f"USB {target}"
        elif hiddev:
            target, selector = hiddev[1], "--hiddev"
            identifier, connection = f"ddc:hiddev-{target}", f"USB hiddev{target}"
        else:
            continue
        monitor = re.search(r"Monitor:\s*(.+)", block)
        parts = monitor[1].strip().split(":", 2) if monitor else []
        name = parts[1].strip() if len(parts) >= 2 else "Màn hình rời"
        serial = parts[2].strip() if len(parts) == 3 else ""
        connector = re.search(r"DRM connector:\s*(\S+)", block)
        if connector:
            connection = f"{connector[1]} · {connection}"
        if serial:
            connection += f" · {serial}"
        displays.append(Display(identifier, name, connection, "ddc", target, selector=selector))
    return displays


@dataclass(frozen=True)
class Connector:
    name: str
    model: str
    bus: str | None

    @property
    def internal(self) -> bool:
        return any(part in self.name for part in ("-eDP-", "-LVDS-", "-DSI-"))


def read_connectors(drm_root: Path) -> list[Connector]:
    connectors = []
    for path in sorted(drm_root.glob("card*-*")):
        try:
            if (path / "status").read_text().strip() != "connected":
                continue
        except OSError:
            continue
        model = re.sub(r"^card\d+-", "", path.name)
        try:
            edid = (path / "edid").read_bytes()
            for offset in (54, 72, 90, 108):
                descriptor = edid[offset : offset + 18]
                if len(descriptor) == 18 and descriptor[:5] == b"\x00\x00\x00\xfc\x00":
                    model = descriptor[5:18].decode("ascii", errors="replace").strip("\n\x00 ")
                    break
        except OSError:
            pass
        ddc_name = (path / "ddc").resolve().name
        match = re.fullmatch(r"i2c-(\d+)", ddc_name)
        connectors.append(Connector(path.name, model, match[1] if match else None))
    return connectors


class HardwareBackend:
    mode = "hardware"

    def __init__(
        self,
        backlight_root: Path = Path("/sys/class/backlight"),
        drm_root: Path = Path("/sys/class/drm"),
        runner: Callable[..., CommandResult] = run_command,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.backlight_root = backlight_root
        self.drm_root = drm_root
        self.runner = runner
        self.which = which

    def discover(self) -> Discovery:
        displays: list[Display] = []
        notices: list[str] = []
        connectors = read_connectors(self.drm_root)
        internal = [connector for connector in connectors if connector.internal]
        backlights = sorted(self.backlight_root.glob("*"))
        has_brightnessctl = self.which("brightnessctl") is not None
        for path in backlights:
            name = internal[0].model if len(backlights) == len(internal) == 1 else "Đèn nền màn hình"
            connection = internal[0].name if len(backlights) == len(internal) == 1 else "Đèn nền"
            display = Display(
                f"backlight:{path.name}", name, f"{connection} · {path.name}", "backlight", path.name
            )
            try:
                display = replace(display, brightness=self.read(display))
                if not has_brightnessctl:
                    display = replace(display, error="Chưa cài brightnessctl. Chạy ./scripts/install.sh.")
            except BrightnessError as exc:
                display = replace(display, error=str(exc))
            displays.append(display)

        ddc_error = ""
        ddc_displays: list[Display] = []
        if self.which("ddcutil") is None:
            ddc_error = "Chưa cài ddcutil. Chạy ./scripts/install.sh để điều khiển màn hình rời."
            notices.append(ddc_error)
        else:
            try:
                result = self.runner(["ddcutil", "detect", "--brief"], timeout=45)
                ddc_displays = parse_ddc_displays(result.stdout)
                # Một số phiên bản vẫn báo thiết bị hợp lệ khi một bus khác bị lỗi.
                diagnostics = result.stdout + "\n" + result.stderr
                permission_warning = any(
                    word in diagnostics.lower()
                    for word in ("permission denied", "access denied", "eacces")
                )
                # ddcutil 1.4.1 có thể trả mã 0 cùng lỗi quyền trên stderr.
                if not ddc_displays and (
                    result.returncode or result.stderr.strip() or permission_warning
                ):
                    require_success(replace(result, returncode=1), "ddcutil")
                if ddc_displays and (result.returncode or permission_warning):
                    notices.append(
                        "Một số bus không truy cập được. Xem mục quyền truy cập trong README.md. "
                        "Các màn hình hợp lệ vẫn được liệt kê."
                    )
                for display in ddc_displays:
                    connector = next(
                        (item for item in connectors if item.bus == display.target and display.selector == "--bus"),
                        None,
                    )
                    if connector and connector.name not in display.connection:
                        display = replace(display, connection=f"{connector.name} · {display.connection}")
                    try:
                        display = replace(display, brightness=self.read(display))
                    except BrightnessError as exc:
                        display = replace(display, error=str(exc))
                    displays.append(display)
                if not ddc_displays:
                    ddc_error = (
                        "Không phát hiện màn hình DDC/CI. Bật DDC/CI trong menu màn hình, "
                        "kiểm tra cáp và quyền I²C rồi quét lại."
                    )
                    if any(not item.internal for item in connectors):
                        notices.append(ddc_error)
            except BrightnessError as exc:
                ddc_error = str(exc)
                notices.append(ddc_error)

        ddc_buses = {item.target for item in ddc_displays if item.selector == "--bus"}
        for connector in connectors:
            if connector.internal and backlights:
                continue
            if connector.bus in ddc_buses or any(
                connector.name in item.connection for item in ddc_displays
            ):
                continue
            error = (
                "Driver chưa cung cấp thiết bị đèn nền cho màn hình này."
                if connector.internal
                else ddc_error or "Màn hình này không cung cấp DDC/CI qua kết nối hiện tại."
            )
            displays.append(
                Display(f"connector:{connector.name}", connector.model, connector.name, "unsupported", "", error=error)
            )
        return Discovery(tuple(displays), tuple(notices))

    def read(self, display: Display) -> Brightness:
        if display.backend == "backlight":
            path = self.backlight_root / display.target
            try:
                return Brightness(
                    int((path / "brightness").read_text()),
                    int((path / "max_brightness").read_text()),
                )
            except (OSError, ValueError) as exc:
                raise BrightnessError("Không đọc được đèn nền. Thiết bị có thể đã bị ngắt kết nối.") from exc
        if display.backend == "ddc":
            result = self.runner(["ddcutil", display.selector, display.target, "getvcp", "10", "--terse"])
            return parse_vcp(require_success(result, "ddcutil"))
        raise BrightnessError(display.error or "Màn hình chưa hỗ trợ điều khiển độ sáng.")

    def set(self, display: Display, percent: int) -> Brightness:
        validate_percent(percent)
        if not display.available:
            raise BrightnessError(display.error or "Chưa đọc được độ sáng của màn hình.")
        if display.backend == "backlight":
            brightness = self.read(display)
            result = self.runner([
                "brightnessctl", "--class=backlight", f"--device={display.target}",
                "--machine-readable", "set", str(brightness.raw_value(percent)),
            ])
            require_success(result, "brightnessctl")
        elif display.backend == "ddc":
            result = self.runner([
                "ddcutil", display.selector, display.target, "setvcp", "10",
                str(display.brightness.raw_value(percent)),
            ])
            require_success(result, "ddcutil")
        else:
            raise BrightnessError("Màn hình chưa hỗ trợ điều khiển độ sáng.")
        return self.read(display)


class DemoBackend:
    """Thiết bị giả lập, không chạy lệnh hay truy cập phần cứng."""

    def __init__(self) -> None:
        self.displays = {
            item.identifier: item
            for item in (
                Display("demo:laptop", "Màn hình laptop", "eDP-1 · Màn hình tích hợp", "demo", "laptop", Brightness(72, 100)),
                Display("demo:dell", "Dell P2722H", "HDMI-1 · Màn hình rời", "demo", "dell", Brightness(58, 100)),
                Display("demo:asus", "ASUS ProArt", "DP-1 · Màn hình rời", "demo", "asus", Brightness(85, 100)),
            )
        }

    def discover(self) -> Discovery:
        return Discovery(tuple(self.displays.values()))

    def read(self, display: Display) -> Brightness:
        return self.displays[display.identifier].brightness

    def set(self, display: Display, percent: int) -> Brightness:
        validate_percent(percent)
        brightness = Brightness(percent, 100)
        self.displays[display.identifier] = replace(display, brightness=brightness)
        return brightness
