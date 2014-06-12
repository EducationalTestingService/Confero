import tornado
from tornado import websocket
import ujson
import psutil
from psychopy.iohub.util import NumPyRingBuffer
from psychopy.iohub import EventConstants, EyeTrackerConstants
import numpy as np
#
## Websocket server for sending / receiving msg's from Experiment Feedback Monitor
#
class WebSocket(websocket.WebSocketHandler):
    server_app_websockets = None
    ws_key = None
    def open(self):
        self.set_nodelay(True)
        if self.ws_key in self.server_app_websockets:
            print "View Server WARNING: WebSocket type %s already exists. Only one ws per type is currently supported."
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
            pass
        else:
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
            elif msg_type == 'OPEN_USER_MANUAL':
                from webserver import ControlFeedbackServer
                ControlFeedbackServer.openUserManual()
                msg_type = 'UNKNOWN'
            if msg_type is not 'UNKNOWN':
                dc_sw.write_message(message)

        else:
            print("")
            print("WARNING: Data Collection Web Socket is not Running. Msg not sent. Is the Data Collection application running?")
            print("")

class TrackBrowserWebSocket(WebSocket):
    ws_key = "TRACK_CLIENT"
    def open(self):
        print('TrackBrowserWebSocket created.')
        WebSocket.open(self)
        dc_ws = self.server_app_websockets.get('DATA_COLLECTION')
        if not dc_ws:
            pass
        else:
            self.event_filter = dc_ws.data_collection_state.setdefault('confero_track_ws_device_filter',[])

    def on_message(self, message):
        dc_sw = self.server_app_websockets.get("DATA_COLLECTION")
        if dc_sw:
            msg_dict = ujson.loads(message)
            msg_type = msg_dict.get('msg_type', 'UNKNOWN')
            if msg_type is 'UNKNOWN':
                msg_type = msg_dict.get('type', 'UNKNOWN')

            if msg_type == 'ECHO':
                self.write_message(message)
            elif msg_type == 'device_filter':
                self.device_filter=msg_dict['device_list']
                dc_sw.data_collection_state['confero_track_ws_device_filter'] = self.device_filter

            elif msg_type == 'UNKNOWN':
                self.write_message(self.createErrorMsgmessage(msg_dict, "Unknown Message Type"))
        else:
            print("")
            print("WARNING: Data Collection Web Socket is not Running.")
            print("")

    def createErrorMsg(self,msg,reason):
        return ujson.dump(dict(type='ERROR', rx_msg=msg, reason=reason))

def createLeftEyeInfo(dev_data):
    dev_data["left_eye_gaze"] = [None,'']
    dev_data["left_eye_pos"] = [None,'']
    dev_data["left_eye_pupil"] = [None,'']

def createRightEyeInfo(dev_data):
    dev_data["right_eye_gaze"] = [None,'']
    dev_data["right_eye_pos"] = [None,'']
    dev_data["right_eye_pupil"] = [None,'']

def createAveragedEyeInfo(dev_data):
    # just right eye cells for now
    dev_data["right_eye_gaze"] = [None,'']
    dev_data["right_eye_pos"] = [None,'']
    dev_data["right_eye_pupil"] = [None,'']

def clearLeftEyeInfo(dev_data):
    dev_data["left_eye_gaze"][0] = None
    dev_data["left_eye_pos"][0] = None
    dev_data["left_eye_pupil"][0] = None

def clearRightEyeInfo(dev_data):
    dev_data["right_eye_gaze"][0] = None
    dev_data["right_eye_pos"][0] = None
    dev_data["right_eye_pupil"][0] = None

def clearAveragedEyeInfo(dev_data):
    dev_data["right_eye_gaze"][0] = None
    dev_data["right_eye_pos"][0] = None
    dev_data["right_eye_pupil"][0] = None

