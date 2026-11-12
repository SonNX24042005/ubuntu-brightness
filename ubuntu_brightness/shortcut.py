"""Phím tắt toàn cục: extension GNOME Shell (cả màn hình khóa) hoặc custom shortcut của GNOME."""

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .models import BrightnessError

MEDIA_KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA = MEDIA_KEYS_SCHEMA + ".custom-keybinding"
CUSTOM_ROOT = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
SHORTCUT_PATH = CUSTOM_ROOT + "ubuntu-brightness-reset/"
SHORTCUT_NAME = "Độ sáng màn hình: đưa tất cả về 100%"
DEFAULT_BINDING = "<Super><Alt>0"

EXTENSION_UUID = "ubuntu-brightness@ubuntubrightness.github.io"
EXTENSION_SCHEMA = "org.gnome.shell.extensions.ubuntu-brightness"
EXTENSION_KEY = "reset-all"
EXTENSION_FILES = (
    "metadata.json",
    "extension.js",
    f"schemas/{EXTENSION_SCHEMA}.gschema.xml",
)
EXTENSION_ACTIVE = 1
EXTENSION_ERROR = 3
EXTENSION_OUT_OF_DATE = 4

# Các nhóm phím tắt hệ thống thường gặp trên Ubuntu để cảnh báo trùng lặp.
SYSTEM_SCHEMAS = (
    "org.gnome.desktop.wm.keybindings",
    "org.gnome.shell.keybindings",
    "org.gnome.mutter.keybindings",
    "org.gnome.mutter.wayland.keybindings",
    MEDIA_KEYS_SCHEMA,
    "org.gnome.shell.extensions.dash-to-dock",
)


@dataclass(frozen=True)
class ShortcutState:
    installed: bool
    binding: str
    command: str
    lock_screen: bool = False


def _schema(schema_id: str):
    source = Gio.SettingsSchemaSource.get_default()
    return source.lookup(schema_id, True) if source else None


def available() -> bool:
    return _schema(MEDIA_KEYS_SCHEMA) is not None and _schema(CUSTOM_SCHEMA) is not None


def _require() -> None:
    if not available():
        raise BrightnessError(
            "Không tìm thấy cài đặt phím tắt của GNOME. Phím tắt toàn cục cần desktop Ubuntu GNOME."
        )


def reset_command() -> str:
    run_script = Path(__file__).resolve().parent.parent / "run.sh"
    return f"{shlex.quote(str(run_script))} reset"


def normalize(accelerator: str) -> str:
    """Trả về tên chuẩn của tổ hợp phím, hoặc chuỗi rỗng nếu không hợp lệ."""
    ok, key, mods = Gtk.accelerator_parse(accelerator)
    if not ok or key == 0:
        return ""
    return Gtk.accelerator_name(key, mods)


def display_label(accelerator: str) -> str:
    ok, key, mods = Gtk.accelerator_parse(accelerator) if accelerator else (False, 0, 0)
    return Gtk.accelerator_get_label(key, mods) if ok and key else "Chưa đặt"


def extension_source() -> Path:
    return Path(__file__).resolve().parent.parent / "gnome-extension"


def extension_dir() -> Path:
    data_root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return data_root / "gnome-shell" / "extensions" / EXTENSION_UUID


