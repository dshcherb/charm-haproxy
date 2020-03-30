#!/usr/bin/env python3

import unittest
import sys

sys.path.append('lib') # noqa
sys.path.append('src') # noqa

from src import charm
from ops.testing import Harness

from unittest.mock import patch, call


class TestHaproxyCharm(unittest.TestCase):

    @patch('pathlib.Path.write_text')
    @patch('subprocess.check_call')
    def test_install(self, mock_check_call, write_text):
        harness = Harness(charm.HaproxyCharm)
        harness.begin()
        harness.charm.on.install.emit()

        mock_check_call.assert_has_calls([
            call(['apt', 'update']),
            call(['apt', 'install', '-yq', 'haproxy'])
        ])

        harness.charm.HAPROXY_ENV_FILE.write_text.assert_called()
        harness.charm.haproxy_conf_file.write_text.assert_called()


if __name__ == '__main__':
    unittest.main()
