# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals
from psychopy.iohub import Computer
"""
Message Types, defined as dicts, which the data collection application can send
to the feedback server via the websocket connection.
"""

# DataCollection msg type holds and data for each device being monitored,
# including list of events for each device type which occurred since the last
# DataCollection message sent.
#
# DataCollection dict contains a set of dict values. keys == device types,
# values == the dict holding any information related to the device to be sent
# with the msg.
#
# Only devices that are being used / monitored should be added to the
# DataCollection dict for an experiment.
#
DataCollection = dict(msg_type='DataCollection')

# Info on current session (if any)
#
experiment_session = {
    "open": [False,''],
    "code": ['',''],
    'experiment_name': ['',''],
    "start_time": [None,'sec'],
    "duration": [None,'sec'],
    "recording": [False,''],
    "recording_counter": [0,''],
    "recording_start_time":[0.0,'sec'],
    "current_time":[0.0,'sec']
}
DataCollection['experiment_session'] = experiment_session

# Device dicts to add to DataCollection msg when app starts up.
#

input_computer = {
    "cpu_usage_all": [None,r'%'],
    "memory_usage_all": [None,r'%'],
    'up_time': [None,'sec'],
    "countdown_time": [1.0,'sec']
}
DataCollection['input_computer'] = input_computer

display = {               # name of iohub device class
    "resolution": [None,'pix']
    }
DataCollection['display'] = display

keyboard = {            # name of iohub device class
    "events": [None,''],       # list of any new events received from the device
    "type": [None,''],
    "auto_repeated": [None,''],
    "scan_code": [None,''],
    "key_id": [None,''],
    "ucode": [None,''],
    "key": [None,''],
    "modifiers": [None,''],
    "window_id": [None,''],
    "last_event_time": [None,'sec'],
    "countdown_time": [0.1,'sec'], # how often should this device info be updated in
    }                     # the DataCollection message (in secs)
DataCollection['keyboard'] = keyboard

mouse = {                 # name of iohub device class
    "events": [None,''],       # list of any new events received from the device
                        # if recording is False, events will be empty None
    "type": [None,''],
    "last_event_time":[None,'sec'],
    "position": [None,''], # current mouse position
    "buttons": [None,''],   # current mouse buttons pressed
    "scroll": [None,''],    # current mouse scroll wheel 'position'
    "modifiers": [None,''],
    "window_id": [None,''],
    "countdown_time": [0.033,'sec'],
    }
DataCollection['mouse'] = mouse


eyetracker = {          # name of iohub device class
    "model": [None, ''], # eye tracker model
    "sampling_rate": [None, 'Hz'],
    "time": [None, ' sec'],    # current tracker time, in secs
    "track_eyes": [None, ''],    # LEFT, RIGHT, BINOCULAR, MONOCULAR 
    "eye_sample_type":[None, ''], 
    "average_gaze_position": [None, ''], # current avg. gaze position
    
    "et_left_eye_status": [None, ''], 
    "et_right_eye_status": [None, ''], 
    "et_left_eye_state": [None, ''], 
    "et_right_eye_state": [None, ''], 
    "et_left_eye_gaze": [None, ''], 
    "et_right_eye_gaze": [None, ''], 
    "et_left_eye_pos": [None, ''], 
    "et_right_eye_pos": [None, ''], 
    "et_left_eye_pupil": [None, ''], 
    "et_right_eye_pupil": [None, ''], 
    "et_left_eye_noise": [None, ''], 
    "et_right_eye_noise": [None, ''],     
    "countdown_time": [0.033, ' sec']
    }  # end eye tracker
DataCollection['eyetracker'] = eyetracker