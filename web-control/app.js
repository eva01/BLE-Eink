const CLASSES = {
  nrf: {
    label: "NRF / Nordic",
    serviceUuid: "62750001-d828-918d-fb46-b6c11c675aec",
    writeUuid: "62750002-d828-918d-fb46-b6c11c675aec",
    versionUuid: "62750003-d828-918d-fb46-b6c11c675aec",
    filters: [{ namePrefix: "NRF_EPD" }, { services: ["62750001-d828-918d-fb46-b6c11c675aec"] }],
    optionalServices: [
      "62750001-d828-918d-fb46-b6c11c675aec",
      "0000fe59-0000-1000-8000-00805f9b34fb",
    ],
  },
  da: {
    label: "DA / Dialog Tag",
    serviceUuid: "00001f10-0000-1000-8000-00805f9b34fb",
    writeUuid: "00001f1f-0000-1000-8000-00805f9b34fb",
    filters: [{ namePrefix: "NRF-" }, { services: ["00001f10-0000-1000-8000-00805f9b34fb"] }],
    optionalServices: [
      "00001f10-0000-1000-8000-00805f9b34fb",
      "0000221f-0000-1000-8000-00805f9b34fb",
      "13187b10-eba9-a3ba-044e-83d3217d9a38",
      "0000fef5-0000-1000-8000-00805f9b34fb",
    ],
  },
};

const DA_SEQUENCES = {
  "type-250x128": ["e0 01", "daTimestamp", "e2"],
  "type-296x128": ["e0 02", "daTimestamp", "e2"],
  "type-296x152": ["e0 04", "daTimestamp", "e2"],
  "type-300x400": ["e0 03", "daTimestamp", "e2"],
  "mode-picture": ["e1 00", "daTimestamp", "e2"],
  "mode-calendar": ["e1 01", "daTimestamp", "e2"],
  "mode-time": ["e1 02", "daTimestamp", "e2"],
  "sync-time": ["daTimestamp", "e2"],
};

let activeClass = "nrf";
let connectedClass = null;
let bluetoothDevice = null;
let writeCharacteristic = null;
let versionCharacteristic = null;

const statusEl = document.querySelector("#status");
const statusDot = document.querySelector("#statusDot");
const connectButton = document.querySelector("#connectButton");
const disconnectButton = document.querySelector("#disconnectButton");
const deviceNameEl = document.querySelector("#deviceName");
const deviceMetaEl = document.querySelector("#deviceMeta");
const firmwareVersionEl = document.querySelector("#firmwareVersion");
const systemTimeEl = document.querySelector("#systemTime");
const logEl = document.querySelector("#log");
const rawHexEl = document.querySelector("#rawHex");

function log(message) {
  const time = new Date().toLocaleTimeString();
  logEl.textContent += `[${time}] ${message}\n`;
  logEl.scrollTop = logEl.scrollHeight;
}

function setConnected(connected, label = "") {
  statusEl.textContent = connected ? `Connected${label ? `: ${label}` : ""}` : "Disconnected";
  statusDot.classList.toggle("connected", connected);
  connectButton.disabled = connected;
  disconnectButton.disabled = !connected;
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.disabled = connected;
  });
}

function setActiveClass(nextClass) {
  if (connectedClass) {
    log("Disconnect before changing target.");
    return;
  }
  activeClass = nextClass;
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.class === activeClass);
  });
  document.querySelector("#nrfPanel").classList.toggle("hidden", activeClass !== "nrf");
  document.querySelector("#daPanel").classList.toggle("hidden", activeClass !== "da");
  rawHexEl.placeholder = activeClass === "nrf" ? "20 00 00 00 00 08 01" : "e1 02";
  deviceMetaEl.textContent = `${CLASSES[activeClass].label} selected. Connect to write commands.`;
}

function parseHex(hex) {
  const trimmed = hex.trim();
  if (!trimmed) {
    throw new Error("Hex is required.");
  }
  if (!/^[0-9a-fA-F]{2}([ :,-]?[0-9a-fA-F]{2})*$/.test(trimmed)) {
    throw new Error("Use complete hex bytes separated by spaces, colons, commas, or hyphens.");
  }
  const tokens = /[ :,-]/.test(trimmed)
    ? trimmed.split(/[ :,-]+/).filter(Boolean)
    : trimmed.match(/[0-9a-fA-F]{2}/g);
  if (!tokens || tokens.some((token) => token.length !== 2)) {
    throw new Error("Use complete two-digit hex bytes.");
  }
  return new Uint8Array(tokens.map((token) => Number.parseInt(token, 16)));
}

function toHex(bytes) {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join(" ");
}

function signedByte(value) {
  return value < 0 ? 0x100 + value : value;
}

function nrfTimePacket(mode) {
  const now = new Date();
  const timestamp = Math.floor(now.getTime() / 1000);
  const timezone = signedByte(-(now.getTimezoneOffset() / 60));
  return new Uint8Array([
    0x20,
    (timestamp >>> 24) & 0xff,
    (timestamp >>> 16) & 0xff,
    (timestamp >>> 8) & 0xff,
    timestamp & 0xff,
    timezone,
    mode,
  ]);
}

