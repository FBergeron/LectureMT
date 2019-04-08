#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""translator.py: Translation worker that will query any request found on the translation queue."""
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
import re
import subprocess
import sys
import threading
import time
import timeit

from translation_client import TensorFlowClient, OpenNMTClient, KNMTClient, TranslationClientFactory

log = None
 
logging.basicConfig()


class Worker(threading.Thread):

    def __init__(self, name, lang_pair, 
        rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password,
        translator_type, translator_host, translator_port, segmenter_host, segmenter_port, segmenter_command):
        threading.Thread.__init__(self)
        self.name = name
        self.lang_pair = lang_pair
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_username = rabbitmq_username
        self.rabbitmq_password = rabbitmq_password
        self.lang_source, self.lang_target = self.lang_pair.split("-")
        self.translator_type = translator_type
        self.translator_host = translator_host
        self.translator_port = translator_port
        self.segmenter_host = segmenter_host
        self.segmenter_port = segmenter_port
        self.segmenter_command = segmenter_command
        log.debug("Creating translation worker: name={0} lang_pair={1} translator={2}:{3} segmenter={4}:{5}".format(name, lang_pair, translator_host, translator_port, segmenter_host, segmenter_port))

    def run(self):
        while True:
            credentials = pika.PlainCredentials(self.rabbitmq_username, self.rabbitmq_password)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host, port=self.rabbitmq_port, credentials=credentials))
            channel = connection.channel()

            req_queue_name = 'trans_req_{0}'.format(self.lang_pair)
            channel.queue_declare(queue=req_queue_name, durable=True)

            def process_translation_request(ch, method, properties, body):
                try:
                    start_request = timeit.default_timer()
                    translation = json.loads(body) 
                    log.debug("T-{0}: translation: {1}".format(self.name, translation))
                    log.debug("T-{0}: text to translate: {1}".format(self.name, translation['text_source']))

                    if self.segmenter_command == '':
                        segmenter_output = translation['text_source']
                    else:
                        segmenter_cmd = re.sub(r'TEXT', translation['text_source'], self.segmenter_command)
                        segmenter_cmd = re.sub(r'HOST', self.segmenter_host, segmenter_cmd)
                        segmenter_cmd = re.sub(r'PORT', self.segmenter_port, segmenter_cmd)
                        log.debug("T-{0}: cmd={1}".format(self.name, segmenter_cmd))

                        segmenter_output = subprocess.check_output(segmenter_cmd, shell=True, universal_newlines=True)
                        segmenter_output = segmenter_output.strip()
                        log.debug("T-{0}: segmenter_output={1}".format(self.name, segmenter_output))
                    
                    client = TranslationClientFactory.create("{0}Client".format(self.translator_type), self.translator_host, int(self.translator_port), log)
                    translated_text = client.submit(segmenter_output)

                    log.debug("trans_req_id={0} translated_text={1}".format(translation['id'], translated_text))

                    resp_queue_name = 'trans_resp_{0}'.format(self.lang_pair)
                    channel.queue_declare(queue=resp_queue_name, durable=True)

                    message = json.dumps({'id': translation['id'], 'translated_text': translated_text})
                    channel.basic_publish(exchange='', routing_key=resp_queue_name, body=message, 
                        properties=pika.BasicProperties( delivery_mode = 2, # make message persistent
                    ))

                    processing_time = timeit.default_timer() - start_request
                    log.debug("Finish processing request {0} by translation worker {1} in {2} s.".format(translation['id'], self.name, processing_time)) 
                except:
                    log.debug("Unexpected error: {0}\n".format(sys.exc_info()[0]))
                ch.basic_ack(delivery_tag = method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(req_queue_name, process_translation_request)

            channel.start_consuming()

def do_start_worker(config_file, worker_config_file, worker_logging_config_file):
    if worker_logging_config_file:
        logging.config.fileConfig(worker_logging_config_file)
    global log
    log = logging.getLogger("default")

    config = configparser.ConfigParser()
    config.read(config_file)

    worker_config = configparser.ConfigParser()
    worker_config.read(worker_config_file)

    worker = Worker(worker_config['Translation']['Id'], worker_config['Translation']['LanguagePair'], 
        config['RabbitMQ']['Host'], config['RabbitMQ']['Port'], config['RabbitMQ']['Username'], config['RabbitMQ']['Password'],
        worker_config['Translation']['Type'], 
        worker_config['Translation']['Host'], worker_config['Translation']['Port'],
        worker_config['Segmentation']['Host'], worker_config['Segmentation']['Port'],
        worker_config['Segmentation']['Command'])
    worker.start()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python lecturemt/translator.py worker_conf_file worker_logging_conf_file")
        print("Example: python lecturemt/translator.py conf/worker_ja-en_1.ini conf/worker_ja-en_1_logging.ini")
        exit(1)
 
    worker_config = sys.argv[1]
    worker_log_config = sys.argv[2]
    do_start_worker("conf/config.ini", worker_config, worker_log_config)
