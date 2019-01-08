#!/usr/bin/env python3

activate_this = '/home/frederic/python_envs/web_LectureMT/bin/activate_this.py'
exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

from bottle import get, post, delete, route, run, template 
import configparser
from lecturemt.client import Client
import sys

config = configparser.ConfigParser()
config.read("config.ini")

translations = [1,2,3,4]


@get('/hello/<name>') 
def index(name): 
    return template('<b>Hello {{name}}</b>!', name=name) 

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

@get('/things')
def get_things():
    my_dict = {1: 'apple', 2: 'ball'}
    return my_dict

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