def setLeftEyeInfo(dev_data, status, sample):
    dev_data["left_eye_gaze"][0] = int(sample['left_gaze_x']), int(sample['left_gaze_y'])
    dev_data["left_eye_pos"][0] = int(sample['left_eye_cam_x']), int(sample['left_eye_cam_y']), int(sample['left_eye_cam_z'])
    dev_data["left_eye_pupil"][0] = sample['left_pupil_measure1']

def setRightEyeInfo(dev_data, status, sample):
    dev_data["right_eye_gaze"][0] = int(sample['right_gaze_x']), int(sample['right_gaze_y'])
    dev_data["right_eye_pos"][0] = int(sample['right_eye_cam_x']), int(sample['right_eye_cam_y']), int(sample['right_eye_cam_z'])
    dev_data["right_eye_pupil"][0] = sample['right_pupil_measure1']

def setAveragedEyeInfo(dev_data, status, sample):
    dev_data["right_eye_gaze"][0] = int(sample['gaze_x']), int(sample['gaze_y'])
    dev_data["right_eye_pos"][0] = int(sample['eye_cam_x']), int(sample['eye_cam_y']), int(sample['eye_cam_z'])
    dev_data["right_eye_pupil"][0] = sample['pupil_measure1']

class DataCollectionWebSocket(WebSocket):
    ws_key = "DATA_COLLECTION"
    def open(self):
        WebSocket.open(self)
        self.data_collection_state = dict(experiment_names_msg=None,
                                          server_computer=dict(cpu_usage_all = [None, ' %'], memory_usage_all = [None, ' %'])
                                         )
        
    def on_message(self, message):
        msg_list = ujson.loads(message)

        to_send=[]
        for m in msg_list:
            msg_type = m.get('msg_type', 'UNKNOWN')
            if msg_type =='DataCollection':
                if m.get('input_computer'):
                    self.data_collection_state['server_computer']['cpu_usage_all'][0] = float(psutil.cpu_percent(0.0))
                    self.data_collection_state['server_computer']["memory_usage_all"][0] = psutil.virtual_memory().percent
                    m['server_computer'] = self.data_collection_state['server_computer']
                elif m.get('eyetracker'):
                    self.processEyeTrackerData(m.get('eyetracker'))
                    m['eyetracker'] =  self.data_collection_state['eyetracker']
            elif msg_type == 'EXP_FOLDER_LIST':
                self.data_collection_state['experiment_names_msg'] = m
            elif msg_type == 'DATA_COLLECT_CONFIG':
                self.data_collection_state['data_collection_config'] = m

            if msg_type is not 'UNKNOWN':
                to_send.append(m)

        if len(to_send) > 0:
            ws_ui = self.server_app_websockets.get("WEB_UI")
            if ws_ui:
                ws_ui.write_message(ujson.dumps(to_send))

            ws_tc = self.server_app_websockets.get("TRACK_CLIENT")
            if ws_tc:
                dev_filter = self.data_collection_state.get('confero_track_ws_device_filter')
                if dev_filter is None:
                    ws_tc.write_message(ujson.dumps(to_send))
                else:
                    filtered_to_send=[]
                    for msg in to_send:
                        if msg['msg_type'] == 'DataCollection':
                            msg_dict = dict(msg_type = 'DataCollection')
                            for dev_name, dev_stats in msg.items():
                                if dev_name in dev_filter:
                                    msg_dict[dev_name]  =  dev_stats
                            filtered_to_send.append(msg_dict)
                    if filtered_to_send:
                        ws_tc.write_message(ujson.dumps(filtered_to_send))

    def processEyeTrackerData(self, dev_data):
        current_et_data = self.data_collection_state.get('eyetracker')
        if current_et_data is None:
            current_et_data = dev_data
            new_fields = {
                "eye_sample_type": [None, ''],
                "proportion_valid_samples": [None, ' %'],
                "time": [None, ' sec'],    # time of last sample received
                "rms_noise": [None, ' RMS'], 
                "stdev_noise": [None, ' STDEV'], 
                }
            current_et_data.update(new_fields)
            self.data_collection_state['eyetracker'] = current_et_data
            self.data_collection_state['proportion_valid_samples']=NumPyRingBuffer(int(current_et_data["sampling_rate"][0]), dtype=np.int8)
        else:
             current_et_data.update(dev_data)
        dcapp_config=self.data_collection_state['data_collection_config']
        new_samples = current_et_data.get('samples')[0]
        sampling_rate=float(current_et_data["sampling_rate"][0])

        if new_samples:
            latest_sample_event = new_samples[-1]
            current_et_data['time'][0]=latest_sample_event['time']
            tracking_eyes = dev_data.get('track_eyes')[0]
            eyename='BOTH'
            sample_type = current_et_data.get('eye_sample_type')[0]
            noise_win_size=dcapp_config.get('noise_calculation',{}).get("win_size",0.2)
            noise_sample_count=int(sampling_rate*noise_win_size)

            if tracking_eyes == 'BINOCULAR_AVERAGED':
                sample_type = "Monocular"
                eyename='AVERAGED'
                if self.data_collection_state.get('right_eye') is None:
                    self.data_collection_state['right_eye']=dict(x=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),y=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),pupil=NumPyRingBuffer(noise_sample_count, dtype=np.float64))
                createAveragedEyeInfo(current_et_data)
            #----

            elif tracking_eyes == EyeTrackerConstants.LEFT_EYE:
                if self.data_collection_state.get('left_eye') is None:
                    createLeftEyeInfo(current_et_data)
                    self.data_collection_state['left_eye']=dict(x=NumPyRingBuffer(noise_sample_count, dtype=np.float64),
                                    y=NumPyRingBuffer(noise_sample_count, dtype=np.float64),
                                    pupil=NumPyRingBuffer(noise_sample_count, dtype=np.float64)) 
                eyename='LEFT'
                if sample_type is None:
                    sample_type = "Monocular"     
            elif tracking_eyes <= EyeTrackerConstants.MONOCULAR:
                if self.data_collection_state.get('right_eye') is None:
                    self.data_collection_state['right_eye']=dict(x=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),y=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),pupil=NumPyRingBuffer(noise_sample_count, dtype=np.float64)) 
                    createRightEyeInfo(current_et_data)
                eyename='RIGHT'
                if sample_type is None:
                    sample_type = "Monocular"     
            else:
                if self.data_collection_state.get('right_eye') is None:
                    createLeftEyeInfo(current_et_data)                  
                    createRightEyeInfo(current_et_data)
                    self.data_collection_state['left_eye']=dict(x=NumPyRingBuffer(noise_sample_count, dtype=np.float64),
                                    y=NumPyRingBuffer(noise_sample_count, dtype=np.float64),
                                    pupil=NumPyRingBuffer(noise_sample_count, dtype=np.float64)) 
                    self.data_collection_state['right_eye']=dict(x=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),y=NumPyRingBuffer(noise_sample_count,
                                dtype=np.float64),pupil=NumPyRingBuffer(noise_sample_count, dtype=np.float64)) 
                if sample_type is None:
                    sample_type = "Binocular"

            #----

            if sample_type is None:
                current_et_data['eye_sample_type'][0] = sample_type   

            new_sample_count=len(new_samples)
            if tracking_eyes == 'BINOCULAR_AVERAGED':
                valid_samples=[v for v in new_samples if v['status']!=22]
            else:
                valid_samples=[v for v in new_samples if v['status']==0]
            valid_sample_count=len(valid_samples)
            invalid_sample_count=new_sample_count-valid_sample_count

            #----

            s=None
            right_eye_buffers=None
            left_eye_buffers=None
            for s in valid_samples:
                if eyename == 'AVERAGED':
                    right_eye_buffers = self.data_collection_state['right_eye']
                    right_eye_buffers['x'].append(s['gaze_x'])
                    right_eye_buffers['y'].append(s['gaze_y'])
                    right_eye_buffers['pupil'].append(s['pupil_measure1'])
                elif eyename == 'BOTH':
                    rgx,rgy=s['right_gaze_x'],s['right_gaze_y']
                    lgx,lgy=s['left_gaze_x'],s['left_gaze_y']
                    right_eye_buffers = self.data_collection_state['right_eye']
                    right_eye_buffers['x'].append(rgx)
                    right_eye_buffers['y'].append(rgy)
                    right_eye_buffers['pupil'].append(s['right_pupil_measure1'])
                    left_eye_buffers = self.data_collection_state['left_eye']
                    left_eye_buffers['x'].append(lgx)
                    left_eye_buffers['y'].append(lgx)
                    left_eye_buffers['pupil'].append(s['left_pupil_measure1'])
                elif eyename == 'RIGHT':
                    right_eye_buffers = self.data_collection_state['right_eye']
                    if sample_type == 'Binocular':
                        right_eye_buffers['x'].append(s['right_gaze_x'])
                        right_eye_buffers['y'].append(s['right_gaze_y'])
                        right_eye_buffers['pupil'].append(s['right_pupil_measure1'])
                    else:
                        right_eye_buffers['x'].append(s['gaze_x'])
                        right_eye_buffers['y'].append(s['gaze_y'])
                        right_eye_buffers['pupil'].append(s['pupil_measure1'])
                else: # LEFT
                    left_eye_buffers = self.data_collection_state['left_eye']
                    if sample_type == 'Binocular':
                        left_eye_buffers['x'].append(s['left_gaze_x'])
                        left_eye_buffers['y'].append(s['left_gaze_y'])
                        left_eye_buffers['pupil'].append(s['left_pupil_measure1'])
                    else:
                        left_eye_buffers['x'].append(s['gaze_x'])
                        left_eye_buffers['y'].append(s['gaze_y'])
                        left_eye_buffers['pupil'].append(s['pupil_measure1'])
                                

            def calcrms(x, axis=None):
                return float(np.sqrt(np.mean(np.power(x,2.0), axis=axis))) / len(x)

            rms=None
            stdev=None

            if right_eye_buffers is not None and right_eye_buffers['x'].isFull():
                right_x=right_eye_buffers['x'].getElements()
                right_y=right_eye_buffers['y'].getElements()
                stdev=(right_x.std()+right_y.std())/2.0
                rms=(calcrms(right_x)+calcrms(right_y))/2.0

            if left_eye_buffers is not None and left_eye_buffers['x'].isFull():
                left_x=left_eye_buffers['x'].getElements()
                left_y=left_eye_buffers['y'].getElements()
                left_rms=(calcrms(left_x)+calcrms(left_y))/2.0
                left_stdev=(left_x.std()+left_y.std())/2.0
                if rms is not None:
                    rms=(rms+left_rms)/2.0
                else:
                    rms=left_rms
                if stdev is not None:
                    stdev=(stdev+left_stdev)/2.0
                else:
                    stdev=left_rms
                    
            prop_vsamples=self.data_collection_state['proportion_valid_samples']
            for i in range(valid_sample_count):
                prop_vsamples.append(1)
            for i in range(invalid_sample_count):
                prop_vsamples.append(0)                    
    
                    
            prop_valid_samples=prop_vsamples.sum()/float(sampling_rate)

            current_et_data.get('samples')[0]=None
            if rms:
                current_et_data['rms_noise'][0] = rms
            if stdev:
                current_et_data['stdev_noise'][0] = stdev  
            if prop_valid_samples:
                current_et_data['proportion_valid_samples'][0] = int(prop_valid_samples*100.0)
            
            if valid_samples:
                s=valid_samples[-1]
                status='TBC'

                if eyename == 'AVERAGED':
                    setAveragedEyeInfo(current_et_data,status,s)
                elif eyename == 'BOTH':
                    setLeftEyeInfo(current_et_data,status,s)
                    setRightEyeInfo(current_et_data,status,s)
                elif eyename == 'LEFT':
                    setLeftEyeInfo(current_et_data,status,s)
                else:
                    setRightEyeInfo(current_et_data,status,s)
    
            assert self.data_collection_state['eyetracker'] == current_et_data

