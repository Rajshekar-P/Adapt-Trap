# HoneyPy Copyright (C) 2013-2017 foospidy
# https://github.com/foospidy/HoneyPy
# See LICENSE for details

from twisted.internet import protocol
from twisted.python import log
import uuid

### START CUSTOM IMPORTS ###
import os
import hashlib
############################


class HashCountRandom(protocol.Protocol):  ### Set custom protocol class name
    localhost = None
    remote_host = None
    session = None

    ### START CUSTOM VARIABLES ###############################################################

    ##########################################################################################

    # handle events
    def connectionMade(self):
        self.connect()

        ### START CUSTOM CODE ####################################################################
        self.count = 0
        self.tx('ACCEPT_CONN: ' + str(self.remote_host.host) + '\n')
        ##########################################################################################

    def dataReceived(self, data):
        self.rx(data)

        ### START CUSTOM CODE ####################################################################
        # custom code
        self.count = self.count + 1
        self.tx(self.md5sum(self.count) + ':' + str(os.urandom(99)) + '\n')
        ##########################################################################################

    ### START CUSTOM FUNCTIONS ###################################################################
    def md5sum(self, data):
        m = hashlib.md5()
        m.update(str(data).encode())
        return m.hexdigest()

    ##############################################################################################

    def connect(self):
        self.local_host = self.transport.getHost()
        self.remote_host = self.transport.getPeer()
        self.session = uuid.uuid1()
        log.msg('%s %s CONNECT %s %s %s %s %s' % (
            self.session, self.remote_host.type,
            self.local_host.host, self.local_host.port,
            self.factory.name, self.remote_host.host, self.remote_host.port
        ))

    def clientConnectionLost(self):
        self.transport.loseConnection()

    def tx(self, data):
        # fix: safely convert bytes to hex string if data is bytes
        if isinstance(data, str):
            encoded_hex = data.encode().hex()
        elif isinstance(data, bytes):
            encoded_hex = data.hex()
        else:
            encoded_hex = str(data)

        log.msg('%s %s TX %s %s %s %s %s %s' % (
            self.session, self.remote_host.type,
            self.local_host.host, self.local_host.port,
            self.factory.name, self.remote_host.host, self.remote_host.port,
            encoded_hex
        ))
        self.transport.write(data.encode() if isinstance(data, str) else data)

    def rx(self, data):
        # fix: safely convert bytes to hex string if data is bytes
        if isinstance(data, str):
            encoded_hex = data.encode().hex()
        elif isinstance(data, bytes):
            encoded_hex = data.hex()
        else:
            encoded_hex = str(data)

        log.msg('%s %s RX %s %s %s %s %s %s' % (
            self.session, self.remote_host.type,
            self.local_host.host, self.local_host.port,
            self.factory.name, self.remote_host.host, self.remote_host.port,
            encoded_hex
        ))


class pluginFactory(protocol.Factory):
    protocol = HashCountRandom  ### Set protocol to custom protocol class name

    def __init__(self, name=None):
        self.name = name or 'HoneyPy'
