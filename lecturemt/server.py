#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py: Translation server that works asynchronously and dispatches requests to multiple translation servers."""
__author__ = "Frederic Bergeron"
__license__ = "undecided"
__version__ = "1.0"
__email__ = "bergeron@nlp.ist.i.kyoto-u.ac.jp"
__status__ = "Development"

from collections import deque
import configparser
import json
import logging
import logging.config
import queue
from random import randint
import re
import socket
import socketserver
import subprocess
import sys
import threading
from time import sleep
import timeit
import uuid

from translation_client import OpenNMTClient, KNMTClient

BUFFER_SIZE = 4096

EOM = "==== EOM ===="

lang_pairs = ['ja-en']

log = None
 
logging.basicConfig()


class RequestQueue(queue.Queue):

    def __init__(self):
        queue.Queue.__init__(self)


class Worker(threading.Thread):

    def __init__(self, name, lang_pair, translator_host, translator_port, segmenter_host, segmenter_port, segmenter_command, manager):
        threading.Thread.__init__(self)
        self.name = name
        self.lang_pair = lang_pair
        self.lang_source, self.lang_target = self.lang_pair.split("-")
        self.translator_host = translator_host
        self.translator_port = translator_port
        self.segmenter_host = segmenter_host
        self.segmenter_port = segmenter_port
        self.segmenter_command = segmenter_command
        self.manager = manager

    def run(self):
        while True:
            translation_id = self.manager.translation_request_queues[self.lang_pair].get(True)
            log.debug("Start processing request {0} by worker {1}...".format(translation_id, self.name))
            self.manager.update_status_translation(translation_id, "PROCESSING")
            start_request = timeit.default_timer()
            
            log.debug("translator: {0}:{1} segmenter: {2}:{3}".format(self.translator_host, self.translator_port, self.segmenter_host, self.segmenter_port))
            translation = self.manager.get_translation("admin", translation_id)
            log.debug("translation: {0}".format(translation))
            log.debug("text to translate: {0}".format(translation['text_source']))

            segmenter_cmd = re.sub(r'TEXT', translation['text_source'], self.segmenter_command)
            segmenter_cmd = re.sub(r'HOST', self.segmenter_host, segmenter_cmd)
            segmenter_cmd = re.sub(r'PORT', self.segmenter_port, segmenter_cmd)
            log.debug("cmd={0}".format(segmenter_cmd))

            segmenter_output = subprocess.check_output(segmenter_cmd, shell=True, universal_newlines=True)
            segmenter_output = segmenter_output.strip()
            log.debug("segmenter_output={0}".format(segmenter_output))
            
            # client = OpenNMTClient(self.translator_host, int(self.translator_port), log)
            client = KNMTClient(self.translator_host, int(self.translator_port), log)
            response = client.submit(segmenter_output)

            log.debug("response={0}".format(response))

            self.manager.update_text_translation(translation_id, response)
            processing_time = timeit.default_timer() - start_request
            log.debug("Finish processing request {0} by worker {1} in {2} s.".format(translation_id, self.name, processing_time)) 





