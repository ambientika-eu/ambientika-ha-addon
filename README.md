# Ambientika Add-ons for Home Assistant

<p align="center">
  <img src="https://raw.githubusercontent.com/ambientika-eu/ambientika-ha-addon/main/logo.png" alt="Ambientika by Südwind" width="300"/>
</p>

<p align="center">
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"/></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2023.1%2B-blue.svg" alt="HA Version"/>
  <img src="https://img.shields.io/github/v/release/ambientika-eu/ambientika-ha-addon" alt="Release"/>
  <img src="https://img.shields.io/badge/maintained%20by-Südwind%20GmbH-green.svg" alt="Maintained by Südwind"/>
</p>

> **Official** Home Assistant Add-on repository for **Ambientika** ventilation units by [Südwind GmbH](https://www.ambientika.eu).

---

<p align="center">
  <img src="neuracell-x-logo.png" alt="NeuraCell-X - AI Neural Control System (patent-pending)" width="480">
</p>

<h3 align="center">Powered by NeuraCell-X&reg; &mdash; the patent-pending AI Neural Control System</h3>

<p align="center">
  <b>Active radon protection</b> &nbsp;&middot;&nbsp; <b>Intelligent dew-point ventilation</b> &nbsp;&middot;&nbsp; <b>Whole-home, fully automatic</b>
</p>

<p align="center">
  <img alt="Radon" src="https://img.shields.io/badge/Radon-active%20protection-38e1c8">
  <img alt="Dew point" src="https://img.shields.io/badge/Taupunkt-dew--point%20control-3ac6e6">
  <img alt="Patent-pending" src="https://img.shields.io/badge/NeuraCell--X-patent%20pending-6aa9ff">
  <img alt="TUV" src="https://img.shields.io/badge/hardware-T%C3%9CV%20gepr%C3%BCft-4caf50">
</p>

> **When radon rises**, every unit shifts to a gentle fresh-air overpressure (Zuluft, Stufe 1) that slows radon ingress. **When the outside air is too humid to ventilate**, the units pause so no moisture is drawn in. **When conditions are safe again**, normal operation is restored &mdash; automatically, with radon protection always taking priority.

---

## Available Add-ons

### 🌀 Ambientika MQTT Bridge

Connects your Ambientika ventilation units to Home Assistant via MQTT with full Auto-Discovery support.

| Feature | Details |
|---|---|
| **Controls** | Operating mode, fan speed, humidity level, light sensor level; a *Filter zuruecksetzen* button |
| **Sensors** | Temperature and humidity (raw and averaged), air quality, filter status (effective and raw), mode (effective and raw), fan speed, humidity level, light sensor level, device role, last mode, zone - each text value with a numeric companion; diagnostic: filter reset status, filter acknowledgement since / valid until |
| **Binary Sensors** | Humidity alarm, night alarm |
| **Discovery** | MQTT Auto-Discovery (devices appear automatically in HA) |
| **Devices** | Supports up to 20 units per installation |
| **NeuraCell-X®** | Patent-pending radon protection + dew-point control (see below) |

---

## NeuraCell-X&reg; &mdash; patent-pending radon & dew-point protection

![NeuraCell-X](neuracell-x-logo.png)

**NeuraCell-X&reg;** is the AI Neural Control System built into the bridge. It couples the
Ambientika radon meter and dew-point control (Taupunktsteuerung) with your ventilation units:

- **Radon protection (highest priority):** radon alarm &rarr; all units to Intake (Zuluft / supply air) at fan **Stufe 1** &mdash; a gentle fresh-air overpressure that actively slows radon ingress.
- **Dew-point control:** ventilating would raise indoor humidity &rarr; units switch **off**; conditions favourable again &rarr; ventilation released.
- **Exact restore:** when all protections clear, every unit returns to the exact mode it had before.

The live status is published to `ambientika/neuracell/state` and surfaced natively on every platform:

| Platform | NeuraCell-X&reg; surface |
|---|---|
| **Home Assistant** | Auto-discovered *Radon Protection Active*, *Radon Level*, *Radon Meter Connected*, *Ventilation Blocked (Dew Point)*, *Dew Point Controller Connected*, *Dew Point Indoor / Outdoor* |
| **ioBroker** | `ambientika.0.neuracell.*` states |
| **Apple / Google / Alexa** (Homebridge) | *NeuraCell-X* accessory: Radon Protection + Dew-Point Block occupancy sensors |
| **Matter** (SmartThings, ...) | *NeuraCell-X Radon Protection* contact sensor |
| **Node-RED / Loxone** | `ambientika/neuracell/state` inputs (see the examples) |

Configure it in the add-on options: `radon_source` (`signal` or `device`), `radon_threshold`,
`radon_protection_fan`, `dewpoint_source` (`signal`, `computed` or `device`), `dewpoint_margin`, and
more - every option is listed under [Configuration](#configuration) below.

*NeuraCell-X&reg; and PhaseCell-X&reg; are registered trademarks of S&uuml;dwind / Ambientika. Patent pending.*

---

## Installation

1. In Home Assistant, go to **Settings → Apps** and click **Install app** (before HA 2026.2: **Settings → Add-ons → Add-on Store**)
2. Click the three-dot menu (top right) → **Repositories**
3. Add this URL:
   ```
   https://github.com/ambientika-eu/ambientika-ha-addon
   ```
4. Search for **"Ambientika MQTT Bridge"** and click **Install**
5. Configure your Ambientika account credentials and MQTT broker settings
6. Start the add-on

### Prerequisites

- A running **MQTT broker** (e.g. the [Mosquitto add-on](https://github.com/home-assistant/addons/tree/master/mosquitto)); its user name and password go into `mqtt_username` / `mqtt_password`
- An **Ambientika account** — the same e-mail address and password you use in the Ambientika app. There is no separate account for the bridge.

---

## Configuration

| Option | Default | Description |
|---|---|---|
| `ambientika_username` | – | E-mail address of your Ambientika app account |
| `ambientika_password` | – | Password of your Ambientika app account |
| `mqtt_host` | `core-mosquitto` | MQTT broker hostname |
| `mqtt_port` | `1883` | MQTT broker port |
| `mqtt_username` | – | Broker user — **required** for the Mosquitto add-on, which refuses anonymous connections |
| `mqtt_password` | – | Broker password |
| `mqtt_topic_prefix` | `ambientika` | MQTT topic prefix |
| `poll_interval` | `30` | Polling interval in seconds (10–300) |
| `availability_failure_threshold` | `3` | Consecutive failed reads before a unit is shown unavailable |
| `log_level` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `command_coalesce_ms` | `800` | Commands for the same unit within this window are applied in one call (`0` = immediately) |
| `average_window_min` | `30` | Window of the averaged sensors *Humidity (averaged)* and *Temperature (averaged)*, in minutes (1–240; at least twenty poll intervals; details in DOCS.md) |
| `average_window_devices` | *(empty)* | Own window for single units: `unit=minutes` entries, comma-separated, by serial number or by the unit's name as in the app (1–240 minutes), e.g. `A1B2C3D4E5F6=15, Schlafzimmer Eltern=60`. The serial number is the safe way (it is in the add-on log and in the app); a name must match the app's spelling - upper/lower case does not matter, and a hyphen, underscore or space count as the same separator; anything else does matter. Units not listed use `average_window_min` (details in DOCS.md) |
| `slave_filter_soft_reset` | `false` | Maintenance acknowledgement for Slave filter counters |
| `filter_ack_ttl_days` | `90` | How long an acknowledgement stays valid |

Leaving `mqtt_username` and `mqtt_password` empty is the most common setup
mistake: the log then shows `MQTT connection failed (rc=5)`.

### NeuraCell-X (radon protection and dew-point control)

The options starting with `radon_` and `dewpoint_` configure the radon and
dew-point protection. They only matter if you have the matching hardware, and
the defaults are safe to leave alone. The Ambientika radon meter
(`radon/<id>/state`) and the Ambientika Taupunktsteuerung (`dew-point/<id>/state`,
`ventilating`) are read directly with the defaults, nothing to configure. The
sensors *Radon Meter Connected* and *Dew Point Controller Connected* show whether
the two devices are still talking to the broker: their Last Will counts at once,
a radon meter silent for longer than `radon_meter_timeout` (30 min) counts as
disconnected as well, also after an add-on restart (the meters seen so far are
remembered on the broker). A third-party dew-point controller needs
`dewpoint_availability_topic` or `dewpoint_signal_timeout` for that (with
`dewpoint_source: device` it follows the cloud reads instead). How the two
protections work together (radon first, exact restore of every unit's mode) is
described in the
[project README](https://github.com/ambientika-eu/ambientika-mqtt-bridge#neuracell-x--patent-pending-radon--dew-point-protection).

**Radon protection** - radon alarm: every unit to Intake (supply air) at
`radon_protection_fan` until the value is back below the threshold minus the
hysteresis.

| Option | Default | Description |
|---|---|---|
| `neuracell_enabled` | `true` | Radon protection on or off |
| `radon_source` | `signal` | `signal`: the radon value and alarm come from the MQTT topics below. `device`: the radon meter's status is read from the Ambientika cloud, no MQTT signal needed |
| `radon_threshold` | `300` | Bq/m³ at which radon protection starts (50–1000; 300 is the German reference value). With `radon_source: device` also the limit for a numeric alarm field |
| `radon_hysteresis` | `50` | Bq/m³ the value must fall below the threshold before protection ends (0–500) |
| `radon_protection_fan` | `Low` | Fan speed during radon protection: `Low`, `Medium` or `High` |
| `radon_meter_topic` | `radon/+/state` | Native topic of the Ambientika radon meter (MQTT mode 4, `{"mittelwert": …}`), read directly. `none` switches the direct read off |
| `radon_meter_timeout` | `30` | Minutes without any message from an Ambientika radon meter before it counts as disconnected (0 = off; the meter reports every 10 minutes, 20 or more is recommended) |
| `radon_topic` | `ambientika/radon/value` | Topic with a radon value in Bq/m³ from any other source: a plain number or JSON (see `radon_value_key`); MQTT wildcards allowed. With several sources the highest current value decides |
| `radon_alarm_topic` | `ambientika/radon/alarm` | Topic with an explicit alarm (`ON`/`OFF`, `true`/`false`). Value and alarm are combined, either one keeps protection on. `none` = ignored, so a stale retained `ON` can never hold protection |
| `radon_value_key` | `mittelwert` | JSON key of the radon value when `radon_topic` or the meter topic carries JSON |
| `radon_device_serial` | *(empty)* | `radon_source: device`: serial number of the radon meter (shown in the add-on log). The meter is read only, never exposed as a fan |
| `radon_device_alarm_field` | `air_quality` | `radon_source: device`: the status field of the meter that carries its alarm or level. A numeric field is compared with `radon_threshold`, a text field with the values below |
| `radon_device_alarm_values` | `Bad,Poor,Very Bad,Alarm,Alert` | `radon_source: device`: text values of that field that mean "radon alarm" (comma-separated, upper/lower case does not matter) |

**Dew-point control** - ventilating would raise indoor humidity: the units in
`dewpoint_block_devices` switch off until conditions are favourable again. Radon
protection always has priority.

| Option | Default | Description |
|---|---|---|
| `dewpoint_enabled` | `true` | Dew-point control on or off |
| `dewpoint_source` | `signal` | `signal`: a block signal from MQTT - the Ambientika Taupunktsteuerung on its own topic (below) or a third-party source on `dewpoint_block_topic`. `computed`: the bridge computes indoor and outdoor dew point from four sensor topics. `device`: the Taupunktsteuerung's status is read from the Ambientika cloud |
| `dewpoint_block_devices` | *(empty)* | Units the block applies to, by name as in the app or serial number, comma-separated (e.g. the basement units). Empty = all units |
| `dewpoint_controller_topic` | `dew-point/+/state` | Native topic of the Ambientika Taupunktsteuerung (MQTT firmware), read directly; its Last Will on `dew-point/<id>/availability/state` and its sensor messages are watched automatically. `none` switches the direct read off |
| `dewpoint_controller_key` | `ventilating` | JSON key in those messages; `false` means: block ventilation |
| `dewpoint_block_topic` | `ambientika/dewpoint/block` | `signal`: topic of a third-party block signal (`ON`/`true`/`1` = block). The last message wins. Leave it at its default so it does not overlap the controller topic |
| `dewpoint_block_key` | *(empty)* | JSON key of the block flag when `dewpoint_block_topic` carries a JSON object |
| `dewpoint_availability_topic` | *(empty)* | `signal`: availability topic with Last Will of a third-party controller (`online`/`offline`, `true`/`false` or JSON with `state`). The Ambientika controller needs none |
| `dewpoint_signal_timeout` | `0` | `signal`: minutes without any message from the controller before it counts as disconnected (0 = off). For controllers without Last Will; not applied while a Last Will reports online |
| `dewpoint_lost_action` | `keep` | While the controller counts as disconnected: `keep` the last block state, `release` ventilation, or `block` the units. Radon keeps priority either way |
| `dewpoint_indoor_temp_topic` | `ambientika/dewpoint/indoor_temp` | `computed`: indoor temperature in °C |
| `dewpoint_indoor_humidity_topic` | `ambientika/dewpoint/indoor_humidity` | `computed`: indoor relative humidity in % |
| `dewpoint_outdoor_temp_topic` | `ambientika/dewpoint/outdoor_temp` | `computed`: outdoor temperature in °C |
| `dewpoint_outdoor_humidity_topic` | `ambientika/dewpoint/outdoor_humidity` | `computed`: outdoor relative humidity in % |
| `dewpoint_margin` | `1.0` | `computed`: block as soon as the outdoor dew point reaches the indoor dew point minus this margin (°C) - ventilating would then add moisture |
| `dewpoint_hysteresis` | `0.5` | `computed`: release only once the outdoor dew point is this much (°C) below that line again |
| `dewpoint_device_serial` | *(empty)* | `dewpoint_source: device`: serial number of the Taupunktsteuerung (shown in the add-on log). It is read only, never exposed as a fan |
| `dewpoint_device_block_modes` | `Off` | `dewpoint_source: device`: operating modes of the Taupunktsteuerung that mean "block" (comma-separated) |

The full user documentation is in
[`ambientika_mqtt_bridge/DOCS.md`](ambientika_mqtt_bridge/DOCS.md); Home Assistant
shows it in the add-on's **Documentation** tab.

---

## Support

- 🐛 **Issues & Bug Reports:** [GitHub Issues](https://github.com/ambientika-eu/ambientika-ha-addon/issues)
- 🌐 **Website:** [www.ambientika.eu](https://www.ambientika.eu)
- 📧 **E-Mail:** [info@ambientika.eu](mailto:info@ambientika.eu)

---

## About

This add-on is developed and maintained by **Südwind GmbH**, the manufacturer of Ambientika ventilation systems.

© Südwind GmbH – [www.ambientika.eu](https://www.ambientika.eu)

---

## Humidity and dew-point control

The folder feuchteregelung holds a ready-made Home Assistant package for humidity- and dew-point-based ventilation control. It is generated from a short configuration file, so ten units can be covered without copy-paste errors, and it builds on the entities this add-on creates.

The point that matters: ventilation only dries a room when the outdoor air holds less water in absolute terms. Relative humidity is the wrong measure for that decision — outside at 28 °C and 60 % there are 16.3 g of water per m³, inside at 22 °C and 60 % only 11.6. The package therefore works with absolute humidity and dew point throughout, and applies a per-unit sensor offset taken from your own comparison measurement.

Installation, the calibration procedure and the reasoning behind it are described in feuchteregelung/README.md. 56 tests, no hardware required.
