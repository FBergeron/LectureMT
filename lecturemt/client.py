#!/usr/bin/env python3
"""client.py: Client to communicate with the LectureMT server."""
__author__ = "Frederic Bergeron"
__license__ = "undecided"
__version__ = "1.0"
__email__ = "bergeron@nlp.ist.i.kyoto-u.ac.jp"
__status__ = "Development"

import socket
import sys

EOM = "==== EOM ===="

class Client:

    def __init__(self, host='localhost', port=46000, buffer_size=4096):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size

    def submit(self, text):
        text += EOM
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        s.send(text.encode('utf-8'))
        response = ''
        try: 
            while True:
                try:
                    resp = s.recv(self.buffer_size)
                    if resp:
                        response += resp.decode('utf-8')
                    else:
                        break
                except:
                    break
        finally:
            s.close()
        return response

def main():
    import argparse
    parser = argparse.ArgumentParser(description= "Send a request to the LectureMT Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--host", help = "Host of the server", default = 'localhost')
    parser.add_argument("--port", help = "Port of the server", default = 46000)
    parser.add_argument("--bufsize", help = "Size of the buffer", default = 4096)
    args = parser.parse_args()

    client = Client(args.host, int(args.port), buffer_size=int(args.bufsize))
    request = ''
    for line in sys.stdin:
        request += line

    response = client.submit(request)
    print(response)

if __name__ == '__main__':
    main()
