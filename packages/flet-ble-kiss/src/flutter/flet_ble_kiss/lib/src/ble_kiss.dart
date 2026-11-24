// A KISS TNC over Bluetooth Low Energy, for the Python side of the app (aprs_kiss_app/ble_flet.py).
//
// KISS over BLE (github.com/hessu/aprs-specs, BLE-KISS-API.md): one GATT service; the app writes KISS
// bytes to one characteristic and gets the TNC's by notifications on another, cut into pieces as the
// link allows: the Python side puts the frames back together like from a serial line.
// Used by Mobilinkd TNC3/TNC4, PicoAPRS, the CA2RXU LoRa APRS Tracker, B.B. Link, VR-N76 / UV-Pro …
//
// Methods: scan, connect, write, disconnect, ping. Events: "data" (base64 of the bytes received),
// "lost" (the link dropped, with the reason).

import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:flet/flet.dart';
import 'package:flutter/foundation.dart';
import 'package:universal_ble/universal_ble.dart';

const kissService = "00000001-ba2a-46c9-ae49-01b0961f68bb";
const kissWrite = "00000002-ba2a-46c9-ae49-01b0961f68bb"; // to the TNC
const kissNotify = "00000003-ba2a-46c9-ae49-01b0961f68bb"; // from the TNC

class BleKissService extends FletService {
  BleKissService({required super.control});

  String? _device; // the one connected
  int _chunk = 20; // bytes per write: the ATT MTU less 3
  bool _withResponse = true;
  StreamSubscription<Uint8List>? _values;
  StreamSubscription<BleConnectionChange>? _connection;
  final Map<String, BleDevice> _seen = {};

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_invokeMethod);
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("BleKiss.$name");
    switch (name) {
      case "ping":
        return "ok";
      case "scan":
        return await _scan(((args?["seconds"] ?? 6) as num).toDouble());
      case "connect":
        return await _connect(args["id"] as String);
      case "write":
        await _write(base64Decode(args["data"] as String));
        return null;
      case "disconnect":
        await _disconnect();
        return null;
      default:
        throw Exception("Unknown BleKiss method: $name");
    }
  }

  Future<void> _ready() async {
    await UniversalBle.requestPermissions();
    var state = await UniversalBle.getBluetoothAvailabilityState();
    if (state == AvailabilityState.unknown || state == AvailabilityState.resetting) {
      // iOS and macOS know only a moment after the start
      state = await UniversalBle.availabilityStream
          .firstWhere((s) => s != AvailabilityState.unknown && s != AvailabilityState.resetting)
          .timeout(const Duration(seconds: 5), onTimeout: () => state);
    }
    switch (state) {
      case AvailabilityState.poweredOff:
        throw Exception("Bluetooth is off: switch it on");
      case AvailabilityState.unauthorized:
        throw Exception("Not allowed to use Bluetooth: allow it for the app in the system settings");
      case AvailabilityState.unsupported:
        throw Exception("This device has no Bluetooth LE");
      default:
        return;
    }
  }

  /// The devices around for `seconds`: those offering KISS first, then the others with a name.
  Future<List<Map<String, dynamic>>> _scan(double seconds) async {
    await _ready();
    final found = <String, BleDevice>{};
    final sub = UniversalBle.scanStream.listen((d) {
      found[d.deviceId] = d;
      _seen[d.deviceId] = d;
    });
    try {
      await UniversalBle.startScan();
      await Future.delayed(Duration(milliseconds: (seconds * 1000).round()));
    } finally {
      await UniversalBle.stopScan();
      await sub.cancel();
    }
    final list = found.values
        .where((d) => _offersKiss(d) || (d.name ?? "").isNotEmpty)
        .map((d) => {
              "id": d.deviceId,
              "name": d.name ?? "",
              "rssi": d.rssi,
              "kiss": _offersKiss(d),
            })
        .toList();
    list.sort((a, b) {
      final k = (b["kiss"] == true ? 1 : 0) - (a["kiss"] == true ? 1 : 0);
      return k != 0 ? k : ((b["rssi"] as int?) ?? -999) - ((a["rssi"] as int?) ?? -999);
    });
    return list;
  }

  bool _offersKiss(BleDevice d) => d.services.any((s) => BleUuidParser.compareStrings(s, kissService));

  /// Finds the device by a short scan when this run has not seen it yet (iOS knows a device only so).
  Future<void> _find(String id) async {
    if (_seen.containsKey(id)) return;
    final done = Completer<void>();
    final sub = UniversalBle.scanStream.listen((d) {
      _seen[d.deviceId] = d;
      if (d.deviceId == id && !done.isCompleted) done.complete();
    });
    try {
      await UniversalBle.startScan();
      await done.future.timeout(const Duration(seconds: 10), onTimeout: () {});
    } finally {
      await UniversalBle.stopScan();
      await sub.cancel();
    }
  }

  Future<Map<String, dynamic>> _connect(String id) async {
    await _disconnect();
    await _ready();
    await _find(id);
    await UniversalBle.connect(id, timeout: const Duration(seconds: 20));
    try {
      final services = await UniversalBle.discoverServices(id);
      final service = services.firstWhere((s) => BleUuidParser.compareStrings(s.uuid, kissService),
          orElse: () => throw Exception("The device offers no KISS over Bluetooth LE: "
              "switch KISS on in its Bluetooth settings"));
      BleCharacteristic? out;
      BleCharacteristic? inp;
      for (final c in service.characteristics) {
        if (BleUuidParser.compareStrings(c.uuid, kissWrite)) out = c;
        if (BleUuidParser.compareStrings(c.uuid, kissNotify)) inp = c;
      }
      if (out == null || inp == null) {
        throw Exception("The device's KISS service is incomplete");
      }
      _withResponse = out.properties.contains(CharacteristicProperty.write);
      var mtu = 23;
      try {
        mtu = await UniversalBle.requestMtu(id, 517);
      } catch (e) {
        debugPrint("BleKiss: MTU $e");
      }
      _chunk = max(20, mtu - 3);
      _device = id;
      _values = UniversalBle.characteristicValueStream(id, kissNotify).listen((value) {
        if (_device == id && value.isNotEmpty) {
          control.triggerEvent("data", base64Encode(value));
        }
      });
      _connection = UniversalBle.connectionChangeStream(id).listen((change) {
        if (!change.isConnected && _device == id) {
          _device = null;
          _values?.cancel();
          control.triggerEvent("lost", change.error ?? "Bluetooth LE link lost");
        }
      });
      await UniversalBle.subscribeNotifications(id, kissService, kissNotify);
      return {"mtu": mtu, "name": _seen[id]?.name ?? ""};
    } catch (e) {
      _device = null;
      await _values?.cancel();
      await _connection?.cancel();
      try {
        await UniversalBle.disconnect(id);
      } catch (_) {}
      rethrow;
    }
  }

  Future<void> _write(Uint8List data) async {
    final id = _device;
    if (id == null) throw Exception("Bluetooth LE TNC not connected");
    for (var i = 0; i < data.length; i += _chunk) {
      final part = data.sublist(i, min(i + _chunk, data.length));
      await UniversalBle.write(id, kissService, kissWrite, part, withoutResponse: !_withResponse);
    }
  }

  Future<void> _disconnect() async {
    final id = _device;
    _device = null;
    await _values?.cancel();
    await _connection?.cancel();
    _values = null;
    _connection = null;
    if (id == null) return;
    try {
      await UniversalBle.unsubscribe(id, kissService, kissNotify);
    } catch (_) {}
    try {
      await UniversalBle.disconnect(id);
    } catch (_) {}
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    _disconnect();
    super.dispose();
  }
}
