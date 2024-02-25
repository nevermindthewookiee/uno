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
import rti.connextdds as dds
from . data import dds as dds_data
from pathlib import Path
from tempfile import NamedTemporaryFile

from typing import Sequence, Mapping, Tuple, Union, Optional, Iterable, TYPE_CHECKING

from enum import Enum

from .uvn_id import UvnId
from .render import Templates
from .log import Logger as log

if TYPE_CHECKING:
  from .agent import Agent

class UvnTopic(Enum):
  UVN_ID = 0
  CELL_ID = 1
  BACKBONE = 2
  DNS = 3


class DdsParticipantConfig:
  CONFIG_TEMPLATE_FILENAME = "uno.xml"
  PARTICIPANT_PROFILE_ROOT = "UnoParticipants::RootAgent"
  PARTICIPANT_PROFILE_CELL = "UnoParticipants::CellAgent"

  def __init__(self,
      participant_xml_config: str,
      participant_profile: str,
      writers: Iterable[UvnTopic] | None = None,
      readers: Mapping[UvnTopic, dict] | None = None,
      user_conditions: Iterable[dds.GuardCondition] | None = None) -> None:
    self.participant_profile = participant_profile
    self.participant_xml_config = participant_xml_config
    self.writers = list(writers or [])
    self.readers = dict(readers or {})
    self.user_conditions = list(user_conditions or [])


  @staticmethod
  def load_config_template(filename: str) -> str:
    from importlib.resources import as_file, files
    with as_file(files(dds_data).joinpath(filename)) as config_file:
      return config_file.read_text()


