#!/usr/bin/env python3

activate_this = '/home/frederic/python_envs/web_LectureMT/bin/activate_this.py'
exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

from bottle import get, post, delete, route, request, run, template 
import configparser
from lecturemt.client import Client
import sys

config = configparser.ConfigParser()
config.read("config.ini")

translations = [1,2,3,4]

@get('/say/<msg>') 
def say(msg): 
    return template('<b>{{username}}: {{msg}}</b>!', username=request.environ['REMOTE_USER'], msg=msg) 

@get('/api_version')
def get_api_version():
    return '1.0'

@get('/server_version')
def get_server_version():
    client = Client(config['Server']['Host'], int(config['Server']['Port']))
    request = '{"type": "get_server_version"}'
    response = None
    try:
        response = client.submit(request)
    except:
        response = str(sys.exc_info()[0])
    return response

@get('/translations')
def get_translations():
    resp = '<ul>'
    for trans in translations:
        resp += '<li>{0}</li>'.format(trans)
    resp += '</ul>'
    return resp

@post('/translation/<id>')
def get_translation(id):
    translations.append(id)
    resp = '<ul>'
    for trans in translations:
        resp += '<li>{0}</li>'.format(trans)
    resp += '</ul>'
    return resp

@delete('/translation/<id>')
def delete_translation(id):
    translations.remove(int(id))
    resp = '<ul>'
    for trans in translations:
        resp += '<li>{0}</li>'.format(trans)
    resp += '</ul>'
    return resp

run(server='cgi') 

