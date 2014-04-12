# -*- coding: utf-8 -*-
from __future__ import division
"""
Created on Mon Feb 17 17:51:58 2014

@author: Sol
"""

import tornado
from tornado import websocket
from tornado.web import RequestHandler
import tornado.ioloop
from tornado.ioloop import IOLoop
import psutil

from proc_util import startSubProcess,startNodeWebStreamer,quiteSubprocs

import timeit, time
IOLoop.time = timeit.default_timer

import webbrowser
import string, Queue
import random
import os
import ujson
from psychopy.iohub import EventConstants, EyeTrackerConstants

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

        response={"rpc_mapped":calls,'rpc_notfound':skipped}
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
#
## Websocket server for sending / receiving msg's from Experiment Feedback Monitor
#
class WebSocket(websocket.WebSocketHandler):
    server_app_websockets = None
    ws_key = None
    def open(self):
        self.set_nodelay(True)
        self.server_app_websockets[self.ws_key] = self

    def on_message(self, message):
        print("{0} TO HANDLE: ".format(self.__class__.__name__), ujson.loads(message))

    def on_pong(self, data):
        #Invoked when the response to a ping frame is received.
        try:
            websocket.WebSocketHandler.on_pong(self,data)
        except tornado.websocket.WebSocketClosedError, e:
            try:
                del self.server_app_websockets[self.ws_key]
            except:
                pass
            raise e

    def on_close(self):
        print "\n** {0} closed.\n".format(self.__class__.__name__)
        try:
            del self.server_app_websockets[self.ws_key]
        except:
            pass

class UIWebSocket(WebSocket):
    ws_key = "WEB_UI"
    def open(self):
        WebSocket.open(self)
        dc_ws = self.server_app_websockets.get('DATA_COLLECTION')
        if not dc_ws:
            pass#self.write_message(ujson.encode([{'msg_type':'UI_GROWL', 'type':'info','text':'No Data Collection Service Connected.'},]))
        else:
            #self.write_message(ujson.encode([{'msg_type':'UI_GROWL', 'type':'success','text':'Data Collection Service Already Running.'},]))
            # send the known list of experiment names on the data collection
            # service..
            self.write_message(ujson.encode([dc_ws.data_collection_state['experiment_names_msg'],]))
    def on_message(self, message):
        dc_sw = self.server_app_websockets.get("DATA_COLLECTION")
        if dc_sw:
            msg_dict = ujson.loads(message)

            msg_type = msg_dict.get('msg_type', 'UNKNOWN')
            if msg_type is 'UNKNOWN':
                msg_type = msg_dict.get('type', 'UNKNOWN')

            if msg_type == 'EXPERIMENT_SELECTED':
                dc_sw.data_collection_state['active_experiment'] = msg_dict.get('name')
            #print "SENDING MSG TO DC:'",msg_dict
            if msg_type is not 'UNKNOWN':
                dc_sw.write_message(message)

        else:
            print("")
            print("WARNING: Data Collection Web Socket is not Running. Msg not sent. Is the Data Collection application running?")
            print("")

