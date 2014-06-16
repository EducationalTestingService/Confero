# -*- coding: utf-8 -*-
from __future__ import division
"""
Created on Mon Feb 17 17:51:58 2014

@author: Sol
"""

import timeit
import  time
import webbrowser
import string
import Queue
import random
import os
import ujson
import copy

import psutil
import numpy as np

import tornado
from tornado import websocket
from tornado.web import RequestHandler
import tornado.ioloop
from tornado.ioloop import IOLoop
IOLoop.time = timeit.default_timer

from websockets import UIWebSocket, DataCollectionWebSocket, TrackBrowserWebSocket
from proc_util import startNodeWebStreamer, quiteSubprocs



def showSimpleWin32Dialog(message, caption):
    import win32gui
    win32gui.MessageBox(None, message, caption, 0)

def keyChainValue(cdict, *key_path):
    result = cdict.get(key_path[0])
    key_path = list(key_path[1:])
    for key in key_path:
        if not hasattr(result, 'get'):
            return result
        result = result.get(key)
    return result

#### Restful Handlers
class RestAppHandler(tornado.web.RequestHandler):
    server_app=None

class RestAppRpcHandler(RestAppHandler):
    def get(self,slug):
        path_tokens = slug.split('/')
        calls = {}
        skipped = []
        for pt in path_tokens:
            if pt and hasattr(self.server_app, pt):
                if pt.lower().endswith('quit') or pt.lower().endswith('quit/'):
                    print("Calling quit()")
                    self.server_app.quit()
                    return
                r = getattr(self.server_app, pt)()
                if r:
                    self.redirect(r)
                    return
                else:
                    calls.append(pt)
            else:
                skipped.append(pt)

        response = {"rpc_mapped": calls, 'rpc_notfound': skipped}
        self.write(response)


# Standard App Handlers

class BaseHandler(tornado.web.RequestHandler):
    pass
#    def get_current_user(self):
#        return self.get_secure_cookie("user")
#
#    def get_user_locale(self):
#        if hasattr(self.current_user, 'prefs'):
#            return self.current_user.prefs.get('locale', None)
        
class MainHandler(BaseHandler):
    #@tornado.web.authenticated
    def get(self):
        #name = tornado.escape.xhtml_escape(self.current_user)
        #
        appconfig = ControlFeedbackServer.app_config
        vshost = keyChainValue(appconfig, 'screen_capture',
                               'http_stream',
                               'host')
        rport = keyChainValue(appconfig,
                              'screen_capture',
                              'http_stream',
                              'read_port')
        vstream_scale = keyChainValue(appconfig,
                                      'screen_capture',
                                      'http_stream',
                                      'ffmpeg_settings',
                                      'scale')
        screen_cap_width, screen_cap_height = keyChainValue(appconfig,
                                  'screen_capture',
                                  'screen_resolution')
        screen_cap_width = int(screen_cap_width*vstream_scale)-int(screen_cap_width*vstream_scale)%2
        screen_cap_height = int(screen_cap_height*vstream_scale)- int(screen_cap_height*vstream_scale)%2

        self.render("index.html", video_server_host=vshost,
                    video_server_port=rport,
                    video_canvas_width=screen_cap_width,
                    video_canvas_height=screen_cap_height)

class ShutdownHandler(BaseHandler):
    def get(self):
        self.render("shutdown.html")

