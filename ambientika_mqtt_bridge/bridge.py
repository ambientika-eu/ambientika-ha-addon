#!/usr/bin/env python3
"""
Ambientika MQTT Bridge – Home Assistant Add-on  v1.1.2
=======================================================
Connects the Ambientika Cloud API to a local MQTT broker22
23

with full Home Assistant MQTT Auto-Discovery support.

API library : ambientika_py 0.0.5  (wingertge/ambientika-py)
MQTT library: paho-mqtt >= 2.0.0

GitHub: https://github.com/ambientika-eu/ambientika-ha-addon
"""

import asyncio
import json
import logging
import os
import signal
import sys

import paho.mqtt.client as mqtt
from ambientika_py import (
    Ambientika,
    DeviceMode,
    FanSpeed,
    HumidityLevel,
    ,
    OperatingMode,
    authenticate,
)
from returns.result import Failure, Success

# ---------------------------------------------------------------------------
# Configuration  (injected by run.sh from Home Assistant Add-on options)
# ---------------------------------------------------------------------------

AMBIENTIKA_USERNAME: str = os.getenv("AMBIENTIKA_USERNAME", "")
AMBIENTIKA_PASSWORD: str = os.getenv("AMBIENTIKA_PASSWORD", "")
AMBIENTIKA_API_HOST: str = os.getenv(
    "AMBIENTIKA_API_HOST", "https://app.ambientika.eu:4521"
)

MQTT_HOST: str = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD_MQTT", "")
MQTT_TOPIC_PREFIX: str = os.getenv("MQTT_TOPIC_PREFIX", "ambientika")
DISCOVERY_PREFIX: str = os.getenv("DISCOVERY_PREFIX", "homeassistant")

POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "30"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

SW_VERSION = "1.1.2"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ambientika.bridge")

# ---------------------------------------------------------------------------
# Enum value helpers
# ---------------------------------------------------------------------------

# Map OperatingMode enum members to the string values expected by bridge.py
# ambientika_py 0.0.5 uses IntEnum – we publish .name for readability
def mode_to_str(mode: OperatingMode) -> str:
    return mode.name  # e.g. "Smart", "Night", "Off" …

def fan_to_str(fan: FanSpeed) -> str:
    return fan.name  # "Low", "Medium", "High"

def hum_to_str(hum: HumidityLevel) -> str:
    return hum.name  # "Dry", "Normal", "Moist"

def light_to_str(lvl: ) -> str:
    return lvl.name  # "NotAvailable", "Off", "Low", "Medium"

# All valid string values for the HA select entities
ALL_MODES   = [m.name for m in OperatingMode]
ALL_FANS    = [f.name for f in FanSpeed]
ALL_HUMS    = [h.name for h in HumidityLevel]
ALL_LIGHTS  = [l.name for l in ]

# ---------------------------------------------------------------------------
# MQTT topic helpers
# ---------------------------------------------------------------------------

