#!/usr/bin/env python3
import argparse
import asyncio
import calendar
import os
from binascii import hexlify
from datetime import datetime

from bleak import BleakClient


WRITE_ME_UUID = "00001f1f-0000-1000-8000-00805f9b34fb"
READ_NOTIFY_UUID = "0000331f-0000-1000-8000-00805f9b34fb"

COMMANDS = {
    "e3": bytes.fromhex("e3"),
    "e4": bytes.fromhex("e4"),
    "e102": bytes.fromhex("e1 02"),
    "invert": bytes.fromhex("e3"),
    "name-toggle": bytes.fromhex("e4"),
    "type-250x128": bytes.fromhex("e0 01"),
    "type-296x128": bytes.fromhex("e0 02"),
    "type-300x400": bytes.fromhex("e0 03"),
    "type-296x152": bytes.fromhex("e0 04"),
    "mode-picture": bytes.fromhex("e1 00"),
    "mode-calendar": bytes.fromhex("e1 01"),
    "mode-time": bytes.fromhex("e1 02"),
}


def hex_bytes(value: bytes | bytearray | memoryview | None) -> str:
    if not value:
        return ""
    return hexlify(bytes(value), " ").decode("ascii")


async def send(address: str, target: str, payload: bytes, wait: float) -> None:
    target_uuid = {
        "write-me": WRITE_ME_UUID,
        "read-notify": READ_NOTIFY_UUID,
    }[target]

    def on_notify(sender, data: bytearray) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        printable = bytes(data).decode("utf-8", errors="replace")
        text = f" text={printable!r}" if printable.strip() else ""
        print(f"[{now}] notify {sender}: {hex_bytes(data)}{text}")

    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")

        for service in client.services:
            for char in service.characteristics:
                if "notify" not in char.properties and "indicate" not in char.properties:
                    continue
                try:
                    await client.start_notify(char.uuid, on_notify)
                except Exception as exc:
                    print(f"notify start failed {char.uuid}: {exc}")
                else:
                    print(f"notify started {char.uuid}")

        print(f"Writing {hex_bytes(payload)} to {target_uuid} ({target})")
        await client.write_gatt_char(target_uuid, payload, response=True)
        await asyncio.sleep(wait)

        if target_uuid == READ_NOTIFY_UUID:
            value = await client.read_gatt_char(READ_NOTIFY_UUID)
            print(f"readback {READ_NOTIFY_UUID}: {hex_bytes(value)}")


def local_wall_epoch() -> int:
    now = datetime.now().astimezone()
    local_as_utc = now.replace(tzinfo=None)
    return calendar.timegm(local_as_utc.timetuple())


async def sync_time(address: str, wait: float) -> None:
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        sequence = [
            bytes.fromhex("e1 02"),
            bytes([0xDD]) + local_wall_epoch().to_bytes(4, "big"),
            bytes.fromhex("e2"),
            bytes.fromhex("e1 01"),
            bytes([0xDD]) + local_wall_epoch().to_bytes(4, "big"),
            bytes.fromhex("e2"),
            bytes.fromhex("e3"),
            bytes.fromhex("e4"),
        ]
        for payload in sequence:
            print(f"Writing {hex_bytes(payload)} to {WRITE_ME_UUID}")
            await client.write_gatt_char(WRITE_ME_UUID, payload, response=True)
            await asyncio.sleep(0.15)
        await asyncio.sleep(wait)


async def command_with_timestamp(address: str, payload: bytes, wait: float) -> None:
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        sequence = [
            payload,
            bytes([0xDD]) + local_wall_epoch().to_bytes(4, "big"),
            bytes.fromhex("e2"),
        ]
        for item in sequence:
            print(f"Writing {hex_bytes(item)} to {WRITE_ME_UUID}")
            await client.write_gatt_char(WRITE_ME_UUID, item, response=True)
            await asyncio.sleep(0.15)
        await asyncio.sleep(wait)


async def timestamp_only(address: str, wait: float) -> None:
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        sequence = [
            bytes([0xDD]) + local_wall_epoch().to_bytes(4, "big"),
            bytes.fromhex("e2"),
        ]
        for item in sequence:
            print(f"Writing {hex_bytes(item)} to {WRITE_ME_UUID}")
            await client.write_gatt_char(WRITE_ME_UUID, item, response=True)
            await asyncio.sleep(0.15)
        await asyncio.sleep(wait)


def parse_payload(args: argparse.Namespace) -> bytes:
    if args.hex:
        return bytes.fromhex(args.hex)
    return COMMANDS[args.command]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send controlled non-OTA commands to a DA14585/SYD8810 e-paper tag."
    )
    parser.add_argument(
        "--address",
        default=os.environ.get("DA_DIALOG_ADDRESS"),
        help="CoreBluetooth device id/address. Can also be set with DA_DIALOG_ADDRESS.",
    )
    parser.add_argument(
        "--target",
        choices=["write-me", "read-notify"],
        default="write-me",
        help="Non-OTA characteristic to write.",
    )
    parser.add_argument("command", choices=[*sorted(COMMANDS), "sync-time", "full-sync"], nargs="?", default="e102")
    parser.add_argument("--hex", help="Custom hex payload, e.g. 'e1 02'.")
    parser.add_argument("--wait", type=float, default=5.0)
    args = parser.parse_args()

    if not args.address:
        parser.error("provide --address or set DA_DIALOG_ADDRESS")

    if args.command == "sync-time":
        await timestamp_only(args.address, args.wait)
    elif args.command == "full-sync":
        await sync_time(args.address, args.wait)
    elif args.command.startswith("type-") or args.command.startswith("mode-"):
        await command_with_timestamp(args.address, COMMANDS[args.command], args.wait)
    else:
        await send(args.address, args.target, parse_payload(args), args.wait)


if __name__ == "__main__":
    asyncio.run(main())