def extension_info() -> dict:
    """Trạng thái extension do GNOME Shell đang chạy báo về; rỗng nếu Shell chưa nạp."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync(
            "org.gnome.Shell",
            "/org/gnome/Shell",
            "org.gnome.Shell.Extensions",
            "GetExtensionInfo",
            GLib.Variant("(s)", (EXTENSION_UUID,)),
            GLib.VariantType.new("(a{sv})"),
            Gio.DBusCallFlags.NO_AUTO_START,
            1000,
            None,
        )
    except GLib.Error:
        return {}
    return reply.unpack()[0]


def extension_active() -> bool:
    return int(extension_info().get("state", 0)) == EXTENSION_ACTIVE


def install_extension() -> None:
    """Chép extension vào thư mục người dùng, biên dịch schema và bật trong GNOME Shell."""
    source, target = extension_source(), extension_dir()
    changed = False
    for name in EXTENSION_FILES:
        data = (source / name).read_bytes()
        destination = target / name
        if not destination.is_file() or destination.read_bytes() != data:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            changed = True
    if changed or not (target / "schemas" / "gschemas.compiled").is_file():
        compiler = shutil.which("glib-compile-schemas")
        if compiler is None:
            raise BrightnessError("Thiếu glib-compile-schemas. Cài gói libglib2.0-bin rồi thử lại.")
        subprocess.run([compiler, str(target / "schemas")], check=True, capture_output=True)
    shell = Gio.Settings.new("org.gnome.shell")
    enabled = shell.get_strv("enabled-extensions")
    if EXTENSION_UUID not in enabled:
        shell.set_strv("enabled-extensions", [*enabled, EXTENSION_UUID])
    disabled = shell.get_strv("disabled-extensions")
    if EXTENSION_UUID in disabled:
        shell.set_strv("disabled-extensions", [item for item in disabled if item != EXTENSION_UUID])


def extension_settings() -> Gio.Settings | None:
    schemas = extension_dir() / "schemas"
    if not (schemas / "gschemas.compiled").is_file():
        return None
    try:
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(schemas), Gio.SettingsSchemaSource.get_default(), False
        )
    except GLib.Error:
        return None
    schema = source.lookup(EXTENSION_SCHEMA, False)
    return Gio.Settings.new_full(schema, None, None) if schema else None


def extension_status() -> str:
    """Mô tả ngắn vì sao phím tắt chưa dùng được ở màn hình khóa; rỗng khi đã dùng được."""
    info = extension_info()
    state = int(info.get("state", 0))
    if state == EXTENSION_ACTIVE:
        return ""
    if state == EXTENSION_ERROR:
        return f"Extension báo lỗi: {info.get('error', 'không rõ')}."
    if state == EXTENSION_OUT_OF_DATE:
        return "Extension chưa hỗ trợ phiên bản GNOME Shell này."
    if Gio.Settings.new("org.gnome.shell").get_boolean("disable-user-extensions"):
        return "GNOME đang tắt mọi extension. Bật lại trong ứng dụng Extensions."
    if not extension_dir().is_dir():
        return "Chưa cài extension cho màn hình khóa."
    return (
        "Để dùng ở màn hình khóa, khởi động lại GNOME Shell một lần: nhấn Alt+F2, gõ r rồi Enter "
        "(trên X11), hoặc đăng xuất rồi đăng nhập lại."
    )


def _custom(path: str) -> Gio.Settings:
    return Gio.Settings.new_with_path(CUSTOM_SCHEMA, path)


def _remove_custom() -> None:
    media_keys = Gio.Settings.new(MEDIA_KEYS_SCHEMA)
    paths = media_keys.get_strv("custom-keybindings")
    if SHORTCUT_PATH in paths:
        media_keys.set_strv("custom-keybindings", [item for item in paths if item != SHORTCUT_PATH])
        settings = _custom(SHORTCUT_PATH)
        for key in ("name", "command", "binding"):
            settings.reset(key)


def read() -> ShortcutState:
    _require()
    if extension_active():
        settings = extension_settings()
        if settings is not None:
            values = settings.get_strv(EXTENSION_KEY)
            return ShortcutState(
                True, values[0] if values else "", settings.get_string("command"), True
            )
    paths = Gio.Settings.new(MEDIA_KEYS_SCHEMA).get_strv("custom-keybindings")
    if SHORTCUT_PATH not in paths:
        return ShortcutState(False, "", "")
    settings = _custom(SHORTCUT_PATH)
    return ShortcutState(True, settings.get_string("binding"), settings.get_string("command"))


def write(binding: str) -> ShortcutState:
    """Tạo hoặc cập nhật phím tắt; chuỗi rỗng giữ mục đã tạo nhưng tắt phím."""
    _require()
    if binding:
        binding = normalize(binding)
        if not binding:
            raise BrightnessError("Tổ hợp phím không hợp lệ, ví dụ đúng: <Super><Alt>0.")
    # Extension luôn giữ bản sao mới nhất để dùng ngay khi GNOME Shell nạp nó.
    settings = extension_settings()
    if settings is not None:
        settings.set_strv(EXTENSION_KEY, [binding] if binding else [])
        settings.set_string("command", reset_command())
    if extension_active() and settings is not None:
        _remove_custom()
    else:
        media_keys = Gio.Settings.new(MEDIA_KEYS_SCHEMA)
        custom = _custom(SHORTCUT_PATH)
        custom.set_string("name", SHORTCUT_NAME)
        custom.set_string("command", reset_command())
        custom.set_string("binding", binding)
        paths = media_keys.get_strv("custom-keybindings")
        if SHORTCUT_PATH not in paths:
            media_keys.set_strv("custom-keybindings", [*paths, SHORTCUT_PATH])
    Gio.Settings.sync()
    return read()


def ensure() -> ShortcutState:
    """Cài extension, tạo phím mặc định khi chưa có và cập nhật lệnh nếu thư mục dự án đã đổi."""
    _require()
    try:
        install_extension()
    except (OSError, subprocess.CalledProcessError, GLib.Error):
        # Không có extension thì vẫn dùng custom shortcut, chỉ thiếu màn hình khóa.
        pass
    state = read()
    if not state.installed:
        settings = extension_settings()
        if settings is not None:
            values = settings.get_strv(EXTENSION_KEY)
            return write(values[0] if values else "")
        return write(DEFAULT_BINDING)
    # Khi extension đã giữ phím, mục custom shortcut cũ phải được gỡ để không tranh phím.
    leftover = state.lock_screen and SHORTCUT_PATH in Gio.Settings.new(
        MEDIA_KEYS_SCHEMA
    ).get_strv("custom-keybindings")
    if leftover or state.command != reset_command():
        return write(state.binding)
    return state


def conflicts(binding: str) -> list[str]:
    """Liệt kê phím tắt GNOME khác đang dùng cùng tổ hợp phím."""
    target = normalize(binding)
    if not target or not available():
        return []
    found = []
    for path in Gio.Settings.new(MEDIA_KEYS_SCHEMA).get_strv("custom-keybindings"):
        if path == SHORTCUT_PATH:
            continue
        settings = _custom(path)
        if normalize(settings.get_string("binding")) == target:
            found.append(settings.get_string("name") or path)
    for schema_id in SYSTEM_SCHEMAS:
        schema = _schema(schema_id)
        if schema is None:
            continue
        settings = Gio.Settings.new(schema_id)
        for key in schema.list_keys():
            value = settings.get_value(key)
            kind = value.get_type_string()
            if kind == "s":
                values = [value.unpack()]
            elif kind == "as":
                values = value.unpack()
            else:
                continue
            if any(normalize(item) == target for item in values if item):
                summary = schema.get_key(key).get_summary()
                found.append(summary or f"{schema_id} {key}")
    return found
