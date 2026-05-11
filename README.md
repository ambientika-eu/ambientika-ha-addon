# Ambientika Add-ons for Home Assistant

<p align="center">
  <img src="https://www.ambientika.eu/wp-content/uploads/ambientika-logo.png" alt="Ambientika by Südwind" width="300"/>
</p>

<p align="center">
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"/></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2023.1%2B-blue.svg" alt="HA Version"/>
  <img src="https://img.shields.io/github/v/release/ambientika-eu/ambientika-ha-addon" alt="Release"/>
  <img src="https://img.shields.io/badge/maintained%20by-Südwind%20GmbH-green.svg" alt="Maintained by Südwind"/>
</p>

> **Official** Home Assistant Add-on repository for **Ambientika** ventilation units by [Südwind GmbH](https://www.ambientika.eu).

---

## Available Add-ons

### 🌀 Ambientika MQTT Bridge

Connects your Ambientika ventilation units to Home Assistant via MQTT with full Auto-Discovery support.

| Feature | Details |
|---|---|
| **Controls** | Operating mode, fan speed, humidity setpoint |
| **Sensors** | Humidity, temperatures, air quality, power consumption |
| **Binary Sensors** | Filter alarm, defrost active |
| **Discovery** | MQTT Auto-Discovery (devices appear automatically in HA) |
| **Devices** | Supports up to 20 units per installation |

---

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the three-dot menu (top right) → **Repositories**
3. Add this URL:
   ```
   https://github.com/ambientika-eu/ambientika-ha-addon
   ```
4. Search for **"Ambientika MQTT Bridge"** and click **Install**
5. Configure your Ambientika account credentials and MQTT broker settings
6. Start the add-on

### Prerequisites

- A running **MQTT broker** (e.g. the [Mosquitto add-on](https://github.com/home-assistant/addons/tree/master/mosquitto))
- An active **Ambientika cloud account** (from your Ambientika app)

---

## Configuration

| Option | Default | Description |
|---|---|---|
| `ambientika_username` | – | Your Ambientika account e-mail |
| `ambientika_password` | – | Your Ambientika account password |
| `mqtt_host` | `core-mosquitto` | MQTT broker hostname |
| `mqtt_port` | `1883` | MQTT broker port |
| `mqtt_username` | – | MQTT username (optional) |
| `mqtt_password` | – | MQTT password (optional) |
| `mqtt_topic_prefix` | `ambientika` | MQTT topic prefix |
| `poll_interval` | `30` | Polling interval in seconds (10–300) |
| `log_level` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

---

## Support

- 🐛 **Issues & Bug Reports:** [GitHub Issues](https://github.com/ambientika-eu/ambientika-ha-addon/issues)
- 🌐 **Website:** [www.ambientika.eu](https://www.ambientika.eu)
- 📧 **E-Mail:** [info@ambientika.eu](mailto:info@ambientika.eu)

---

## About

This add-on is developed and maintained by **Südwind GmbH**, the manufacturer of Ambientika ventilation systems.

© Südwind GmbH – [www.ambientika.eu](https://www.ambientika.eu)
