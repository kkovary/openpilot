"""
Driver modes: one switch between Kyle's setup and a factory-safety setup for other drivers.

- kyle: openpilot gas/brake (alpha longitudinal) with curve slowing, speed limit assist, etc.
- maya: alpha longitudinal off, so the car's own ACC and factory AEB/FCW are active.

Turning alpha longitudinal off makes sunnypilot clear or downgrade the settings that depend on it
(curve slowing toggles, speed limit assist -> warning, experimental mode). Switching to maya saves
Kyle's values first, and switching back restores them exactly.

Only switch while offroad: CarParams (and with it longitudinal control) is decided at car start.
"""
from openpilot.common.params import Params

KYLE = 0
MAYA = 1
MODE_NAMES = ["kyle", "maya"]

# Everything that alpha longitudinal off changes, directly or through sunnypilot's cleanup.
SNAPSHOT_KEYS = (
  "AlphaLongitudinalEnabled",
  "ExperimentalMode",
  "SmartCruiseControlVision",
  "SmartCruiseControlMap",
  "CustomAccIncrementsEnabled",
  "SpeedLimitMode",
  "SpeedLimitOffsetType",
  "SpeedLimitValueOffset",
)

MAYA_SETTINGS = {
  "AlphaLongitudinalEnabled": False,
  "ExperimentalMode": False,
}

# Used to restore kyle mode if no snapshot was ever saved (e.g. the device started in maya mode).
KYLE_DEFAULTS = {
  "AlphaLongitudinalEnabled": True,
  "SmartCruiseControlVision": True,
  "SmartCruiseControlMap": True,
  "SpeedLimitMode": 3,  # assist
  "SpeedLimitOffsetType": 1,  # fixed
  "SpeedLimitValueOffset": 5,
}


def get_mode(params: Params) -> int:
  mode = params.get("DriverMode", return_default=True)
  return mode if mode in (KYLE, MAYA) else KYLE


def _apply(params: Params, values: dict) -> None:
  # alpha longitudinal goes first: the UI clears curve slowing whenever it reads alpha long as off
  for key in sorted(values, key=lambda k: k != "AlphaLongitudinalEnabled"):
    value = values[key]
    if value is None:
      params.remove(key)
    else:
      params.put(key, value, block=True)


def set_mode(params: Params, mode: int) -> bool:
  """Switch driver mode. Returns True if anything changed."""
  if mode not in (KYLE, MAYA) or mode == get_mode(params):
    return False

  if mode == MAYA:
    params.put("DriverModeKyleSnapshot", {key: params.get(key) for key in SNAPSHOT_KEYS}, block=True)
    _apply(params, MAYA_SETTINGS)
  else:
    _apply(params, params.get("DriverModeKyleSnapshot") or KYLE_DEFAULTS)

  params.put("DriverMode", mode, block=True)
  return True
