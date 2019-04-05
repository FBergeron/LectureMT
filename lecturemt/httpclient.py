#!/usr/bin/env python3

from http.client import HTTPSConnection
from base64 import b64encode
import json
import logging

class LectureMT_Http_Client:

    max_attempts = 3

    def __init__(self, endpoint, username, password):
        self.server = endpoint[0:endpoint.index('/')]
        self.service_prefix = endpoint[endpoint.index('/'):]
        self.username = username
        self.password = password

    def get_translations(self):
        for i in range(0, LectureMT_Http_Client.max_attempts):
            logging.debug("get_translations attempt {0}".format(i))
            con = HTTPSConnection(self.server, timeout=10)
            try:
                usernameAndPassword = b64encode("{0}:{0}".format(self.username, self.password).encode('utf-8')).decode('ascii')
                headers = { 'Authorization': 'Basic {0}'.format(usernameAndPassword),
                            'Accept': 'application/json' }
                logging.debug("before request")
                x = con.request('GET', '{0}/translations'.format(self.service_prefix), headers=headers)
                logging.debug("after request x={0}".format(x))
                response = con.getresponse()
                logging.debug("get_translations before read")
                data = response.read()
                logging.debug("get_translations after read")
                if len(data) > 0:
                    json_data = json.loads(data.decode('utf-8'))
                    return json_data
            except Exception as ex:
                logging.debug("This error occurred: {0}\nTrying one more time...".format(ex))
            finally:
                con.close()
        logging.debug("Hmmm, data is empty after 3 attempts!!!")
        return {}

    def get_translation(self, trans_id):
        for i in range(0, LectureMT_Http_Client.max_attempts):
            logging.debug("get_translation attempt {0}".format(i))
            con = HTTPSConnection(self.server, timeout=10)
            try:
                usernameAndPassword = b64encode("{0}:{0}".format(self.username, self.password).encode('utf-8')).decode('ascii')
                headers = { 'Authorization': 'Basic {0}'.format(usernameAndPassword),
                            'Accept': 'application/json' }
                logging.debug("before request")
                x = con.request('GET', '{0}/translation/{1}'.format(self.service_prefix, trans_id), headers=headers)
                logging.debug("after request x={0}".format(x))
                response = con.getresponse()
                logging.debug("get_translation before read")
                data = response.read()
                logging.debug("get_translation after read")
                if len(data) > 0:
                    json_data = json.loads(data.decode('utf-8'))
                    return json_data
            except Exception as ex:
                logging.debug("This error occurred: {0}\nTrying one more time...".format(ex))
            finally:
                con.close()
        logging.debug("Hmmm, data is empty!!!")
        return {}

    def post_translation(self, lang_src, lang_tgt, text):
        post_data = { "lang_source": lang_src, "lang_target": lang_tgt, "text_source": text }
        str_post_data = json.dumps(post_data)
        for i in range(0, LectureMT_Http_Client.max_attempts):
            logging.debug("post_translation attempt {0}".format(i))
            con = HTTPSConnection(self.server, timeout=10)
            try:
                usernameAndPassword = b64encode("{0}:{0}".format(self.username, self.password).encode('utf-8')).decode('ascii')
                headers = { 'Authorization': 'Basic {0}'.format(usernameAndPassword), 'Accept': 'application/json' } 
                logging.debug("before request")
                x = con.request('POST', '{0}/translation'.format(self.service_prefix), str_post_data, headers=headers)
                logging.debug("after request x={0}".format(x))
                response = con.getresponse()
                logging.debug("post_data before read")
                data = response.read()
                logging.debug("post_data after read")
                if len(data) > 0:
                    json_data = json.loads(data.decode('utf-8'))
                    return json_data
            except Exception as ex:
                logging.debug("This error occurred: {0}\nTrying one more time...".format(ex))
            finally:
                con.close()

        logging.debug("Hmmm, data is empty!!!")
        return {}
        
    def delete_translation(self, trans_id):
        for i in range(0, LectureMT_Http_Client.max_attempts):
            logging.debug("delete_translation attempt {0}".format(i))
            con = HTTPSConnection(self.server, timeout=10)
            try:
                usernameAndPassword = b64encode("{0}:{0}".format(self.username, self.password).encode('utf-8')).decode('ascii')
                headers = { 'Authorization': 'Basic {0}'.format(usernameAndPassword), 
                            'Accept': 'application/json' }
                logging.debug("before request")
                x = con.request('DELETE', '{0}/translation/{1}'.format(self.service_prefix, trans_id), headers=headers)
                logging.debug("after request x={0}".format(x))
                response = con.getresponse()
                logging.debug("delete_translation before read")
                data = response.read()
                logging.debug("delete_translation after read")
                if len(data) > 0:
                    json_data = json.loads(data.decode('utf-8'))
                    return json_data
            except Exception as ex:
                logging.debug("This error occurred: {0}\nTrying one more time...".format(ex))
            finally:
                con.close()
        logging.debug("Hmmm, data is empty!!!")
        return {}

# def main():
#     import argparse
#     parser = argparse.ArgumentParser(description= "Send a request to the LectureMT Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#     parser.add_argument("--host", help = "Host of the server", default = 'localhost')
#     parser.add_argument("--port", help = "Port of the server", default = 46000)
#     parser.add_argument("--bufsize", help = "Size of the buffer", default = 4096)
#     args = parser.parse_args()
# 
#     client = Client(args.host, int(args.port), buffer_size=int(args.bufsize))
#     request = ''
#     for line in sys.stdin:
#         request += line
# 
#     response = client.submit(request)
#     print(response)
# 
# if __name__ == '__main__':
#     main()
# 
# 
#     
# server = 'lotus.kuee.kyoto-u.ac.jp'
# service_prefix = '/~frederic/LectureMT-dev/api/1.0/'
# username = 'fred'
# password = 'fred'
# 
# print('data={0}'.format(data))
# 
