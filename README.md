# Share Wi-Fi

A small Python + GTK app for sharing saved Wi-Fi networks on Linux Mint and Ubuntu. Choose a network, authenticate once, and let a phone scan the QR code to join.

## Download and install

Download **share-wifi_1.2.0_all.deb** from [Releases](../../releases/latest), double-click it, and choose Install. Open **Share Wi-Fi** from your applications menu.

Tested on Linux Mint 22.3. Other Ubuntu/Debian systems with GTK 3 and NetworkManager may work but have not been tested.

## Use

1. Select a saved network and click **Unlock sharing**.
2. Authenticate with an administrator account.
3. Scan the QR code with your phone's camera or Wi-Fi QR scanner.

Switch networks without authenticating again. Click **Lock sharing** to hide credentials, or close the app. If the saved password is unavailable, enter it yourself. Refresh reloads saved profiles without changing your network connection.

## Privacy and limitations

Credentials are processed locally; this app does not write passwords or QR images to disk or send them over the internet. Administrator authentication guards this app's display. It does not change NetworkManager permissions or restrict other tools that can read saved passwords. Authentication lasts until you lock sharing or close the app.

Enterprise and Enhanced Open Wi-Fi sharing are unsupported. Phone compatibility varies, particularly for WPA3 and WEP. A phone successfully joined using the generated QR code during testing.

## Build from source

Requires Python 3, python3-gi, python3-qrcode, gir1.2-gtk-3.0, NetworkManager, policykit-1, and dpkg-deb.

```sh
python3 test_app.py
sh build.sh
sudo apt install ./dist/share-wifi_1.2.0_all.deb
```

Install the package before running the app: it installs the administrator authentication policy as well as the menu launcher. Running the Python file alone does not install that policy.

## Uninstall

Remove Share Wi-Fi through your package manager, or run `sudo apt remove share-wifi`.

## Reporting problems

Open a GitHub issue with your Linux distribution, version, and what happened. Do not include Wi-Fi passwords or screenshots showing passwords or QR codes.
