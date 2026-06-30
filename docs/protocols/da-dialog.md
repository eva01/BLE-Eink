# DA / Dialog E-Paper Firmware Class

This class covers DA14585/SYD8810-style Bluetooth electronic price tags using a Dialog/Renesas BLE surface.

## Device Identity

Observed examples advertise with names like:

```text
NRF-......
```

The naming is misleading: the observed device reports Dialog/Renesas DA14585 device information and exposes a Dialog SUOTA service.

```text
Manufacturer: Dialog Semi
Model:        DA14585
Firmware:     v_6.0.18.1182.1
```

## GATT Surface

Application write characteristic:

```text
Service: 00001f10-0000-1000-8000-00805f9b34fb
Char:    00001f1f-0000-1000-8000-00805f9b34fb
Props:   write
Label:   Write me
```

Image/data characteristic:

```text
Service: 13187b10-eba9-a3ba-044e-83d3217d9a38
Char:    4b646063-6264-f3a7-8941-e65356ea82fe
Props:   write, notify
Label:   LED State
```

Echo/read characteristic:

```text
Service: 0000221f-0000-1000-8000-00805f9b34fb
Char:    0000331f-0000-1000-8000-00805f9b34fb
Props:   read, write, notify
Label:   Read me (notify)
```

Firmware update service:

```text
Service: 0000fef5-0000-1000-8000-00805f9b34fb
Type:    Dialog/Renesas SUOTA-style firmware update
```

Do not write to SUOTA characteristics during normal control.

## Timestamp Encoding

Time is written as:

```text
dd <4-byte timestamp>
```

The timestamp is big-endian seconds for local wall-clock time encoded as if it were UTC.

## Commands

All commands below are written to `00001f1f-0000-1000-8000-00805f9b34fb`.

Panel type:

```text
e0 01 = 250x128 (2.13)
e0 02 = 296x128 (2.9)
e0 03 = 300x400 (4.2)
e0 04 = 296x152 (2.6)
```

Display mode:

```text
e1 00 = picture mode
e1 01 = calendar mode
e1 02 = time mode / time-face cycle
```

Actions:

```text
dd <timestamp> = set current time value
e2 = refresh/apply screen update
e3 = invert color
e4 = hide/show BLE name
```

Observed button sequences:

```text
Time mode:
e1 02
dd <timestamp>
e2

Calendar mode:
e1 01
dd <timestamp>
e2

Picture mode:
e1 00
dd <timestamp>
e2

Sync time:
dd <timestamp>
e2
```

Repeated raw `e1 02` appears to cycle time faces. At least three time faces were confirmed.

## Picture Transfer

Picture upload writes to `4b646063-6264-f3a7-8941-e65356ea82fe`.

Observed structure:

```text
00 00
02 00 00
03 ... repeated image chunks
01 01
```

The `03` chunks include an apparent chunk prefix and payload. Some transfers used chunks beginning with `03 ff ...`; later chunks used `03 00 ...`. The final marker was `01 01`.
