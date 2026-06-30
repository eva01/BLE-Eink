import CoreBluetooth
import Foundation

private func data(_ hex: String) -> Data {
    let cleaned = hex
        .split { $0 == " " || $0 == "\n" || $0 == "\t" }
        .joined()
    var bytes = [UInt8]()
    var index = cleaned.startIndex
    while index < cleaned.endIndex {
        let next = cleaned.index(index, offsetBy: 2)
        bytes.append(UInt8(cleaned[index..<next], radix: 16) ?? 0)
        index = next
    }
    return Data(bytes)
}

private extension Data {
    var hexString: String {
        map { String(format: "%02x", $0) }.joined(separator: " ")
    }

    var asciiString: String {
        String(data: self, encoding: .utf8) ?? ""
    }
}

final class DADialogTrap: NSObject, CBPeripheralManagerDelegate {
    private let advertisedName: String
    private var manager: CBPeripheralManager!
    private var values: [CBUUID: Data] = [:]
    private var names: [CBUUID: String] = [:]
    private var notifyCharacteristics: [CBUUID: CBMutableCharacteristic] = [:]

    init(advertisedName: String) {
        self.advertisedName = advertisedName
        super.init()
        manager = CBPeripheralManager(delegate: self, queue: nil)
    }

    func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
        guard peripheral.state == .poweredOn else {
            print("Bluetooth state: \(peripheral.state.rawValue). Waiting for powered on...")
            return
        }

