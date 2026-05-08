# Ambientika Add-ons for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Official Home Assistant Add-on repository for Ambientika ventilation units by [Südwind GmbH](https://www.ambientika.eu).

## Available Add-ons

### [Ambientika MQTT Bridge](./ambientika_mqtt_bridge)

Connects your Ambientika ventilation units to Home Assistant via MQTT with Auto-Discovery support.

- Controls operating mode, fan speed, humidity setpoint
- Sensors: humidity, temperatures, air quality, power consumption
- Binary sensors: filter alarm, defrost active
- MQTT Auto-Discovery (devices appear automatically in HA)

## Installation

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**
2. Click the **three-dot menu** (top right) > **Repositories**
3. Add this URL:
```
https://github.com/ambientika-eu/ambientika-ha-addon
```
4. Search for **"Ambientika MQTT Bridge"** and install

## Support

- GitHub: https://github.com/ambientika-eu/ambientika-mqtt-bridge
- Website: https://www.ambientika.eu
- Email: info@ambientika.eu
