"""Giao diện GTK 4 với lựa chọn màn hình và thanh trượt độ sáng."""

from dataclasses import replace
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from .controller import Controller
from .models import BrightnessError, Display


def label(text: str = "", css: str = "", xalign: float = 0) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=xalign)
    if css:
        widget.add_css_class(css)
    return widget


def dispatch(callback, *arguments) -> None:
    GLib.idle_add(callback, *arguments)


class BrightnessWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, backend, demo: bool = False) -> None:
        super().__init__(application=application, title="Độ sáng màn hình")
        self.set_default_size(880, 720)
        self.set_size_request(720, 560)
        self.add_css_class("brightness-window")
        self.software = getattr(backend, "mode", "") == "software"
        self.controller = Controller(backend, dispatch)
        self.displays: dict[str, Display] = {}
        self.rows = {}
        self.original: dict[str, int] = {}
        self.wanted: dict[str, int] = {}
        self.write_errors: dict[str, str] = {}
        self._scanning = False
        self._updating = False
        self._rebuilding = False
        self._closing = False
        self._closed = False
        self._debounce = None
        self._debounced = None
        self._build_ui(demo)
        self.connect("close-request", self._on_close)
        self.refresh()

    def _build_ui(self, demo: bool) -> None:
        header = Gtk.HeaderBar()
        header.set_title_widget(label("Độ sáng màn hình", "header-title", 0.5))
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Quét lại màn hình (Ctrl+R)")
        self.refresh_button.connect("clicked", lambda _button: self.refresh())
        header.pack_end(self.refresh_button)
        help_button = Gtk.Button.new_from_icon_name("help-about-symbolic")
        help_button.set_tooltip_text("Hướng dẫn sử dụng")
        help_button.connect("clicked", self._show_help)
        header.pack_end(help_button)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)
        if demo:
            banner = label("Chế độ xem thử · Các màn hình bên dưới được giả lập", "demo-banner", 0.5)
            root.append(banner)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        root.append(content)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        sidebar.set_size_request(245, -1)
        sidebar.add_css_class("sidebar")
        sidebar.append(label("Màn hình của bạn", "section-title"))
        self.count_label = label("Đang tìm màn hình…", "muted")
        sidebar.append(self.count_label)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("display-list")
        self.listbox.connect("row-selected", self._on_selected)
        sidebar_scroll = Gtk.ScrolledWindow(vexpand=True)
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_child(self.listbox)
        sidebar.append(sidebar_scroll)
        note = label("Chọn một màn hình để điều chỉnh độ sáng riêng.", "muted")
        note.set_wrap(True)
        note.set_max_width_chars(27)
        sidebar.append(note)
        content.append(sidebar)

        main_scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        main_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main.add_css_class("main-panel")
        main_scroll.set_child(main)
        content.append(main_scroll)

        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.name_label = label("Đang tìm màn hình…", "display-title")
        self.name_label.set_wrap(True)
        self.connection_label = label("", "muted")
        self.connection_label.set_wrap(True)
        heading.append(self.name_label)
        heading.append(self.connection_label)
        main.append(heading)

        self.error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.error_box.add_css_class("error-box")
        self.error_label = label()
        self.error_label.set_wrap(True)
        self.error_label.set_selectable(True)
        self.error_label.set_max_width_chars(65)
        self.error_box.append(self.error_label)
        self.error_box.set_visible(False)
        main.append(self.error_box)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("brightness-card")
        monitor = Gtk.Image.new_from_icon_name("video-display-symbolic")
        monitor.set_pixel_size(72)
        monitor.add_css_class("monitor-art")
        card.append(monitor)
        self.percent_label = label("—", "brightness-value", 0.5)
        card.append(self.percent_label)
        card.append(label("Độ sáng màn hình", "muted", 0.5))
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.set_tooltip_text("Điều chỉnh độ sáng từ 0 đến 100%")
        self.scale.connect("value-changed", self._on_scale_changed)
        card.append(self.scale)
        ends = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ends.append(label("0%", "muted"))
        ends.append(Gtk.Box(hexpand=True))
        ends.append(label("100%", "muted"))
        card.append(ends)

        self.presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)
        for percent in (0, 25, 50, 75, 100):
            button = Gtk.Button(label=f"{percent}%")
            if percent == 100:
                button.set_tooltip_text("Đưa màn hình đã chọn về 100% (Ctrl+0)")
            button.connect("clicked", lambda _button, value=percent: self.scale.set_value(value))
            self.presets.append(button)
        card.append(self.presets)
        hint = label(
            "Làm tối hình ảnh · 0% = ảnh đen\nCtrl+0: đưa màn hình đã chọn về 100%"
            if self.software else "Điều chỉnh đèn nền của màn hình",
            "muted", 0.5,
        )
        hint.set_wrap(True)
        card.append(hint)
        main.append(card)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.restore_button = Gtk.Button(label="Khôi phục mức ban đầu")
        self.restore_button.set_tooltip_text("Khôi phục độ sáng được đọc khi mở ứng dụng")
        self.restore_button.connect("clicked", self._restore)
        actions.append(self.restore_button)
        main.append(actions)
        self.display_status = label("Đang đọc thông tin màn hình…", "muted")
        self.display_status.set_wrap(True)
        main.append(self.display_status)
        main.append(Gtk.Box(vexpand=True))

        self.notice_label = label("", "notice")
        self.notice_label.set_wrap(True)
        self.notice_label.set_visible(False)
        root.append(self.notice_label)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer.add_css_class("footer")
        self.spinner = Gtk.Spinner()
        footer.append(self.spinner)
        self.sync_label = label("Đang quét màn hình…", "muted")
        footer.append(self.sync_label)
        footer.append(Gtk.Box(hexpand=True))
        footer.append(label(
            "X11 · Làm tối bằng xrandr" if self.software else "Ubuntu 24.04 · Độ sáng đèn nền",
            "muted",
        ))
        root.append(footer)
        self._render(None)

    @property
    def selected(self) -> Display | None:
        row = self.listbox.get_selected_row()
        return self.displays.get(row.identifier) if row else None

    def refresh(self) -> None:
        if self._scanning or self.controller.busy or self._debounce or self._closing:
            return
        self._scanning = True
        self._update_busy()
        self.listbox.set_sensitive(False)
        self.scale.set_sensitive(False)
        self.presets.set_sensitive(False)
        self.restore_button.set_sensitive(False)
        self.controller.discover(self._on_discovery)

    def _on_discovery(self, discovery, error) -> None:
        if self._closed:
            return
        previous = self.selected.identifier if self.selected else None
        self._scanning = False
        if error:
            self.notice_label.set_text(str(error))
            self.notice_label.set_visible(True)
            self._render(self.selected)
        else:
            self._rebuilding = True
            child = self.listbox.get_first_child()
            while child:
                self.listbox.remove(child)
                child = self.listbox.get_first_child()
            self.displays = {item.identifier: item for item in discovery.displays}
            self.rows.clear()
            self.write_errors.clear()
            for display in discovery.displays:
                if display.brightness:
                    self.original.setdefault(display.identifier, display.brightness.percent)
                self._append_display(display)
            self.count_label.set_text(f"{len(discovery.displays)} màn hình được phát hiện")
            text = "\n".join(notice.splitlines()[0] for notice in discovery.notices)
            self.notice_label.set_text(text)
            self.notice_label.set_visible(bool(text))
            self._rebuilding = False
            row = self.rows.get(previous, (None, None))[0]
            if row is None:
                available = next((item for item in discovery.displays if item.available), None)
                row = self.rows[available.identifier][0] if available else self.listbox.get_row_at_index(0)
            self.listbox.select_row(row)
            self._render(self.selected)
        self.listbox.set_sensitive(not self._closing)
        self._update_busy()

    def _append_display(self, display: Display) -> None:
        row = Gtk.ListBoxRow()
        row.identifier = display.identifier
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.add_css_class("display-row")
        icon_name = "computer-symbolic" if display.internal else "video-display-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(22)
        box.append(icon)
        description = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, hexpand=True)
        name = label(display.name, "row-title")
        name.set_ellipsize(3)
        name.set_max_width_chars(18)
        description.append(name)
        category = "Màn hình tích hợp" if display.internal else "Màn hình rời"
        description.append(label(category if display.available else "Chưa hỗ trợ", "row-subtitle"))
        box.append(description)
        value = label(f"{display.brightness.percent}%" if display.brightness else "—", "row-value")
        box.append(value)
        row.set_tooltip_text(f"{display.name}\n{display.connection}")
        row.set_child(box)
        self.listbox.append(row)
        self.rows[display.identifier] = (row, value)

    def _on_selected(self, _listbox, _row) -> None:
        if self._rebuilding:
            return
        # Gửi yêu cầu đã gắn với màn hình cũ trước khi hiển thị màn hình mới.
        if self._debounce:
            GLib.source_remove(self._debounce)
            self._flush_debounce()
        self._render(self.selected)

    def _render(self, display: Display | None) -> None:
        self._updating = True
        available = bool(display and display.available and not self._scanning and not self._closing)
        self.scale.set_sensitive(available)
        self.presets.set_sensitive(available)
        self.restore_button.set_sensitive(available)
        if display is None:
            self.name_label.set_text("Đang tìm màn hình…" if self._scanning else "Chưa tìm thấy màn hình")
            self.connection_label.set_text("Kết nối màn hình rồi nhấn nút quét lại.")
            self.percent_label.set_text("—")
            self.error_box.set_visible(False)
            self.display_status.set_text("Cài các công cụ cần thiết bằng ./scripts/install.sh.")
        else:
            self.name_label.set_text(display.name)
            self.connection_label.set_text(
                f"{display.connection} · Làm tối bằng xrandr" if display.backend == "xrandr"
                else display.connection
            )
            value = self.wanted.get(display.identifier)
            if value is None and display.brightness:
                value = display.brightness.percent
            self.percent_label.set_text(f"{value}%" if value is not None else "—")
            self.scale.set_value(value if value is not None else 50)
            error = self.write_errors.get(display.identifier, display.error)
            self.error_label.set_text(error)
            self.error_box.set_visible(bool(error))
            if display.identifier in self.wanted:
                self.display_status.set_text("Đang áp dụng độ sáng cho màn hình này…")
            elif error:
                self.display_status.set_text("Kiểm tra hướng dẫn rồi thử lại hoặc quét lại màn hình.")
            else:
                self.display_status.set_text("Sẵn sàng · Chỉ điều chỉnh màn hình đã chọn")
        self._updating = False

    def _on_scale_changed(self, scale) -> None:
        display = self.selected
        if self._updating or not display or not display.available or self._closing:
            return
        percent = int(scale.get_value() + 0.5)
        self.wanted[display.identifier] = percent
        self.percent_label.set_text(f"{percent}%")
        self.display_status.set_text("Đang áp dụng độ sáng cho màn hình này…")
        if self._debounce:
            GLib.source_remove(self._debounce)
        self._debounced = (display, percent)
        self._debounce = GLib.timeout_add(350, self._flush_debounce)
        self._update_busy()

    def _flush_debounce(self) -> bool:
        self._debounce = None
        request = self._debounced
        self._debounced = None
        if request:
            self.controller.set(*request, self._on_applied)
        self._update_busy()
        return False

    def _on_applied(self, identifier, requested, brightness, error) -> None:
        if self._closed:
            return
        display = self.displays.get(identifier)
        if display is None:
            return
        if brightness:
            self.displays[identifier] = replace(display, brightness=brightness)
            self.rows[identifier][1].set_text(f"{brightness.percent}%")
        if self.wanted.get(identifier) == requested:
            self.wanted.pop(identifier, None)
            if error:
                self.write_errors[identifier] = str(error)
            else:
                self.write_errors.pop(identifier, None)
        if self.selected and self.selected.identifier == identifier:
            self._render(self.selected)
        self._update_busy()

    def _restore(self, _button) -> None:
        display = self.selected
        if display and display.identifier in self.original:
            self.scale.set_value(self.original[display.identifier])

    def reset_to_full(self) -> None:
        if self.selected and self.selected.available and not self._scanning and not self._closing:
            self.scale.set_value(100)

    def _update_busy(self) -> None:
        busy = self._scanning or self.controller.busy or self._debounce is not None
        self.refresh_button.set_sensitive(not busy and not self._closing)
        if busy:
            self.spinner.start()
            self.sync_label.set_text("Đang quét màn hình…" if self._scanning else "Đang áp dụng độ sáng…")
        else:
            self.spinner.stop()
            self.sync_label.set_text("Sẵn sàng")
        if self._closing:
            self.sync_label.set_text("Đang hoàn tất thay đổi trước khi đóng…")

    def _show_help(self, _button) -> None:
        help_window = Gtk.Window(title="Hướng dẫn sử dụng", transient_for=self, modal=True)
        help_window.set_default_size(490, 350)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.add_css_class("main-panel")
        box.append(label("Điều chỉnh từng màn hình", "display-title"))
        mode_help = (
            "Làm tối bằng xrandr: 0% cho ảnh đen, 100% bỏ làm tối hình ảnh. "
            "Đèn nền vẫn giữ mức đang có. Dùng Ctrl+0 khi cửa sổ đang được chọn "
            "để đưa màn hình về 100%.\n\n"
            if self.software else
            "Màn hình rời cần hỗ trợ và bật DDC/CI trong menu của màn hình. "
            "Mức đèn nền 0% có thể vẫn sáng tùy thiết bị.\n\n"
        )
        instructions = label(
            "1. Chọn màn hình trong danh sách bên trái.\n\n"
            "2. Kéo thanh trượt hoặc chọn một mức sáng có sẵn. "
            "Thay đổi được áp dụng sau khi bạn ngừng kéo một lát.\n\n"
            "3. Nhấn nút quét lại sau khi cắm hoặc rút màn hình.\n\n"
            + mode_help +
            "Nếu báo thiếu công cụ hoặc thiếu quyền, xem README.md trong thư mục dự án.\n\n"
            "Ctrl+0: về 100%. Ctrl+R: quét lại. Ctrl+Q: đóng ứng dụng."
        )
        instructions.set_wrap(True)
        instructions.set_max_width_chars(60)
        box.append(instructions)
        close = Gtk.Button(label="Đã hiểu", halign=Gtk.Align.END)
        close.connect("clicked", lambda _button: help_window.close())
        box.append(close)
        help_window.set_child(box)
        help_window.present()

    def _on_close(self, _window) -> bool:
        if self._closing:
            return True
        if self._debounce:
            GLib.source_remove(self._debounce)
            self._flush_debounce()
        self._closing = True
        self.listbox.set_sensitive(False)
        self._render(self.selected)
        self._update_busy()
        GLib.timeout_add(50, self._finish_close)
        return True

    def _finish_close(self) -> bool:
        if self.controller.busy or self._scanning:
            return True
        self._closed = True
        self.controller.close()
        self.get_application().quit()
        return False


