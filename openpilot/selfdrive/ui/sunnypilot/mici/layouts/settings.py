"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.mici.layouts.settings import settings as OP
from openpilot.selfdrive.ui.mici.layouts.settings.settings import SettingsBigButton
from openpilot.selfdrive.ui.mici.layouts.settings.device.device_layout import DeviceLayoutMici
from openpilot.selfdrive.ui.mici.widgets.button import BigCircleButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog, BigDialog
from openpilot.selfdrive.ui.sunnypilot.mici.layouts.sunnylink import SunnylinkLayoutMici
from openpilot.selfdrive.ui.sunnypilot.mici.layouts.models import ModelsLayoutMici
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.sunnypilot.system.driver_mode import KYLE, MAYA, MODE_NAMES, active_mode, apply_pending_restore, get_mode, set_mode
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr

ICON_SIZE = 70
BIG_ICON_SIZE = 110


class DriverModeButton(SettingsBigButton):
  """Switch between kyle mode (openpilot gas/brake) and maya mode (stock ACC + factory AEB).
  A switch applies at the next car start; until then the card shows "restart car"."""
  def __init__(self):
    self._wheel_icon = gui_app.texture("icons_mici/wheel.png", ICON_SIZE, ICON_SIZE)
    super().__init__(tr("driver"), "", self._wheel_icon)
    self.set_click_callback(self._on_click)
    # fires on every onroad/offroad change and once at startup
    ui_state.add_offroad_transition_callback(self._on_offroad_transition)
    self.refresh()

  def refresh(self):
    self._selected = get_mode(ui_state.params)
    self._update_label()

  def _restart_needed(self) -> bool:
    return ui_state.started and ui_state.CP is not None and active_mode(ui_state.CP.openpilotLongitudinalControl) != self._selected

  def _update_label(self):
    value = f"{MODE_NAMES[self._selected]} mode"
    if self._restart_needed():
      value += " · " + tr("restart car")
    if value != self.value:
      self.set_value(value)

  def _update_state(self):
    super()._update_state()
    self._update_label()

  def _on_offroad_transition(self):
    if not ui_state.started:
      apply_pending_restore(ui_state.params)
    self.refresh()

  def _on_click(self):
    if ui_state.engaged:
      gui_app.push_widget(BigDialog(tr("disengage to switch drivers"), ""))
      return

    new_mode = MAYA if self._selected == KYLE else KYLE
    # kyle mode turns factory AEB off, so it gets the red slider
    title = tr("slide for kyle mode") if new_mode == KYLE else tr("slide for maya mode")
    gui_app.push_widget(BigConfirmationDialog(title, self._wheel_icon, red=new_mode == KYLE,
                                              confirm_callback=lambda: self._switch(new_mode)))

  def _switch(self, mode: int):
    set_mode(ui_state.params, mode, offroad=not ui_state.started)
    self.refresh()
    apply_note = tr("Turn the car off and on to apply.") if ui_state.started else tr("Applies when the car starts.")
    if mode == MAYA:
      desc = tr("Car's own cruise control and emergency braking; sunnypilot still steers.")
    else:
      desc = tr("sunnypilot gas and brake with your saved settings; factory emergency braking is off.")
    gui_app.push_widget(BigDialog(tr("maya mode selected") if mode == MAYA else tr("kyle mode selected"), f"{desc} {apply_note}"))


class SunnylinkBigButton(SettingsBigButton):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._label.set_font_weight(FontWeight.AUDIOWIDE)

  def _get_label_font_size(self):
    # Audiowide runs wider than Inter: "sunnylink" wraps to two lines at 64
    return 56


class SettingsLayoutSP(OP.SettingsLayout):
  def __init__(self):
    OP.SettingsLayout.__init__(self)

    device_panel = DeviceLayoutMici()
    self._scroller._items[2].set_click_callback(lambda: gui_app.push_widget(device_panel))

    self.icon_offroad_enable = gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/always_offroad.png", BIG_ICON_SIZE,
                                               BIG_ICON_SIZE)
    self.icon_offroad_disable = gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/disable_offroad.png", BIG_ICON_SIZE,
                                                BIG_ICON_SIZE)
    self.icon_offroad_slider = gui_app.texture("icons_mici/settings/device/lkas.png", BIG_ICON_SIZE, BIG_ICON_SIZE)

    sunnylink_panel = SunnylinkLayoutMici()
    sunnylink_btn = SunnylinkBigButton(tr("sunnylink"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/sunnylink.png", 76, 44))
    sunnylink_btn.set_click_callback(lambda: gui_app.push_widget(sunnylink_panel))

    models_panel = ModelsLayoutMici()
    models_btn = SettingsBigButton(tr("models"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_models.png", ICON_SIZE, ICON_SIZE))
    models_btn.set_click_callback(lambda: gui_app.push_widget(models_panel))

    # onroad: enable button sits at the front (left of toggles)
    self._enable_offroad_btn_onroad = BigCircleButton(self.icon_offroad_enable, red=True)
    self._enable_offroad_btn_onroad.set_click_callback(lambda: self._handle_always_offroad(True))
    self._enable_offroad_btn_onroad.set_visible(lambda: ui_state.started and not ui_state.always_offroad)

    # offroad: enable button sits at the end (right of developer)
    self._enable_offroad_btn_offroad = BigCircleButton(self.icon_offroad_enable, red=True)
    self._enable_offroad_btn_offroad.set_click_callback(lambda: self._handle_always_offroad(True))
    self._enable_offroad_btn_offroad.set_visible(lambda: not ui_state.started and not ui_state.always_offroad)

    self._disable_offroad_btn = BigCircleButton(self.icon_offroad_disable, red=False)
    self._disable_offroad_btn.set_click_callback(lambda: self._handle_always_offroad(False))
    self._disable_offroad_btn.set_visible(lambda: ui_state.always_offroad)

    items = self._scroller._items.copy()

    items.insert(1, models_btn)
    items.insert(5, sunnylink_btn)

    # front slots (only one ever visible at a time): exit-always-offroad, then enable-onroad
    items.insert(0, self._enable_offroad_btn_onroad)
    items.insert(0, self._disable_offroad_btn)
    # end slot: enable-offroad (right of developer)
    items.append(self._enable_offroad_btn_offroad)

    # driver mode first, so it's the first card on the settings screen
    self._driver_mode_btn = DriverModeButton()
    items.insert(0, self._driver_mode_btn)

    self._scroller._items.clear()
    for item in items:
      self._scroller.add_widget(item)

  def _update_state(self):
    super()._update_state()

  def show_event(self):
    super().show_event()
    self._driver_mode_btn.refresh()

  def _handle_always_offroad(self, enable: bool):

    def _set_offroad_status(status: bool):
      if not ui_state.engaged:
        ui_state.params.put_bool("OffroadMode", status)
        ui_state.always_offroad = status

    if not enable:
      dlg = BigConfirmationDialog(tr("slide to exit always offroad"), self.icon_offroad_slider, red=False,
                                  confirm_callback=lambda: _set_offroad_status(False))
    else:
      if ui_state.engaged:
        gui_app.push_widget(BigDialog(tr("disengage to enable always offroad"), "", ))
        return

      dlg = BigConfirmationDialog(tr("slide to force offroad"), self.icon_offroad_slider, red=True,
                                  confirm_callback=lambda: _set_offroad_status(True))
    gui_app.push_widget(dlg)