class DataCollectionWebSocket(WebSocket):
    ws_key = "DATA_COLLECTION"
    def open(self):
        WebSocket.open(self)
        self.data_collection_state = dict(experiment_names_msg=None,
                                          server_computer=dict(cpu_usage_all=[None, r' %'],memory_usage_all=[None, r' %']))

    def on_message(self, message):
        msg_list = ujson.loads(message)

        to_send=[]
        for m in msg_list:
            msg_type = m.get('msg_type', 'UNKNOWN')
            if msg_type == 'EXP_FOLDER_LIST':
                self.data_collection_state['experiment_names_msg'] = m
            elif msg_type =='DataCollection':
                if m.get('input_computer'):
                    self.data_collection_state['server_computer']['cpu_usage_all'][0] = float(psutil.cpu_percent(0.0))
                    self.data_collection_state['server_computer']["memory_usage_all"][0] = psutil.virtual_memory().percent
                    m['server_computer'] = self.data_collection_state['server_computer']
                elif m.get('eyetracker'):
                    m['eyetracker'] = self.processEyeTrackerData(m.get('eyetracker'))

            if msg_type is not 'UNKNOWN':
                to_send.append(m)

        if len(to_send) > 0:
            ws_ui = self.server_app_websockets.get("WEB_UI")
            if ws_ui:
                ws_ui.write_message(ujson.dumps(to_send))

    def processEyeTrackerData(self, dev_data):
        current_et_data = self.data_collection_state.get('eyetracker')
        if current_et_data is None:
            current_et_data = dev_data
            new_fields = {
                "eye_sample_type": [None, ''],
                "status": [None, ''],
                "time": [None, ' sec'],    # time of last sample received
                "left_eye_status": [None, ''],
                "right_eye_status": [None, ''],
                "left_eye_gaze": [None, ''],
                "right_eye_gaze": [None, ''],
                "left_eye_pos": [None, ''],
                "right_eye_pos": [None, ''],
                "left_eye_pupil": [None, ''],
                "right_eye_pupil": [None, ''],
                "left_eye_noise": [None, ''],
                "right_eye_noise": [None, '']}
            new_fields.setdefault('samples', [None, None])
            current_et_data.update(new_fields)
            self.data_collection_state['eyetracker'] = current_et_data

        new_samples = dev_data.get('samples')[0]
        if new_samples:
            latest_sample_event = dev_data['samples'][0][-1]
            sample_type = dev_data['eye_sample_type'][0]
            if sample_type is None:
                if latest_sample_event['type'] == EventConstants.BINOCULAR_EYE_SAMPLE:
                    sample_type = "Binocular"
                else:
                    sample_type = "Monocular"
            current_et_data['eye_sample_type'][0] = sample_type
            current_et_data["time"][0] = latest_sample_event['time']
            current_et_data["status"][0] = latest_sample_event['status']

        print('got ET data:',dev_data)
        return current_et_data

    def MOVE_TO_WEBSERVER_CODE(self, dev_data, latest_sample_event, sample_type):
        # Update eye tracker left and right eye data fields based on
        # eye sample type and eye being tracked
        #
        tracking_eyes = dev_data['track_eyes'][0]
        #print("tracking_eyes:", tracking_eyes,sample_type)
        et_left_eye_status = "TRACKING"
        et_right_eye_status = "TRACKING"
        if latest_sample_event['status'] in [2, 22]:
            et_left_eye_status = "MISSING"
        if latest_sample_event['status'] in [20, 22]:
            et_right_eye_status = "MISSING"

        # helpers
        def clearLeftEyeInfo(dev_data):
            dev_data["left_eye_status"][0] = None
            dev_data["left_eye_gaze"][0] = None
            dev_data["left_eye_pos"][0] = None
            dev_data["left_eye_pupil"][0] = None
            dev_data["left_eye_noise"][0] = None
        def clearRightEyeInfo(dev_data):
            dev_data["right_eye_status"][0] = None
            dev_data["right_eye_gaze"][0] = None
            dev_data["right_eye_pos"][0] = None
            dev_data["right_eye_pupil"][0] = None
            dev_data["right_eye_noise"][0] = None
        def setLeftEyeInfo(dev_data, status, sample):
            dev_data["left_eye_status"][0] = status
            dev_data["left_eye_gaze"][0] = sample['left_gaze_x'], sample['left_gaze_y']
            dev_data["left_eye_pos"][0] = sample['left_eye_cam_x'], sample['left_eye_cam_y'], sample['left_eye_cam_z']
            dev_data["left_eye_pupil"][0] = sample['left_pupil_measure1']
            dev_data["left_eye_noise"][0] = 'TBC'
        def setRightEyeInfo(dev_data, status, sample):
            dev_data["right_eye_status"][0] = status
            dev_data["right_eye_gaze"][0] = sample['right_gaze_x'], sample['right_gaze_y']
            dev_data["right_eye_pos"][0] = sample['right_eye_cam_x'], sample['right_eye_cam_y'], sample['right_eye_cam_z']
            dev_data["right_eye_pupil"][0] = sample['right_pupil_measure1']
            dev_data["right_eye_noise"][0] = 'TBC'

        if sample_type == "Binocular":
            if tracking_eyes and tracking_eyes <= EyeTrackerConstants.MONOCULAR:
                # Monocular data in a binocular sample type
                if tracking_eyes == EyeTrackerConstants.LEFT_EYE:
                    # access only left eye fields
                    setLeftEyeInfo(dev_data, et_left_eye_status, latest_sample_event)
                    # Clear out right eye related data fields
                    # Web app could use et_right_eye_status
                    # to test if right eye data should be even displayed
                    # based on a null value.
                    clearRightEyeInfo(dev_data)
                else:
                    # any other monoc. eye type can be assumed
                    # to be the right eye
                    setRightEyeInfo(dev_data, et_right_eye_status, latest_sample_event)
                    # Clear out left eye related data fields
                    # Web app could use et_left_eye_status
                    # to test if right eye data should be even displayed
                    # based on a null value.
                    clearLeftEyeInfo(dev_data)

            elif tracking_eyes or tracking_eyes <= EyeTrackerConstants.BINOCULAR:
                # Binocular data in a binocular sample type
                setRightEyeInfo(dev_data, et_right_eye_status, latest_sample_event)
                setLeftEyeInfo(dev_data, et_left_eye_status, latest_sample_event)

        else:
            if tracking_eyes and tracking_eyes == EyeTrackerConstants.LEFT_EYE:
                # access only left eye fields
                setLeftEyeInfo(dev_data, et_left_eye_status, latest_sample_event)
                #clear out right eye related data fields
                clearRightEyeInfo(dev_data)
            else:
                # any other monoc. eye type can be assumed
                # to be the right eye
                setRightEyeInfo(dev_data, et_right_eye_status, latest_sample_event)
                #clear out left eye related data fields
                clearLeftEyeInfo(dev_data)

