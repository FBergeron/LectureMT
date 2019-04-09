#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py: Translation server that works asynchronously and dispatches requests to multiple translation servers."""
__author__ = "Frederic Bergeron"
__license__ = "undecided"
__version__ = "1.0"
__email__ = "bergeron@nlp.ist.i.kyoto-u.ac.jp"
__status__ = "Development"

import configparser
import datetime
import json
import logging
import logging.config
import pika
from random import randint
import re
import socket
import socketserver
import sys
import threading
import time
import timeit
import uuid

BUFFER_SIZE = 4096

EOM = "==== EOM ===="

log = None
 
logging.basicConfig()


class TranslationCleaner(threading.Thread):

    # Every 5 minutes (or 3000 secs), check if some translations have been there for too long (more than 10 minutes (or 6000 secs)). 
    def __init__(self, manager, delay=300, expiration_delay=600):
        threading.Thread.__init__(self)
        self.manager = manager
        self.delay = delay
        self.expiration_delay = expiration_delay

    def run(self):
        while True:
            time.sleep(self.delay)
            self.manager.remove_expired_translations(self.expiration_delay)


class Worker(threading.Thread):

    def __init__(self, name, lang_pair, rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password, manager):
        threading.Thread.__init__(self)
        self.name = name
        self.lang_pair = lang_pair
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_username = rabbitmq_username
        self.rabbitmq_password = rabbitmq_password
        self.manager = manager
        log.debug("Creating worker: name={0} lang_pair={1}".format(name, lang_pair))

    def run(self):
        credentials = pika.PlainCredentials(self.rabbitmq_username, self.rabbitmq_password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host, port=self.rabbitmq_port, credentials=credentials))
        channel = connection.channel()

        queue_name = 'trans_resp_{0}'.format(self.lang_pair)
        channel.queue_declare(queue=queue_name, durable=True)

        def process_translation_response(ch, method, properties, body):
            trans_resp = json.loads(body)
            self.manager.update_text_translation(trans_resp['id'], trans_resp['translated_text'])
            ch.basic_ack(delivery_tag = method.delivery_tag)
            log.debug("Translation request {0} has been processed.".format(trans_resp['id']))

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue_name, process_translation_response)

        channel.start_consuming()

class Manager(object):

    def __init__(self, config):
        self.config = config
        self.translations = {}
        self.workers = []
        self.mutex = threading.Lock()
       
        lang_pairs = self.config['Server']['LanguagePairs'].split(',')
        for lang_pair in lang_pairs:
            worker_name = "Handler_{0}".format(lang_pair)
            worker = Worker(worker_name, lang_pair, 
                self.config['RabbitMQ']['Host'], self.config['RabbitMQ']['Port'],
                self.config['RabbitMQ']['Username'], self.config['RabbitMQ']['Password'], self)
            self.workers.append(worker)
            worker.start()

        self.translation_cleaner = TranslationCleaner(self)
        self.translation_cleaner.start()

    def get_translations(self, user_id):
        if user_id == "admin":
            self.mutex.acquire()
            translations = {k : {"status": v["status"], "owner": v["owner"]} for k, v in self.translations.items()}
            self.mutex.release()
            return translations 

        self.mutex.acquire()
        translations = {k : v["status"] for k, v in self.translations.items() if v['owner'] == user_id}
        self.mutex.release()
        return translations 

    def update_status_translation(self, id, status):
        self.mutex.acquire()
        if id in self.translations:
            self.translations[id]['status'] = status
        self.mutex.release()

    def update_text_translation(self, id, text):
        self.mutex.acquire()
        if id in self.translations:
            self.translations[id]['text_target'] = text
            self.translations[id]['date_processed'] = str(datetime.datetime.now())
            self.translations[id]['status'] = 'PROCESSED'
        self.mutex.release()

    def add_translation(self, translation):
        lang_pair = "{0}-{1}".format(translation['lang_source'], translation['lang_target'])

        # Ignore the translation if it concerns an unsupported language pair.
        if not lang_pair in self.config['Server']['LanguagePairs'].split(","):
            return {}

        self.mutex.acquire()
        try:
            translation['status'] = "PENDING"
            self.translations[translation['id']] = translation

            # For now, I assume that the translation is a single sentence.
            # For example, a client application could split the text in several sentences and
            # submit each sentence using the REST API.
            # Otherwise, we need to split the text here in several sentences and
            # associate the subtranslation (for a sentence) to the parent translation (the whole text).

            credentials = pika.PlainCredentials(self.config['RabbitMQ']['Username'], self.config['RabbitMQ']['Password'])
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.config['RabbitMQ']['Host'], port=self.config['RabbitMQ']['Port'], credentials=credentials))
            channel = connection.channel()

            queue_name = 'trans_req_{0}'.format(lang_pair)
            channel.queue_declare(queue=queue_name, durable=True)

            message = json.dumps(translation)
            channel.basic_publish(exchange='', routing_key=queue_name, body=message, 
                properties=pika.BasicProperties( delivery_mode = 2, # make message persistent
            ))
            connection.close() 

            return translation
        finally:
            self.mutex.release()

    def get_translation(self, user_id, translation_id):
        self.mutex.acquire()
        try:
            if not translation_id in self.translations:
                return {}
            
            translation = self.translations[translation_id]

            if user_id == "admin":
                return translation
            
            return translation if translation['owner'] == user_id else {}
        finally:
            self.mutex.release()

    def remove_translation(self, user_id, translation_id):
        if not translation_id in self.translations:
            return {}
        self.mutex.acquire()
        try:
            translation = self.translations[translation_id]
            if user_id in ["admin", translation['owner']]:
                del self.translations[translation_id]
                return translation
        finally:
            self.mutex.release()

        return {}

    def remove_expired_translations(self, expiration_delay):
        self.mutex.acquire()
        try:
            expired_translations = [k for (k,v) in self.translations.items() if self._is_expired(v, expiration_delay)]
            for trans_id in expired_translations:
                del self.translations[trans_id]
        finally:
            self.mutex.release()

    def _is_expired(self, translation, expiration_delay):
        delta = datetime.datetime.now() - datetime.datetime.strptime(translation['date_submission'], '%Y-%m-%d %H:%M:%S.%f')
        return (delta.seconds > expiration_delay)



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



