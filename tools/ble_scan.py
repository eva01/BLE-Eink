#!/usr/bin/env python3
import argparse
import asyncio
from datetime import datetime
from binascii import hexlify
from collections.abc import Iterable

from bleak import BleakClient, BleakScanner


def hex_bytes(value: bytes | bytearray | memoryview | None) -> str:
    if not value:
        return ""
    return hexlify(bytes(value), " ").decode("ascii")


def format_uuid(uuid: str) -> str:
    known = {
        "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
        "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
        "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
        "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    }
    return f"{uuid} ({known[uuid.lower()]})" if uuid.lower() in known else uuid


def matches_name(name: str | None, targets: Iterable[str]) -> bool:
    if not targets:
        return True
    normalized = (name or "").lower()
    return any(target.lower() in normalized for target in targets)


async def discover(duration: float, names: list[str]) -> list[tuple[object, object]]:
    print(f"Scanning for {duration:g}s...")
    found = await BleakScanner.discover(timeout=duration, return_adv=True)
    devices: list[tuple[object, object]] = []

    for device, adv in found.values():
        if not matches_name(device.name or adv.local_name, names):
            continue
        devices.append((device, adv))

    if not devices:
        print("No matching BLE devices found.")
        return []

    for idx, (device, adv) in enumerate(devices, start=1):
        name = device.name or adv.local_name or "<unknown>"
        print(f"\n[{idx}] {name}")
        print(f"    address/id: {device.address}")
        print(f"    rssi:       {adv.rssi} dBm")
        if adv.local_name:
            print(f"    adv name:   {adv.local_name}")
        if adv.service_uuids:
            print("    adv services:")
            for uuid in adv.service_uuids:
                print(f"      - {format_uuid(uuid)}")
        if adv.manufacturer_data:
            print("    manufacturer data:")
            for company_id, data in adv.manufacturer_data.items():
                print(f"      - 0x{company_id:04x}: {hex_bytes(data)}")
        if adv.service_data:
            print("    service data:")
            for uuid, data in adv.service_data.items():
                print(f"      - {format_uuid(uuid)}: {hex_bytes(data)}")

    return devices


async def inspect_device(device, read_values: bool) -> None:
    if isinstance(device, str):
        label = device
    else:
        label = f"{device.name or '<unknown>'} ({device.address})"
    print(f"\nConnecting to {label}...")
    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")
        print("\nGATT services:")

        for service in client.services:
            print(f"\nService {format_uuid(service.uuid)}")
            for char in service.characteristics:
                props = ", ".join(char.properties) or "none"
                print(f"  Characteristic {char.uuid}")
                print(f"    handle:     {char.handle}")
                print(f"    properties: {props}")

                for descriptor in char.descriptors:
                    print(f"    descriptor: {descriptor.uuid} handle={descriptor.handle}")
                    if read_values:
                        try:
                            value = await client.read_gatt_descriptor(descriptor.handle)
                        except Exception as exc:
                            print(f"      descriptor read: failed: {exc}")
                        else:
                            printable = bytes(value).decode("utf-8", errors="replace")
                            print(f"      descriptor hex:  {hex_bytes(value)}")
                            if printable.strip():
                                print(f"      descriptor text: {printable!r}")

                if read_values and "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                    except Exception as exc:
                        print(f"    read:       failed: {exc}")
                    else:
                        printable = bytes(value).decode("utf-8", errors="replace")
                        print(f"    read hex:   {hex_bytes(value)}")
                        if printable.strip():
                            print(f"    read text:  {printable!r}")


async def monitor_device(device, seconds: float) -> None:
    if isinstance(device, str):
        label = device
    else:
        label = f"{device.name or '<unknown>'} ({device.address})"
    print(f"\nConnecting to {label}...")

    def on_notify(sender, data: bytearray) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        printable = bytes(data).decode("utf-8", errors="replace")
        text = f" text={printable!r}" if printable.strip() else ""
        print(f"[{now}] notify {sender}: {hex_bytes(data)}{text}")

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")
        started = []
        for service in client.services:
            for char in service.characteristics:
                if "notify" not in char.properties and "indicate" not in char.properties:
                    continue
                try:
                    await client.start_notify(char.uuid, on_notify)
                except Exception as exc:
                    print(f"notify start failed {char.uuid}: {exc}")
                else:
                    started.append(char.uuid)
                    print(f"notify started {char.uuid}")

        if not started:
            print("No notify/indicate characteristics found.")
            return

        print(f"Monitoring notifications for {seconds:g}s...")
        await asyncio.sleep(seconds)

        for uuid in started:
            try:
                await client.stop_notify(uuid)
            except Exception as exc:
                print(f"notify stop failed {uuid}: {exc}")


async def write_probe(device, uuid: str, payload: bytes, seconds: float) -> None:
    if isinstance(device, str):
        label = device
    else:
        label = f"{device.name or '<unknown>'} ({device.address})"
    print(f"\nConnecting to {label}...")

    def on_notify(sender, data: bytearray) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        printable = bytes(data).decode("utf-8", errors="replace")
        text = f" text={printable!r}" if printable.strip() else ""
        print(f"[{now}] notify {sender}: {hex_bytes(data)}{text}")

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties or "indicate" in char.properties:
                    try:
                        await client.start_notify(char.uuid, on_notify)
                    except Exception as exc:
                        print(f"notify start failed {char.uuid}: {exc}")
                    else:
                        print(f"notify started {char.uuid}")

        print(f"Writing {hex_bytes(payload)} to {uuid}")
        await client.write_gatt_char(uuid, payload, response=True)
        await asyncio.sleep(seconds)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan BLE devices and inspect advertised/GATT capabilities."
    )
    parser.add_argument(
        "--name",
        action="append",
        default=["NRF"],
        help="Device name substring to match. Repeat for multiple names.",
    )
    parser.add_argument("--duration", type=float, default=8.0, help="Scan duration in seconds.")
    parser.add_argument(
        "--connect",
        action="store_true",
        help="Connect to the first matching device and enumerate services.",
    )
    parser.add_argument(
        "--address",
        help="Connect directly to a known BLE address/id instead of discovering first.",
    )
    parser.add_argument(
        "--read",
        action="store_true",
        help="Read characteristics that explicitly advertise the read property.",
    )
    parser.add_argument(
        "--monitor",
        type=float,
        help="Subscribe to all notify/indicate characteristics for N seconds.",
    )
    parser.add_argument("--write-uuid", help="Characteristic UUID for a controlled write probe.")
    parser.add_argument("--write-hex", help="Hex payload for a controlled write probe, e.g. '70 69 6e 67'.")
    args = parser.parse_args()

    if args.address:
        if args.write_uuid and args.write_hex:
            payload = bytes.fromhex(args.write_hex)
            await write_probe(args.address, args.write_uuid, payload, args.monitor or 5)
            return
        if args.monitor:
            await monitor_device(args.address, args.monitor)
            return
        await inspect_device(args.address, args.read)
        return

    devices = await discover(args.duration, args.name)
    if args.connect and devices:
        if args.monitor:
            await monitor_device(devices[0][0], args.monitor)
        else:
            await inspect_device(devices[0][0], args.read)


if __name__ == "__main__":
    asyncio.run(main())
