#!/usr/bin/env python3
"""
Ambientika MQTT Bridge – Home Assistant Add-on
Connects Ambientika Cloud API to local MQTT broker with HA Auto-Discovery.

GitHub: https://github.com/ambientika-eu/ambientika-mqtt-bridge
"""

import json
import logging
import os
import signal
import sys
import time
import threading
import requests
import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Configuration from environment (set by run.sh from HA Add-on options)
# ---------------------------------------------------------------------------

AMBIENTIKA_USERNAME  = os.getenv("AMBIENTIKA_USERNAME", "")
AMBIENTIKA_PASSWORD  = os.getenv("AMBIENTIKA_PASSWORD", "")
MQTT_HOST            = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT            = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME        = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD_MQTT   = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC_PREFIX    = os.getenv("MQTT_TOPIC_PREFIX", "ambientika")
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
# Ambientika Cloud API
# ---------------------------------------------------------------------------

API_BASE    = "https://ambientika.eu/api/v1"
AUTH_TOKEN  = None

def api_login():
    global AUTH_TOKEN
    try:
        resp = requests.post(f"{API_BASE}/auth/login", json={
            "username": AMBIENTIKA_USERNAME,
            "password": AMBIENTIKA_PASSWORD,
        }, timeout=10)
        resp.raise_for_status()
        AUTH_TOKEN = resp.json().get("token")
        logger.info("Ambientika API: authenticated")
        return True
    except Exception as exc:
        logger.error(f"API login failed: {exc}")
        return False

def api_get_devices():
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    try:
        resp = requests.get(f"{API_BASE}/devices", headers=headers, timeout=10)
        if resp.status_code == 401:
            logger.warning("Token expired, re-authenticating...")
            api_login()
            resp = requests.get(f"{API_BASE}/devices",
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error(f"get_devices failed: {exc}")
        return []

def api_set_mode(device_id, mode):
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    try:
        resp = requests.post(f"{API_BASE}/devices/{device_id}/mode",
                             json={"mode": mode}, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info(f"Set mode {mode} on {device_id}")
    except Exception as exc:
        logger.error(f"set_mode failed: {exc}")

# ---------------------------------------------------------------------------
# MQTT Auto-Discovery helpers
# ---------------------------------------------------------------------------

mqtt_client: mqtt.Client = None

def publish_discovery(device):
    dev_id  = device["id"].replace("-", "_")
    dev_name = device.get("name", f"Ambientika {dev_id}")

    device_block = {
        "identifiers": [f"ambientika_{dev_id}"],
        "name": dev_name,
        "manufacturer": "Südwind GmbH",
        "model": "Ambientika",
        "sw_version": "1.0.0",
    }

    sensors = [
        ("humidity",    "Humidity",                    "%",  "humidity"),
        ("temperature", "Supply Air Temperature",       "°C", "temperature"),
        ("ext_temp",    "Outdoor Temperature",          "°C", "temperature"),
        ("aqi",         "Air Quality",                 None, "aqi"),
        ("fan_speed",   "Fan Speed",                   None, None),
        ("power",       "Power Consumption",            "W",  "power_factor"),
    ]

    for key, friendly, unit, dev_class in sensors:
        config = {
            "name": friendly,
            "state_topic": f"{MQTT_TOPIC_PREFIX}/{dev_id}/status",
            "value_template": f"{{{{ value_json.{key} }}}}",
            "unique_id": f"ambientika_{dev_id}_{key}",
            "device": device_block,
        }
        if unit:
            config["unit_of_measurement"] = unit
        if dev_class:
            config["device_class"] = dev_class

        mqtt_client.publish(
            f"homeassistant/sensor/ambientika_{dev_id}/{key}/config",
            json.dumps(config), retain=True
        )

    # Binary sensors
    for key, friendly, dev_class in [
        ("filter_alarm", "Filter Alarm", "problem"),
        ("defrost",      "Defrost Active", "cold"),
    ]:
        config = {
            "name": friendly,
            "state_topic": f"{MQTT_TOPIC_PREFIX}/{dev_id}/status",
            "value_template": f"{{{{ value_json.{key} | lower }}}}",
            "payload_on": "true",
            "payload_off": "false",
            "device_class": dev_class,
            "unique_id": f"ambientika_{dev_id}_{key}",
            "device": device_block,
        }
        mqtt_client.publish(
            f"homeassistant/binary_sensor/ambientika_{dev_id}/{key}/config",
            json.dumps(config), retain=True
        )

    # Select (operating mode)
    config = {
        "name": "Operating Mode",
        "command_topic": f"{MQTT_TOPIC_PREFIX}/{dev_id}/set/mode",
        "state_topic":   f"{MQTT_TOPIC_PREFIX}/{dev_id}/status",
        "value_template": "{{ value_json.mode }}",
        "options": ["Auto","ManualLow","ManualMedium","ManualHigh","Night","Standby","Away","Boost"],
        "unique_id": f"ambientika_{dev_id}_mode",
        "device": device_block,
    }
    mqtt_client.publish(
        f"homeassistant/select/ambientika_{dev_id}/mode/config",
        json.dumps(config), retain=True
    )
    logger.debug(f"Discovery published for {dev_id}")

# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"MQTT connected to {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(f"{MQTT_TOPIC_PREFIX}/+/set/#")
    else:
        logger.error(f"MQTT connect failed rc={rc}")

def on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) < 4:
        return
    dev_id = parts[1]
    cmd    = parts[3]
    value  = msg.payload.decode()
    logger.info(f"Command: {dev_id}/{cmd} = {value}")
    if cmd == "mode":
        api_set_mode(dev_id.replace("_", "-"), value)

# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def poll_and_publish():
    devices = api_get_devices()
    for dev in devices:
        dev_id = dev["id"].replace("-", "_")
        publish_discovery(dev)
        payload = {
            "mode":         dev.get("operatingMode", "Auto"),
            "humidity":     dev.get("humidity", 0),
            "temperature":  dev.get("supplyAirTemperature", 0),
            "ext_temp":     dev.get("outdoorTemperature", 0),
            "aqi":          dev.get("airQualityIndex", 0),
            "fan_speed":    dev.get("fanSpeed", 0),
            "power":        dev.get("powerConsumption", 0),
            "filter_alarm": dev.get("filterAlarm", False),
            "defrost":      dev.get("defrostActive", False),
        }
        mqtt_client.publish(
            f"{MQTT_TOPIC_PREFIX}/{dev_id}/status",
            json.dumps(payload), retain=True
        )
        logger.debug(f"Published status for {dev_id}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global mqtt_client

    logger.info("=== Ambientika MQTT Bridge starting ===")

    if not api_login():
        logger.error("Cannot authenticate with Ambientika API. Check username/password.")
        sys.exit(1)

    mqtt_client = mqtt.Client(client_id="ambientika-ha-addon")
    if MQTT_USERNAME:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD_MQTT)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logger.info(f"Connecting to MQTT broker {MQTT_HOST}:{MQTT_PORT} ...")
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()

    # Graceful shutdown
    running = threading.Event()
    running.set()

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        running.clear()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT,  shutdown)

    while running.is_set():
        try:
            poll_and_publish()
        except Exception as exc:
            logger.error(f"Poll error: {exc}")
        running.wait(POLL_INTERVAL)

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    logger.info("Ambientika MQTT Bridge stopped.")

if __name__ == "__main__":
    main()
