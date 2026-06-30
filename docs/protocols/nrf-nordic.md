# NRF / Nordic E-Paper Firmware Class

This class covers e-paper displays using Nordic nRF firmware and a custom BLE service.

## Observed Example

```text
Name pattern: NRF_EPD_....
App version observed: 0x18
```

Exact local CoreBluetooth identifiers are intentionally omitted because they are machine-specific and not useful for a public project.

## GATT Surface

Application service:

```text
Service: 62750001-d828-918d-fb46-b6c11c675aec
Char:    62750002-d828-918d-fb46-b6c11c675aec
Props:   write-without-response, write, notify
```

Application version:

```text
Service: 62750001-d828-918d-fb46-b6c11c675aec
Char:    62750003-d828-918d-fb46-b6c11c675aec
Props:   read
```

Nordic DFU:

```text
Service: 0000fe59-0000-1000-8000-00805f9b34fb
Char:    8ec90003-f315-4f60-9fb8-838830daea50
Props:   write, indicate
```

## Commands

```text
0x00 = SET_PINS
0x01 = INIT
0x02 = CLEAR
0x03 = SEND_COMMAND
0x04 = SEND_DATA
0x05 = REFRESH
0x06 = SLEEP
0x20 = SET_TIME
0x21 = SET_WEEK_START
0x30 = WRITE_IMAGE
0x90 = SET_CONFIG
0x91 = SYS_RESET
0x92 = SYS_SLEEP
0x99 = CFG_ERASE
```

## Time Sync Packet

The time-sync command writes byte `0x20` followed by:

```text
unix_timestamp_be[4], timezone_hours_i8, display_mode
```

Known display modes:

```text
0x01 = calendar mode
0x02 = clock mode
```

Example shape:

```text
20 <ts3> <ts2> <ts1> <ts0> <tz> 01
```

The timestamp is current Unix time in seconds. The firmware adds the timezone offset before rendering the calendar/clock.

## Caution

OTA is possible in principle because the Nordic DFU service is exposed, but a matching DFU package and exact target assumptions are required. Do not write to DFU during normal probing.
