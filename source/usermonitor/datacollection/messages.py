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
    "duration": [0.0,'sec'],
    "recording": [False,''],
    "recording_counter": [0,''],
    "recording_start_time":[0.0,'sec'],
    "current_time":[0.0,'sec']
}

# Device dicts to add to DataCollection msg when app starts up.
#

input_computer = {
    "cpu_usage_all": [None,r'%'],
    "memory_usage_all": [None,r'%'],
    "disk_usage": [None,r''],
    'network_usage': [None,''],
    'up_time': [0.0,'sec'],
    "countdown_time": [1.0,'sec']
}

display = {               # name of iohub device class
    "recording": [False,''], # Is screen capture process running for the monitor
    "duration": [0.0,'sec'],# number of seconds into this recording period
    "resolution": [[0,0],'pix']
    }

keyboard = {            # name of iohub device class
    "recording": [False,''], # Is iohub currently recording events from device
    "duration": [0.0,'sec'],# number of sessions into this recording period
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

mouse = {                 # name of iohub device class
    "recording": [False,''], # Is iohub currently recording events from device
    "duration": [0,'sec'],# number of sessions into this recording period
    "events": [None,''],       # list of any new events received from the device
                        # if recording is False, events will be empty None
    "type": [None,''],
    "last_event_time":[None,'sec'],
    "position": [[0.0, 0.0],''], # current mouse position
    "buttons": [[],''],   # current mouse buttons pressed
    "scroll": [0,''],    # current mouse scroll wheel 'position'
    "modifiers": [[],''],
    "window_id": [0,''],
    "countdown_time": [0.033,'sec'],
    }

# EyeInfo dict is used within the EyeTracker device dict, up to 3 times.
#
EyeInfo = {            # all data for left eye (if available)
        "found": True, # does the eye tracker have data for this eye
        "position": {
            "gaze": {
                "point": [100,100], # latest (x,y) gaze position
                "noise":{           # available gaze noise levels
                    "rms": 0.12,
                    "peak": 1.3,
                    }
                }, # end gaze position type
            "distance": {
                "point": [100,100,100], # latest (x,y,z) eye position
                "noise": {              # available gaze noise levels
                    "rms": 0.12,
                    "peak": 1.3
                    },
                },  #end distance position type
            },      # end positions
        "pupil": {  # available pupil size / shape measures.
            "area": 20500.0,
            "diameter": 1000.0,
            "radius": 500.0,
            "minor_axis": 970.0,
            "major_axis": 1000.0,
            },  # end pupil
        }

eyetracker = {          # name of iohub device class
    "model": ['Unknown',''], # eye tracker model
    "recording": [False,''], # Is iohub currently recording events from device
    "duration": [132.934,' sec'],# number of seconds into this recording period
    "time": [100.234,' sec'],    # current tracker time, in secs
    "gaze_position": [[0.0, 0.0],''], # current gaze position
    "events": [None,''],     # list of any new eye events received from the device
    "last_event_time": [None,' sec'],
    "type": [None,''],        # This does not include eye samples, which are in
                        # eyes.samples list
#    "eyes":{
#        "samples": [],  # list of eye sample events
#        "left": None,   # dict(EyeInfo),
#        "right": None,  # dict(EyeInfo),
#        "averaged": None,# dict(EyeInfo),
#        },  # end eyes
    "countdown_time": [0.033,' sec']
    }  # end eye tracker
