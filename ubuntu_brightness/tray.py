"""Biểu tượng khay hệ thống (StatusNotifierItem + DBusMenu) trên thanh trên Ubuntu."""

from typing import Callable

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

SNI_WATCHER_BUS = "org.kde.StatusNotifierWatcher"
SNI_WATCHER_PATH = "/StatusNotifierWatcher"
SNI_WATCHER_IFACE = "org.kde.StatusNotifierWatcher"
SNI_PATH = "/StatusNotifierItem"
SNI_IFACE = "org.kde.StatusNotifierItem"
MENU_PATH = "/MenuBar"
MENU_IFACE = "com.canonical.dbusmenu"

SNI_NODE_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ProvideXdgActivationToken">
      <arg name="token" type="s" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="XAyatanaSecondaryActivate">
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
  </interface>
</node>
"""

MENU_NODE_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
  </interface>
</node>
"""


class TrayIcon:
    """Đăng ký biểu tượng thanh tác vụ qua giao thức StatusNotifierItem chuẩn."""

    def __init__(
        self,
        app_id: str,
        on_toggle_window: Callable[[], None],
        on_set_display: Callable[[str, int], None],
        on_reset_all: Callable[[], None],
        on_refresh: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.app_id = app_id
        self._on_toggle_window = on_toggle_window
        self._on_set_display = on_set_display
        self._on_reset_all = on_reset_all
        self._on_refresh = on_refresh
        self._on_quit = on_quit
        self._window_visible = True
        self._displays: list[tuple[str, str, int | None, bool]] = []
        self._revision = 1
        self._nodes: dict[int, tuple[dict[str, GLib.Variant], list[int]]] = {}
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._bus: Gio.DBusConnection | None = None
        self._sni_reg = 0
        self._menu_reg = 0
        self._watcher_id = 0
        self._closed = False
        self._rebuild_tree()
        self._register()

    def _register(self) -> None:
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            sni_info = Gio.DBusNodeInfo.new_for_xml(SNI_NODE_XML).interfaces[0]
            menu_info = Gio.DBusNodeInfo.new_for_xml(MENU_NODE_XML).interfaces[0]
            self._sni_reg = self._bus.register_object(
                SNI_PATH, sni_info, self._on_sni_method, self._on_sni_prop, None
            )
            self._menu_reg = self._bus.register_object(
                MENU_PATH, menu_info, self._on_menu_method, self._on_menu_prop, None
            )
            self._watcher_id = Gio.bus_watch_name_on_connection(
                self._bus,
                SNI_WATCHER_BUS,
                Gio.BusNameWatcherFlags.NONE,
                self._on_watcher_appeared,
                None,
            )
        except GLib.Error:
            self.close()

    def _on_watcher_appeared(self, connection: Gio.DBusConnection, *_args) -> None:
        if self._closed:
            return
        try:
            connection.call(
                SNI_WATCHER_BUS,
                SNI_WATCHER_PATH,
                SNI_WATCHER_IFACE,
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (SNI_PATH,)),
                None,
                Gio.DBusCallFlags.NONE,
                2000,
                None,
                None,
            )
        except GLib.Error:
            pass

    def update(
        self,
        window_visible: bool,
        displays: list[tuple[str, str, int | None, bool]],
    ) -> None:
        if self._closed:
            return
        if self._window_visible == window_visible and self._displays == displays:
            return
        self._window_visible = window_visible
        self._displays = list(displays)
        self._rebuild_tree()
        self._revision += 1
        if self._bus is not None and self._menu_reg:
            updated = [
                (item_id, dict(props))
                for item_id, (props, _) in self._nodes.items()
                if item_id != 0
            ]
            try:
                self._bus.emit_signal(
                    None,
                    MENU_PATH,
                    MENU_IFACE,
                    "ItemsPropertiesUpdated",
                    GLib.Variant("(a(ia{sv})a(ias))", (updated, [])),
                )
                self._bus.emit_signal(
                    None,
                    MENU_PATH,
                    MENU_IFACE,
                    "LayoutUpdated",
                    GLib.Variant("(ui)", (self._revision, 0)),
                )
            except GLib.Error:
                pass

    def _rebuild_tree(self) -> None:
        nodes: dict[int, tuple[dict[str, GLib.Variant], list[int]]] = {}
        callbacks: dict[int, Callable[[], None]] = {}
        root_children: list[int] = []

        def add_item(
            item_id: int,
            text: str = "",
            enabled: bool = True,
            item_type: str = "standard",
            children: list[int] | None = None,
            callback: Callable[[], None] | None = None,
        ) -> int:
            props: dict[str, GLib.Variant] = {
                "visible": GLib.Variant("b", True),
                "enabled": GLib.Variant("b", enabled),
                "type": GLib.Variant("s", item_type),
            }
            if item_type != "separator":
                props["label"] = GLib.Variant("s", text)
            if children is not None:
                props["children-display"] = GLib.Variant("s", "submenu")
            nodes[item_id] = (props, children or [])
            if callback is not None:
                callbacks[item_id] = callback
            return item_id

        toggle_text = (
            "Ẩn cửa sổ điều chỉnh" if self._window_visible else "Mở cửa sổ điều chỉnh"
        )
        root_children.append(add_item(1, toggle_text, callback=self._on_toggle_window))

        available_count = 0
        if self._displays:
            root_children.append(add_item(2, item_type="separator"))
            for index, (identifier, name, percent, available) in enumerate(self._displays):
                base_id = 100 + index * 20
                suffix = f"{percent}%" if percent is not None else "—"
                title = f"{name} · {suffix}"
                if available:
                    available_count += 1
                    sub_ids: list[int] = []
                    for offset, level in enumerate((100, 75, 50, 25, 0), start=1):
                        sub_id = base_id + offset
                        mark = f"✓ {level}%" if percent == level else f"{level}%"
                        sub_ids.append(
                            add_item(
                                sub_id,
                                mark,
                                callback=lambda ident=identifier, val=level: self._on_set_display(
                                    ident, val
                                ),
                            )
                        )
                    root_children.append(add_item(base_id, title, children=sub_ids))
                else:
                    root_children.append(add_item(base_id, title, enabled=False))

        root_children.append(add_item(3, item_type="separator"))
        root_children.append(
            add_item(
                4,
                "Đưa tất cả màn hình về 100%",
                enabled=available_count > 0,
                callback=self._on_reset_all,
            )
        )
        root_children.append(add_item(5, "Quét lại màn hình", callback=self._on_refresh))
        root_children.append(add_item(6, item_type="separator"))
        root_children.append(add_item(7, "Thoát hẳn ứng dụng", callback=self._on_quit))

        nodes[0] = ({"children-display": GLib.Variant("s", "submenu")}, root_children)
        self._nodes = nodes
        self._callbacks = callbacks

    def _filter_props(self, item_id: int, names: list[str]) -> dict[str, GLib.Variant]:
        props, _ = self._nodes.get(item_id, ({}, []))
        if not names:
            return dict(props)
        return {key: val for key, val in props.items() if key in names}

    def _serialize_layout(
        self, item_id: int, depth: int, prop_names: list[str]
    ) -> tuple[int, dict[str, GLib.Variant], list[GLib.Variant]]:
        props = self._filter_props(item_id, prop_names)
        _, children_ids = self._nodes.get(item_id, ({}, []))
        children_variants: list[GLib.Variant] = []
        if depth != 0:
            next_depth = -1 if depth < 0 else depth - 1
            for child_id in children_ids:
                if child_id in self._nodes:
                    child_tuple = self._serialize_layout(child_id, next_depth, prop_names)
                    children_variants.append(GLib.Variant("(ia{sv}av)", child_tuple))
        return (item_id, props, children_variants)

    def _on_sni_prop(self, _conn, _sender, _path, _iface, prop_name: str):
        empty_pixmaps = GLib.Variant("a(iiay)", [])
        mapping = {
            "Category": GLib.Variant("s", "Hardware"),
            "Id": GLib.Variant("s", self.app_id),
            "Title": GLib.Variant("s", "Độ sáng màn hình"),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("i", 0),
            "IconThemePath": GLib.Variant("s", ""),
            "Menu": GLib.Variant("o", MENU_PATH),
            "ItemIsMenu": GLib.Variant("b", True),
            "IconName": GLib.Variant("s", "display-brightness-symbolic"),
            "IconPixmap": empty_pixmaps,
            "OverlayIconName": GLib.Variant("s", ""),
            "OverlayIconPixmap": empty_pixmaps,
            "AttentionIconName": GLib.Variant("s", ""),
            "AttentionIconPixmap": empty_pixmaps,
            "AttentionMovieName": GLib.Variant("s", ""),
        }
        return mapping.get(prop_name)

    def _on_sni_method(self, _conn, _sender, _path, _iface, method: str, _params, invocation):
        if method in ("Activate", "SecondaryActivate", "XAyatanaSecondaryActivate"):
            GLib.idle_add(self._trigger, self._on_toggle_window)
        invocation.return_value(None)

    def _on_menu_prop(self, _conn, _sender, _path, _iface, prop_name: str):
        mapping = {
            "Version": GLib.Variant("u", 3),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status": GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return mapping.get(prop_name)

    def _on_menu_method(self, _conn, _sender, _path, _iface, method: str, params, invocation):
        if method == "GetLayout":
            parent_id, depth, prop_names = params.unpack()
            layout = self._serialize_layout(parent_id, depth, list(prop_names))
            invocation.return_value(GLib.Variant("(u(ia{sv}av))", (self._revision, layout)))
        elif method == "GetGroupProperties":
            ids, prop_names = params.unpack()
            names = list(prop_names)
            result = [
                (item_id, self._filter_props(item_id, names))
                for item_id in ids
                if item_id in self._nodes
            ]
            invocation.return_value(GLib.Variant("(a(ia{sv}))", (result,)))
        elif method == "GetProperty":
            item_id, name = params.unpack()
            props, _ = self._nodes.get(item_id, ({}, []))
            val = props.get(name, GLib.Variant("s", ""))
            invocation.return_value(GLib.Variant("(v)", (val,)))
        elif method == "Event":
            item_id, event_id, _data, _timestamp = params.unpack()
            if event_id == "clicked" and item_id in self._callbacks:
                GLib.idle_add(self._trigger, self._callbacks[item_id])
            invocation.return_value(None)
        elif method == "EventGroup":
            (events,) = params.unpack()
            for item_id, event_id, _data, _timestamp in events:
                if event_id == "clicked" and item_id in self._callbacks:
                    GLib.idle_add(self._trigger, self._callbacks[item_id])
            invocation.return_value(GLib.Variant("(ai)", ([],)))
        elif method == "AboutToShow":
            invocation.return_value(GLib.Variant("(b)", (False,)))
        elif method == "AboutToShowGroup":
            invocation.return_value(GLib.Variant("(aiai)", ([], [])))
        else:
            invocation.return_value(None)

    @staticmethod
    def _trigger(callback: Callable[[], None]) -> bool:
        callback()
        return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._watcher_id:
            Gio.bus_unwatch_name(self._watcher_id)
            self._watcher_id = 0
        if self._bus is not None:
            if self._sni_reg:
                self._bus.unregister_object(self._sni_reg)
                self._sni_reg = 0
            if self._menu_reg:
                self._bus.unregister_object(self._menu_reg)
                self._menu_reg = 0
            self._bus = None
