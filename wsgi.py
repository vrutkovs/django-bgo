#!/usr/bin/env python
import os
import imp
import sys

sys.path.append(os.path.join('wsgi'))
sys.path.append(os.path.join('wsgi', 'bgo'))
sys.path.append(os.path.join('wsgi', 'bgo', 'bgo'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'bgo.settings'

if __name__ == '__main__':
    ip = 'localhost'
    port = 8051
    zapp = imp.load_source('application', 'wsgi/application')

    from wsgiref.simple_server import make_server
    httpd = make_server(ip, port, zapp.application)
    httpd.serve_forever()
