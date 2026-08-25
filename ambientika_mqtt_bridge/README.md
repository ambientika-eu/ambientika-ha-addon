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

## Prerequisites

- An **MQTT broker**. If you have none, install the official **Mosquitto broker**
  add-on first and start it.
- An **Ambientika account** — the same e-mail address and password you use in the
  Ambientika app. There is no separate account for the bridge.

## Configuration

After installation, configure the add-on via the **Configuration** tab:

| Option | Description | Default |
|--------|-------------|---------|
| `ambientika_username` | E-mail address of your Ambientika app account | *(required)* |
| `ambientika_password` | Password of your Ambientika app account | *(required)* |
| `mqtt_host` | MQTT broker hostname | `core-mosquitto` |
| `mqtt_port` | MQTT broker port | `1883` |
| `mqtt_username` | Broker user — **required** for the Mosquitto add-on, which refuses anonymous connections | *(empty)* |
| `mqtt_password` | Broker password | *(empty)* |
| `mqtt_topic_prefix` | MQTT topic prefix | `ambientika` |
| `poll_interval` | Polling interval in seconds (10-300) | `30` |
| `availability_failure_threshold` | Consecutive failed reads before a unit is shown unavailable | `3` |
| `log_level` | Log verbosity | `INFO` |
| `command_coalesce_ms` | Commands for the same unit within this window are applied in one call (`0` = immediately) | `800` |
| `slave_filter_soft_reset` | Maintenance acknowledgement for Slave filter counters | `false` |
| `filter_ack_ttl_days` | How long an acknowledgement stays valid | `90` |

Leaving `mqtt_username` and `mqtt_password` empty is the most common setup
mistake: the log then shows `MQTT connection failed (rc=5)`.

The full user documentation is in [DOCS.md](DOCS.md); Home Assistant shows it in
the add-on's **Documentation** tab.

## Home Assistant Auto-Discovery

The bridge publishes MQTT Auto-Discovery messages so your Ambientika devices appear automatically under:

**Settings > Devices & Services > MQTT > Devices**

### Distinguishing the internal state in SMART mode

The `Mode` control shows the *set* macro-mode. In the automatic modes
(`Smart` / `Auto`) that value stays `Smart`, even though the unit internally
switches between concrete functions — heat recovery vs. free cooling
(`MasterSlaveFlow`), night mode, etc.

To make the actually-running function distinguishable in SMART mode, the bridge
also publishes a read-only diagnostic sensor **"Active Operating Mode (SMART)"**
(`last_operating_mode`), which reflects the concrete mode the unit reports. The
`Fan Speed` sensor already reports the real running speed, so together they let
you see exactly what SMART is doing at any moment.

## Support

- GitHub: https://github.com/ambientika-eu/ambientika-mqtt-bridge
- Website: https://www.ambientika.eu
