# -*- coding: utf-8 -*-
from __future__ import division
from psychopy.iohub import EventConstants

IOHUB_DATA_FOLDER_PATH = r'..\..\track\results\first_exp'
IOHUB_DATA_FILE_NAME = 'iohub_events.hdf5'
SESSION_CODE = 'calc_evt_fields'

UNFILTERED_SAMPLE_TYPE = EventConstants.BINOCULAR_EYE_SAMPLE
FILTERED_SAMPLE_TYPE =  EventConstants.MONOCULAR_EYE_SAMPLE
FILTER_ID = 23

from psychopy.iohub.datastore.util import ExperimentDataAccessUtility
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.font_manager import FontProperties

dataAccessUtil = None

def loadEventFile(data_folder_path, file_name, session_name):
    global dataAccessUtil
    dataAccessUtil = ExperimentDataAccessUtility(data_folder_path, #IOHUB_DATA_FOLDER_PATH,
                                               file_name, #IOHUB_DATA_FILE_NAME,
                                               experimentCode=None,
                                               sessionCodes=[session_name, ])#SESSION_CODE,])

def closeEventFile():
    global dataAccessUtil
    if dataAccessUtil:
        dataAccessUtil.close()
        dataAccessUtil = None

def getRecordingPeriodSamples(event_type, event_fields, filter_id=0):
    global dataAccessUtil
    return dataAccessUtil.getEventAttributeValues(event_type,
                event_fields,
                filter_id = filter_id,
                conditionVariablesFilter=None,
                startConditions={'time':('>=','@TRIAL_START@')},
                endConditions={'time':('<=','@TRIAL_END@')},
                )

def getUnfilteredSamples():
    # Get unfiltered event data
    eye_field_names=['time', 'event_id', 'status']
    eye_specific_fields = ['gaze_x', 'gaze_y']#, 'pupil_measure1', ]
    if UNFILTERED_SAMPLE_TYPE == EventConstants.BINOCULAR_EYE_SAMPLE:
        for eye_prepend in ['left_','right_']:
            eye_field_names.extend([eye_prepend+f for f in eye_specific_fields])
    else:
        eye_field_names.extend(eye_specific_fields)

    return getRecordingPeriodSamples(UNFILTERED_SAMPLE_TYPE,
                                                   eye_field_names)

def getFilteredSamples():
    filtered_eye_field_names=['time', 'event_id', 'status']
    filtered_eye_specific_fields = ['gaze_x', 'gaze_y', 'raw_x', 'raw_y', 'velocity_x', 'velocity_y']#, 'pupil_measure1', 'velocity_xy']
    if FILTERED_SAMPLE_TYPE == EventConstants.BINOCULAR_EYE_SAMPLE:
        for eye_prepend in ['left_', 'right_']:
            filtered_eye_field_names.extend([eye_prepend+f for f in filtered_eye_specific_fields])
    else:
        filtered_eye_field_names.extend(filtered_eye_specific_fields)

    return getRecordingPeriodSamples(FILTERED_SAMPLE_TYPE,
                                               filtered_eye_field_names,
                                               FILTER_ID)


def plotSampleFieldTraces(sample_traces,session_code, recording_id):
    deg_pos_colors=((0.,1,0),(0.,0, 1))#,(0.,1, 1),(0.,0.,.25),(0.,0.,0.))
    velocity_colors=((1,.8,.2),(.25,0.0,0.25),(1,0.,0.),(1,0.25,0.25))

    time = sample_traces['time']

    fig = plt.figure('Session %s - Trial %d'%(session_code, recording_id+1), figsize=(12,8))
    plt.title("Filtered Eye Samples and Online Parsed Events\n( Session: %s, Recording: %d )"%(session_code, recording_id+1))

    ax = plt.gca()
    ax.plot(time, sample_traces['gaze']['x'], label='Horz. Pos. (Degrees)', color=deg_pos_colors[0])
    ax.plot(time, sample_traces['gaze']['y'], label='Vert. Pos. (Degrees)', color=deg_pos_colors[1])
    ax.set_xlabel('Time')
    ax.set_ylabel('Position (Degrees)',color=deg_pos_colors[-1])

    tmin=time.min()//1
    tmax=time.max()//1+1

    plt.xticks(np.arange(tmin, tmax, 0.5), rotation='vertical')
    trans = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)

    for tl in ax.get_yticklabels():
        tl.set_color(deg_pos_colors[-1])

    ax2 = ax.twinx()
