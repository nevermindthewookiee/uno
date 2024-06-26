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
from typing import TYPE_CHECKING
from pathlib import Path

from uno.registry.versioned import Versioned

if TYPE_CHECKING:
  from .cloud_provider import CloudProvider


class CloudEmailServer(Versioned):
  PROPERTIES = [
    "root",
  ]
  REQ_PROPERTIES = [
    "root",
  ]

  def prepare_root(self, val: str | Path) -> Path:
    return Path(val)

  # def __update_str_repr__(self) -> str:
  #   cls_name = self.log.camelcase_to_kebabcase(CloudEmailServer.__qualname__)
  #   self._str_repr = f"{cls_name}({self.parent})"

  @property
  def provider(self) -> "CloudProvider":
    from .cloud_provider import CloudProvider

    assert isinstance(self.parent, CloudProvider)
    return self.parent

  def send(self, sender: str, to: list[str], subject: str, body: str) -> None:
    raise NotImplementedError()
