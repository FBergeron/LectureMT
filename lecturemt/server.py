#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py: Translation server that works asynchronously and dispatches requests to multiple translation servers."""
__author__ = "Frederic Bergeron"
__license__ = "undecided"
__version__ = "1.0"
__email__ = "bergeron@nlp.ist.i.kyoto-u.ac.jp"
__status__ = "Development"

import json
import configparser
import logging
import logging.config
import socket
import socketserver
import sys
import threading
import timeit

BUFFER_SIZE = 4096

EOM = "==== EOM ===="

log = None
 
logging.basicConfig()

class Manager(object):

    def __init__(self):
        pass

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):

    daemon_threads = True
    allow_reuse_address = True

    def make_request_handler(self, manager):
        class ServerRequestHandler(socketserver.BaseRequestHandler, object):

            def __init__(self, *args, **kwargs):
                self.manager = manager
                super(ServerRequestHandler, self).__init__(*args, **kwargs)

            def handle(self):
                start_request = timeit.default_timer()
                log.debug("Handling request...")

                # Read until EOM delimiter is met. 
                total_data = []
                data = ''
                while True:
                    data = self.request.recv(BUFFER_SIZE).decode('utf-8')
                    if EOM in data:
                        total_data.append(data[:data.find(EOM)])
                        break
                    total_data.append(data)
                    if len(total_data)>1:
                        #check if EOM was split
                        last_pair = total_data[-2] + total_data[-1]
                        if EOM in last_pair:
                            total_data[-2] = last_pair[:last_pair.find(EOM)]
                            total_data.pop()
                            break
                str_data = ''.join(total_data)

                log.debug("Request to server={0}".format(str_data))
                response = {}
                json_data = None
                try:
                    json_data = json.loads(str_data)
                except Exception as e:
                    log.info("Invalid JSON data. Request ignored.")

                if json_data:    
                    if json_data['type'] == 'get_server_version':
                        response = {'server_version': '1.0'}

                    log.debug("Request processed in {0} s. by {1}".format(timeit.default_timer() - start_request, threading.current_thread().name))
                    response = json.dumps(response)
                    log.debug("Response from server={0}".format(response))
                    self.request.sendall(response.encode('utf-8'))

        return ServerRequestHandler

    def __init__(self, server_address):
        self.manager = Manager()
        handler_class = self.make_request_handler(self.manager)
        socketserver.TCPServer.__init__(self, server_address, handler_class)

def do_start_server(config_file, log_config):
    if log_config:
        logging.config.fileConfig(log_config)
    global log
    log = logging.getLogger("default")

    config = configparser.ConfigParser()
    config.read(config_file)
    server = Server((config['Server']['Host'], int(config['Server']['Port'])))
    ip, port = server.server_address
    log.info("Start listening for requests on {0}:{1}...".format(socket.gethostname(), port))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()

    log.info("Stop listening for requests on {0}:{1}...".format(socket.gethostname(), port))
    sys.exit(0)


if __name__ == "__main__":
    do_start_server("conf/config.ini", "conf/config_logging.ini")
