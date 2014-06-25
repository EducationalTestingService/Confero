# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 23:43:45 2014

@author: Sol
"""
from register_server import ConferoBonjourService
from webserver import ControlFeedbackServer
from psychopy.iohub import Loader, load
from findserver import findConferoViewServer
import os
if __name__ == "__main__":
    app_config = load(file(os.path.abspath(r'..\settings\app_config.yaml'), 'r'),
                        Loader=Loader)

    print
    print "Confero Server Starting... "
    bonsvc = None
    server_ip = app_config.get('http_address',None)
    if server_ip.lower() in [None, 'default', 'auto', 'bonjour']:
        bonsvc = ConferoBonjourService()
        view_server_info = findConferoViewServer()

        app_config['http_address'] = view_server_info['ip']
        app_config['http_port'] = view_server_info['port']

        print "Registered Confero Server with Bonjour for ip", app_config['http_address'],' : ',app_config['http_port']
        print
    else:
        print " Confero Server being started with app_config IP settings:", app_config['http_address'],' : ',app_config['http_port']
        print
    server = ControlFeedbackServer(app_config, bonsvc)
    server.serveForever()