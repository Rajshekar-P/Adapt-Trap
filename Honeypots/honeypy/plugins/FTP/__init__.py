from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from twisted.python import log
from plugins import PluginBase
from datetime import datetime

class FTPProtocol(Protocol):
    def connectionMade(self):
        self.peer = self.transport.getPeer()
        self.state = "AUTH"
        self.username = None

        self.sendLine("220 FTP Honeypot Ready")

        if hasattr(self.factory, "logger") and self.factory.logger:
            self.factory.logger.info(f"FTP connection from {self.peer.host}:{self.peer.port}")
        else:
            log.msg(f"FTP connection from {self.peer.host}:{self.peer.port}")

    def dataReceived(self, data):
        cmd = data.decode().strip()
        response_lines = self.handleCommand(cmd)
        if isinstance(response_lines, list):
            for line in response_lines:
                self.sendLine(line)
        elif response_lines:
            self.sendLine(response_lines)

    def handleCommand(self, cmd):
        parts = cmd.split(" ", 1)
        command = parts[0].upper()
        argument = parts[1] if len(parts) > 1 else ""

        # ✅ MongoDB-compatible structured logging
        if hasattr(self.factory, "logger") and self.factory.logger:
            try:
                self.factory.logger.msg({
                    'event_type': 'ftp_command',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'source_ip': self.peer.host,
                    'source_port': self.peer.port,
                    'command': command,
                    'args': [argument] if argument else []
                })
            except Exception as e:
                log.err(f"[!] FTP logger.msg failed: {e}")
        else:
            log.msg(f"FTP command from {self.peer.host}: {command} {argument}")

        # ✅ Handle commands
        if command == "USER":
            self.username = argument
            return "331 Username ok, need password"

        elif command == "PASS":
            return f"230 Login successful for {self.username}"

        elif command == "LIST":
            return [
                "150 Here comes the directory listing (simulated)",
                "-rw-r--r-- 1 root root 1337 Jul 28 14:00 secrets.txt",
                "226 Directory send OK"
            ]

        elif command == "RETR":
            if argument:
                return [
                    f"150 Opening BINARY mode data connection for {argument} (simulated)",
                    "FAKE FILE CONTENT HERE",
                    "226 Transfer complete"
                ]
            else:
                return "501 No filename given."

        elif command == "STOR":
            if argument:
                return [
                    f"150 Ready to receive {argument} (simulated)",
                    "226 Upload successful (simulated)"
                ]
            else:
                return "501 No filename given."

        elif command == "FEAT":
            return [
                "211-Features:",
                " MDTM",
                " REST STREAM",
                " SIZE",
                " UTF8",
                "211 End"
            ]

        elif command == "SYST":
            return "215 UNIX Type: L8 (Fake)"

        elif command == "QUIT":
            self.transport.loseConnection()
            return "221 Goodbye"

        else:
            if hasattr(self.factory, "logger") and self.factory.logger:
                self.factory.logger.msg({
                    'event_type': 'ftp_command',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'source_ip': self.peer.host,
                    'source_port': self.peer.port,
                    'command': command,
                    'args': [argument] if argument else [],
                    'note': 'Unknown command'
                })

            return "502 Command not implemented"

    def sendLine(self, line):
        self.transport.write((line + "\r\n").encode())


class pluginMain(PluginBase):
    def __init__(self, options=None):
        if not isinstance(options, dict):
            options = {}
        super().__init__(options)

        self.plugin_name = "FTP"
        self.logger = getattr(self, "logger", None)

        port_raw = options.get("port")
        try:
            if isinstance(port_raw, str) and ":" in port_raw:
                self.plugin_port = int(port_raw.split(":")[-1])
            elif isinstance(port_raw, int):
                self.plugin_port = port_raw
            else:
                self.plugin_port = 2244
        except Exception as e:
            log.err(f"[!] Failed to parse FTP plugin port from config: {e}")
            self.plugin_port = 2244

        self.started = False
        self.listener = None

    def buildProtocol(self, addr):
        proto = FTPProtocol()
        proto.factory = self
        return proto

    def startHoneyService(self):
        if self.started:
            msg = f"FTP honeypot already running on port {self.plugin_port}"
            if self.logger:
                self.logger.warning(msg)
            else:
                log.msg("[!] " + msg)
            return

        msg = f"Starting FTP honeypot on TCP port {self.plugin_port}"
        if self.logger:
            self.logger.info(msg)
        else:
            log.msg("[+] " + msg)

        factory = Factory()
        factory.protocol = FTPProtocol
        factory.logger = self.logger
        factory.buildProtocol = self.buildProtocol
        self.listener = reactor.listenTCP(self.plugin_port, factory)
        self.started = True
        return self.listener

    def doStart(self):
        return self.startHoneyService()

    def doStop(self):
        if self.listener:
            self.listener.stopListening()
            self.listener = None
        self.started = False


pluginFactory = pluginMain
