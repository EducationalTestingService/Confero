"""
Example of using a user defined DeviceEventFilter to create a filtered version
of an event stream. Here we will process eye tracker samples using the filter.
"""

from psychopy import core, visual
from psychopy.iohub import start, EventConstants
from psychopy.data import TrialHandler,importConditions
from psychopy.iohub import TimeTrigger, DeviceEventTrigger
from psychopy.iohub import TargetStim, PositionGrid, ValidationProcedure
import time
import numpy as np
getTime = core.getTime

win = visual.Window()
io = start()

# Get the keyboard and mouse devices for future access.
keyboard = io.devices.keyboard
mouse = io.devices.mouse
tracker = io.devices.tracker
experiment = io.devices.experiment

filter_path_and_file=r'..\eyetracker.py','EyeTrackerEventParser'
filter_id = tracker.addFilter(*filter_path_and_file)
if filter_id == -1:
    print "** Error, filter not installed:",filter_path_and_file
else:
    print "Filter installed. filter_id =",filter_id

exp_conditions= [
    {'session_id': 1,
     'trial_id': 1,
     'TRIAL_START': 0.0,
     'TRIAL_END': 0.0
    }
]

trials = TrialHandler(exp_conditions,1)
io.createTrialHandlerRecordTable(trials)

tracker.runSetupProcedure()

t=0
for trial in trials:
    trial['session_id']=io.getSessionID()
    trial['trial_id']=t+1
    tracker.setRecordingState(True)
    trial['TRIAL_START']=getTime()
    prev_evt_time=0
    while not keyboard.getKey(['q',]):
        win.flip()
        evts = tracker.getEvents(filter_id = 23)
        for evt in evts:
            if evt.type not in [EventConstants.MONOCULAR_EYE_SAMPLE, EventConstants.BINOCULAR_EYE_SAMPLE]:
                print evt.time, evt.time - prev_evt_time, EventConstants.getName(evt.type), evt.event_id#, evt.filter_id, evt.gaze_x, evt.gaze_y, evt.pupil_measure1, evt.velocity_x, evt.velocity_y, evt.velocity_xy, evt.status
                prev_evt_time = evt.time
    trial['TRIAL_END']=getTime()
    io.addRowToConditionVariableTable(trial.values())
    tracker.setRecordingState(False)

    tracker.resetFilter(*filter_path_and_file)
win.close()
io.quit()