class DdsParticipant:
  WRITER_NAMES = {
    UvnTopic.UVN_ID: "Publisher::UvnInfoWriter",
    UvnTopic.CELL_ID: "Publisher::CellInfoWriter",
    UvnTopic.BACKBONE: "MetadataPublisher::UvnDeploymentWriter",
    UvnTopic.DNS: "Publisher::NameserverWriter",
  }

  READER_NAMES = {
    UvnTopic.UVN_ID: "Subscriber::UvnInfoReader",
    UvnTopic.CELL_ID: "Subscriber::CellInfoReader",
    UvnTopic.BACKBONE: "MetadataSubscriber::UvnDeploymentReader",
    UvnTopic.DNS: "Subscriber::NameserverReader",
  }

  READERS_PROCESSING_ORDER = {
    UvnTopic.UVN_ID: 0,
    UvnTopic.CELL_ID: 1,
    UvnTopic.DNS: 2,
    UvnTopic.BACKBONE: 3,
  }

  TOPIC_TYPES = {
    UvnTopic.UVN_ID: "uno::UvnInfo",
    UvnTopic.CELL_ID: "uno::CellInfo",
    UvnTopic.DNS: "uno::NameserverDatabase",
    UvnTopic.BACKBONE: "uno::UvnDeployment",
  }

  REGISTERED_TYPES = {
    *TOPIC_TYPES.values(),
    "uno::DnsRecord",
    "uno::CellSiteSummary",
    "uno::CellPeerSummary",
    "uno::IpAddress",
  }

  def __init__(self) -> None:
    self._qos_provider = None
    self._dp = None
    self._waitset = None
    self.writers = {}
    self._writer_conditions = {}
    self._readers = {}
    self.types = {}
    self._reader_conditions = {}
    self._data_conditions = {}
    self._exit_condition = None
    self._user_conditions = []


  def start(self,
      config: DdsParticipantConfig,
      config_file_out: Optional[str]=None) -> None:
    log.debug("[DDS] STARTING...")

    if config_file_out is not None:
      config_file = config_file_out
    else:
      tmp_config_h = NamedTemporaryFile()
      tmp_config = Path(tmp_config_h.name)
      config_file = tmp_config

    config_file.write_text(config.participant_xml_config)

    qos_provider = dds.QosProvider(str(config_file))
    self.types = self._register_types(qos_provider)

    self._dp = qos_provider.create_participant_from_config(config.participant_profile)

    self.writers, self._writer_conditions = self._create_writers(self._dp, config.writers)

    self._readers, self._reader_conditions, self._data_conditions = self._create_readers(self._dp, config.readers)

    self._exit_condition = dds.GuardCondition()

    self._user_conditions = config.user_conditions

    self._waitset = dds.WaitSet()

    for condition in (
        self._exit_condition,
        *self._writer_conditions.values(),
        *self._reader_conditions.values(),
        *self._data_conditions.values(),
        *self._user_conditions):
      self._waitset += condition
    
    log.activity("[DDS] started")


  def stop(self) -> None:
    log.debug("[DDS] STOP in process...")
    for condition in (
        self._exit_condition,
        *self._writer_conditions.values(),
        *self._reader_conditions.values(),
        *self._data_conditions.values(),
        *self._user_conditions):
      if not condition:
        continue
      self._waitset -= condition
    if self._dp:
      self._dp.close()

    self._waitset = None
    self.writers = {}
    self._writer_conditions = {}
    self._readers = {}
    self.types = {}
    self._reader_conditions = {}
    self._data_conditions = {}
    self._user_conditions = []
    self._exit_condition = None
    self._dp = None
    log.activity("[DDS] stopped")


  def wait(self) -> Tuple[bool, Sequence[Tuple[UvnTopic, dds.DataWriter]], Sequence[Tuple[UvnTopic, dds.DataReader]], Sequence[Tuple[UvnTopic, dds.DataReader, dds.QueryCondition]], Sequence[dds.Condition]]:
    # log.debug("[DDS] waiting on waitset...")
    active_conditions = self._waitset.wait(dds.Duration(1))
    # log.debug(f"[DDS] waitset returned {len(active_conditions)} conditions")
    if len(active_conditions) == 0:
      return (False, [], [], [], [])
    assert(len(active_conditions) > 0)
    if self._exit_condition in active_conditions:
      return (True, [], [], [], [])

    active_writers = [
      (topic, self.writers[topic])
      for topic, cond in self._writer_conditions.items()
        if cond in active_conditions
    ]
    active_readers = sorted(
      ((topic, self._readers[topic])
      for topic, cond in self._reader_conditions.items()
        if cond in active_conditions),
      key=lambda t: self.READERS_PROCESSING_ORDER[t[0]]
    )
    active_data = [
      (topic, self._readers[topic], self._data_conditions[topic])
      for topic, cond in self._data_conditions.items()
        if cond in active_conditions
    ]
    active_user = [
      cond for cond in self._user_conditions
        if cond in active_conditions
    ]

    return (False, active_writers, active_readers, active_data, active_user)


  def _register_types(self, qos_provider: dds.QosProvider) -> Mapping[str, dds.StructType]:
    return {
      t: qos_provider.type(qos_provider.type_libraries[0], t)
        for t in self.REGISTERED_TYPES
    }

  def _create_writers(self, dp: dds.DomainParticipant, writer_topics: Sequence[UvnTopic]) -> Tuple[Mapping[UvnTopic, dds.DataWriter], Mapping[UvnTopic, dds.StatusCondition]]:
    writers = {}
    conditions = {}
    for topic in writer_topics:
      writer = dds.DynamicData.DataWriter(
        dp.find_datawriter(self.WRITER_NAMES[topic])
      )
      if writer is None:
        raise RuntimeError("failed to lookup writer", topic)
      writers[topic] = writer
      status_condition = dds.StatusCondition(writer)
      status_condition.enabled_statuses = (
        dds.StatusMask.PUBLICATION_MATCHED | 
        dds.StatusMask.LIVELINESS_LOST |
        dds.StatusMask.OFFERED_INCOMPATIBLE_QOS
      )
      conditions[topic] = status_condition

    return (writers, conditions)


  def _create_readers(self,
      dp: dds.DomainParticipant,
      reader_topics: Mapping[UvnTopic, Mapping[str, Union[str, Sequence[str]]]]) -> Tuple[Mapping[UvnTopic, dds.DataReader], Mapping[UvnTopic, dds.StatusCondition], Mapping[UvnTopic, dds.QueryCondition]]:
    readers = {}
    status_conditions = {}
    data_conditions = {}
    data_state = dds.DataState(dds.SampleState.NOT_READ)

    for topic, topic_query in reader_topics.items():
      reader = dds.DynamicData.DataReader(
        dp.find_datareader(self.READER_NAMES[topic])
      )
      if reader is None:
        raise RuntimeError("failed to lookup reader", topic)
      readers[topic] = reader

      status_condition = dds.StatusCondition(reader)
      status_condition.enabled_statuses = (
        dds.StatusMask.SUBSCRIPTION_MATCHED | 
        dds.StatusMask.LIVELINESS_CHANGED |
        dds.StatusMask.REQUESTED_INCOMPATIBLE_QOS
      )
      status_conditions[topic] = status_condition

      if topic_query:
        query = dds.Query(reader, topic_query["query"], topic_query["params"])
        data_condition = dds.QueryCondition(query, data_state)
      else:
        data_condition = dds.ReadCondition(reader, data_state)
      data_conditions[topic] = data_condition

    return (readers, status_conditions, data_conditions)
