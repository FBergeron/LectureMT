#!/usr/bin/env python3

activate_this = '/home/frederic/python_envs/web_LectureMT/bin/activate_this.py'
exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

from bottle import get, post, delete, route, request, response, run, template 
import configparser
import datetime
import json
from lecturemt.client import Client
import sys

config = configparser.ConfigParser()
config.read("config.ini")

@get('/say/<msg>') 
def say(msg): 
    return template('<b>{{username}}: {{msg}}</b>!', username=request.environ['REMOTE_USER'], msg=msg) 

@get('/api_version')
def get_api_version():
    return '1.0'

@get('/server_version')
def get_server_version():
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    req = '{"action": "get_server_version"}'
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])
    return resp

@get('/server_status')
def get_server_status():
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    req = '{"action": "get_server_status"}'
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])
    return resp

@get('/translation_queues')
def get_translations():
    return {}

@get('/translation_queue/<id>')
def get_translation_queue(id):
    return {}

@get('/translations')
def get_translations():
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    req = template('{"action": "get_translations", "user_id": "{{user_id}}"}', user_id=request.environ['REMOTE_USER'])
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])
    return resp

@post('/translation')
def add_translation():
    str_content = request.body.read().decode('utf-8')
    json_content = json.loads(str_content)

    if not "lang_source" in json_content or not "lang_target" in json_content or not "text_source" in json_content:
        response.status = 400
        return 'Invalid request.'

    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    str_template = '{"action": "add_translation", "user_id": "{{user_id}}", ' \
                   '"lang_source": "{{lang_source}}", "lang_target": "{{lang_target}}", ' \
                   '"text_source": "{{text_source}}", ' \
                   '"date_submission": "{{date_submission}}"}'
    req = template(str_template, user_id=request.environ['REMOTE_USER'], lang_source=json_content['lang_source'], lang_target=json_content['lang_target'], text_source=json_content['text_source'], date_submission=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])

    if resp == "{}":
        response.status = 400
        return 'Invalid request.'

    return resp

@get('/translation/<id>')
def get_translation(id):
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    str_template = '{"action": "get_translation", "user_id": "{{user_id}}", "translation_id": "{{trans_id}}"}'
    req = template(str_template, user_id=request.environ['REMOTE_USER'], trans_id=id)
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])
    return resp

@delete('/translation/<id>')
def delete_translation(id):
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    str_template = '{"action": "remove_translation", "user_id": "{{user_id}}", "translation_id": "{{trans_id}}"}'
    req = template(str_template, user_id=request.environ['REMOTE_USER'], trans_id=id)
    resp = {}
    try:
        resp = client.submit(req)
    except:
        resp = str(sys.exc_info()[0])
    return resp

run(server='cgi') 