#    ax2.plot(time, sample_traces['velocity']['x'],label='X Velocity',color=velocity_colors[0],alpha=0.5)
#    ax2.plot(time, sample_traces['velocity']['y'],label='Y Velocity',color=velocity_colors[1],alpha=0.5)
    ax2.plot(time, sample_traces['velocity']['x'],label='X Velocity',color=velocity_colors[0])
    ax2.plot(time, sample_traces['velocity']['y'],label='Y Velocity',color=velocity_colors[1])
    ax2.plot(time, sample_traces['velocity']['x_thresh'],label='X Velocity Threshold',color=velocity_colors[2])
    ax2.plot(time, sample_traces['velocity']['y_thresh'],label='Y Velocity Threshold',color=velocity_colors[3])
    ax2.set_ylabel('Velocity (degrees / second)',color=velocity_colors[1])
    for tl in ax2.get_yticklabels():
        tl.set_color(velocity_colors[-1])


    # Above Thresh data vertical bars (Saccades)
    ax.fill_between(time, 0, 1, where=(sample_traces['velocity']['x']-sample_traces['velocity']['x_thresh'])>=0, facecolor=(0.5,0,0), edgecolor=(0.5,0,0),
                    alpha=0.5, transform=trans)
    ax.fill_between(time, 0, 1, where=(sample_traces['velocity']['y']-sample_traces['velocity']['y_thresh'])>=0, facecolor=(0.5,0,0), edgecolor=(0.5,0,0),
                    alpha=0.5, transform=trans)

    # Missing data vertical bars
    ax.fill_between(time, 0, 1, where=sample_traces['status']==22, facecolor=(0,0,0), edgecolor=(0,0,0),
                    alpha=.95, transform=trans)


    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles.extend(handles2)
    labels.extend(labels2)
    #plt.legend(handles,labels,bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.) #plt.legend(loc=(1.01,.8))

    box = ax2.get_position()
    ax.set_position([box.x0, box.y0, box.width, box.height-.05])
    ax2.set_position([box.x0, box.y0, box.width, box.height-.05])
    fontP = FontProperties()
    fontP.set_size('small')
    plt.legend(handles,labels, loc='upper left', bbox_to_anchor=(.8, 1.15), borderaxespad=0,prop = fontP)

    plt.grid()
    plt.show()

if __name__ == '__main__':
    try:
        # Load iohub HDF5 file

        loadEventFile(IOHUB_DATA_FOLDER_PATH, IOHUB_DATA_FILE_NAME, SESSION_CODE)

        unfiltered_sample_data = getUnfilteredSamples()
        filtered_sample_data = getFilteredSamples()

        # Close iohub HDF5 file
        closeEventFile()

        # plot data for each recording period in the session

        for t, sample_data in enumerate(filtered_sample_data):
            # Create a mask to be used to define periods of
            # missing data in a data trace
            #
            sample_traces = dict()
            sample_traces['time'] = sample_data.time
            sample_traces['status'] = sample_data.status
            sample_traces['gaze'] = dict()
            sample_traces['gaze']['x'] = sample_data.gaze_x
            sample_traces['gaze']['y'] = sample_data.gaze_y
            #sample_traces['pupil'] = sample_data.pupil_measure1
            sample_traces['velocity'] = dict()
            sample_traces['velocity']['x'] = sample_data.velocity_x
            sample_traces['velocity']['y'] = sample_data.velocity_y
            #sample_traces['velocity']['xy'] = sample_data.velocity_xy
            sample_traces['velocity']['x_thresh'] = sample_data.raw_x
            sample_traces['velocity']['y_thresh'] = sample_data.raw_y
            sample_traces['invalid_data_mask'] = sample_data.status==22

            plotSampleFieldTraces(sample_traces, SESSION_CODE, t)
    except Exception, e:
        import traceback
        traceback.print_exc()
    finally:
        closeEventFile()
