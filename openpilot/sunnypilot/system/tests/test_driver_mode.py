from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.sunnypilot.system.driver_mode import KYLE, MAYA, KYLE_DEFAULTS, SNAPSHOT_KEYS, active_mode, apply_pending_restore, \
                                                   get_mode, set_mode


class TestDriverMode(OpenpilotTestCase):
  def _kyle_setup(self, params):
    params.put_bool("AlphaLongitudinalEnabled", True, block=True)
    params.put_bool("SmartCruiseControlVision", True, block=True)
    params.put_bool("SmartCruiseControlMap", True, block=True)
    params.put("SpeedLimitMode", 3, block=True)
    params.put("SpeedLimitOffsetType", 1, block=True)
    params.put("SpeedLimitValueOffset", 5, block=True)

  def _sunnypilot_cleanup(self, params):
    # what sunnypilot does on its own while alpha long is off
    params.remove("SmartCruiseControlVision")
    params.remove("SmartCruiseControlMap")
    params.put("SpeedLimitMode", 2, block=True)

  def test_default_is_kyle(self):
    assert get_mode(Params()) == KYLE

  def test_maya_turns_alpha_long_off(self):
    params = Params()
    self._kyle_setup(params)
    assert set_mode(params, MAYA, offroad=True)
    assert get_mode(params) == MAYA
    assert not params.get_bool("AlphaLongitudinalEnabled")
    assert not params.get_bool("ExperimentalMode")

  def test_round_trip_offroad_restores_kyle_settings(self):
    params = Params()
    self._kyle_setup(params)
    before = {key: params.get(key) for key in SNAPSHOT_KEYS}
    set_mode(params, MAYA, offroad=True)
    self._sunnypilot_cleanup(params)
    set_mode(params, KYLE, offroad=True)
    assert get_mode(params) == KYLE
    assert {key: params.get(key) for key in SNAPSHOT_KEYS} == before
    assert not params.get_bool("DriverModeRestorePending")

  def test_kyle_onroad_defers_restore_until_offroad(self):
    params = Params()
    self._kyle_setup(params)
    before = {key: params.get(key) for key in SNAPSHOT_KEYS}
    set_mode(params, MAYA, offroad=True)
    self._sunnypilot_cleanup(params)

    set_mode(params, KYLE, offroad=False)
    # next car start must already get openpilot longitudinal
    assert params.get_bool("AlphaLongitudinalEnabled")
    assert params.get_bool("DriverModeRestorePending")
    assert params.get("SpeedLimitMode") == 2

    assert apply_pending_restore(params)
    assert {key: params.get(key) for key in SNAPSHOT_KEYS} == before
    assert not apply_pending_restore(params)

  def test_maya_cancels_pending_restore(self):
    params = Params()
    self._kyle_setup(params)
    set_mode(params, MAYA, offroad=True)
    set_mode(params, KYLE, offroad=False)
    set_mode(params, MAYA, offroad=False)
    assert not params.get_bool("DriverModeRestorePending")
    assert not params.get_bool("AlphaLongitudinalEnabled")

  def test_unset_keys_stay_unset(self):
    params = Params()
    params.put_bool("AlphaLongitudinalEnabled", True, block=True)
    set_mode(params, MAYA, offroad=True)
    params.put_bool("CustomAccIncrementsEnabled", True, block=True)
    set_mode(params, KYLE, offroad=True)
    assert params.get("CustomAccIncrementsEnabled") is None

  def test_kyle_without_snapshot_uses_defaults(self):
    params = Params()
    params.put("DriverMode", MAYA, block=True)
    assert set_mode(params, KYLE, offroad=True)
    for key, value in KYLE_DEFAULTS.items():
      assert params.get(key) == value

  def test_same_mode_is_noop(self):
    params = Params()
    self._kyle_setup(params)
    assert not set_mode(params, KYLE, offroad=True)
    assert params.get("DriverModeKyleSnapshot") is None

  def test_active_mode(self):
    assert active_mode(True) == KYLE
    assert active_mode(False) == MAYA
