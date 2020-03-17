#!/usr/bin/env python3

import logging
import sys

sys.path.append('lib') # noqa

import subprocess

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import ActiveStatus

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from interface_proxy_listen_tcp import ProxyListenTcpInterfaceRequires

logger = logging.getLogger(__name__)


class HaproxyCharm(CharmBase):

    state = StoredState()

    HAPROXY_ENV_FILE = Path('/etc/default/haproxy')

    def __init__(self, *args):
        super().__init__(*args)

        self.haproxy_conf_file = Path(f'/etc/haproxy/juju-{self.app.name}.cfg')

        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)
        self.framework.observe(self.on.stop, self.on_stop)
        self.framework.observe(self.on.config_changed, self.on_config_changed)

        self.tcp_backends = ProxyListenTcpInterfaceRequires(self, 'proxy-listen-tcp')
        self.framework.observe(self.tcp_backends.on.backends_changed, self.on_backends_changed)

        self.state.set_default(started=False)

    def on_install(self, event):
        subprocess.check_call(['apt', 'update'])
        subprocess.check_call(['apt', 'install', '-yq', 'haproxy'])

        ctxt = {'haproxy_app_config': self.haproxy_conf_file}
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('haproxy.env.j2')
        rendered_content = template.render(ctxt)
        self.HAPROXY_ENV_FILE.write_text(rendered_content)
        self.haproxy_conf_file.write_text('')

    def on_start(self, event):
        if not self.state.started:
            subprocess.check_call(['systemctl', 'start', 'haproxy'])
            self.state.started = True

        self.model.unit.status = ActiveStatus()

    def on_stop(self, event):
        if self.state.started:
            # TODO: handle the new "remove" hook https://github.com/juju/juju/pull/11237
            subprocess.check_call(['systemctl', 'stop', 'haproxy'])
            self.state.started = False

    def on_config_changed(self, event):
        # TODO: handle real global config changes.
        subprocess.check_call(['systemctl', 'restart', 'haproxy'])

    def on_backends_changed(self, event):
        ctxt = {
            'listen_proxies': self.tcp_backends.listen_proxies
        }
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('haproxy.conf.j2')
        rendered_content = template.render(ctxt)
        self.haproxy_conf_file.write_text(rendered_content)

        subprocess.check_call(['systemctl', 'restart', 'haproxy'])


if __name__ == '__main__':
    main(HaproxyCharm)
