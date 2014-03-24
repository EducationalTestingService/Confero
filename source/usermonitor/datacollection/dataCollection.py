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
from psychopy.iohub.client import ioHubExperimentRuntime
from psychopy.iohub import EventConstants, MouseConstants, Computer
from psychopy.iohub.util import NumPyRingBuffer

from util import PriorityQueue, createPath
import messages


class DataCollectionRuntime(ioHubExperimentRuntime):
    script_dir=os.path.dirname(__file__)
    OTHER_RESULTS_DIR=os.path.abspath(os.path.join(script_dir, '.\\results'))
    cpu_usage_buffer = NumPyRingBuffer(30)
    def run(self, *args, **kwargs):
        appcfg=self.getConfiguration()
        self.command_queue=PriorityQueue()
        # dict of last events returned by hub for each device event type
        self.events_by_type = dict()
        self.stats_info_updates = dict()
        self.device_info_update_funcs=dict()
        self.device_monitor_countdowns = dict()
        self.recording_devices={}
        self.device_info_stats={}

        self.hub.sendMessageEvent("Started New Experiment Session: %s"%(self.getSessionMetaData().get('code','CODE_MISSING')),"data_monitoring")
        self._quit_char = self.keyChainValue(appcfg, 'manual_termination',
                                             'keyboard', 'key')
        self._quit_modifier = self.keyChainValue(appcfg, 'manual_termination',
                                                 'keyboard', 'modifier')    
        self.event_posting_interval = self.keyChainValue(appcfg, 
                                                         'experimenter_server',
                                                         'event_streaming', 
                                                         'stream_interval')
        # Setup devices
        self.computer=self.devices.computer
        self.keyboard = self.hub.getDevice('kb')
        self.display = self.devices.display
        self.mouse = self.hub.getDevice('mouse')
        self.eyetracker = self.hub.getDevice('tracker')
        #--

#        config_info = dict()        auto_report_events: False
#        config_info['app_config_yaml']=self.getConfiguration()
#        config_info['screen_capture_display_resolution'] = self.display.getPixelResolution()
#        self.ui_server_websocket.send(ujson.encode([{'msg_type':'APP_CONFIG_INFO', 'data': config_info},]))

        self.createDeviceStatsMessageDicts()

        # Create folder that will hold data and log files for the current
        # session. 
        # Note: This does not include the ioHub Data Store hdf5 file, which
        # is saved in the same directory as this script.
        if not self.createResultsFolder():
            self.close()
            return
        #--

        # Start the application processing / event loop
        # This method does not return until the application is quiting.        
        return_value=self.runEventLoop()
        self.hub.sendMessageEvent("Experiment Session Complete: %s"%(self.getSessionMetaData().get('code','CODE_MISSING')),"data_monitoring")

        # Close any application resources as needed and quit the ffmpeg
        # subprocess.
        self.close()
        return return_value

    def createDeviceStatsMessageDicts(self):
        display_info=copy.deepcopy(messages.display)
        self.device_info_stats['display']=display_info

        keyboard_info=copy.deepcopy(messages.keyboard)
        self.device_info_stats['keyboard']=keyboard_info

        mouse_info=copy.deepcopy(messages.mouse)
        self.device_info_stats['mouse']=mouse_info

        tracker_info=copy.deepcopy(messages.eyetracker)
        self.device_info_stats['eyetracker']=tracker_info

        session_info=copy.deepcopy(messages.experiment_session)
        self.device_info_stats['experiment_session']=session_info
        self.stats_info_updates['experiment_session'] = session_info
        session_info['code'][0]=self.getSessionMetaData().get('code')
        session_info['start_time'][0]=self.computer.getTime()

        display_info['resolution'][0] = self.display.getPixelResolution()
        display_unit_type = self.display.getCoordinateType()
        display_info['resolution'][1] = display_unit_type
        self.stats_info_updates['display'] = display_info

        input_computer_info=copy.deepcopy(messages.input_computer)
        self.device_info_stats['input_computer']=input_computer_info
        self.updateInputComputerStats()
        self.device_monitor_countdowns['input_computer'] = CountdownTimer(input_computer_info.get('countdown_time', [0.01,''])[0])
        self.device_info_update_funcs['input_computer'] = self.updateInputComputerStats

        if self.keyboard:
            self.recording_devices['keyboard']=[self.keyboard, keyboard_info]
            self.device_info_update_funcs['keyboard'] = self.updateKeyboardMsgInfo
        if self.mouse:
            self.recording_devices['mouse']=[self.mouse, mouse_info]
            self.device_info_update_funcs['mouse'] = self.updateMouseMsgInfo
            mouse_info['position'][1] = display_unit_type
        if self.eyetracker:
            print(" TODO: Finish updateEyetrackerMsgInfo function")
            self.recording_devices['eyetracker']=[self.eyetracker, tracker_info]
