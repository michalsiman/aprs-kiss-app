# Changelog

## 0.1.0 – 2026-11-17

First standalone version, for Linux.

- The radio core of the Home Assistant integration 0.3.4 (KISS, AX.25, APRS, APRS-IS, iGate,
  sessions) without Home Assistant; `Engine` replaces the integration's hub and announces events
  to listeners.
- TNC transports are pluggable (TCP and serial built in), ready for Android USB and Bluetooth.
- Settings and message history saved as JSON in the user's data folder.
- Flet desktop app: map, messages, stations, terminal, chat, monitor, settings; English and Czech.
- Tests of the core and of the engine against the simulated TNC; CI and a Linux build workflow.