class BrightnessApplication(Gtk.Application):
    def __init__(self, backend, demo: bool = False) -> None:
        application_id = "io.github.ubuntubrightness.demo" if demo else "io.github.ubuntubrightness"
        if not demo and getattr(backend, "mode", "") == "hardware":
            application_id += ".hardware"
        super().__init__(application_id=application_id, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.backend = backend
        self.demo = demo
        self.window = None
        for name in ("refresh", "quit", "full-brightness"):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", self._on_action)
            self.add_action(action)
        self.set_accels_for_action("app.refresh", ["<Primary>r"])
        self.set_accels_for_action("app.quit", ["<Primary>q"])
        self.set_accels_for_action("app.full-brightness", ["<Primary>0"])

    def _on_action(self, action, _parameter) -> None:
        if self.window:
            if action.get_name() == "refresh":
                self.window.refresh()
            elif action.get_name() == "full-brightness":
                self.window.reset_to_full()
            else:
                self.window.close()

    def do_activate(self) -> None:
        if self.window is None:
            css = Gtk.CssProvider()
            css.load_from_path(str(Path(__file__).with_name("style.css")))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self.window = BrightnessWindow(self, self.backend, self.demo)
        self.window.present()


def launch(backend, demo: bool = False) -> int:
    if not Gtk.init_check():
        raise BrightnessError("Không có phiên đồ họa. Mở ứng dụng trong desktop Ubuntu hoặc dùng lệnh list/set.")
    GLib.set_application_name("Độ sáng màn hình")
    return BrightnessApplication(backend, demo).run([])
