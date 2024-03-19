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
from typing import Generator, TYPE_CHECKING
from functools import cached_property
import ipaddress

from .user import User
from ..core.log import Logger as log

from .versioned import Versioned, prepare_name
from .database_object import OwnableDatabaseObject, DatabaseObjectOwner
from .cell_settings import CellSettings

if TYPE_CHECKING:
  from .uvn import Uvn

class Cell(Versioned, OwnableDatabaseObject, DatabaseObjectOwner):
  PROPERTIES = [
    "uvn_id",
    "settings",
    "address",
    "excluded",
    "name",
    "allowed_lans",
  ]
  RO_PROPERTIES = [
    "uvn_id",
    "name",
  ]
  REQ_PROPERTIES = RO_PROPERTIES
  STR_PROPERTIES = [
    "id",
    "name",
  ]
  DB_TABLE = "cells"
  DB_TABLE_PROPERTIES = PROPERTIES
  DB_OWNER = User
  DB_OWNER_TABLE = "cells_credentials"

  INITIAL_EXCLUDED = False
  def INITIAL_SETTINGS(self) -> CellSettings:
    return self.deserialize_child(CellSettings)
  def INITIAL_ALLOWED_LANS(self) -> set[ipaddress.IPv4Network]:
    return set()


  @property
  def nested(self) -> Generator[Versioned, None, None]:
    yield self.settings


  @cached_property
  def uvn(self) -> "Uvn":
    from .uvn import Uvn
    return next(self.db.load(Uvn, id=self.uvn_id))


  def validate_new(self) -> None:
    self.uvn.validate_cell(self)


  def prepare_name(self, val: str) -> None:
    return prepare_name(self.db, val)


  def prepare_settings(self, val: "str | dict | CellSettings") -> CellSettings:
    return self.deserialize_child(CellSettings, val)


  def prepare_allowed_lans(self, val: "str | list[str] | set[ipaddress.IPv4Network]") -> set[ipaddress.IPv4Network]:
    return self.deserialize_collection(ipaddress.IPv4Network, val, set)


  def serialize_allowed_lans(self, val: set[ipaddress.IPv4Network]) -> set[str]:
    return sorted(str(v) for v in val)


