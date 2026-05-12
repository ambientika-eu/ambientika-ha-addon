#!/usr/bin/env python3
"""
Ambientika MQTT Bridge – Home Assistant Add-on
Connects Ambientika Cloud API to local MQTT broker with HA Auto-Discovery.

GitHub: https://github.com/ambientika-eu/ambientika-ha-addon
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading

import paho.mqtt.client as mqtt

try:
    from ambientika_py import AmbientikaAPI
    from ambientika_py.models import OperatingMode, FanSpeed, HumidityLevel
except ImportError:
    print("ERROR: ambientika_py not installed. Run: pip install ambientika_py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration from environment (set by run.sh from HA Add-on options)
# ---------------------------------------------------------------------------

AMBIENTIKA_USERNAME  = os.getenv("AMBIENTIKA_USERNAME", "")
AMBIENTIKA_PASSWORD  = os.getenv("AMBIENTIKA_PASSWORD", "")
AMBIENTIKA_API_HOST  = os.getenv("AMBIENTIKA_API_HOST", "https://app.ambientika.eu:4521")

MQTT_HOST            = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT            = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME        = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD_MQTT   = os.getenv("MQTT_PASSWORD_MQTT", "")
MQTT_TOPIC_PREFIX    = os.getenv("MQTT_TOPIC_PREFIX", "ambientika")
DISCOVERY_PREFIX     = os.getenv("DISCOVERY_PREFIX", "homeassistant")

POLL_INTERVAL        = int(os.getenv("POLL_INTERVAL", "30"))
LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger("ambientika.bridge")

# ---------------------------------------------------------------------------
# Topic helpers
# ---------------------------------------------------------------------------

def state_topic(serial):
    return f"{MQTT_TOPIC_PREFIX}/{serial}/state"

def avail_topic(serial):
    return f"{MQTT_TOPIC_PREFIX}/{serial}/availability"

def cmd_topic(serial, attr):
    return f"{MQTT_TOPIC_PREFIX}/{serial}/set/{attr}"

# ---------------------------------------------------------------------------
# HA Auto-Discovery
# ---------------------------------------------------------------------------

def publish_discovery(mqttc, serial, device_name):
    device_block = {
        "identifiers": [serial],
        "name": device_name,
        "manufacturer": "Südwind GmbH",
        "model": "Ambientika Smart",
        "sw_version": "1.1.0",
    }
    avail = avail_topic(serial)
    state = state_topic(serial)

    # Sensors
    for key, name, unit, dc, icon in [
        ("temperature",    "Temperature",          "°C", "temperature",    None),
        ("humidity",       "Humidity",             "%",  "humidity",       None),
        ("air_quality",    "Air Quality",          None, None,             "mdi:air-filter"),
        ("filters_status", "Filter Status",        None, None,             "mdi:air-filter"),
        ("operating_mode", "Mode",                 None, None,             "mdi:fan"),
        ("fan_speed",      "Fan Speed",            None, None,             "mdi:speedometer"),
        ("humidity_level", "Humidity Level",       None, None,             "mdi:water-percent"),
        ("device_role",    "Device Role",          None, None,             "mdi:information"),
    ]:
        cfg = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "availability_topic": avail,
            "device": device_block,
        }
        if unit:  cfg["unit_of_measurement"] = unit
        if dc:    cfg["device_class"] = dc
        if icon:  cfg["icon"] = icon
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/sensor/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    # Binary sensors
    for key, name, dc in [
        ("humidity_alarm", "Humidity Alarm", "moisture"),
        ("night_alarm",    "Night Alarm",    "problem"),
    ]:
        cfg = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "payload_on": "True",
            "payload_off": "False",
            "availability_topic": avail,
            "device": device_block,
            "device_class": dc,
        }
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/binary_sensor/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    # Selects (controllable)
    for key, name, opts, icon in [
        ("operating_mode", "Mode",          [m.value for m in OperatingMode], "mdi:fan"),
        ("fan_speed",      "Fan Speed",     [s.value for s in FanSpeed],      "mdi:speedometer"),
        ("humidity_level", "Humidity Level",[h.value for h in HumidityLevel], "mdi:water-percent"),
    ]:
        cfg = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}_select",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "command_topic": cmd_topic(serial, key),
            "options": opts,
            "availability_topic": avail,
            "device": device_block,
            "icon": icon,
        }
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/select/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    logger.debug("Discovery published for %s (%s)", device_name, serial)

# ---------------------------------------------------------------------------
# Bridge class
# ---------------------------------------------------------------------------

class AmbientikaHABridge:
    def __init__(self):
        self.api = None
        self.devices = []
        self._running = False
        self._mqtt_connected = False
        self._fail_count = {}
        self._loop = None

        self.mqttc = mqtt.Client(client_id="ambientika-ha-addon", protocol=mqtt.MQTTv5)
        if MQTT_USERNAME:
            self.mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD_MQTT)
        self.mqttc.on_connect    = self._on_connect
        self.mqttc.on_disconnect = self._on_disconnect
        self.mqttc.on_message    = self._on_message
        self.mqttc.will_set(
            f"{MQTT_TOPIC_PREFIX}/bridge/availability", "offline", qos=1, retain=True
        )

    def _on_connect(self, client, userdata, flags, rc, props=None):
        if rc == 0:
            logger.info("MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
            self._mqtt_connected = True
            for dev in self.devices:
                for attr in ("operating_mode", "fan_speed", "humidity_level"):
                    client.subscribe(cmd_topic(dev.serial_number, attr))
            client.publish(
                f"{MQTT_TOPIC_PREFIX}/bridge/availability", "online", qos=1, retain=True
            )
        else:
            logger.error("MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc, props=None):
        logger.warning("MQTT disconnected rc=%s", rc)
        self._mqtt_connected = False

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace").strip()
        for dev in self.devices:
            for attr in ("operating_mode", "fan_speed", "humidity_level"):
                if msg.topic == cmd_topic(dev.serial_number, attr):
                    asyncio.run_coroutine_threadsafe(
                        self._apply_command(dev, attr, payload), self._loop
                    )

    async def _apply_command(self, dev, attr, value):
        try:
            if attr == "operating_mode":
                await dev.change_mode(operating_mode=OperatingMode(value))
            elif attr == "fan_speed":
                await dev.change_mode(fan_speed=FanSpeed(value))
            elif attr == "humidity_level":
                await dev.change_mode(humidity_level=HumidityLevel(value))
            logger.info("Applied %s=%s to %s", attr, value, dev.serial_number)
            await asyncio.sleep(1)
            await self._poll_device(dev)
        except Exception as exc:
            logger.error("Command error: %s", exc)

    async def _poll_device(self, dev):
        serial = dev.serial_number
        try:
            status = await dev.get_status()
            payload = {}
            for k in ("temperature", "humidity", "air_quality", "filters_status",
                      "operating_mode", "fan_speed", "humidity_level", "device_role",
                      "humidity_alarm", "night_alarm"):
                v = getattr(status, k, None)
                payload[k] = v.value if hasattr(v, "value") else (str(v) if v is not None else "")
            self._fail_count[serial] = 0
            self.mqttc.publish(state_topic(serial), json.dumps(payload), qos=0, retain=True)
            self.mqttc.publish(avail_topic(serial), "online", qos=1, retain=True)
        except Exception as exc:
            self._fail_count[serial] = self._fail_count.get(serial, 0) + 1
            logger.warning("Poll failed for %s (%d): %s", serial, self._fail_count[serial], exc)
            if self._fail_count[serial] >= 3:
                await self._re_auth()

    async def _re_auth(self):
        try:
            await self.api.login(AMBIENTIKA_USERNAME, AMBIENTIKA_PASSWORD)
            self.devices = await self.api.get_devices()
            logger.info("Re-auth OK, %d devices", len(self.devices))
        except Exception as exc:
            logger.error("Re-auth failed: %s", exc)

    async def run(self):
        self._loop = asyncio.get_event_loop()
        logger.info("=== Ambientika MQTT Bridge starting ===")
        logger.info("API host: %s", AMBIENTIKA_API_HOST)
        logger.info("MQTT broker: %s:%s", MQTT_HOST, MQTT_PORT)
        logger.info("Topic prefix: %s", MQTT_TOPIC_PREFIX)
        logger.info("Poll interval: %ss", POLL_INTERVAL)

        self.api = AmbientikaAPI(host=AMBIENTIKA_API_HOST)
        try:
            await self.api.login(AMBIENTIKA_USERNAME, AMBIENTIKA_PASSWORD)
        except Exception as exc:
            logger.error("API login failed: %s", exc)
            logger.error("Please check your Ambientika username and password.")
            sys.exit(1)

        self.devices = await self.api.get_devices()
        logger.info("Found %d device(s)", len(self.devices))

        self.mqttc.connect_async(MQTT_HOST, MQTT_PORT)
        self.mqttc.loop_start()

        for _ in range(30):
            if self._mqtt_connected:
                break
            await asyncio.sleep(1)
        if not self._mqtt_connected:
            logger.error("MQTT connect timeout after 30s")
            sys.exit(1)

        # Publish HA Auto-Discovery for all devices
        for dev in self.devices:
            name = getattr(dev, "name", dev.serial_number) or dev.serial_number
            publish_discovery(self.mqttc, dev.serial_number, name)

        # Main polling loop
        self._running = True
        while self._running:
            for dev in self.devices:
                await self._poll_device(dev)
            await asyncio.sleep(POLL_INTERVAL)

    def stop(self):
        logger.info("Shutting down...")
        self._running = False
        try:
            self.mqttc.publish(
                f"{MQTT_TOPIC_PREFIX}/bridge/availability", "offline", qos=1, retain=True
            )
            self.mqttc.disconnect()
            self.mqttc.loop_stop()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    bridge = AmbientikaHABridge()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, bridge.stop)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        loop.run_until_complete(bridge.run())
    except KeyboardInterrupt:
        bridge.stop()
    finally:
        loop.close()
        logger.info("Ambientika MQTT Bridge stopped.")

if __name__ == "__main__":
    main()