function daTimestampPacket() {
  const now = new Date();
  const value = Math.floor(Date.UTC(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    now.getHours(),
    now.getMinutes(),
    now.getSeconds(),
  ) / 1000);
  return new Uint8Array([
    0xdd,
    (value >>> 24) & 0xff,
    (value >>> 16) & 0xff,
    (value >>> 8) & 0xff,
    value & 0xff,
  ]);
}

function startSystemClock() {
  const update = () => {
    systemTimeEl.textContent = new Date().toLocaleTimeString();
  };
  update();
  setInterval(update, 1000);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ensureConnected(expectedClass = activeClass) {
  if (!writeCharacteristic || connectedClass !== expectedClass) {
    throw new Error(`Connect to a ${CLASSES[expectedClass].label} device first.`);
  }
}

async function writeBytes(bytes, expectedClass = activeClass, withResponse = true) {
  ensureConnected(expectedClass);
  if (withResponse) {
    await writeCharacteristic.writeValueWithResponse(bytes);
  } else {
    await writeCharacteristic.writeValueWithoutResponse(bytes);
  }
  log(`write ${toHex(bytes)}`);
}

async function writeSequence(items, expectedClass = activeClass) {
  for (const item of items) {
    const bytes = item === "daTimestamp" ? daTimestampPacket() : parseHex(item);
    await writeBytes(bytes, expectedClass);
    await sleep(150);
  }
}

async function connect() {
  if (!navigator.bluetooth) {
    log("Web Bluetooth is not available in this browser.");
    return;
  }

  const config = CLASSES[activeClass];
  bluetoothDevice = await navigator.bluetooth.requestDevice({
    filters: config.filters,
    optionalServices: config.optionalServices,
  });

  bluetoothDevice.addEventListener("gattserverdisconnected", () => {
    cleanupConnection();
    log("device disconnected");
  });

  const server = await bluetoothDevice.gatt.connect();
  const service = await server.getPrimaryService(config.serviceUuid);
  writeCharacteristic = await service.getCharacteristic(config.writeUuid);
  versionCharacteristic = config.versionUuid ? await service.getCharacteristic(config.versionUuid) : null;
  connectedClass = activeClass;
  const name = bluetoothDevice.name || bluetoothDevice.id;
  deviceNameEl.textContent = name;
  deviceMetaEl.textContent = config.label;
  setConnected(true, name);
  log(`connected to ${name}`);
  if (connectedClass === "nrf") {
    await readNrfVersion();
  }
}

function cleanupConnection() {
  writeCharacteristic = null;
  versionCharacteristic = null;
  connectedClass = null;
  firmwareVersionEl.textContent = "--";
  setConnected(false);
}

function disconnect() {
  if (bluetoothDevice?.gatt?.connected) {
    bluetoothDevice.gatt.disconnect();
  }
  cleanupConnection();
}

async function readNrfVersion() {
  if (!versionCharacteristic) {
    throw new Error("NRF app-version characteristic is not available.");
  }
  const value = await versionCharacteristic.readValue();
  const version = value.getUint8(0);
  firmwareVersionEl.textContent = `0x${version.toString(16).padStart(2, "0")}`;
  log(`firmware version 0x${version.toString(16).padStart(2, "0")}`);
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setActiveClass(button.dataset.class));
});

connectButton.addEventListener("click", () => {
  connect().catch((error) => log(`connect failed: ${error.message}`));
});

disconnectButton.addEventListener("click", disconnect);

document.querySelector("#clearLog").addEventListener("click", () => {
  logEl.textContent = "";
});

document.querySelectorAll("[data-nrf-time-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    const mode = Number.parseInt(button.dataset.nrfTimeMode, 10);
    writeBytes(nrfTimePacket(mode), "nrf").catch((error) => log(`sync failed: ${error.message}`));
  });
});

document.querySelectorAll("[data-nrf-raw]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.confirm && !window.confirm(button.dataset.confirm)) {
      return;
    }
    writeSequence([button.dataset.nrfRaw], "nrf").catch((error) => log(`write failed: ${error.message}`));
  });
});

document.querySelector("#nrfReadVersion").addEventListener("click", () => {
  readNrfVersion().catch((error) => log(`read failed: ${error.message}`));
});

document.querySelectorAll("[data-da-sequence]").forEach((button) => {
  button.addEventListener("click", () => {
    writeSequence(DA_SEQUENCES[button.dataset.daSequence], "da").catch((error) => log(`write failed: ${error.message}`));
  });
});

document.querySelectorAll("[data-da-raw]").forEach((button) => {
  button.addEventListener("click", () => {
    writeSequence([button.dataset.daRaw], "da").catch((error) => log(`write failed: ${error.message}`));
  });
});

document.querySelector("#rawSend").addEventListener("click", () => {
  writeSequence([rawHexEl.value], activeClass).catch((error) => log(`write failed: ${error.message}`));
});

setActiveClass("nrf");
setConnected(false);
startSystemClock();
