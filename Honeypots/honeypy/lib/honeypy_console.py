# HoneyPy Copyright (C) 2013-2017 foospidy
# https://github.com/foospidy/HoneyPy
# See LICENSE for details
# HoneyPy Console

import base64
import os
import shutil
from twisted.internet import reactor
from twisted.protocols import basic
from twisted.python import log


class HoneyPyConsole(basic.LineReceiver):
    delimiter = b"\n"  # Twisted expects delimiter to be bytes

    def connectionMade(self):
        self.do_banner()
        self.sendLine("HoneyPy Console. For help type 'help'.")
        self.transport.write(b'HoneyPy> ')

    def lineReceived(self, line):
        if not line:
            self.transport.write(b'HoneyPy> ')
            return

        # Parse command
        commandParts = line.decode().split()
        command = commandParts[0].lower()
        args = commandParts[1:]

        try:
            method = getattr(self, 'do_' + command)
        except AttributeError:
            self.sendLine('Error: no such command.')
        else:
            try:
                method(*args)
            except Exception as e:
                self.sendLine('Error: ' + str(e))

        exit_commands = ['exit', 'quit']

        if command not in exit_commands:
            self.transport.write(b'HoneyPy> ')

    def sendLine(self, line):
        """Override to handle str/bytes properly."""
        if isinstance(line, str):
            line = line.encode()
        super().sendLine(line)

    def do_help(self, command=None):
        """help [command]: List commands, or show help on the given command"""
        if command:
            self.sendLine(getattr(self, 'do_' + command).__doc__)
        else:
            commands = [cmd[3:] for cmd in dir(self) if cmd.startswith('do_')]
            self.sendLine("Valid commands: " + " ".join(commands))

    def do_start(self):
        """start: Start all configured services"""
        if len(self.services[1]) == 0:
            self.sendLine('No services are enabled.')
        else:
            i = 0
            for i in range(len(self.services[1])):
                self.services[1][i].startListening()

            self.sendLine(f'{i + 1} service(s) started!')

    def do_stop(self):
        """stop: Stop all configured services"""
        i = 0
        for i in range(len(self.services[1])):
            self.services[1][i].stopListening()

        self.sendLine(f'{i + 1} service(s) stopped!')

    def do_banner(self):
        """banner: Display HoneyPy banner"""
        banner = (
            "ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfX18gICAgICAgCiAgL1wgIC9cX19fICBf"
            "IF9fICAgX19fIF8gICBfICAvIF8gXF8gICBfIAogLyAvXy8gLyBfIFx8ICdfIFwgLyBfIFwgfCB8"
            "IHwvIC9fKS8gfCB8IHwKLyBfXyAgLyAoXykgfCB8IHwgfCAgX18vIHxffCAvIF9fXy98IHxffCB8"
            "ClwvIC9fLyBcX19fL3xffCB8X3xcX19ffFxfXywgXC8gICAgIFxfXywgfAogICAgICAgICAgICAg"
            "ICAgICAgICAgICB8X19fLyAgICAgICB8X19fLyAKCg=="
        )
        banner_decoded = base64.b64decode(banner).decode()
        self.sendLine(banner_decoded)
        self.sendLine('[HoneyPy Copyright (c) 2013-2017. foospidy]\n')

    def do_list(self, list_type='services'):
        """list: List information. Usage: list [services|profiles|loggers]"""
        if list_type == 'profiles':
            self._list_profiles()
        elif list_type == 'loggers':
            self._list_loggers()
        else:
            self._list_services()

    def _list_services(self):
        """list services: List all configured services"""
        for i in range(len(self.services[0])):
            self.sendLine(self.services[0][i] + '\t' + str(self.services[1][i]))

    def _list_loggers(self):
        """list loggers: List all enabled loggers"""
        for section in self.config.sections():
            if section != 'honeypy':
                if self.config.get(section, 'enabled').lower() == 'yes':
                    self.sendLine('\t Enabled\t' + section)
                else:
                    self.sendLine('\t Disabled\t' + section)

    @staticmethod
    def _list_profiles():
        """list profiles: List all available profiles"""
        path = 'etc/profiles/'
        files = next(os.walk(path))[2]

        for f in files:
            parts = f.split('.')
            if len(parts) >= 3 and parts[0] == 'services' and parts[2] == 'profile':
                print(parts[1])

    def do_set(self, setting='profile', value='default'):
        """set: Change settings. Usage: set profile <profile>"""
        if self._set_profile(value) and setting == 'profile':
            self.sendLine(f'Profile changed to {value}')
            self.sendLine('Quit and restart HoneyPy for profile change to take effect!')
        else:
            self.sendLine('Error! No change.')

    @staticmethod
    def _set_profile(profile='default'):
        changed = False
        src = f'etc/profiles/services.{profile}.profile'
        dst = 'etc/services.cfg'

        if os.path.isfile(dst):
            shutil.copy2(src, dst)
            changed = True

        return changed

    def do_test(self, test='loggers'):
        """test: Generate a test event"""
        if test == 'loggers':
            self._test_loggers()

    @staticmethod
    def _test_loggers():
        """test loggers: generate a test event"""
        log.msg(
            '%s %s  TCP TEST %s %s %s %s %s %s' %
            ('session', "test", '127.0.0.1', '-1', 'test', '127.0.0.1', '-1', 'TestFromHoneyPyConsole'),
            system='test'
        )

    def do_exit(self):
        """exit: Exit HoneyPy"""
        self.sendLine('Goodbye.')
        self.transport.loseConnection()

    def do_quit(self):
        """quit: Quit HoneyPy"""
        self.sendLine('Goodbye.')
        self.transport.loseConnection()

    def connectionLost(self, reason):
        # stop the reactor, only because this is meant to be run in Stdio.
        reactor.stop()

    def __init__(self, config, services):
        self.config = config
        self.services = services