###############################################################################

class ControlFeedbackServer(object):
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        #"cookie_secret": 'ICXQQRAC45OG',
        #"login_url": "/login",
        #"xsrf_cookies": True,
    }

    handlers=[
            (r"/", MainHandler),
            #(r"/login", LoginHandler),
            #(r"/login", LoginHandler),
            (r"/shutdown", ShutdownHandler),
            #(r"/sandbox/(.*)",SandboxHandler),
            (r"/ui_websocket",UIWebSocket),
            (r"/data_websocket",DataCollectionWebSocket),
            (r"/rest_app/rpc/(.*)",RestAppRpcHandler),
            (r"/(apple-touch-icon\.png)", tornado.web.StaticFileHandler,
             dict(path=settings['static_path'])),
            ]

    get_cmd_queue = Queue.Queue()
    get_event_queue = Queue.Queue()
    web_sockets = dict()
    app_config = None
    def __init__(self, app_config):
        self.webapp = tornado.web.Application(self.handlers, **self.settings)
        self.ssproxy = None
        self._win_dialog_thread=None
        ControlFeedbackServer.app_config = app_config
        UIWebSocket.server_app_websockets = self.web_sockets
        DataCollectionWebSocket.server_app_websockets = self.web_sockets
        RestAppRpcHandler.server_app = self

    def serveForever(self):
        try: 
            self.ssproxy=startNodeWebStreamer(self.app_config)
            time.sleep(.5)
    
            # Start webapp server
            self.webapp.listen(8888)
            IOLoop.instance()
            autolaunch=keyChainValue(self.app_config, 'auto_launch_webapp')
            if autolaunch:            
                IOLoop.instance().add_timeout(self.getServerTime()+0.5,
                                          self.openWebAppGUI)
            else:
                def showWinDialog(server_ip,server_port):                
                    showSimpleWin32Dialog("Use the following URL to open the "
                                          "UserMonitor Web Interface:"
                                          "\nhttp://%s:%d/"%(server_ip, server_port),
                                          "UserMonitor Web UI Available")
    
                server_ip = keyChainValue(self.app_config,
                                       'experimenter_server',
                                       'address')
                server_port = keyChainValue(self.app_config,
                                       'experimenter_server',
                                       'port')
                import threading                       
                self._win_dialog_thread = threading.Timer(0.5, showWinDialog,args=[server_ip,server_port])
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
            print 'Quiting Tornado server.....'
            if self.ssproxy:
                quiteSubprocs([self.ssproxy,])
                self.ssproxy=None
            IOLoop.instance().stop()
            print 'Tornado server stopped OK.'
            
            if self._win_dialog_thread and self._win_dialog_thread.isAlive():
                self._win_dialog_thread=None
                quiteSubprocs([psutil.Process(),])
            
        IOLoop.instance().add_timeout(self.getServerTime()+2.0,_exit)

    #def _terminate(self):

    @staticmethod
    def getServerTime():
        return IOLoop.time()

    @staticmethod
    def openWebAppGUI():
        appconfig = ControlFeedbackServer.app_config
        server_ip = keyChainValue(appconfig,
                               'experimenter_server',
                               'address')
        server_port = keyChainValue(appconfig,
                               'experimenter_server',
                               'port')
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
    def id_generator(size=12, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def __del__(self):
        self.quit()

