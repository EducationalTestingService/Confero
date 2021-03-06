# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

import os
from functools import partial
import subprocess, psutil, ujson,copy
from collections import deque
import socket
from websocket import WebSocketConnectionClosedException
from psychopy import visual, core
from psychopy.clock import CountdownTimer
from psychopy.data import TrialHandler
from psychopy.iohub.client import ioHubExperimentRuntime
from psychopy.iohub import EventConstants, MouseConstants, Computer, EyeTrackerConstants
from psychopy.iohub.util import NumPyRingBuffer
getTime=core.getTime
from util import PriorityQueue, createPath
import messages


from psychopy.iohub import ioHubConnection
from psychopy.iohub import TimeTrigger, DeviceEventTrigger,Loader, load
from psychopy.iohub import TargetStim, PositionGrid, ValidationProcedure

import time
import numpy as np

class DataCollectionRuntime(ioHubExperimentRuntime):
    script_dir=os.path.dirname(__file__)
    results_root_folder = None
    active_exp_name=None
    cpu_usage_buffer = NumPyRingBuffer(3)
    view_server_ip = None
    def run(self, *args):
        self._app_config_file_path, self._io_config_file_path = args
        appcfg=self.getConfiguration()
        self.command_queue=PriorityQueue()
        # dict of last events returned by hub for each device event type
        self.events_by_type = dict()
        self.stats_info_updates = dict()
        self.device_info_update_funcs=dict()
        self.device_monitor_countdowns = dict()
        self.recording_devices={}
        self.device_info_stats={}
        self.recording_condition_variables=None
        self.recording_vars = None
        self.hub.sendMessageEvent("Started New Experiment Session: %s"%(self.getSessionMetaData().get('code','CODE_MISSING')),"data_monitoring")
        self._quit_char = self.keyChainValue(appcfg, 'manual_termination',
                                             'keyboard', 'key')
        self._quit_modifier = self.keyChainValue(appcfg, 'manual_termination',
                                                 'keyboard', 'modifier')    
        # Setup devices
        self.computer=self.devices.computer
        self.keyboard = self.hub.getDevice('keyboard')
        self.display = self.devices.display
        self.mouse = self.hub.getDevice('mouse')
        self.eyetracker = self.hub.getDevice('tracker')

        self._device_event_filter=dict()
        # Add filters if needed:
        event_filters = self.keyChainValue(appcfg, 'event_filters')
        if event_filters:
            for device_name, event_filter_config in event_filters.items():
                if self.hub.getDevice(device_name) is None:
                    continue
                filter_file_path = event_filter_config.get('file_path', '.')
                filter_class_name = event_filter_config.get('class_name')
                filtered_events_only = event_filter_config.get('stream_filtered_only', False)
                filter_kwargs = event_filter_config.get('params', {})
                filter_kwargs['display_device'] = dict(pixel_res=self.display.getPixelResolution(), mm_size=self.display.getPhysicalDimensions(), eye_distance=self.display.getDefaultEyeDistance())

                et_config=self.eyetracker.getConfiguration()
                runtime_settings=et_config.get('runtime_settings')
                if runtime_settings:
                    srate=runtime_settings.get('sampling_rate')
                    if srate:
                        filter_kwargs['sampling_rate'] = float(srate)
                    else:
                        raise ValueError("sampling_rate could not be read!")

                filter_id = self.hub.getDevice(device_name).addFilter(filter_file_path, filter_class_name, filter_kwargs)
                #print("ADDED FILTER: ", filter_id)
                if filter_id >= 0:
                    if filtered_events_only is True:
                        self._device_event_filter[device_name] = filter_id
                else:
                    print("ERROR: Filter not installed:",filter_file_path,filter_class_name)
        #--

        self.createDeviceStatsMessageDicts()

        # Create folder that will hold data and log files for the current
        # session. 
        # Note: This does not include the ioHub Data Store hdf5 file, which
        # is saved in the same directory as this script.
        if not self.createSessionResultsFolder():
            self.close()
            return
        #--

        # Start the application processing / event loop
        # This method does not return until the application is quiting.        
        return_value=self.runEventLoop()

        # Close any application resources as needed and quit the ffmpeg
        # subprocess.
        self.close()
        return return_value,None

    def resetDataCollectionStats(self):
        self.events_by_type = dict()
        self.stats_info_updates = dict()
        self.device_info_update_funcs=dict()
        self.device_monitor_countdowns = dict()
        self.recording_devices={}
        self.device_info_stats={}
        self.cpu_usage_buffer.clear()

    def createDeviceStatsMessageDicts(self):
        display_info=copy.deepcopy(messages.display)
        self.device_info_stats['display']=display_info

        keyboard_info=copy.deepcopy(messages.keyboard)
        self.device_info_stats['keyboard']=keyboard_info

        mouse_info=copy.deepcopy(messages.mouse)
        self.device_info_stats['mouse']=mouse_info
        
        if self.eyetracker:
            tracker_info=copy.deepcopy(messages.eyetracker)
            self.device_info_stats['eyetracker']=tracker_info
            et_config=self.eyetracker.getConfiguration()
            tracker_info["model"][0] = u"{0} : {1}".format(
                                                et_config.get('manufacturer_name','-'),
                                                et_config.get('model_name','-'))
                                                
            tracker_info["sampling_rate"][0] = 'N/A'
            tracker_info["track_eyes"][0] = 'N/A'
            runtime_settings=et_config.get('runtime_settings')
            if runtime_settings:
                srate=runtime_settings.get('sampling_rate')
                track_eyes=runtime_settings.get('track_eyes')                
                if srate:
                    tracker_info["sampling_rate"][0] =  srate
                if track_eyes:
                    tracker_info["track_eyes"][0] =  track_eyes

        session_info=copy.deepcopy(messages.experiment_session)
        self.device_info_stats['experiment_session']=session_info
        self.stats_info_updates['experiment_session'] = session_info
        session_info['code'][0]=self.getSessionMetaData().get('code')
        session_info['start_time'][0]=self.computer.getTime()
        session_info['experiment_name'][0] = self.active_exp_name
        display_info['resolution'][0] = self.display.getPixelResolution()
        display_unit_type = self.display.getCoordinateType()
        display_info['resolution'][1] = display_unit_type
        self.stats_info_updates['display'] = display_info

        input_computer_info=copy.deepcopy(messages.input_computer)
        self.device_info_stats['input_computer']=input_computer_info
        self.updateInputComputerStats()
        cntimer = CountdownTimer(input_computer_info.get('countdown_time', [0.01,''])[0])
        #cntimer._label = "Computer Info"
        self.device_monitor_countdowns['input_computer'] = cntimer
        self.device_info_update_funcs['input_computer'] = self.updateInputComputerStats

        if self.keyboard:
            self.recording_devices['keyboard']=[self.keyboard, keyboard_info]
            self.device_info_update_funcs['keyboard'] = self.updateKeyboardMsgInfo
        if self.mouse:
            self.recording_devices['mouse']=[self.mouse, mouse_info]
            self.device_info_update_funcs['mouse'] = self.updateMouseMsgInfo
            mouse_info['position'][1] = display_unit_type
        if self.eyetracker:
            self.recording_devices['eyetracker']=[self.eyetracker, tracker_info]
            self.device_info_update_funcs['eyetracker'] = self.updateEyetrackerMsgInfo
            tracker_info['average_gaze_position'][1] = display_unit_type

    def runEventLoop(self):
        event_loop_rate = self.getConfiguration().get('event_loop_rate', 0.001)
        run = True
        gtime=self.computer.getTime
        self.hub.clearEvents('all')
        try:
            while run:
                # Send iohub events to MonitoringServer
                self.handleMsgTx()

                cmd = self.handleMsgRx()
                if cmd:
                    run=False
                    return cmd
                        
                # Check for App exit
                if self.checkForTerminateEvent():
                    print("SESSION CLOSED BY COLLECTION APP TERMINATE EVENT.")
                    run = False
                    break
                # check for any commands that need to be handled
                self.handleCommands()
               
                core.wait(event_loop_rate, 0.002)
        except Exception, e:
            print("Run Loop Exception: ", e)
            import traceback
            traceback.print_exc()
            raise e
            
    def handleCommands(self):
        while len(self.command_queue):
            task,args=self.command_queue.pop()
            task(*args)

    @classmethod
    def getActiveExperimentNames(cls,inactiveexptoken):
        _, exp_dirs, _ = next(os.walk(cls.results_root_folder))

        exp_names_session_counts = []
        if inactiveexptoken:
            exp_dirs = [exp_name for exp_name in exp_dirs if exp_name.find(inactiveexptoken) == -1]

        for exp_name in exp_dirs:
            _, session_dirs, _ = next(os.walk(os.path.join(cls.results_root_folder,exp_name)))
            exp_names_session_counts.append((exp_name, session_dirs))

        return exp_names_session_counts
    
    # Start the ffmpeg screen capturing sub process
    def beginScreenCaptureStream(self):
        try:
            self._ffmpeg_proc=self.startScreenCaptureStream()
            return True
        except Exception, e:
            print ('ERROR: startScreenCaptureStream Failed. Exiting App.')
            self.close()
            return False

    def createSessionResultsFolder(self):
        # Create folder for saved video file(s), etc.
        session_code = self.device_info_stats['experiment_session']['code'][0]
        try:
            self._session_results_folder=os.path.join(self.results_root_folder,self.active_exp_name,session_code)
            createPath(self._session_results_folder)
            #print("CREATED _session_results_folder: "+self._session_results_folder)
            import shutil
            shutil.copy(self._app_config_file_path, self._session_results_folder)
            shutil.copy(self._io_config_file_path, self._session_results_folder)

        except Exception, e:
            print('ERROR: Folder creation failed [{0}]. Exiting App.'.format(
                                                self._session_results_folder))
            return False
        
        return True

    def updateLocalEventsCache(self, events):
        for e in events:
            self.events_by_type.setdefault(e['type'],
                                           deque(maxlen=128)).appendleft(e)



    def updateInputComputerStats(self,):
        self.cpu_usage_buffer.append(psutil.cpu_percent(0.0))
        input_computer = self.device_info_stats['input_computer']
        input_computer['cpu_usage_all'][0] = float(self.cpu_usage_buffer.mean())
        input_computer["memory_usage_all"][0] = psutil.virtual_memory().percent
        return input_computer


    def updateMouseMsgInfo(self):
        dev_data = self.device_info_stats['mouse']
        kwargs = dict(asType='dict')
        filter_device_events = self._device_event_filter.get('mouse')
        if filter_device_events is not None:
           kwargs['filter_id'] = filter_device_events
        new_events = self.mouse.getEvents(**kwargs)
        self.updateLocalEventsCache(new_events)

        if dev_data["events"][0] is None and (new_events is None or len(new_events) == 0):
            dev_data["events"][0] = []
            dev_data["type"][0] = "N/A"
            dev_data['last_event_time'][0] = 0.0
            dev_data["position"][0] = self.mouse.getPosition()
            dev_data["buttons"][0] = list()
            dev_data["scroll"][0] = 0
            dev_data["modifiers"][0] = list()
            dev_data["window_id"][0] = 0
            return dev_data

        if new_events:
            dev_data["events"][0] = new_events
            mevent = dev_data["events"][0][-1]
            dev_data["type"][0] = EventConstants.getName(mevent["type"])
            dev_data['last_event_time'][0] = mevent['time']
            dev_data["position"][0] = mevent['x_position'], mevent['y_position']
            buttons=[]
            ebuttons=mevent['pressed_buttons']
            if ebuttons > 0:
                if MouseConstants.MOUSE_BUTTON_LEFT & ebuttons > 0:
                    buttons.append('LEFT')
                if MouseConstants.MOUSE_BUTTON_RIGHT & ebuttons > 0:
                    buttons.append('RIGHT')
                if MouseConstants.MOUSE_BUTTON_MIDDLE & ebuttons > 0:
                    buttons.append('MIDDLE')
            dev_data["buttons"][0] = buttons
            dev_data["scroll"][0] = mevent['scroll_x']
            dev_data["modifiers"][0] = mevent['modifiers']
            dev_data["window_id"][0] = mevent['window_id']
            return dev_data

    def updateKeyboardMsgInfo(self):
        dev_data = self.device_info_stats['keyboard']
        kwargs = dict(asType='dict')
        filter_device_events = self._device_event_filter.get('keyboard')
        if filter_device_events is not None:
           kwargs['filter_id'] = filter_device_events
        new_events = self.keyboard.getEvents(**kwargs)
        self.updateLocalEventsCache(new_events)

        if dev_data["events"][0] is None and (new_events is None or len(new_events) == 0):
            dev_data["type"][0] = "N/A"
            dev_data["auto_repeated"][0] = 0
            dev_data["scan_code"][0] = 0
            dev_data["key_id"][0] = 0
            dev_data["ucode"][0] = 0
            dev_data['last_event_time'][0] = 0.0
            dev_data["key"][0] = ''
            dev_data["modifiers"][0] = []
            dev_data["window_id"][0] = 0
            dev_data["events"][0] = []
            return dev_data

        if new_events:
            dev_data["events"][0]=new_events
            mevent = dev_data["events"][0][-1]
            dev_data["type"][0] = EventConstants.getName(mevent["type"])
            dev_data["auto_repeated"][0] = mevent["auto_repeated"]
            dev_data["scan_code"][0] = mevent["scan_code"]
            dev_data["key_id"][0] = mevent["key_id"]
            dev_data["ucode"][0] = mevent["ucode"]
            dev_data['last_event_time'][0] = mevent['time']
            dev_data["key"][0] = mevent["key"]
            dev_data["modifiers"][0] = mevent["modifiers"]
            dev_data["window_id"][0] = mevent["window_id"]
            return dev_data

    def updateEyetrackerMsgInfo(self):
        if self.eyetracker is None:
            return
        #print ('updateEyetrackerMsgInfo:', getTime()*1000.0)
        dev_data = self.device_info_stats['eyetracker']

        gp = self.eyetracker.getLastGazePosition()
        if isinstance(gp, (tuple, list)):
            gp = int(gp[0]), int(gp[1])
        else:
            gp = None

        dev_data_update = False
        if dev_data["average_gaze_position"][0] != gp:            
            dev_data["average_gaze_position"][0] = gp
            dev_data_update = True

        kwargs = dict(asType='dict')
        filter_device_events = self._device_event_filter.get('tracker')
        if filter_device_events is not None:
           kwargs['filter_id'] = filter_device_events
        new_events = self.eyetracker.getEvents(**kwargs)
        new_samples=[e for e in new_events if e['type'] in [EventConstants.BINOCULAR_EYE_SAMPLE, EventConstants.MONOCULAR_EYE_SAMPLE]]
        new_events=[e for e in new_events if e['type'] not in [EventConstants.BINOCULAR_EYE_SAMPLE, EventConstants.MONOCULAR_EYE_SAMPLE]]
        self.updateLocalEventsCache(new_events)
        import math
        if new_samples:
            #print("NEW SAMPLE COUNT: ",len(new_samples))
            for s in new_samples:
                for k, v in s.items():
                    if isinstance(v, np.generic):
                        s[k]=np.asscalar(v)
                    if math.isnan(v):
                        s[k] = 0
                    elif math.isinf(v):
                        s[k] = 0
            dev_data["samples"][0] = new_samples
            return dev_data
 
        if dev_data_update:
            return dev_data

    def exitApplicationCleanly(self):
        # - stop recording if needed
        # - close session if needed
        # then pass on exit.
        self.stopDeviceRecording()
        self.hub.quit()
        if self.getConfiguration().get('autorun_ssa_creation', False):
            print("Starting SSA file creation for last session.")
            print ("Please Wait .",)
            conv_proc = self.startSSAconvertion()
            while conv_proc.poll() == None:
                core.wait(1.0, .1)
                print (".",)
            print("")
        return 'EXIT_PROGRAM'

    def handleMsgRx(self):
        try:
            server_msg=self.ui_server_websocket.recv()
            msg=ujson.loads(server_msg)
            if msg.get('type') == 'experiment_message':
                self.hub.sendMessageEvent(msg.get('text'), msg.get('category'))
            if msg.get('type') == 'JS_EVENT':
                time = msg.get('time')
                if time == -1:
                    time = getTime()
                self.hub.sendMessageEvent(msg.get('text'), msg.get('category'),sec_time=time)
            elif msg.get('type') == 'EXIT_PROGRAM':
                return self.exitApplicationCleanly()
            elif msg.get('type') == 'START_EXP_SESSION':
                self.stopDeviceRecording()
                #print("MSG RX: ",msg)
                return 'START_EXP_SESSION'
            elif msg.get('type') == "CLOSE_EXP_SESSION":
                #print("MSG RX: ",msg)
                self.stopDeviceRecording()
                self.hub.sendMessageEvent("Experiment Session Complete: %s"%(self.getSessionMetaData().get('code', 'CODE_MISSING')), "data_monitoring")
                msg={'msg_type': 'EXP_SESSION_CLOSED', 'type': "success"}
                if self.getConfiguration().get('autorun_ssa_creation', False):
                    self.startSSAconvertion()
                self.sendToWebServer(msg)
                self.resetDataCollectionStats()
                self.createDeviceStatsMessageDicts()
                self.handleMsgTx()
                self.resetWebAppDataStats()
                return 'CLOSE_EXP_SESSION'
            elif msg.get('type') == 'START_RECORDING':
                self.startDeviceRecording()
            elif msg.get('type') == 'STOP_RECORDING':
                self.stopDeviceRecording()
            elif msg.get('type') == 'START_EYETRACKER_CALIBRATION':
                self.startEyeTrackerCalibration()
            elif msg.get('type') == 'START_EYETRACKER_VALIDATION':
                validation_config = load(file(os.path.abspath(os.path.join(r'..\settings', 'validation_config.yaml')), 'r'), Loader=Loader).get('validation')
                self.startEyeTrackerValidation(validation_config)
            else:
                print('!!Unhandled Server Message:', msg)

        except socket.error, e:
            if e.errno == 10035:
                pass
            else:
                print("Socket Error:", e)
                return self.exitApplicationCleanly()
        except WebSocketConnectionClosedException, wse:
            print("WebSocketConnectionClosedException:", wse)
            return self.exitApplicationCleanly()

    def sendToWebServer(self,*args):
        try:
            tosend=ujson.dumps(args)
            self.ui_server_websocket.send(tosend)
        except Exception, e:
            print(">>>")
            print("SendToWebServer failed: ",e)
            #import traceback
            #traceback.print_exc()
            print("Attempted to send:",args)
            print("<<<")

    def resetWebAppDataStats(self):
        self.sendToWebServer(messages.DataCollection)

    def handleMsgTx(self):
        data_collection = copy.deepcopy(messages.DataCollection)
        data_collection.clear()
        data_collection['msg_type'] = 'DataCollection'
        ctime=core.getTime()
        self.device_info_stats['experiment_session']['current_time'][0]= ctime
        self.device_info_stats['experiment_session']['duration'][0]= ctime - self.device_info_stats['experiment_session']['start_time'][0]
        self.device_info_stats['input_computer']['up_time'][0] = ctime- self.device_info_stats['experiment_session']['start_time'][0]
        for device_label,device_timer in self.device_monitor_countdowns.iteritems():
            if device_timer.getTime() <= 0.0:
                # timer expired for given device reporting interval, so send
                # updated info for device
                dev_update = self.device_info_update_funcs[device_label]()
                if dev_update:
                    self.stats_info_updates[device_label] = dev_update
                device_timer.reset()
                #print('device_timer reset:', getTime(), device_timer._label, device_timer.getTime())

        update_count = len(self.stats_info_updates)
        if update_count > 0:
            for k, v in self.stats_info_updates.iteritems():
                data_collection[k] = v
            self.sendToWebServer(data_collection)
            self.stats_info_updates.clear()



    def keyChainValue(self, cdict, *key_path):
        result = cdict.get(key_path[0])
        key_path = list(key_path[1:])
        for key in key_path:
            if not hasattr(result, 'get'):
                return result
            result = result.get(key)
        return result
        
    def checkForTerminateEvent(self):
        # Check for App exit
        kb_events = self.events_by_type.get(EventConstants.KEYBOARD_PRESS)
        while kb_events and len(kb_events) > 0:
            ke = kb_events.pop()
            char = ke['char'].lower()
            kmods = ke['modifiers']
            if char == self._quit_char and self._quit_modifier in kmods:
                self.hub.sendMessageEvent("User Terminated data collection runtime using CTRL-C.","data_monitoring")
                return True
        return False
        
    def close(self):
        try:
            self.hub.quit()
        except Exception, e:
            print ('**Exception self.hub.quit():',e)


    def startSubProcess(self, *args,**kwargs):
        stdout_file=kwargs['stdout_file']
        stderr_file=kwargs['stderr_file']
        cmd_line=' '.join([str(a) for a in args])
        with open(stdout_file,"w") as out, open(stderr_file,"w") as err:
            p=subprocess.Popen(cmd_line, stdin=subprocess.PIPE, 
                               stdout=out, stderr=err
                               )
        return p

    def startEyeTrackerCalibration(self):
        self.hub.sendMessageEvent("CALIBRATION STARTING. Enabling keyboard events.")
        et = self.eyetracker
        kb=self.keyboard
        result=False
        if et:
            kbisrecording=kb.isReportingEvents()
            etisrecording=et.isRecordingEnabled()
            if not kbisrecording:
                kb.enableEventReporting(True)
            if etisrecording:
                et.setRecordingState(False)
            result=et.runSetupProcedure()
            if not kbisrecording:
                kb.enableEventReporting(False)
            if etisrecording:
                et.setRecordingState(True)
        self.hub.sendMessageEvent("CALIBRATION COMPLETE. Disabling keyboard events.")
        cmtype="success"
        if result in [False,None,EyeTrackerConstants.EYETRACKER_CALIBRATION_ERROR,
                      EyeTrackerConstants.EYETRACKER_ERROR,]:
            cmtype="error"                  
        msg={'msg_type':'EYETRACKER_CALIBRATION_COMPLETE','type':cmtype}
        self.sendToWebServer(msg)

    def startEyeTrackerValidation(self, validation_config):
        self.hub.sendMessageEvent("VALIDATION STARTING. Enabling keyboard events.")
        et = self.eyetracker
        kb=self.keyboard
        display = self.display
        result = False
        if et:
            kbisrecording=kb.isReportingEvents()

            if not kbisrecording:
                kb.enableEventReporting(True)

            # Validation specific code starts.....
            
            res=display.getPixelResolution() # Current pixel resolution of the Display to be used
            coord_type=display.getCoordinateType()
            win=visual.Window(res, monitor=display.getPsychopyMonitorName(), # name of the PsychoPy Monitor Config file if used.
                                    units=coord_type, # coordinate space to use.
                                    fullscr=True, # We need full screen mode.
                                    allowGUI=False, # We want it to be borderless
                                    screen= display.getIndex() # The display index to use, assuming a multi display setup.
                                    )


            save_figure = validation_config.get('save_figure')
            if save_figure:
                validation_config['save_figure'] = self._session_results_folder

            ##### Run a validation procedure
            validation_proc=ValidationProcedure(
                                                win,
                                                configuration=validation_config
                                                )

            # Run the validation process. The method does not return until the process
            # is complete.
            # Returns the validation calculation results and data collected for the
            # analysis.                       
            results = validation_proc.display()
            
            # The last calculated validation results can also be retrieved using
            #results = validation_proc.getValidationResults()

            win.close()
            ##### Validation code ends
            
            if not kbisrecording:
                kb.enableEventReporting(False)
            self.hub.clearEvents('all')
        # set result to hardcoded True for now
        result = True

        self.hub.sendMessageEvent("VALIDATION COMPLETE. Disabling keyboard events.")
        cmtype="success"
        if result in [False,None,EyeTrackerConstants.EYETRACKER_CALIBRATION_ERROR,
                      EyeTrackerConstants.EYETRACKER_ERROR,]:
            cmtype="error"                  
        msg={'msg_type':'EYETRACKER_VALIDATION_COMPLETE','type':cmtype}
        self.sendToWebServer(msg)

    def startDeviceRecording(self):
        if self.recording_vars is None:
            self.recording_vars=[]
            for i in range(256):
                self.recording_vars.append({'session_id': self.hub.experimentSessionID,
                                            'trial_id': i,
                                            'TRIAL_START': 0.0,
                                            'TRIAL_END': 0.0
                                            })
            self.recording_condition_variables = TrialHandler(
                                                    self.recording_vars, 1)
            self.hub.createTrialHandlerRecordTable(self.recording_condition_variables)

        self.current_rec_vars = self.recording_condition_variables.next()

        session_info=self.device_info_stats['experiment_session']

        data_collect_config = self.getConfiguration().get('recording_period', {})
        start_msg_txt = data_collect_config.get('start_msg', 'RECORDING_STARTED')
        start_events_msg_text = data_collect_config.get('event_period', {}).get('start_msg', 'START_EVENT_PERIOD')

        if session_info['recording'][0] is False:
            self.stats_info_updates['experiment_session'] = session_info
            session_info['recording'][0] =True
            session_info['recording_counter'][0]+=1

            self.hub.sendMessageEvent(start_msg_txt,"data_monitoring")
            for device_label,(iohub_device,device_msg_dict) in self.recording_devices.iteritems():
                iohub_device.enableFilters()
                iohub_device.enableEventReporting(True)
                cntimer = CountdownTimer(device_msg_dict.get('countdown_time', [0.25,''])[0])
                #cntimer._label = device_label
                self.device_monitor_countdowns[device_label] = cntimer
            session_info['recording_start_time'][0] =getTime()
            self.current_rec_vars['TRIAL_START'] = getTime()

            self.beginScreenCaptureStream()

            core.wait(0.25, 0.05)

            cmtype="success"
            msg={'msg_type':start_msg_txt,'type':cmtype}
            self.sendToWebServer(msg)


            self.runVisualSyncProcedure()
            self.hub.clearEvents("all")
            self.hub.sendMessageEvent(start_events_msg_text, "data_monitoring")

    def stopDeviceRecording(self):
        data_collect_config = self.getConfiguration().get('recording_period', {})
        end_msg_txt = data_collect_config.get('end_msg', 'RECORDING_STOPPED')
        end_events_msg_text = data_collect_config.get('event_period', {}).get('end_msg', 'END_EVENT_PERIOD')
        self.hub.sendMessageEvent(end_events_msg_text, "data_monitoring")
        session_info=self.device_info_stats['experiment_session']
        if session_info['recording'][0] is True:
            session_info['recording'][0] =False
            self.stats_info_updates['experiment_session'] = session_info

            self.hub.sendMessageEvent("Stopping Recording Block: %d"%(session_info['recording_counter'][0] ), "data_monitoring")

            for device_label, (iohub_device, device_msg_dict) in self.recording_devices.iteritems():
                iohub_device.enableEventReporting(False)
                iohub_device.enableFilters(False)
                del self.device_monitor_countdowns[device_label]
            session_info['recording_start_time'][0] = 0.0
            session_info['recording'][0] = False
            self.current_rec_vars['TRIAL_END'] = getTime()
            self.hub.addRowToConditionVariableTable(self.current_rec_vars.values())
            self.runVisualSyncProcedure()
            # try to ensure frames with visual sync stim have been written
            # to video file
            core.wait(3.0,.2)
            self.hub.clearEvents("all")
            self.stopffmpeg()

            cmtype="success"
            msg={'msg_type': end_msg_txt, 'type': cmtype}
            self.sendToWebServer(msg)
            
            self.hub.sendMessageEvent(end_msg_txt, "data_monitoring")

    def startSSAconvertion(self):
        #print("EXP, SESS:", self.active_exp_name, self.getSessionMetaData().get('code'))
        #print("generate_ssa_files.bat %s %s"%(self.active_exp_name, self.getSessionMetaData().get('code')))
        self.p = subprocess.Popen("generate_ssa_files.bat %s %s"%(self.active_exp_name, self.getSessionMetaData().get('code')), shell=True)
        return self.p

    def startScreenCaptureStream(self):
        appcfg=self.getConfiguration()
        scParam=partial(self.keyChainValue,appcfg,'screen_capture')
        sess_results_dir=self._session_results_folder
        pjoin=os.path.join
        dshow_v=scParam('dshow_filters','video')
        dshow_a=scParam('dshow_filters','audio')
        audio_arg=''
        if dshow_a:
            #TODO: If audio source is Mic, set audio_buffer_size to 80
            audio_arg=':audio="%s"'%(dshow_a)
        rtbufsize=scParam('dshow_filters','ffmpeg_settings','rtbufsize')        
        cli='-f dshow -rtbufsize {0}k -i video="{1}"{2} '.format(
                                                            rtbufsize, dshow_v,
                                                            audio_arg
                                                            )
        
        threads=scParam('http_stream','ffmpeg_settings','threads')
        scale=scParam('http_stream','ffmpeg_settings','scale')
        px,py=self.display.getPixelResolution()
        stream_width = px
        stream_height = py
        scale_mpeg_stream = False
        if scale is not None and scale not in (1.0, 1):
            stream_width = int(px*scale)-int(px*scale)%2
            stream_height = int(py*scale)-int(py*scale)%2
            scale_mpeg_stream = True
        rate = scParam('http_stream','ffmpeg_settings','r')
        bv = scParam('http_stream','ffmpeg_settings','b','v')
        cli += '-threads {0} '.format(threads)
        if scale_mpeg_stream:
            cli += '-s {0}x{1} '.format(stream_width, stream_height)
        cli += '-f mpeg1video -b:v {0}k -r {1} '.format(bv, rate)

        host=self.view_server_ip
        write_port=scParam('http_stream','write_port')
        uri=scParam('http_stream','uri')
        cli+='http://{0}:{1}/{2}/{3}/{4}/ '.format(host, write_port, uri,
                                                stream_width, stream_height
                                                )

        avFile=scParam('media_file','name')
        avExtension=scParam('media_file','extension')
        codec=scParam('media_file','ffmpeg_settings','codec')
        crf=scParam('media_file','ffmpeg_settings','crf')
        pix_fmt=scParam('media_file','ffmpeg_settings','pix_fmt')
        preset=scParam('media_file','ffmpeg_settings','preset')
        g=scParam('media_file','ffmpeg_settings','g')
        threads=scParam('media_file','ffmpeg_settings','threads')
        rec_count=self.device_info_stats['experiment_session']['recording_counter'][0]
        cli+='-vcodec {0} -pix_fmt {5} -crf {1} -preset {2} -g {6} -threads {3} "{4}"'.format(
                                        codec, crf, preset, threads,
                                        pjoin(sess_results_dir,avFile+"_%d."%(rec_count)+avExtension),
                                        pix_fmt,g
                                        )

        fmpPath=scParam('ffmpeg','path')       
        if not os.path.isabs(fmpPath):
            fmpPath=pjoin(self.script_dir,fmpPath)
        ffmpeg=os.path.abspath(pjoin(fmpPath,scParam('ffmpeg','exe')))
        stdout_file=pjoin(sess_results_dir, scParam('ffmpeg','stdout_file')+"_%d"%(rec_count)+".txt")
        stderr_file=pjoin(sess_results_dir, scParam('ffmpeg','stderr_file')+"_%d"%(rec_count)+".txt")

        self.hub.sendMessageEvent("Starting subprocess.", "ffmpeg_init")
        #print("STARTING FFMPEG:",ffmpeg,cli)
        p = self.startSubProcess(ffmpeg, cli, 
                                    stdout_file=stdout_file, 
                                    stderr_file=stderr_file)
        self.hub.sendMessageEvent("Subprocess call returned...sleep(1.0)...", "ffmpeg_init")
        core.wait(1.0,.2)
        self.hub.sendMessageEvent("sleep(1.0) complete.", "ffmpeg_init")

        return p

    def stopffmpeg(self):
        a,b = self._ffmpeg_proc.communicate(r"q\n\r")

    def runVisualSyncProcedure(self):
        sync_config = self.getConfiguration()['video_event_sync']
        colors = sync_config.get('colors', [255,0])
        l, t, r, b = sync_config.get('region', [0, 0, 10, 10])
        cycle_count = sync_config.get('cycle_count', 3)
        state_duration = sync_config.get('phase_duration', 0.125)

        rgbcolors = []
        for c in colors:
            gsc = c/255.0*2.0-1.0
            rgbcolors.append((gsc, gsc, gsc))
        win_pos = l, t
        sync_win = visual.Window((r-l, b-t), color=rgbcolors[0],
                                 screen=0, pos=win_pos,
                                 allowGUI=False, units='pix')    
        fill_rect = visual.Rect(sync_win, r-l, b-t, fillColor=rgbcolors[1],
                                lineWidth=1, lineColor=rgbcolors[1],
                                interpolate=False)

        def displayState(color_index):
            fill_rect.fillColor=rgbcolors[color_index]
            fill_rect.lineColor=rgbcolors[color_index]

            fill_rect.draw()
            flip_time = sync_win.flip()

            self.hub.sendMessageEvent(text=str(fill_rect.fillColor),
                                  category="video_sync",
                                  sec_time=flip_time)

            wait_for=state_duration-(core.getTime()-flip_time)
            core.wait(wait_for)

        for i in range(cycle_count):
            displayState(1)
            displayState(0)
            
        sync_win.close()