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
from pathlib import Path
from functools import cached_property

from .lighttpd import Lighttpd
from ..core.time import Timestamp
from ..registry.cell import Cell
from ..registry.certificate_subject import CertificateSubject
from ..core.htdigest import htdigest_generate
from . import html as views
from .agent_service import AgentService


class WebUi(AgentService):
  PROPERTIES = [
    "views",
  ]
  INITIAL_VIEWS = views

  def __init__(self, **properties):
    self._last_update_ts = None
    self._update_ui = True
    self._lighttpd = None
    super().__init__(**properties)
  

  def check_runnable(self) -> bool:
    return isinstance(self.agent.owner, Cell)


  @property
  def listen_port(self) -> int:
    if isinstance(self.agent.owner, Cell):
      return self.agent.owner.settings.httpd_port
    else:
      raise NotImplementedError()


  @property
  def min_update_delay(self) -> int:
    return self.agent.uvn.settings.timing_profile.status_min_delay


  @cached_property
  def doc_root(self) -> Path:
    doc_root = self.root / "public"
    self.mkdir(doc_root)
    return doc_root


  def _spin_once(self) -> None:
    if (not self._update_ui and self._last_update_ts
      and int(Timestamp.now().subtract(self._last_update_ts).total_seconds()) < self.min_update_delay):
      return
    self.views.index_html(self.agent, self.doc_root)
    self._last_update_ts = Timestamp.now()
    self._update_ui = False


  def request_update(self) -> None:
    self._update_ui = True


  def _start(self) -> None:
    assert(self._lighttpd is None)

    self.root.mkdir(exist_ok=True, parents=True)
    self.doc_root.mkdir(exist_ok=True, parents=True)
    
    secrets = []
    for user in self.agent.registry.users.values():
      secret_line = htdigest_generate(user.email, user.realm, password_hash=user.password[len("htdigest:"):])
      secrets.append(secret_line)

    self._lighttpd = Lighttpd(
      root=self.root,
      port=self.listen_port,
      doc_root=self.doc_root,
      log_dir=self.agent.log_dir,
      cert_subject=CertificateSubject(org=self.agent.uvn.name, cn=self.agent.owner.name),
      secret="\n".join(secrets),
      auth_realm=self.agent.uvn.name,
      protected_paths=["^/particles"],
      bind_addresses=list(self.agent.bind_addresses))
    self._lighttpd.start()


  def _stop(self, assert_stopped: bool) -> None:
    if self._lighttpd is None:
      return
    try:
      self._lighttpd.stop()
    finally:
      self._lighttpd = None
