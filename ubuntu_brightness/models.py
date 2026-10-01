"""Kiểu dữ liệu dùng chung cho giao diện và công cụ điều khiển."""

from dataclasses import dataclass


class BrightnessError(Exception):
    """Lỗi có thể hiển thị trực tiếp cho người dùng."""


def validate_percent(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise BrightnessError("Độ sáng phải là số nguyên từ 0 đến 100%.")
    return value


@dataclass(frozen=True)
class Brightness:
    current: int
    maximum: int

    def __post_init__(self) -> None:
        if self.maximum <= 0 or not 0 <= self.current <= self.maximum:
            raise BrightnessError("Thiết bị trả về giá trị độ sáng không hợp lệ.")

    @property
    def percent(self) -> int:
        return int(self.current * 100 / self.maximum + 0.5)

    def raw_value(self, percent: int) -> int:
        validate_percent(percent)
        if percent == 0:
            return 0
        return min(self.maximum, max(1, int(self.maximum * percent / 100 + 0.5)))


@dataclass(frozen=True)
class Display:
    identifier: str
    name: str
    connection: str
    backend: str
    target: str
    brightness: Brightness | None = None
    error: str = ""
    selector: str = "--bus"

    @property
    def internal(self) -> bool:
        return self.backend == "backlight" or self.target == "laptop" or (
            self.backend == "xrandr" and self.target.startswith(("eDP", "LVDS", "DSI"))
        )

    @property
    def available(self) -> bool:
        return self.brightness is not None and not self.error


@dataclass(frozen=True)
class Discovery:
    displays: tuple[Display, ...]
    notices: tuple[str, ...] = ()