class ControlFeedbackServer(object):
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        #"cookie_secret": 'ICXQQRAC45OG',
        #"login_url": "/login",
        #"xsrf_cookies": True,
    }

    handlers=[
            (r"/", MainHandler),
            (r"/shutdown", ShutdownHandler),
            (r"/ui_websocket",UIWebSocket),
            (r"/data_websocket",DataCollectionWebSocket),
            (r"/track_client_ws",TrackBrowserWebSocket),
            (r"/rest_app/rpc/(.*)",RestAppRpcHandler),
            (r"/(apple-touch-icon\.png)", tornado.web.StaticFileHandler,
             dict(path=settings['static_path'])),
            ]

    get_cmd_queue = Queue.Queue()
    get_event_queue = Queue.Queue()
    web_sockets = dict()
    app_config = None
    def __init__(self, app_config, bonjour_service):
        self.webapp = tornado.web.Application(self.handlers, **self.settings)
        self.ssproxy = None
        self.bonjour_service = bonjour_service
        self.bonjour_service.checkForDaemonRequests()
        self._win_dialog_thread=None
        ControlFeedbackServer.app_config = app_config
        UIWebSocket.server_app_websockets = self.web_sockets
        DataCollectionWebSocket.server_app_websockets = self.web_sockets
        TrackBrowserWebSocket.server_app_websockets = self.web_sockets
        RestAppRpcHandler.server_app = self

    def serveForever(self):
        try: 
            self.ssproxy=startNodeWebStreamer(self.app_config)
            time.sleep(.5)
    
            # Start webapp server
            self.webapp.listen(8888)
            IOLoop.instance()

            def checkForDaemonRequests():
                if self.bonjour_service:
                    self.bonjour_service.checkForDaemonRequests()

            def register_timed_callback():
                self.bonjour_service.tornado_callback = tornado.ioloop.PeriodicCallback(checkForDaemonRequests,1000)
                self.bonjour_service.tornado_callback.start()

            IOLoop.instance().add_callback(register_timed_callback)

            autolaunch=keyChainValue(self.app_config, 'auto_launch_webapp')
            if autolaunch:            
                IOLoop.instance().add_timeout(self.getServerTime()+0.5,
                                          self.openWebAppGUI)
            else:
                def showWinDialog(server_ip,server_port):                
                    showSimpleWin32Dialog("Use the following URL to open the "
                                          "Confero View Interface:"
                                          "\nhttp://%s:%d/"%(server_ip, server_port),
                                          "Confero View Available")
    
                server_ip = keyChainValue(self.app_config,
                                       'http_address')
                server_port = keyChainValue(self.app_config,
                                       'http_port')
                import threading                       
                self._win_dialog_thread = threading.Timer(0.5, showWinDialog, args=[server_ip,server_port])
                self._win_dialog_thread.start()
                
                
            tornado.locale.load_translations(
                os.path.join(os.path.dirname(__file__), "translations"))
    
            IOLoop.instance().start()
        except Exception, e:
            print('WEBAPP_SERVER EXCETION:', e)
        else:
            print('WEBAPP_SERVER STOPPED OK')
            
            
    def quit(self):
        def _exit():
            if self.bonjour_service and self.bonjour_service.tornado_callback:
                self.bonjour_service.tornado_callback.stop()
                self.bonjour_service.tornado_callback = None

            print 'Quiting Tornado server.....'
            if self.ssproxy:
                quiteSubprocs([self.ssproxy,])
                self.ssproxy=None
            IOLoop.instance().stop()
            print 'Tornado server stopped OK.'
            
            if self._win_dialog_thread and self._win_dialog_thread.isAlive():
                self._win_dialog_thread=None
                quiteSubprocs([psutil.Process(),])

        self.bonjour_service.close()
        self.bonjour_service = None

        IOLoop.instance().add_timeout(self.getServerTime()+2.0,_exit)

    #def _terminate(self):

    @staticmethod
    def getServerTime():
        return IOLoop.time()

    @staticmethod
    def openWebAppGUI():
        appconfig = ControlFeedbackServer.app_config
        server_ip = keyChainValue(appconfig,
                               'http_address')
        server_port = keyChainValue(appconfig,
                               'http_port')
        autolaunch=keyChainValue(appconfig, 'auto_launch_webapp')
        if autolaunch:
            if autolaunch.lower() == 'default':
                webbrowser.open_new_tab('http://%s:%d/'%(server_ip,server_port))
            else:
                try:
                    webbrowser.get(autolaunch).open('http://%s:%d/'%(server_ip, server_port))
                except:
                    import traceback
                    print("Error while starting webbrowser.get() with value of", autolaunch)
                    traceback.print_exc()

    @staticmethod
    def openUserManual():
        appconfig = ControlFeedbackServer.app_config
        server_ip = keyChainValue(appconfig,
                               'http_address')
        server_port = keyChainValue(appconfig,
                               'http_port')
        webbrowser.open_new_tab('http://%s:%d/static/docs/index.html'%(server_ip,server_port))


    @staticmethod
    def id_generator(size=12, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def __del__(self):
        self.quit()