def state_topic(serial: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{serial}/state"

def avail_topic(serial: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{serial}/availability"

def cmd_topic(serial: str, attr: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{serial}/set/{attr}"

BRIDGE_AVAIL_TOPIC = f"{MQTT_TOPIC_PREFIX}/bridge/availability"

# ---------------------------------------------------------------------------
# Home Assistant MQTT Auto-Discovery
# ---------------------------------------------------------------------------

def publish_discovery(mqttc: mqtt.Client, serial: str, device_name: str) -> None:
    """Publish HA MQTT Auto-Discovery config messages for one device."""

    device_block = {
        "identifiers": [f"ambientika_{serial}"],
        "name": device_name,
        "manufacturer": "Suedwind GmbH",
        "model": "Ambientika Smart",
        "sw_version": SW_VERSION,
    }
    avail  = avail_topic(serial)
    state  = state_topic(serial)

    # -- Read-only sensors ---------------------------------------------------
    sensors = [
        # (key_in_state_json,  friendly_name,     unit,   device_class,   icon)
        ("temperature",      "Temperature",      "\u00b0C", "temperature",  None),
        ("humidity",         "Humidity",         "%",    "humidity",     None),
        ("air_quality",      "Air Quality",      None,   None,           "mdi:air-filter"),
        ("filters_status",   "Filter Status",    None,   None,           "mdi:air-filter"),
        ("operating_mode",   "Mode",             None,   None,           "mdi:fan"),
        ("fan_speed",        "Fan Speed",        None,   None,           "mdi:speedometer"),
        ("humidity_level",   "Humidity Level",   None,   None,           "mdi:water-percent"),
        ("light_sensor_level","Light Sensor",    None,   None,           "mdi:brightness-6"),
        ("device_role",      "Device Role",      None,   None,           "mdi:information-outline"),
        ("last_mode",        "Last Mode",        None,   None,           "mdi:history"),
    ]
    for key, name, unit, dc, icon in sensors:
        cfg: dict = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "availability_topic": avail,
            "device": device_block,
        }
        if unit: cfg["unit_of_measurement"] = unit
        if dc:   cfg["device_class"]        = dc
        if icon: cfg["icon"]                = icon
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/sensor/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    # -- Binary sensors ------------------------------------------------------
    binary_sensors = [
        ("humidity_alarm", "Humidity Alarm", "moisture"),
        ("night_alarm",    "Night Alarm",    "problem"),
    ]
    for key, name, dc in binary_sensors:
        cfg = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "payload_on":  "True",
            "payload_off": "False",
            "availability_topic": avail,
            "device": device_block,
            "device_class": dc,
        }
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/binary_sensor/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    # -- Controllable select entities ----------------------------------------
    selects = [
        ("operating_mode",    "Mode",           ALL_MODES,  "mdi:fan"),
        ("fan_speed",         "Fan Speed",      ALL_FANS,   "mdi:speedometer"),
        ("humidity_level",    "Humidity Level", ALL_HUMS,   "mdi:water-percent"),
        ("light_sensor_level","Light Sensor",   ALL_LIGHTS, "mdi:brightness-6"),
    ]
    for key, name, options, icon in selects:
        cfg = {
            "name": name,
            "unique_id": f"ambientika_{serial}_{key}_select",
            "state_topic": state,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "command_topic": cmd_topic(serial, key),
            "options": options,
            "availability_topic": avail,
            "device": device_block,
            "icon": icon,
        }
        mqttc.publish(
            f"{DISCOVERY_PREFIX}/select/{serial}_{key}/config",
            json.dumps(cfg), retain=True, qos=1,
        )

    logger.debug("Discovery published for %s  (%s)", device_name, serial)


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class AmbientikaHABridge:
    """Main bridge – polls the Ambientika API and relays data via MQTT."""

    def __init__(self) -> None:
        self._api: Ambientika | None = None
        self._devices: list = []
        self._running: bool = False
        self._mqtt_connected: bool = False
        self._fail_count: dict[str, int] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

        # -- MQTT client setup -----------------------------------------------
        self._mqttc = mqtt.Client(
            client_id="ambientika-ha-addon",
            protocol=mqtt.MQTTv5,
        )
        if MQTT_USERNAME:
            self._mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self._mqttc.will_set(
            BRIDGE_AVAIL_TOPIC, payload="offline", qos=1, retain=True
        )
        self._mqttc.on_connect    = self._on_connect
        self._mqttc.on_disconnect = self._on_disconnect
        self._mqttc.on_message    = self._on_message

    # ------------------------------------------------------------------
    # MQTT callbacks
    # ------------------------------------------------------------------

    def _on_connect(
        self, client: mqtt.Client, userdata, flags, reason_code, properties=None
    ) -> None:
        if reason_code == 0:
            logger.info("MQTT connected  ->  %s:%s", MQTT_HOST, MQTT_PORT)
            self._mqtt_connected = True
            # Subscribe to all command topics
            for dev in self._devices:
                for attr in ("operating_mode", "fan_speed", "humidity_level", "light_sensor_level"):
                    client.subscribe(cmd_topic(dev.serial_number, attr))
            client.publish(BRIDGE_AVAIL_TOPIC, "online", qos=1, retain=True)
        else:
            logger.error("MQTT connect failed  (reason_code=%s)", reason_code)

    def _on_disconnect(
        self, client: mqtt.Client, userdata, reason_code, properties=None
    ) -> None:
        logger.warning("MQTT disconnected  (reason_code=%s)", reason_code)
        self._mqtt_connected = False

    def _on_message(
        self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        """Handle incoming command messages and dispatch to async handler."""
        payload = msg.payload.decode("utf-8", errors="replace").strip()
        for dev in self._devices:
            for attr in ("operating_mode", "fan_speed", "humidity_level", "light_sensor_level"):
                if msg.topic == cmd_topic(dev.serial_number, attr):
                    if self._loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            self._apply_command(dev, attr, payload),
                            self._loop,
                        )
                    return

    # ------------------------------------------------------------------
    # Command handler
    # ------------------------------------------------------------------

    async def _apply_command(self, dev, attr: str, value: str) -> None:
        """Translate an MQTT command into an ambientika_py change_mode call."""
        serial = dev.serial_number
        logger.info("Command  %s = %s  ->  %s", attr, value, serial)
        try:
            # Fetch current status so we can preserve unchanged fields
            current = await self._get_status_dict(dev)
            if current is None:
                logger.error("Cannot apply command – status fetch failed for %s", serial)
                return

            # Build a full DeviceMode TypedDict with the update applied
            mode: DeviceMode = {
                "operating_mode":    OperatingMode[current["operating_mode"]],
                "fan_speed":         FanSpeed[current["fan_speed"]],
                "humidity_level":    HumidityLevel[current["humidity_level"]],
                "light_sensor_level": [current["light_sensor_level"]],
            }

            if attr == "operating_mode":
                mode["operating_mode"] = OperatingMode[value]
            elif attr == "fan_speed":
                mode["fan_speed"] = FanSpeed[value]
            elif attr == "humidity_level":
                mode["humidity_level"] = HumidityLevel[value]
            elif attr == "light_sensor_level":
                mode["light_sensor_level"] = [value]
            else:
                logger.warning("Unknown command attribute: %s", attr)
                return

            result = await dev.change_mode(mode)
            match result:
                case Success(_):
                    logger.info("Command applied successfully  (%s = %s)", attr, value)
                    # Poll immediately so HA reflects the change
                    await asyncio.sleep(1)
                    await self._poll_device(dev)
                case Failure(err):
                    logger.error(
                        "change_mode failed for %s: %s", serial, err
                    )
        except KeyError as exc:
            logger.error("Invalid value '%s' for %s: %s", value, attr, exc)
        except Exception as exc:
            logger.exception("Unexpected error applying command: %s", exc)

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    async def _get_status_dict(self, dev) -> dict | None:
        """Fetch device status and return a flat dict, or None on error."""
        result = await dev.status()
        match result:
            case Success(status):
                return {
                    "operating_mode":     mode_to_str(status["operating_mode"]),
                    "fan_speed":          fan_to_str(status["fan_speed"]),
                    "humidity_level":     hum_to_str(status["humidity_level"]),
                    "light_sensor_level": light_to_str(status["light_sensor_level"]),
                    "temperature":        status["temperature"],
                    "humidity":           status["humidity"],
                    "air_quality":        str(status["air_quality"]),
                    "filters_status":     str(status["filters_status"]),
                    "humidity_alarm":     str(status["humidity_alarm"]),
                    "night_alarm":        str(status["night_alarm"]),
                    "device_role":        str(status["device_role"]),
                    "last_mode":          mode_to_str(status["last_operating_mode"]),
                }
            case Failure(err):
                logger.warning(
                    "status() failed for %s: %s", dev.serial_number, err
                )
                return None
            case _:
                return None

    async def _poll_device(self, dev) -> None:
        """Poll a single device and publish its state via MQTT."""
        serial = dev.serial_number
        payload = await self._get_status_dict(dev)

        if payload is not None:
            self._fail_count[serial] = 0
            self._mqttc.publish(
                state_topic(serial),
                json.dumps(payload),
                qos=0,
                retain=True,
            )
            self._mqttc.publish(avail_topic(serial), "online",  qos=1, retain=True)
            logger.debug("Polled %s  ->  mode=%s  temp=%s",
                         serial, payload["operating_mode"], payload["temperature"])
        else:
            count = self._fail_count.get(serial, 0) + 1
            self._fail_count[serial] = count
            logger.warning("Poll failed for %s  (consecutive failures: %d)", serial, count)
            if count >= 3:
                self._mqttc.publish(avail_topic(serial), "offline", qos=1, retain=True)
                logger.info("Triggering re-authentication after %d failures", count)
                await self._re_auth()

    async def _re_auth(self) -> None:
        """Re-authenticate and rebuild the device list."""
        logger.info("Re-authenticating with Ambientika API...")
        try:
            result = await authenticate(
                AMBIENTIKA_USERNAME, AMBIENTIKA_PASSWORD, AMBIENTIKA_API_HOST
            )
            match result:
                case Success(api):
                    self._api = api
                    self._devices = await self._collect_devices()
                    logger.info("Re-auth OK – %d device(s) found", len(self._devices))
                    self._fail_count.clear()
                case Failure(err):
                    logger.error("Re-auth failed: %s", err)
        except Exception as exc:
            logger.exception("Re-auth exception: %s", exc)

    async def _collect_devices(self) -> list:
        """Flatten houses -> rooms -> devices into a single list."""
        if self._api is None:
            return []
        result = await self._api.houses()
        match result:
            case Success(houses):
                devices = [
                    dev
                    for house in houses
                    for room  in house.rooms
                    for dev   in room.devices
                ]
                return devices
            case Failure(err):
                logger.error("Failed to fetch device list: %s", err)
                return []
            case _:
                return []

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Connect to the API and MQTT broker, then start polling."""
        self._loop = asyncio.get_event_loop()

        logger.info("=== Ambientika MQTT Bridge  v%s  starting ===", SW_VERSION)
        logger.info("API host      : %s", AMBIENTIKA_API_HOST)
        logger.info("MQTT broker   : %s:%s", MQTT_HOST, MQTT_PORT)
        logger.info("Topic prefix  : %s", MQTT_TOPIC_PREFIX)
        logger.info("Poll interval : %ss", POLL_INTERVAL)

        # -- Authenticate ----------------------------------------------------
        logger.info("Authenticating with Ambientika API...")
        try:
            auth_result = await authenticate(
                AMBIENTIKA_USERNAME, AMBIENTIKA_PASSWORD, AMBIENTIKA_API_HOST
            )
        except Exception as exc:
            logger.error("Authentication exception: %s", exc)
            sys.exit(1)

        match auth_result:
            case Success(api):
                self._api = api
                logger.info("Authentication successful.")
            case Failure(err):
                logger.error("Authentication failed: %s", err)
                logger.error(
                    "Please verify your Ambientika username and password "
                    "in the Add-on configuration."
                )
                sys.exit(1)

        # -- Collect devices -------------------------------------------------
        self._devices = await self._collect_devices()
        if not self._devices:
            logger.warning(
                "No devices found. The bridge will keep running and retry "
                "on the next poll cycle."
            )
        else:
            logger.info("Found %d device(s).", len(self._devices))
            for dev in self._devices:
                logger.info("  Device: %s  (serial: %s)",
                             getattr(dev, "name", "?"), dev.serial_number)

        # -- Connect MQTT ----------------------------------------------------
        logger.info("Connecting to MQTT broker...")
        self._mqttc.connect_async(MQTT_HOST, MQTT_PORT)
        self._mqttc.loop_start()

        # Wait up to 30 s for MQTT connection
        for _ in range(30):
            if self._mqtt_connected:
                break
            await asyncio.sleep(1)
        if not self._mqtt_connected:
            logger.error("MQTT connection timed out after 30 s. Check broker settings.")
            sys.exit(1)

        # -- Publish HA Auto-Discovery ---------------------------------------
        for dev in self._devices:
            name = getattr(dev, "name", None) or dev.serial_number
            publish_discovery(self._mqttc, dev.serial_number, name)
        logger.info("HA Auto-Discovery published for all devices.")

        # -- Polling loop ----------------------------------------------------
        self._running = True
        logger.info("Starting poll loop (every %ds)...", POLL_INTERVAL)
        while self._running:
            for dev in self._devices:
                if not self._running:
                    break
                await self._poll_device(dev)
            if self._running:
                await asyncio.sleep(POLL_INTERVAL)

    def stop(self) -> None:
        """Gracefully shut down the bridge."""
        logger.info("Shutting down Ambientika MQTT Bridge...")
        self._running = False
        try:
            self._mqttc.publish(BRIDGE_AVAIL_TOPIC, "offline", qos=1, retain=True)
            # Mark all devices offline
            for dev in self._devices:
                self._mqttc.publish(avail_topic(dev.serial_number), "offline",
                                    qos=1, retain=True)
            self._mqttc.disconnect()
            self._mqttc.loop_stop()
        except Exception as exc:
            logger.debug("Error during MQTT shutdown: %s", exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    bridge = AmbientikaHABridge()
    loop   = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register OS signals for clean shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, bridge.stop)
        except (NotImplementedError, RuntimeError):
            # Windows / environments that don't support add_signal_handler
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
