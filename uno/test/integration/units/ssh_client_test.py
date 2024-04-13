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
import contextlib
import subprocess
import ipaddress
from typing import Iterable
from uno.test.integration import Experiment, Host


def ssh_client_test(
  experiment: Experiment,
  test_config: Iterable[tuple[Host, Host]],
  batch_size: int | None = None,
  timeout: int = 15,
):
  def _start(host: Host, server: Host) -> subprocess.Popen:
    # Connect via SSH and run a "dummy" test (e.g. verify that the hostname is what we expect)
    # We mostly want to make sure we can establish an SSH connection through the UVN
    experiment.log.activity("SSH START: {} → {}@{}", host, server, server.default_address)
    cmd_keyscan = " ".join(
      [
        "ssh-keyscan",
        # *(["-T", f"{timeout}"] if timeout > 0 else []),
        "-p",
        "22",
        "-H",
        f"{server.default_address}",
        ">>",
        "~/.ssh/known_hosts",
      ]
    )
    cmd_ssh_test = " ".join(
      [
        "ssh",
        *(["-o", f"ConnectTimeout={timeout}"] if timeout > 0 else []),
        f"uno@{server.default_address}",
        "'echo THIS_IS_A_TEST_ON $(hostname)'",
        "|",
        "grep",
        f"'THIS_IS_A_TEST_ON {server.hostname}'",
      ]
    )

    host.exec("sh", "-c", cmd_keyscan, user="uno")
    return host.popen("sh", "-c", cmd_ssh_test, user="uno", capture_output=True)

  def _wait(host: Host, server: Host, test: subprocess.Popen, timeout: float = 60.0) -> None:
    stdout, stderr = test.communicate(timeout=experiment.config["test_timeout"])
    rc = test.wait(timeout)
    assert rc == 0, f"SSH FAILED {host} → {server}@{server.default_address}: rc = {rc}"
    assert (
      stdout.decode().strip() == f"THIS_IS_A_TEST_ON {server.hostname}"
    ), f"SSH FAILED {host} → {server}@{server.default_address}: invalid output"
    experiment.log.info("SSH OK: {}", server)

  if batch_size is None:
    batch_size = len(experiment.networks)

  # Start tests in batches using popen, then wait for them to terminate
  def _wait_batch(batch: list[tuple[Host, Host, ipaddress.IPv4Address, subprocess.Popen]]):
    for host, server, test in batch:
      _wait(host, server, test)

  test_config = list(test_config)
  servers = {s for _, s in test_config}

  with contextlib.ExitStack() as stack:
    for server in servers:
      stack.enter_context(server.ssh_server())
    batch = []
    for host, server in test_config:
      if len(batch) == batch_size:
        _wait_batch(batch)
        batch = []
      test = _start(host, server)
      batch.append((host, server, test))
    if batch:
      _wait_batch(batch)
      batch = []