        print("Bluetooth powered on. Publishing DA/Dialog tag trap GATT...")
        publishServices()
        advertise()
    }

    private func makeChar(
        _ uuid: String,
        name: String,
        properties: CBCharacteristicProperties,
        permissions: CBAttributePermissions,
        readValue: Data? = nil
    ) -> CBMutableCharacteristic {
        let id = CBUUID(string: uuid)
        names[id] = name
        if let readValue {
            values[id] = readValue
        }
        let characteristic = CBMutableCharacteristic(
            type: id,
            properties: properties,
            value: nil,
            permissions: permissions
        )
        if properties.contains(.notify) || properties.contains(.indicate) {
            notifyCharacteristics[id] = characteristic
        }
        return characteristic
    }

    private func publishServices() {
        manager.removeAllServices()

        let battery = CBMutableService(type: CBUUID(string: "180F"), primary: true)
        battery.characteristics = [
            makeChar("2A19", name: "Battery Level", properties: [.read, .notify], permissions: [.readable], readValue: data("00"))
        ]

        let deviceInfo = CBMutableService(type: CBUUID(string: "180A"), primary: true)
        deviceInfo.characteristics = [
            makeChar("2A29", name: "Manufacturer", properties: [.read], permissions: [.readable], readValue: Data("Dialog Semi".utf8)),
            makeChar("2A24", name: "Model", properties: [.read], permissions: [.readable], readValue: Data("DA14585".utf8)),
            makeChar("2A26", name: "Firmware", properties: [.read], permissions: [.readable], readValue: Data("v_6.0.18.1182.1".utf8)),
            makeChar("2A28", name: "Software", properties: [.read], permissions: [.readable], readValue: Data("v_6.0.18.1182.1".utf8)),
            makeChar("2A23", name: "Dummy System ID", properties: [.read], permissions: [.readable], readValue: data("12 34 56 ff fe 9a bc de")),
            makeChar("2A50", name: "PnP ID", properties: [.read], permissions: [.readable], readValue: data("01 d2 00 80 05 00 01")),
        ]

        let suota = CBMutableService(type: CBUUID(string: "FEF5"), primary: true)
        suota.characteristics = [
            makeChar("8082caa8-41a6-4021-91c6-56f9b954cc34", name: "SUOTA mem dev", properties: [.read, .write], permissions: [.readable, .writeable], readValue: Data()),
            makeChar("724249f0-5ec3-4b5f-8804-42345af08651", name: "SUOTA gpio map", properties: [.read, .write], permissions: [.readable, .writeable], readValue: Data()),
            makeChar("6c53db25-47a1-45fe-a022-7c92fb334fd4", name: "SUOTA mem info", properties: [.read], permissions: [.readable], readValue: Data()),
            makeChar("9d84b9a3-000c-49d8-9183-855b673fda31", name: "SUOTA patch len", properties: [.read, .write], permissions: [.readable, .writeable], readValue: Data()),
            makeChar("457871e8-d516-4ca1-9116-57d0b17b9cb2", name: "SUOTA patch data", properties: [.read, .write, .writeWithoutResponse], permissions: [.readable, .writeable], readValue: Data()),
            makeChar("5f78df94-798c-46f5-990a-b3eb6a065c88", name: "SUOTA status", properties: [.read, .notify], permissions: [.readable], readValue: data("00")),
            makeChar("64b4e8b5-0de5-401b-a21d-acc8db3b913a", name: "SUOTA version", properties: [.read], permissions: [.readable], readValue: data("0d")),
            makeChar("42c3dfdd-77be-4d9c-8454-8f875267fb3b", name: "SUOTA mtu", properties: [.read], permissions: [.readable], readValue: data("f4 00")),
            makeChar("b7de1eea-823d-43bb-a3af-c4903dfce23c", name: "SUOTA l2cap", properties: [.read], permissions: [.readable], readValue: data("00 02")),
        ]

        let led = CBMutableService(type: CBUUID(string: "13187b10-eba9-a3ba-044e-83d3217d9a38"), primary: true)
        led.characteristics = [
            makeChar("4b646063-6264-f3a7-8941-e65356ea82fe", name: "LED State", properties: [.write, .notify], permissions: [.writeable])
        ]

        let writeMe = CBMutableService(type: CBUUID(string: "00001f10-0000-1000-8000-00805f9b34fb"), primary: true)
        writeMe.characteristics = [
            makeChar("00001f1f-0000-1000-8000-00805f9b34fb", name: "Write me", properties: [.write], permissions: [.writeable])
        ]

        let readNotify = CBMutableService(type: CBUUID(string: "0000221f-0000-1000-8000-00805f9b34fb"), primary: true)
        readNotify.characteristics = [
            makeChar("0000331f-0000-1000-8000-00805f9b34fb", name: "Read me (notify)", properties: [.read, .write, .notify], permissions: [.readable, .writeable], readValue: Data())
        ]

        [battery, deviceInfo, suota, led, writeMe, readNotify].forEach(manager.add)
    }

    private func advertise() {
        let advertisedServices = [
            CBUUID(string: "FEF5"),
        ]
        manager.startAdvertising([
            CBAdvertisementDataLocalNameKey: advertisedName,
            CBAdvertisementDataServiceUUIDsKey: advertisedServices,
        ])
        print("Advertising as \(advertisedName)")
        print("If the app filters strictly by name, rerun with --name <expected-device-name> and move the real tag away.")
    }

    func peripheralManagerDidStartAdvertising(_ peripheral: CBPeripheralManager, error: Error?) {
        if let error {
            print("Advertising failed: \(error)")
        } else {
            print("Advertising started.")
        }
    }

    func peripheralManager(_ peripheral: CBPeripheralManager, didAdd service: CBService, error: Error?) {
        if let error {
            print("Service add failed \(service.uuid): \(error)")
        } else {
            print("Service added \(service.uuid)")
        }
    }

    func peripheralManager(_ peripheral: CBPeripheralManager, didReceiveRead request: CBATTRequest) {
        let uuid = request.characteristic.uuid
        let value = values[uuid] ?? Data()
        request.value = value
        peripheral.respond(to: request, withResult: .success)
        print("READ  \(names[uuid] ?? "") \(uuid) -> \(value.hexString)")
    }

    func peripheralManager(_ peripheral: CBPeripheralManager, didReceiveWrite requests: [CBATTRequest]) {
        for request in requests {
            let uuid = request.characteristic.uuid
            let value = request.value ?? Data()
            values[uuid] = value
            let ascii = value.asciiString
            let asciiPart = ascii.isEmpty ? "" : " ascii='\(ascii)'"
            print("WRITE \(names[uuid] ?? "") \(uuid) <- \(value.hexString)\(asciiPart)")

            if let notifyCharacteristic = notifyCharacteristics[uuid] {
                peripheral.updateValue(value, for: notifyCharacteristic, onSubscribedCentrals: nil)
            }
        }

        for request in requests where request.characteristic.properties.contains(.write) {
            peripheral.respond(to: request, withResult: .success)
        }
    }

    func peripheralManager(_ peripheral: CBPeripheralManager, central: CBCentral, didSubscribeTo characteristic: CBCharacteristic) {
        print("SUBSCRIBE \(names[characteristic.uuid] ?? "") \(characteristic.uuid) from \(central.identifier)")
    }

    func peripheralManager(_ peripheral: CBPeripheralManager, central: CBCentral, didUnsubscribeFrom characteristic: CBCharacteristic) {
        print("UNSUBSCRIBE \(names[characteristic.uuid] ?? "") \(characteristic.uuid) from \(central.identifier)")
    }
}

let cliName = CommandLine.arguments.dropFirst().first == "--name"
    ? CommandLine.arguments.dropFirst(2).first
    : nil
let trap = DADialogTrap(advertisedName: cliName ?? "DA-TAG-TRAP")
withExtendedLifetime(trap) {
    RunLoop.main.run()
}
