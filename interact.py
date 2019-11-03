#!/usr/bin/python3

import re
import sys
import socket
import selectors
import logging
import subprocess
from time import monotonic as _time

__all__ = ["Interact", "SocketBackend", "ProcessBackend"]

class SocketBackend:
    def __init__(self, host, port):
        self.logger = logging.getLogger("pyinteract.SocketBackend.{id}".format(id=id(self)))
        self.host = host
        self.port = port

        try:
            self.logger.info("connecting to %s:%i", host, port)
            self.socket = socket.create_connection((host, port))
        except:
            self.logger.warning("connection failed!")
            raise

        self.read_selector = self.get_read_selector()

    def get_read_selector(self):
        if hasattr(selectors, 'PollSelector'):
            result = selectors.PollSelector()
        else:
            result = selectors.SelectSelector()
        result.register(self.socket, selectors.EVENT_READ)
        return result

    def close(self):
        self.logger.info("closing")
        if self.socket:
            self.socket.close()
        self.socket = None

    def read(self, timeout=None):
        if not self.socket:
            self.logger.warning("read failed: socket closed")
            raise EOFError()

        if timeout:
            if not self.read_selector.select(timeout):
                self.logger.warning("read failed: timeout")
                raise TimeoutError()

        result = self.socket.recv(1024)

        if not result:
            self.logger.warning("read failed: EOF")
            raise EOFError()

        self.logger.info("read %i bytes", len(result))
        return result

    def write(self, bytestring, timeout=None):
        try:
            self.socket.sendall(bytestring)
            self.logger.info("wrote %i bytes", len(bytestring))
        except:
            self.logger.warning("write failed!")

class ProcessBackend:
    def __init__(self, command, *args, **kwargs):
        self.logger = logging.getLogger("pyinteract.ProcessBackend.{id}".format(id=id(self)))
        self.command = command

        try:
            self.logger.info("running %s with args: %s", command, ", ".join(args))
            self.process = subprocess.Popen(command, *args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        except:
            self.logger.warning("popen failed!")
            raise

        self.read_selector = self.get_read_selector()

    def get_read_selector(self):
        result = selectors.SelectSelector()
        result.register(self.process.stdout, selectors.EVENT_READ)
        return result

    def close(self):
        self.logger.info("closing")
        if self.process:
            self.process.terminate()
        self.process = None

    def read(self, timeout=None):
        if not self.process:
            self.logger.warning("read failed: process ended")
            raise EOFError()

        if timeout:
            self.logger.warning("waiting for read_selector...")
            if not self.read_selector.select(timeout):
                self.logger.warning("read failed: timeout")
                raise TimeoutError()

        self.logger.warning("waiting for readline...")
        result = self.process.stdout.readline()
        self.logger.warning("readline completed")

        if not result:
            self.logger.warning("read failed: EOF")
            raise EOFError()

        self.logger.info("read %i bytes", len(result))
        return result

    def write(self, bytestring, timeout=None):
        try:
            self.process.stdin.write(bytestring)
            self.logger.info("wrote %i bytes", len(bytestring))
        except:
            self.logger.warning("write failed!")
            raise

class Interact:
    def host(host="localhost", port=8080):
        return Interact(SocketBackend(host, port))

    def command(cmd, *args):
        return Interact(ProcessBackend(cmd, *args))

    def __init__(self, backend):
        self.logger = logging.getLogger("pyinteract.Interact.{id}".format(id=id(self)))
        self.backend = backend
        self.buffer = b''

    def close(self):
        self.backend.close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def write(self, buffer):
        self.backend.write(buffer)

    def read_until(self, match, timeout=None):
        deadline = None
        if timeout:
            deadline = _time() + timeout

        while not deadline or _time() <= deadline:
            i = self.buffer.find(match)

            if i >= 0:
                i += len(match)
                result = self.buffer[:i]
                self.buffer = self.buffer[i:]
                return result

            if timeout:
                timeout = deadline = _time()

            self.buffer += self.backend.read(timeout)

        return b''

    def read_all(self):
        try:
            while True:
                self.buffer += self.backend.read()
        except EOFError:
            pass

        result = self.buffer
        self.buffer = b''
        return result

    def expect(self, options, timeout=None):
        deadline = None
        if timeout:
            deadline = _time() + timeout

        indices = range(len(options))

        while not deadline or _time() <= deadline:
            for i in indices:
                m = options[i].search(self.buffer)
                if m:
                    e = m.end()
                    text = self.buffer[:e]
                    self.buffer = self.buffer[e:]
                    return (i, m, text)

            if timeout:
                timeout = deadline = _time()

            self.buffer += self.backend.read(timeout)

        return (-1, None, text)

    def interact(self):
        selector = self.backend.get_read_selector()
        selector.register(sys.stdin, selectors.EVENT_READ)

        while True:
            for key, events in selector.select():
                if key.fileobj is sys.stdin:
                    line = sys.stdin.readline().encode('ascii')
                    if not line:
                        return
                    self.write(line)
                else:
                    try:
                        data = self.backend.read()
                        if data:
                            sys.stdout.write(data.decode('ascii', errors='replace'))
                            sys.stdout.flush()
                    except EOFError:
                        return

def main(method, *args):
    logging.basicConfig(format='%(asctime)-15s %(levelname)s %(name)s - %(message)s', level=logging.DEBUG)
    if method == "cmd":
        with Interact.command(*args) as i:
            i.interact()
    elif method == "host":
        with Interact.host(*args) as i:
            i.interact()
    else:
        print("unknown method: {m}".format(m=method))

if __name__ == "__main__":
    main(*sys.argv[1:])
