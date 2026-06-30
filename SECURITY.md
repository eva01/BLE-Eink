# Security and Disclosure Notes

This project is for devices you own or are authorized to test.

## Do Not Publish

Before opening issues or sharing logs, remove:

- BLE addresses and CoreBluetooth device identifiers
- Raw manufacturer data and service data unless needed for a protocol question
- QR codes, serial numbers, account identifiers, and screenshots with personal data
- Router, WAN, LAN, or packet logs
- Full image-transfer payloads
- Firmware binaries or OTA packages unless redistribution is explicitly allowed

## Safe Testing

- Verify the target device by name and service UUID before writing.
- Avoid DFU/SUOTA services unless doing intentional firmware-update testing.
- Keep real devices away or powered off when using the BLE trap.
- Prefer minimal commands first, then add payloads after confirming behavior.

## Scope

The project does not attempt to bypass pairing, authentication, access control, or firmware protections.
