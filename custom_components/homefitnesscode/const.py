"""Constants, equipment data characteristics and safety defaults."""
DOMAIN = "homefitnesscode"
SERVICE_FTMS = "00001826-0000-1000-8000-00805f9b34fb"
BASE_UUID = "-0000-1000-8000-00805f9b34fb"

def uuid(short: str) -> str:
    return f"0000{short.lower()}{BASE_UUID}"

DATA_CHARS = {"treadmill": uuid("2acd"), "rower": uuid("2ad1"), "bike": uuid("2ad2")}
FEATURE_CHAR = uuid("2acc")
CONTROL_CHAR = uuid("2ad9")
STATUS_CHAR = uuid("2ada")
RANGE_CHARS = {"speed": uuid("2ad4"), "incline": uuid("2ad5"),
               "resistance": uuid("2ad6"), "power": uuid("2ad8")}
TARGET_BITS = {"speed": 0, "incline": 1, "resistance": 2, "power": 3}
COMMANDS = {"speed": 0x02, "incline": 0x03, "resistance": 0x04, "power": 0x05}
CAP_DEFAULTS = {"speed": 6.0, "incline": 5.0, "resistance": 10.0, "power": 200.0}
PLATFORMS = ["sensor", "binary_sensor", "number", "button"]
MACHINE_OPTIONS = ("auto", "treadmill", "bike", "rower")
PROFILE_OPTIONS = ("auto", "ftms", "homefitnesscode", "tacx_fec")

TACX_FEC_SERVICE = "6e40fec1-b5a3-f393-e0a9-e50e24dcca9e"
TACX_RX = "6e40fec3-b5a3-f393-e0a9-e50e24dcca9e"
TACX_TX = "6e40fec2-b5a3-f393-e0a9-e50e24dcca9e"
