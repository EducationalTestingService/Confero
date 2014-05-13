# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 23:43:45 2014

@author: Sol
"""
from webserver import ControlFeedbackServer
from psychopy.iohub import Loader, load
import os
if __name__ == "__main__":
    app_config = load(file(os.path.abspath(r'..\app_config.yaml'), 'r'),
                        Loader=Loader)

    server = ControlFeedbackServer(app_config)
    server.serveForever()