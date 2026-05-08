# Ambientika MQTT Bridge – Home Assistant Add-on

This Home Assistant OS (HAOS) Add-on connects your Ambientika ventilation units to Home Assistant via MQTT with Auto-Discovery support.

## Installation

### Method 1: Add Repository to Home Assistant (Recommended)

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**
2. Click the **three-dot menu** (top right) > **Repositories**
3. Add this URL:
```
https://github.com/ambientika-eu/ambientika-ha-addon
```
4. Click **Add**, then close the dialog
5. Search for **"Ambientika MQTT Bridge"** in the store
6. Click **Install**

## Configuration

After installation, configure the add-on via the **Configuration** tab:

| Option | Description | Default |
|--------|-------------|---------|
| `ambientika_username` | Your Ambientika account email | *(required)* |
| `ambientika_password` | Your Ambientika account password | *(required)* |
| `mqtt_host` | MQTT broker hostname | `core-mosquitto` |
| `mqtt_port` | MQTT broker port | `1883` |
| `mqtt_username` | MQTT username (optional) | |
| `mqtt_password` | MQTT password (optional) | |
| `mqtt_topic_prefix` | MQTT topic prefix | `ambientika` |
| `poll_interval` | Polling interval in seconds | `30` |
| `log_level` | Log verbosity | `INFO` |

## Home Assistant Auto-Discovery

The bridge publishes MQTT Auto-Discovery messages so your Ambientika devices appear automatically under:

**Settings > Devices & Services > MQTT > Devices**

## Support

- GitHub: https://github.com/ambientika-eu/ambientika-mqtt-bridge
- Website: https://www.ambientika.eu
