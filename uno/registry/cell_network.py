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
import ipaddress

from .versioned import Versioned
from .database_object import OwnableDatabaseObject


class CellNetwork(Versioned, OwnableDatabaseObject):
  DB_TABLE = "cell_networks"
  DB_TABLE_PROPERTIES = [
    "subnet",
  ]

  @classmethod
  def DB_OWNER(cls) -> type:
    from .cell import Cell

    return Cell

  DB_OWNER_TABLE_COLUMN = "cell_id"

  PROPERTIES = [
    "subnet",
  ]

  REQ_PROPERTIES = [
    "subnet",
  ]

  def prepare_subnet(self, val: str | int | ipaddress.IPv4Network) -> ipaddress.IPv4Network:
    return ipaddress.ip_network(val)
