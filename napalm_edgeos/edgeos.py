# Copyright 2016 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Napalm driver for Edgeos.

Read napalm.readthedocs.org for more information.
"""

import sys
from napalm_base.base import NetworkDriver
from napalm_base.exceptions import ConnectionException, SessionLockedException, \
                                   MergeConfigException, ReplaceConfigException,\
                                   CommandErrorException

from netmiko import ConnectHandler, SCPConn

class EdgeosDriver(NetworkDriver):
    """Napalm driver for skeleton."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """NAPALM Edgeos Handler."""
        if optional_args is None:
            optional_args = {}
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        self.port = optional_args.get('port', 22)

        self.candidate_cfg = optional_args.get('candidate_cfg', '/config/candidate')

        self.device = None
        self.config_replace = False

    def open(self):
        """Open a connection to the device."""
        self.device = ConnectHandler(
            device_type='vyos',
            host=self.hostname,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            port=self.port
        )

    def close(self):
        """Close the connection to the device."""
        self.device.disconnect()

    def load_replace_candidate(self, filename=None, config=None):
        self.config_replace = True
        error_marker = 'Failed to parse specified config file'

        if config:
            raise NotImplementedError

        if not filename:
            raise ReplaceConfigException("filename empty")

        self.scp_file(source_file=filename, dest_file=self.candidate_cfg)
        self.device.config_mode()

        cmd = 'load {}'.format(self.candidate_cfg)
        output = self.device.send_command(cmd, expect_string='#')

        if error_marker in output:
            self.discard_config()
            raise ReplaceConfigException(output)

    def load_merge_candidate(self, filename=None, config=None):
        raise NotImplementedError

    def commit_config(self, save=True):
        self.config_replace = False
        error_marker = 'Failed to generate committed config'
        output = self.device.send_command('commit', expect_string='#', delay_factor=.1)

        if error_marker in output:
            self.discard_config()
            raise ReplaceConfigException(output)

        if save:
            self.device.send_command('save', expect_string='#')

        self.device.send_command('exit', expect_string='$')

    def discard_config(self):
        self.config_replace = False
        self.device.send_command('exit discard', expect_string='$')

    def compare_config(self):
        if not self.config_replace:
            raise CommandErrorException("compare_config called to early")

        diff = self.device.send_command('compare', expect_string="#").strip()
        diff = '\n'.join(diff.splitlines()[:-1])

        if diff == 'No changes between working and active configurations':
            return ''

        return diff

    def scp_file(self, source_file, dest_file):
        try:
            scp_transfer = SCPConn(self.device)
            scp_transfer.scp_put_file(source_file, dest_file)
        except:
            raise ConnectionException("SCP transfer to remote device failed")
