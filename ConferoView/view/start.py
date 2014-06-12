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

    bonsvc = ConferoBonjourService()
    view_server_info = findConferoViewServer()

    app_config['http_address'] = view_server_info['ip']
    app_config['http_port'] = view_server_info['port']
    app_config.get('screen_capture')['http_stream']['host'] = view_server_info['ip']

    print
    print "Confero Server Started. "
    print "Registered Confero Server with Bonjour for ip", view_server_info['ip']
    print
    server = ControlFeedbackServer(app_config, bonsvc)
    server.serveForever()