class Manager(object):

    def __init__(self, config):
        self.config = config
        self.translations = {}
        self.translation_request_queues = {}
        self.workers = {}
        self.mutex = threading.Lock()
       
        lang_pairs = set([section[18:23] for section in self.config.sections() if section.startswith("TranslationServer_")])
        for lang_pair in lang_pairs:
            self.translation_request_queues[lang_pair] = RequestQueue()
            workerz = []
            self.workers[lang_pair] = workerz
            for idx, server_section in enumerate([section for section in self.config.sections() if section.startswith("TranslationServer_") and section[18:23] == lang_pair]):
                server_number = server_section[server_section.rfind('_') + 1:]
                segmentation_server_prop_name = "SegmentationServer_{0}_{1}".format(lang_pair, server_number)
                worker = Worker("Translater-{0}_{1} ({2}:{3})".format(idx, lang_pair, self.config[server_section]['Host'], self.config[server_section]['Port']), lang_pair, self.config[server_section]['Host'], self.config[server_section]['Port'], self.config[segmentation_server_prop_name]['Host'], self.config[segmentation_server_prop_name]['Port'], self.config['Server']['SegmentationCommand'], self)
                workerz.append(worker)
                worker.start()

    def get_translations(self, user_id):
        if user_id == "admin":
            return self.translations 
        else:
            return {k : v for k, v in self.translations.items() if v['owner'] == user_id}

    def update_status_translation(self, id, status):
        self.mutex.acquire()
        if id in self.translations:
            self.translations[id]['status'] = status
        self.mutex.release()

    def update_text_translation(self, id, text):
        self.mutex.acquire()
        if id in self.translations:
            self.translations[id]['text_target'] = text
            self.translations[id]['status'] = 'PROCESSED'
        self.mutex.release()

    def add_translation(self, translation):
        lang_pair = "{0}-{1}".format(translation['lang_source'], translation['lang_target'])

        # Ignore the translation if it concerns an unsupported language pair.
        if not lang_pair in self.translation_request_queues:
            return {}

        self.mutex.acquire()
        translation['status'] = "PENDING"
        self.translations[translation['id']] = translation

        # For now, I assume that the translation is a single sentence.
        # For example, a client application could split the text in several sentences and
        # submit each sentence using the REST API.
        # Otherwise, we need to split the text here in several sentences and
        # associate the subtranslation (for a sentence) to the parent translation (the whole text).

        self.translation_request_queues[lang_pair].put(translation['id'])
        self.mutex.release()

        return translation

    def get_translation(self, user_id, translation_id):
        if not translation_id in self.translations:
            return {}
        
        translation = self.translations[translation_id]
        if user_id == "admin":
            return translation
        
        return translation if translation['owner'] == user_id else {}

    def remove_translation(self, user_id, translation_id):
        if not translation_id in self.translations:
            return {}
        
        translation = self.translations[translation_id]
        if user_id in ["admin", translation['owner']]:
            del self.translations[translation_id]
            return translation

        return {}


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
                    if json_data['action'] == 'get_server_version':
                        response = {'server_version': '1.0'}
                    elif json_data['action'] == 'get_server_status':
                        response = {'server_status': 'OK'}
                    elif json_data['action'] == 'get_translations':
                        log.debug("get_transactions user_id={0}".format(json_data['user_id']))
                        response = self.manager.get_translations(json_data['user_id'])
                    elif json_data['action'] == 'add_translation':
                        log.debug("add_translation user_id={0}".format(json_data['user_id']))
                        log.debug("text_source={0}".format(json_data['text_source']))

                        translation = {}
                        translation['id'] = str(uuid.uuid4())
                        translation['owner'] = json_data['user_id']
                        translation['lang_source'] = json_data['lang_source']
                        translation['lang_target'] = json_data['lang_target']
                        translation['text_source'] = json_data['text_source']
                        translation['date_submission'] = json_data['date_submission']
                        
                        response = self.manager.add_translation(translation)
                    elif json_data['action'] == 'get_translation':
                        log.debug("get_translation user_id={0}".format(json_data['user_id']))
                        response = self.manager.get_translation(json_data['user_id'], json_data['translation_id'])
                    elif json_data['action'] == 'remove_translation':
                        log.debug("remove_translation user_id={0}".format(json_data['user_id']))
                        response = self.manager.remove_translation(json_data['user_id'], json_data['translation_id'])

                    log.debug("Request processed in {0} s. by {1}".format(timeit.default_timer() - start_request, threading.current_thread().name))
                    response = json.dumps(response, ensure_ascii=False)
                    log.debug("Response from server={0}".format(response))
                    self.request.sendall(response.encode('utf-8'))

        return ServerRequestHandler

    def __init__(self, server_address, config):
        self.manager = Manager(config)
        handler_class = self.make_request_handler(self.manager)
        socketserver.TCPServer.__init__(self, server_address, handler_class)

def do_start_server(config_file, log_config):
    if log_config:
        logging.config.fileConfig(log_config)
    global log
    log = logging.getLogger("default")

    config = configparser.ConfigParser()
    config.read(config_file)
    server = Server((config['Server']['Host'], int(config['Server']['Port'])), config)
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
