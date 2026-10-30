#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p build/DEBIAN build/usr/share/share-wifi build/usr/share/applications build/usr/share/polkit-1/actions build/usr/bin dist
install -m 644 control build/DEBIAN/control
install -m 644 wifi-share.py build/usr/share/share-wifi/wifi-share.py
install -m 644 share-wifi.desktop build/usr/share/applications/share-wifi.desktop
install -m 644 org.sharewifi.policy build/usr/share/polkit-1/actions/org.sharewifi.policy
install -m 755 share-wifi build/usr/bin/share-wifi
dpkg-deb --root-owner-group --build build dist/share-wifi_1.2.0_all.deb
