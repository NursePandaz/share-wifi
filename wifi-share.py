#!/usr/bin/python3
"""Local Wi-Fi sharing window. Credentials are never written to disk."""
import subprocess
import os
import threading
import gi
import qrcode

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib


def nm(*args):
    try:
        p = subprocess.run(['/usr/bin/nmcli', '--escape', 'no', '--wait', '5', *args],
                           capture_output=True, text=True, timeout=15,
                           env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError('NetworkManager is unavailable or took too long. Try Refresh networks.') from error
    if p.returncode:
        raise RuntimeError('Could not read this connection. Try Refresh networks or check network permissions.')
    return p.stdout.removesuffix('\n')



def escape(value):
    return ''.join('\\' + c if c in '\\;,:"' else c for c in value)


class Share(Gtk.Window):
    def __init__(self):
        super().__init__(title='Share Wi-Fi')
        self.set_default_size(440, 570)
        self.set_border_width(24)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(box)
        title = Gtk.Label()
        title.set_markup('<span size="xx-large" weight="bold">Share Wi-Fi</span>')
        box.pack_start(title, False, False, 0)
        box.pack_start(Gtk.Label(label='Choose a saved network, then scan with your phone.'), False, False, 0)
        self.combo = Gtk.ComboBoxText()
        box.pack_start(self.combo, False, False, 0)
        self.password = Gtk.Entry()
        self.password.set_placeholder_text('Wi-Fi password')
        self.password.set_visibility(True)
        box.pack_start(self.password, False, False, 0)
        self.picture = Gtk.Image()
        box.pack_start(self.picture, True, True, 0)
        self.status = Gtk.Label(wrap=True)
        box.pack_start(self.status, False, False, 0)
        button = Gtk.Button(label='Refresh networks')
        button.connect('clicked', self.refresh)
        box.pack_start(button, False, False, 0)
        self.authenticated = False
        share = Gtk.Button(label='Unlock sharing…')
        self.share = share
        share.connect('clicked', self.unlock)
        box.pack_start(share, False, False, 0)
        self.combo.connect('changed', self.network_changed)
        self.password.connect('changed', self.render)
        self.connect('destroy', Gtk.main_quit)
        self.security = None
        self.refresh()

    def refresh(self, *_):
        previous = self.combo.get_active_id()
        self.combo.remove_all()
        try:
            rows = nm('-t', '-f', 'UUID,TYPE', 'connection', 'show').splitlines()
            for row in rows:
                uuid, kind = row.split(':', 1)
                if kind == '802-11-wireless':
                    name = nm('-g', 'connection.id', 'connection', 'show', uuid)
                    self.combo.append(uuid, name)
            if not previous or not self.combo.set_active_id(previous):
                self.combo.set_active(0)
            if self.combo.get_active_id() is None:
                self.status.set_text('No saved Wi-Fi networks found. Connect using your network settings first.')
        except RuntimeError as error:
            self.status.set_text(str(error))

    def network_changed(self, *_):
        if self.authenticated:
            self.select()
        else:
            self.lock()

    def lock(self, *_):
        self.authenticated = False
        self.share.set_label('Unlock sharing…')
        self.security = None
        self.picture.clear()
        self.password.set_text('')
        self.password.set_sensitive(False)
        self.status.set_text('Administrator authentication is required to share this network.')

    def unlock(self, *_):
        if self.authenticated:
            self.lock()
            return
        self.lock()
        if not self.combo.get_active_id():
            return
        # Include process start time and UID to bind authorization to this process.
        stat = open('/proc/self/stat').read().rsplit(')', 1)[1].split()
        subject = f'{os.getpid()},{stat[19]},{os.getuid()}'
        self.share.set_sensitive(False)
        self.status.set_text('Waiting for administrator authentication…')
        def authenticate():
            try:
                result = subprocess.run(['/usr/bin/pkcheck', '--action-id',
                    'org.sharewifi.reveal', '--process', subject,
                    '--allow-user-interaction'], capture_output=True, timeout=120)
                allowed = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                allowed = False
            GLib.idle_add(self.authentication_done, allowed)
        threading.Thread(target=authenticate, daemon=True).start()

    def authentication_done(self, allowed):
        self.share.set_sensitive(True)
        if not allowed:
            self.status.set_text('Sharing remains locked. Authentication was cancelled or denied.')
            return False
        self.authenticated = True
        self.share.set_label('Lock sharing')
        self.password.set_sensitive(True)
        self.select()
        return False

    def select(self, *_):
        if not self.authenticated:
            self.lock()
            return
        self.security = None
        self.picture.clear()
        self.password.set_text('')
        uuid = self.combo.get_active_id()
        if not uuid:
            return
        try:
            def field(name, secret=False):
                return nm(*(['--show-secrets'] if secret else []), '-g', name, 'connection', 'show', uuid)
            self.ssid = field('802-11-wireless.ssid')
            self.hidden = field('802-11-wireless.hidden') == 'yes'
            key = field('802-11-wireless-security.key-mgmt')
            if key in ('wpa-eap', 'ieee8021x', 'wpa-eap-suite-b-192'):
                self.status.set_text('Enterprise Wi-Fi requires individual sign-in and cannot be shared with this QR code.')
                return
            if key == 'owe':
                self.status.set_text('Enhanced Open Wi-Fi sharing is not supported by this app.')
                return
            if key in ('', '--'):
                self.security = 'nopass'
                password = ''
            elif key == 'none':
                self.security = 'WEP'
                index = field('802-11-wireless-security.wep-tx-keyidx')
                password = field('802-11-wireless-security.wep-key' + index, True)
            elif key in ('wpa-psk', 'sae'):
                self.security = 'SAE' if key == 'sae' else 'WPA'
                password = field('802-11-wireless-security.psk', True)
            else:
                self.status.set_text('This network security type is not supported.')
                return
            self.password.set_text(password if password != '--' else '')
            self.render()
        except RuntimeError as error:
            self.security = None
            self.picture.clear()
            self.status.set_text(str(error))

    def render(self, *_):
        self.picture.clear()
        if not self.authenticated or self.security is None:
            return
        password = self.password.get_text()
        if self.security != 'nopass' and not password:
            self.status.set_text('Saved password unavailable. Enter it above to generate the QR code.')
            return
        payload = f'WIFI:T:{self.security};S:{escape(self.ssid)};P:{escape(password)};H:{str(self.hidden).lower()};;'
        qr = qrcode.QRCode(border=4, box_size=1)
        qr.add_data(payload)
        try:
            qr.make(fit=True)
        except qrcode.exceptions.DataOverflowError:
            self.status.set_text('The network details are too long for a QR code.')
            return
        matrix = qr.get_matrix()
        scale = max(1, 320 // len(matrix))
        pixels = bytes(v for row in matrix for _ in range(scale) for cell in row for _ in range(scale) for v in ((0, 0, 0) if cell else (255, 255, 255)))
        size = len(matrix) * scale
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(pixels), GdkPixbuf.Colorspace.RGB, False, 8, size, size, size * 3)
        self.picture.set_from_pixbuf(pixbuf)
        self.status.set_text('Scan to join ' + self.ssid)


if __name__ == '__main__':
    Share().show_all()
    Gtk.main()
