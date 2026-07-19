# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Optional StatusNotifier integration for desktops that provide a tray host."""

from __future__ import annotations

from gettext import gettext as _

from gi.repository import Gio, GLib

from soundsgood.diagnostics import get_logger
from soundsgood.models import PlayState


LOGGER = get_logger("statusnotifier")
ITEM_PATH = "/StatusNotifierItem"
MENU_PATH = "/MenuBar"
ITEM_INTERFACE = "org.kde.StatusNotifierItem"
MENU_INTERFACE = "com.canonical.dbusmenu"
WATCHER_NAME = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"

ITEM_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="Scroll"><arg type="i" direction="in"/><arg type="s" direction="in"/></method>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="u" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewStatus"><arg type="s"/></signal>
    <signal name="NewToolTip"/>
  </interface>
</node>
"""

MENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg name="events" type="a(isvu)" direction="in"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <signal name="LayoutUpdated"><arg name="revision" type="u"/><arg name="parent" type="i"/></signal>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
  </interface>
</node>
"""


class StatusNotifierService:
    """Expose playback controls when a StatusNotifier host is available."""

    OPEN = 1
    PLAY_PAUSE = 2
    PREVIOUS = 3
    NEXT = 4
    SEPARATOR = 5
    QUIT = 6

    def __init__(self, application):
        self._app = application
        self._player = application.props.player
        self._connection = None
        self._registration_ids = []
        self._shutdown = False
        self._cancellable = Gio.Cancellable()
        self._player_handlers = [
            self._player.connect("notify::current-song", self._on_player_changed),
            self._player.connect("notify::play-state", self._on_player_changed),
        ]
        Gio.bus_get(Gio.BusType.SESSION, self._cancellable, self._on_bus_ready)

    def _on_bus_ready(self, _source, result):
        if self._shutdown:
            return
        try:
            self._connection = Gio.bus_get_finish(result)
            item_node = Gio.DBusNodeInfo.new_for_xml(ITEM_XML)
            menu_node = Gio.DBusNodeInfo.new_for_xml(MENU_XML)
            self._registration_ids = [
                self._connection.register_object(
                    ITEM_PATH,
                    item_node.interfaces[0],
                    self._on_item_method,
                    self._get_item_property,
                    None,
                ),
                self._connection.register_object(
                    MENU_PATH,
                    menu_node.interfaces[0],
                    self._on_menu_method,
                    self._get_menu_property,
                    None,
                ),
            ]
            self._connection.call(
                WATCHER_NAME,
                WATCHER_PATH,
                WATCHER_NAME,
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (self._connection.get_unique_name(),)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                self._cancellable,
                self._on_registered,
            )
        except GLib.Error:
            LOGGER.info("StatusNotifier is unavailable on this desktop")
            self.shutdown()

    def _on_registered(self, connection, result):
        if self._shutdown:
            return
        try:
            connection.call_finish(result)
            LOGGER.info("Registered optional StatusNotifier item")
        except GLib.Error:
            LOGGER.info("No compatible StatusNotifier host was found")

    def shutdown(self):
        if self._shutdown:
            return
        self._shutdown = True
        self._cancellable.cancel()
        for handler_id in self._player_handlers:
            if self._player.handler_is_connected(handler_id):
                self._player.disconnect(handler_id)
        self._player_handlers.clear()
        if self._connection:
            for registration_id in self._registration_ids:
                self._connection.unregister_object(registration_id)
        self._registration_ids.clear()
        self._connection = None

    def _get_item_property(
        self, _connection, _sender, _path, _interface, property_name
    ):
        song = self._player.props.current_song
        is_playing = self._player.props.play_state == int(PlayState.PLAYING)
        title = song.props.title if song else _("SoundsGood")
        artist = song.props.artist if song else ""
        values = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "soundsgood"),
            "Title": GLib.Variant("s", title),
            # The item also provides the explicit Quit action while idle, so it
            # must remain discoverable instead of being relegated as passive.
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("u", 0),
            "IconName": GLib.Variant("s", self._app.get_application_id()),
            "IconPixmap": GLib.Variant("a(iiay)", []),
            "OverlayIconName": GLib.Variant("s", "media-playback-start-symbolic" if is_playing else ""),
            "OverlayIconPixmap": GLib.Variant("a(iiay)", []),
            "AttentionIconName": GLib.Variant("s", ""),
            "AttentionIconPixmap": GLib.Variant("a(iiay)", []),
            "ToolTip": GLib.Variant(
                "(sa(iiay)ss)",
                (self._app.get_application_id(), [], title, artist),
            ),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", MENU_PATH),
        }
        return values.get(property_name)

    def _on_item_method(
        self, _connection, _sender, _path, _interface, method_name, parameters, invocation
    ):
        if method_name == "Activate":
            self._app.show_main_window()
        elif method_name == "SecondaryActivate":
            self._player.play_pause()
        elif method_name == "Scroll":
            delta, orientation = parameters.unpack()
            if orientation == "vertical":
                self._player.props.volume = min(
                    1.0, max(0.0, self._player.props.volume + (delta / 1200.0))
                )
        invocation.return_value(None)

    def _menu_properties(self, item_id):
        is_playing = self._player.props.play_state == int(PlayState.PLAYING)
        labels = {
            self.OPEN: _("Open SoundsGood"),
            self.PLAY_PAUSE: _("Pause") if is_playing else _("Play"),
            self.PREVIOUS: _("Previous"),
            self.NEXT: _("Next"),
            self.QUIT: _("Quit"),
        }
        if item_id == self.SEPARATOR:
            return {"type": GLib.Variant("s", "separator")}
        if item_id in labels:
            return {
                "label": GLib.Variant("s", labels[item_id]),
                "enabled": GLib.Variant("b", True),
                "visible": GLib.Variant("b", True),
            }
        return {"children-display": GLib.Variant("s", "submenu")}

    def _menu_item_variant(self, item_id):
        return GLib.Variant(
            "(ia{sv}av)",
            (item_id, self._menu_properties(item_id), []),
        )

    def _menu_layout(self):
        children = [
            self._menu_item_variant(item_id)
            for item_id in (
                self.OPEN,
                self.PLAY_PAUSE,
                self.PREVIOUS,
                self.NEXT,
                self.SEPARATOR,
                self.QUIT,
            )
        ]
        return (0, self._menu_properties(0), children)

    def _on_menu_method(
        self, _connection, _sender, _path, _interface, method_name, parameters, invocation
    ):
        if method_name == "GetLayout":
            invocation.return_value(
                GLib.Variant("(u(ia{sv}av))", (1, self._menu_layout()))
            )
            return
        if method_name == "GetGroupProperties":
            item_ids, _names = parameters.unpack()
            properties = [
                (item_id, self._menu_properties(item_id)) for item_id in item_ids
            ]
            invocation.return_value(GLib.Variant("(a(ia{sv}))", (properties,)))
            return
        if method_name == "GetProperty":
            item_id, name = parameters.unpack()
            value = self._menu_properties(item_id).get(name, GLib.Variant("s", ""))
            invocation.return_value(GLib.Variant("(v)", (value,)))
            return
        if method_name == "Event":
            item_id, event_id, _data, _timestamp = parameters.unpack()
            if event_id == "clicked":
                self._activate_menu_item(item_id)
            invocation.return_value(None)
            return
        if method_name == "EventGroup":
            errors = []
            for item_id, event_id, _data, _timestamp in parameters.unpack()[0]:
                if event_id == "clicked":
                    self._activate_menu_item(item_id)
                else:
                    errors.append(item_id)
            invocation.return_value(GLib.Variant("(ai)", (errors,)))
            return
        if method_name == "AboutToShow":
            invocation.return_value(GLib.Variant("(b)", (False,)))
            return
        if method_name == "AboutToShowGroup":
            invocation.return_value(GLib.Variant("(aiai)", ([], [])))
            return
        invocation.return_dbus_error(
            "com.canonical.dbusmenu.Error.NotSupported",
            f"Unsupported method {method_name}",
        )

    def _activate_menu_item(self, item_id):
        if item_id == self.OPEN:
            self._app.show_main_window()
        elif item_id == self.PLAY_PAUSE:
            self._player.play_pause()
        elif item_id == self.PREVIOUS:
            self._player.previous()
        elif item_id == self.NEXT:
            self._player.next()
        elif item_id == self.QUIT:
            self._app.quit_application()

    def _get_menu_property(
        self, _connection, _sender, _path, _interface, property_name
    ):
        values = {
            "Version": GLib.Variant("u", 4),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status": GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return values.get(property_name)

    def _on_player_changed(self, *_args):
        if not self._connection:
            return
        self._connection.emit_signal(
            None,
            ITEM_PATH,
            ITEM_INTERFACE,
            "NewStatus",
            GLib.Variant("(s)", ("Active",)),
        )
        self._connection.emit_signal(None, ITEM_PATH, ITEM_INTERFACE, "NewTitle", None)
        self._connection.emit_signal(None, ITEM_PATH, ITEM_INTERFACE, "NewToolTip", None)
        self._connection.emit_signal(
            None,
            MENU_PATH,
            MENU_INTERFACE,
            "LayoutUpdated",
            GLib.Variant("(ui)", (1, 0)),
        )
