###############################################################################
# (C) Copyright 2020-2024 Andrea Sorbini
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
###############################################################################
from ..registry.versioned import Versioned, disabled_if


class Runnable(Versioned):
  PROPERTIES = [
    "started",
    "runnable",
  ]
  INITIAL_STARTED = False
  INITIAL_RUNNABLE = True

  def __init__(self, **properties) -> None:
    super().__init__(**properties)
    if not self.check_runnable():
      self.runnable = False

  def __enter__(self) -> "Runnable":
    self.start()
    self.started = True
    self.log.activity("started")
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.log.activity("stopping...")
    try:
      self.stop(assert_stopped=exc_type is not None and not issubclass(exc_type, KeyboardInterrupt))
    finally:
      self.started = False
    self.log.activity("stopped.")

  def check_runnable(self) -> bool:
    return True

  def configure(self, **config_args) -> set[str]:
    result = super().configure(**config_args)
    if not self.check_runnable():
      self.log.error("NOT RUNNABLE ON CONFIGURE")
      config_args["runnable"] = False
    return result

  @disabled_if("runnable", neg=True)
  def start(self) -> None:
    self._start()

  def stop(self, assert_stopped: bool) -> None:
    if assert_stopped:
      self.log.debug("asserting stopped...")
    else:
      self.log.debug("stopping services...")
    return self._stop(assert_stopped)

  @disabled_if("runnable", neg=True)
  def spin_once(self) -> None:
    self._spin_once()

  def _stop(self, assert_stopped: bool) -> None:
    raise NotImplementedError()

  def _start(self) -> None:
    raise NotImplementedError()

  def _spin_once(self) -> None:
    pass
