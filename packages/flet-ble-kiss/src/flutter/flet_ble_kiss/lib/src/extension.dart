import 'package:flet/flet.dart';

import 'ble_kiss.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "BleKiss":
        return BleKissService(control: control);
      default:
        return null;
    }
  }
}
