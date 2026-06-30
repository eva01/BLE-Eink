# BLE Eink

Public notes and tools for BLE e-paper displays that fall into two firmware classes:

- **NRF / Nordic**: nRF-based e-paper firmware using a custom Nordic BLE service.
- **DA / Dialog**: DA14585/SYD8810-style electronic price tags using a Dialog/Renesas BLE surface.

This project is protocol-focused. It does not include firmware images, private logs, router traces, or full image payload dumps.

## Safety

Use these tools only with devices you own or are authorized to test.

- Scan first and verify the target by advertised name and service UUID.
- Do not write to DFU/SUOTA firmware update services during normal control.
- Keep the physical tag away or powered off when using the BLE trap to observe app writes.
- Redact BLE addresses, CoreBluetooth IDs, manufacturer data, QR codes, router/network data, and full image payloads before opening public issues.

Known firmware update services:

```text
NRF / Nordic DFU: 0000fe59-0000-1000-8000-00805f9b34fb
DA / Dialog SUOTA: 0000fef5-0000-1000-8000-00805f9b34fb
```

## Requirements

- Python 3
- `uv` for temporary Python dependencies
- BLE adapter supported by Bleak
- Chrome or Edge for the Web Bluetooth control surface
- macOS + Swift toolchain for the CoreBluetooth trap

## Command-Line Tools

Scan and inspect nearby BLE devices:

```bash
UV_CACHE_DIR=.uv-cache uv run --with bleak python tools/ble_scan.py --name NRF --duration 10
```

Control a DA/Dialog tag. Pass your own CoreBluetooth device id/address:

```bash
UV_CACHE_DIR=.uv-cache uv run --with bleak python tools/da_dialog_send.py --address <device-id> sync-time
UV_CACHE_DIR=.uv-cache uv run --with bleak python tools/da_dialog_send.py --address <device-id> mode-time
UV_CACHE_DIR=.uv-cache uv run --with bleak python tools/da_dialog_send.py --address <device-id> type-250x128
```

You can also set:

```bash
export DA_DIALOG_ADDRESS=<device-id>
```

## English Web Control Surface

Open [web-control/index.html](web-control/index.html) in Chrome or Edge.

The web UI supports:

- NRF device connection and firmware-version read
- NRF calendar-mode and clock-mode time sync
- NRF clear, refresh, panel sleep, MCU sleep, reset, and config erase commands
- DA/Dialog panel type selection
- DA/Dialog picture, calendar, and time modes
- DA/Dialog time sync, refresh, invert, and BLE-name toggle
- Raw hex writes for both DA/Dialog and NRF/Nordic classes

NRF image transfer is not implemented yet. Image writes use `0x30` frames with chunk flags and pixel payload, so they should be added only after validating panel size, color mode, and transfer pacing.

## BLE Trap

The Swift trap emulates the DA/Dialog GATT surface so a mobile app can connect to your Mac and observe write payloads.

Build:

```bash
mkdir -p .swift-cache
swiftc -module-cache-path .swift-cache tools/ble-trap/DADialogTrap.swift -o tools/ble-trap/da-dialog-trap
```

Run with your tag's expected advertised name:

```bash
tools/ble-trap/da-dialog-trap --name <expected-device-name>
```

On macOS, the trap may print harmless errors when trying to publish standard Battery or Device Information services. The custom DA/Dialog services are the important part for app write observation.

## Documentation

- [NRF / Nordic protocol class](docs/protocols/nrf-nordic.md)
- [DA / Dialog protocol class](docs/protocols/da-dialog.md)

## Troubleshooting

- macOS and iOS may show different CoreBluetooth identifiers for the same device.
- A BLE device can disappear if it sleeps, hides its name, or remains connected to a phone.
- Browser Web Bluetooth requires HTTPS or a local file context in a supported browser.
- Some firmware advertises only during short windows; scan for longer if no device appears.