#            self.device_monitor_countdowns['eyetracker'] = CountdownTimer(messages.eyetracker.get('countdown_time', [0.01,''])[0])
            self.device_info_update_funcs['eyetracker'] = self.updateEyetrackerMsgInfo
            tracker_info['gaze_position'][1] = display_unit_type

    def runEventLoop(self):
        self.hub.clearEvents('all')
        event_loop_rate = self.getConfiguration().get('event_loop_rate', 0.001)
        run = True
        gtime=self.computer.getTime
        if 1: #try:
            while run:
                # Send iohub events to MonitoringServer
                self.device_info_stats['input_computer']['up_time'][0] = gtime()- self.device_info_stats['experiment_session']['start_time'][0]
                self.handleMsgTx()

                cmd=self.handleMsgRx()
                if cmd:
                    run=False
                    return cmd

                # Check for App exit
                if self.checkForTerminateEvent():
                    run=False
                    break
    
                # check for any commands that need to be handled
                self.handleCommands()
               
                core.wait(event_loop_rate,0.002)                
        #except Exception, e:
        #    print("Run Loop Exception: ",e)
        #    raise e
            
    def handleCommands(self):
        while len(self.command_queue):
            task,args=self.command_queue.pop()
            task(*args)

    # Start the ffmpeg screen capturing sub process
    def beginScreenCaptureStream(self):
        try:
            self._ffmpeg_proc=self.startScreenCaptureStream()
            return True
        except Exception, e:
            print ('ERROR: startScreenCaptureStream Failed. Exiting App.')
            self.close()
            return False

    def createResultsFolder(self):
        # Create folder for saved video file(s), etc.
        session_code=self.device_info_stats['experiment_session']['code'][0]
            
        try:
            self._session_results_folder=os.path.join(self.OTHER_RESULTS_DIR,
                                                      session_code)
            createPath(self._session_results_folder)
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
        input_computer=self.device_info_stats['input_computer']
        input_computer['cpu_usage_all'][0] = float(self.cpu_usage_buffer.mean())
        input_computer["memory_usage_all"][0] = psutil.virtual_memory().percent

        new_stats = dict(psutil.disk_io_counters(False)._asdict())
        ctime = Computer.getTime()
        if input_computer["disk_usage"][0] is None:
            disk_usage_dict = {}
            disk_usage_dict['start_time']=[ctime,'sec']
            disk_usage_dict['start_bytes_read']=[new_stats['read_bytes'],'']
            disk_usage_dict['start_bytes_write']=[new_stats['write_bytes'],'']
            disk_usage_dict['start_read_time']=[new_stats['read_time'],'']
            disk_usage_dict['start_write_time']=[new_stats['write_time'],'']
            disk_usage_dict['stats_duration']=[0.0,'']
            disk_usage_dict['read_kb_per_sec']=[0,'']
            disk_usage_dict['write_kb_per_sec']=[0,r'kb/sec']
            disk_usage_dict['read_time_perc']=[0.0,'']
            disk_usage_dict['write_time_perc']=[0.0,r'%/sec']
            input_computer["disk_usage"][0] = disk_usage_dict
        else:
            disk_usage_dict = input_computer["disk_usage"][0]
            dur = ctime-disk_usage_dict['start_time'][0]
            read_bytes_per_sec = ((new_stats['read_bytes']-disk_usage_dict['start_bytes_read'][0])/1024.0)/dur
            write_bytes_per_sec = ((new_stats['write_bytes']-disk_usage_dict['start_bytes_write'][0])/1024.0)/dur
            read_time = new_stats['read_time']-disk_usage_dict['start_read_time'][0]
            write_time = new_stats['write_time']-disk_usage_dict['start_write_time'][0]
            disk_usage_dict['stats_duration'][0] = dur
            disk_usage_dict['read_kb_per_sec'][0] = read_bytes_per_sec
            disk_usage_dict['write_kb_per_sec'][0] = write_bytes_per_sec
            disk_usage_dict['read_time_perc'][0]=(read_time/dur)*100.0
            disk_usage_dict['write_time_perc'][0]=(write_time/dur)*100.0
            disk_usage_dict['start_time'][0]=ctime
            disk_usage_dict['start_bytes_read'][0]=new_stats['read_bytes']
            disk_usage_dict['start_bytes_write'][0]=new_stats['write_bytes']
            disk_usage_dict['start_read_time'][0]=new_stats['read_time']
            disk_usage_dict['start_write_time'][0]=new_stats['write_time']


        new_stats=dict(psutil.net_io_counters(False)._asdict())
        ctime=Computer.getTime()
        if input_computer["network_usage"][0] is None:
            net_usage_dict = {}
            net_usage_dict['start_time']=[ctime,'sec']
            net_usage_dict['start_bytes_recv']=[new_stats['bytes_recv'],'']
            net_usage_dict['start_bytes_sent']=[new_stats['bytes_sent'],'']
            net_usage_dict['stats_duration']=[0.0,'sec']
            net_usage_dict['kb_recv_per_sec']=[0,'']
            net_usage_dict['kb_sent_per_sec']=[0,r'kb/sec']
            input_computer["network_usage"][0] = net_usage_dict
        else:
            net_usage_dict = input_computer["network_usage"][0]
            dur = ctime-net_usage_dict['start_time'][0]
            bytes_recv_per_sec = ((new_stats['bytes_recv']-net_usage_dict['start_bytes_recv'][0])/1024.0)/dur
            bytes_sent_per_sec = ((new_stats['bytes_sent']-net_usage_dict['start_bytes_sent'][0])/1024.0)/dur
            net_usage_dict['stats_duration'][0] = dur
            net_usage_dict['kb_recv_per_sec'][0] = bytes_recv_per_sec
            net_usage_dict['kb_sent_per_sec'][0] = bytes_sent_per_sec
            net_usage_dict['start_time'][0]=ctime
            net_usage_dict['start_bytes_recv'][0]=new_stats['bytes_recv']
            net_usage_dict['start_bytes_sent'][0]=new_stats['bytes_sent']
        return input_computer


    def updateMouseMsgInfo(self):
        dev_data = self.device_info_stats['mouse']
        dev_data["recording"][0] = self.mouse.isReportingEvents()
        dev_data["duration"][0] = self.device_info_stats['experiment_session']['duration'][0]
        new_events = self.mouse.getEvents(asType='dict')
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
        dev_data["recording"][0] = self.keyboard.isReportingEvents()
        dev_data["duration"][0] = self.device_info_stats['experiment_session']['duration'][0]
        new_events = self.keyboard.getEvents(asType='dict')

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
        dev_data = self.device_info_stats['eyetracker']
        dev_data["recording"][0] = self.eyetracker.isReportingEvents()
        dev_data["time"][0] = self.eyetracker.trackerSec()
        dev_data["model"][0] = "Unknown Model"
        dev_data["duration"][0] = self.device_info_stats['experiment_session']['duration'][0]
        gp=self.eyetracker.getLastGazePosition()
        if gp:
            print('gp:',gp)
        else:
            gp = [0.0,0.0]
        dev_data["gaze_position"][0] = gp
        new_events = self.eyetracker.getEvents(asType='dict')
        new_events=[e for e in new_events if e['type'] not in [EventConstants.BINOCULAR_EYE_SAMPLE,EventConstants.MONOCULAR_EYE_SAMPLE]]

        self.updateLocalEventsCache(new_events)


        if dev_data["events"][0] is None and (new_events is None or len(new_events) == 0):
            dev_data["type"][0] = "N/A"
            dev_data['last_event_time'][0] = 0.0
            dev_data["events"][0] = []
            return dev_data
        if new_events:
            dev_data["events"][0]=new_events
            mevent = dev_data["events"][0][-1]
            dev_data['last_event_time'][0] = mevent['time']
            dev_data["type"] = EventConstants.getName(mevent["type"])
            return dev_data

    def handleMsgRx(self):
        try:
            server_msg=self.ui_server_websocket.recv()
            msg=ujson.loads(server_msg)
            if msg.get('type') == 'experiment_message':
                self.hub.sendMessageEvent(msg.get('text'), msg.get('category'))
                print('!! TODO: Correct for delay in feedback app experiment_message:', msg)
            elif msg.get('type') == 'START_EXP_SESSION':
                self.stopDeviceRecording()
                print("MSG RX: ",msg)
                return 'START_EXP_SESSION'
            elif msg.get('type') == "CLOSE_EXP_SESSION":
                print("MSG RX: ",msg)
                self.stopDeviceRecording()
                self.createDeviceStatsMessageDicts()
                self.handleMsgTx()
                return 'CLOSE_EXP_SESSION'
            elif msg.get('type') == 'START_RECORDING':
                self.startDeviceRecording()
            elif msg.get('type') == 'STOP_RECORDING':
                self.stopDeviceRecording()
            elif msg.get('type') == 'START_EYETRACKER_CALIBRATION':
                self.startEyeTrackerCalibration()
            elif msg.get('type') == 'START_EYETRACKER_VALIDATION':
                self.startEyeTrackerCalibration()
            elif msg.get('type') == 'START_EYETRACKER_DRIFT_CORRECTION':
                self.startEyeTrackerCalibration()
            else:
                print('!!Unhandled Server Message:', msg)

        except socket.error, e:
            if e.errno == 10035:
                pass
            else:
                print("Exception:", e)
                return 'EXIT_PROGRAM'
        except WebSocketConnectionClosedException, wse:
            print("WebSocketConnectionClosedException:", wse)
            return 'EXIT_PROGRAM'

    def handleMsgTx(self):
        data_collection = messages.DataCollection
        data_collection.clear()
        data_collection['msg_type'] = 'DataCollection'
        self.device_info_stats['experiment_session']['duration'][0]= core.getTime() - self.device_info_stats['experiment_session']['start_time'][0]
        for device_label,device_timer in self.device_monitor_countdowns.iteritems():
            if device_timer.getTime() <= 0.0:
                # timer expired for given device reporting interval, so send
                # updated info for device
                dev_update = self.device_info_update_funcs[device_label]()
                if dev_update:
                    self.stats_info_updates[device_label] = dev_update
                device_timer.reset()

        update_count = len(self.stats_info_updates)
        if update_count > 0:
            for k, v in self.stats_info_updates.iteritems():
                data_collection[k] = v
            try:
                self.ui_server_websocket.send(ujson.dumps([data_collection,]))
            except Exception, e:
                print(">>>")
                print("Warning: Could not send msg to feedback server: ",e)
                print(data_collection)
                print("<<<")
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
            char = ke['key'].lower()
            kmods = ke['modifiers']
            if char == self._quit_char and self._quit_modifier in kmods:
                self.hub.sendMessageEvent("User Terminated data collection runtime using CTRL-C.","data_monitoring")
                return True
        return False
        
    def close(self):
        try:
            if self.eyetracker:
                self.eyetracker.setRecordingState(False)
                self.eyetracker.setConnectionState(False)        
        except Exception, e:
            print ('**Exception in close():',e)
            
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
        return psutil.Process(p.pid)

    def startEyeTrackerCalibration(self):
        print('STARTING CAL...')
        et = self.eyetracker
        print('et',et)
        if et:
            isrecording=et.isRecordingEnabled()
            print('isrecording:',isrecording)
            if isrecording:
                et.setRecordingState(False)
            print('Starting runSetupProcedure')
            et.runSetupProcedure()
            print('Done runSetupProcedure')
            if isrecording:
                et.setRecordingState(True)
            print('END CAL')

    def startEyeTrackerValidation(self):
        print("SHOULD BE STARTING EYE TRACKER *VALIDATION* PROCESS....TBC")
    def startEyeTrackerDriftCorrect(self):
        print("SHOULD BE HANDLING EYE TRACKER *DRIFT CORRECT*....TBC")

    def startDeviceRecording(self):
        session_info=self.device_info_stats['experiment_session']

        if session_info['recording'][0] is False:
            print ("** TODO: RESET DEVICE INFO AT START OF RECORDING **")
            self.stats_info_updates['experiment_session'] = session_info
            session_info['recording'][0] =True
            session_info['recording_counter'][0]+=1

            self.hub.sendMessageEvent("Starting Recording Block: %d"%(session_info['recording_counter'][0]),"data_monitoring")
            for device_label,(iohub_device,device_msg_dict) in self.recording_devices.iteritems():
                iohub_device.enableEventReporting(True)
                self.device_monitor_countdowns[device_label] = CountdownTimer(device_msg_dict.get('countdown_time', [0.01,''])[0])

            self.beginScreenCaptureStream()

            core.wait(0.25,0.05)
            self.hub.clearEvents("all")
            self.hub.sendMessageEvent("Recording Block Started: %d"%(session_info['recording_counter'][0]),"data_monitoring")
            self.runVisualSyncProcedure(3)

    def stopDeviceRecording(self):
        session_info=self.device_info_stats['experiment_session']
        if session_info['recording'][0]  is True:
            print ("** TODO: RESET DEVICE INFO AT END OF RECORDING **")
            session_info['recording'][0] =False
            self.stats_info_updates['experiment_session'] = session_info

            self.hub.sendMessageEvent("Stopping Recording Block: %d"%(session_info['recording_counter'][0] ),"data_monitoring")
            self.hub.clearEvents("all")
            for device_label,(iohub_device,device_msg_dict) in self.recording_devices.iteritems():
                iohub_device.enableEventReporting(False)
                del self.device_monitor_countdowns[device_label]

            self.runVisualSyncProcedure(3)
            # try to ensure frames with visual sync stim have been written
            # to video file
            core.wait(3.0,.2)
            self.quiteSubprocs([self._ffmpeg_proc,])

            self.hub.sendMessageEvent("Recording Block Stopped: %d"%(session_info['recording_counter'][0]),"data_monitoring")


    def startScreenCaptureStream(self):
        appcfg=self.getConfiguration()
        scParam=partial(self.keyChainValue,appcfg,'screen_capture')
        sess_results_dir=self._session_results_folder
        pjoin=os.path.join
        dshow_v=scParam('dshow_filters','video')
        dshow_a=scParam('dshow_filters','audio')
        rtbufsize=scParam('dshow_filters','ffmpeg_settings','rtbufsize')        
        cli='-f dshow -rtbufsize {0}k -i video="{1}":audio="{2}" '.format(
                                                            rtbufsize, dshow_v,
                                                            dshow_a
                                                            )
        
        threads=scParam('http_stream','ffmpeg_settings','threads')
        scale=scParam('http_stream','ffmpeg_settings','scale')
        px,py=self.display.getPixelResolution()
        stream_width=int(px*scale)
        stream_height=int(py*scale)
        rate=scParam('http_stream','ffmpeg_settings','r')
        bv=scParam('http_stream','ffmpeg_settings','b','v')        
        cli+='-threads {0} -s {1}x{2} -f mpeg1video -b:v {3}k -r {4} '.format(
                                                        threads,stream_width,
                                                        stream_height,bv,rate
                                                        )

        host=scParam('http_stream','host')
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
        print("STARTING FFMPEG:",ffmpeg,cli)
        p = self.startSubProcess(ffmpeg, cli, 
                                    stdout_file=stdout_file, 
                                    stderr_file=stderr_file)
        self.hub.sendMessageEvent("Subprocess call returned...sleep(1.0)...", "ffmpeg_init")
        core.wait(1.0,.2)
        self.hub.sendMessageEvent("sleep(1.0) complete.", "ffmpeg_init")

        return p
        
    def quiteSubprocs(self,procs):
        import psutil
        def on_terminate(proc):
            if self.hub:
                try:
                    self.hub.sendMessageEvent("Process {} Terminated OK.".format(proc), "close_subproc")
                except:
                    pass

        for p in procs:
            try:
                p.terminate()
            except Exception, e:
                print('Error during quiteSubprocs:',e)
        gone, alive = psutil.wait_procs(procs=procs, timeout=3, callback=on_terminate)
        for p in alive:
                try:
                    p.kill()
                    if self.hub:
                        self.hub.sendMessageEvent("Process {} had to be KILLED.".format(p), "close_subproc")
                except Exception, e:
                    print ('Error2 during quiteSubprocs:',e)


    def runVisualSyncProcedure(self, cycle_count=3, state_duration=0.333):
        colors=[(1,1,1),(-1,-1,-1)]
        w,h=self.display.getPixelResolution()
        win_pos=0,0#int(-w/2),int(-h/2)
        sync_win = visual.Window((100, 100.0),color=colors[0],
                                 screen=0,pos=win_pos,
                                 allowGUI=False, units='pix')    
        fill_rect = visual.Rect(sync_win,100,100,fillColor=colors[1],
                                lineWidth=5, lineColor=colors[1],
                                interpolate=False)

        def displayState(color_index):
            fill_rect.fillColor=colors[color_index]
            fill_rect.lineColor=colors[color_index]

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