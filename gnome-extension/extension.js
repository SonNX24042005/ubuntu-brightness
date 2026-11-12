// Phím tắt toàn cục của ubuntu-brightness, dùng được cả ở màn hình khóa.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const MEDIA_KEYS_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys';
const CUSTOM_SCHEMA = `${MEDIA_KEYS_SCHEMA}.custom-keybinding`;
const CUSTOM_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/ubuntu-brightness-reset/';
const KEY = 'reset-all';
const MODES = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW | Shell.ActionMode.POPUP |
    Shell.ActionMode.LOCK_SCREEN | Shell.ActionMode.UNLOCK_SCREEN;
// gnome-settings-daemon thả phím bất đồng bộ; đợi trước khi giữ cùng tổ hợp phím.
const RELEASE_DELAY_MS = 1500;

export default class UbuntuBrightnessExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        const delay = this._takeOverCustomShortcut() ? RELEASE_DELAY_MS : 0;
        this._timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delay, () => {
            this._timeout = 0;
            this._bound = Main.wm.addKeybinding(KEY, this._settings,
                Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, MODES,
                () => this._run()) !== Meta.KeyBindingAction.NONE;
            return GLib.SOURCE_REMOVE;
        });
    }

    disable() {
        if (this._timeout) {
            GLib.source_remove(this._timeout);
            this._timeout = 0;
        }
        if (this._bound)
            Main.wm.removeKeybinding(KEY);
        this._bound = false;
        this._settings = null;
    }

    // Chuyển phím tắt tùy chỉnh do ứng dụng tạo sang extension để tránh hai nơi cùng giữ phím.
    _takeOverCustomShortcut() {
        const mediaKeys = new Gio.Settings({schema_id: MEDIA_KEYS_SCHEMA});
        const paths = mediaKeys.get_strv('custom-keybindings');
        if (!paths.includes(CUSTOM_PATH))
            return false;
        const custom = new Gio.Settings({schema_id: CUSTOM_SCHEMA, path: CUSTOM_PATH});
        const binding = custom.get_string('binding');
        const command = custom.get_string('command');
        this._settings.set_strv(KEY, binding ? [binding] : []);
        if (command)
            this._settings.set_string('command', command);
        mediaKeys.set_strv('custom-keybindings', paths.filter(path => path !== CUSTOM_PATH));
        for (const key of ['name', 'command', 'binding'])
            custom.reset(key);
        return true;
    }

    _run() {
        const command = this._settings.get_string('command');
        if (!command)
            return;
        try {
            GLib.spawn_command_line_async(command);
        } catch (e) {
            console.error(`ubuntu-brightness: không chạy được lệnh ${command}: ${e.message}`);
        }
    }
}
