# -*- coding: utf-8 -*-
from __future__ import division

import psychopy.iohub.devices.eventfilters as eventfilters
from psychopy.iohub import EventConstants, DeviceEvent, print2err
from psychopy.iohub.util import NumPyRingBuffer
from scipy.ndimage.filters import gaussian_filter1d
from scipy.signal import medfilt
from numpy import convolve
from timeit import default_timer as getTime
from collections import deque, OrderedDict
import numpy as np

############################### Constants ######################################

DISPLAY_SIZE_MM = (540, 300)
DISPLAY_RES_PIX = (1920, 1080)
DEFAULT_EYE_DISTANCE = 550

# Possible Event Filter Type Def's:
#
#   eventfilters.MovingWindowFilter, {length: 3, knot_pos:'center'}
#
#   eventfilters.PassThroughFilter, {}
#
#   eventfilters.MedianFilter, {length: 3, knot_pos:'center'}
#
#   eventfilters.WeightedAverageFilter, {weights: (25,50,25), knot_pos:'center'}
#
#   eventfilters.StampFilter, {level: 1}

POSITION_FILTER = eventfilters.PassThroughFilter, {}
VELOCITY_FILTER = eventfilters.PassThroughFilter, {}

################### Pixel to Visual Angle Calculation ##########################
"""
Pixel to Visual Angle Calculation.

Uses "symmetric angles" formula provided by Dr. Josh Borah
(jborah AT asleyetracking.com), via email corespondance in 2012.

Assumptions:
   1) unit origin == position 0.0, 0.0 == screen center
   2) Eye is orthoganal to origin of 2D plane

"""

import numpy as np

arctan = np.arctan2
rad2deg = np.rad2deg
hypot = np.hypot
np_abs = np.abs
np_sqrt = np.sqrt

class VisualAngleCalc(object):
    def __init__(self, display_size_mm, display_res_pix, eye_distance_mm=None):
        """
        Used to store calibrated surface information and eye to screen distance
        so that pixel positions can be converted to visual degree positions.

        Note: The information for display_size_mm,display_res_pix, and default
        eye_distance_mm could all be read automatically when opening a ioDataStore
        file. This automation should be implemented in a future release.
        """
        self._display_width = display_size_mm[0]
        self._display_height = display_size_mm[1]
        self._display_x_resolution = display_res_pix[0]
        self._display_y_resolution = display_res_pix[1]
        self._eye_distance_mm = eye_distance_mm
        self.mmpp_x = self._display_width / self._display_x_resolution
        self.mmpp_y = self._display_height / self._display_y_resolution

    def pix2deg(self, pixel_x, pixel_y=None, eye_distance_mm=None):
        """
        Stimulus positions (pixel_x,pixel_y) are defined in x and y pixel units,
        with the origin (0,0) being at the **center** of the display, as to match
        the PsychoPy pix unit coord type.

        The pix2deg method is vectorized, meaning that is will perform the
        pixel to angle calculations on all elements of the provided pixel
        position numpy arrays in one numpy call.

        The conversion process can use either a fixed eye to calibration
        plane distance, or a numpy array of eye distances passed as
        eye_distance_mm. In this case the eye distance array must be the same
        length as pixel_x, pixel_y arrays.
        """
        eye_dist_mm = self._eye_distance_mm
        if eye_distance_mm is not None:
            eye_dist_mm = eye_distance_mm

        x_mm = self.mmpp_x * pixel_x
        y_mm = self.mmpp_y * pixel_y

        Ah = arctan(x_mm, hypot(eye_dist_mm, y_mm))
        Av = arctan(y_mm, hypot(eye_dist_mm, x_mm))

        return rad2deg(Ah), rad2deg(Av)

################################################################################
MONOCULAR_EYE_SAMPLE = EventConstants.MONOCULAR_EYE_SAMPLE
BINOCULAR_EYE_SAMPLE = EventConstants.BINOCULAR_EYE_SAMPLE
FIXATION_START = EventConstants.FIXATION_START
FIXATION_END = EventConstants.FIXATION_END
SACCADE_START = EventConstants.SACCADE_START
SACCADE_END = EventConstants.SACCADE_END
BLINK_START = EventConstants.BLINK_START
BLINK_END = EventConstants.BLINK_END

NO_EYE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
BOTH_EYE = 3

# Event Filter Types:
#   MovingWindowFilter(length, event_type, event_field_name, knot_pos='center', inplace = True)
#   PassThroughFilter(event_type, event_field_name)
#   MedianFilter(length, event_type, event_field_name, knot_pos='center', inplace = True)
#   WeightedAverageFilter(weights, event_type, event_field_name, knot_pos='center', inplace = True)
#   StampFilter(event_type, event_field_name, level=1, inplace = True)

class EyeTrackerEventParser(eventfilters.DeviceEventFilter):
    def __init__(self):
        eventfilters.DeviceEventFilter.__init__(self)
        self.sample_type = None
        self.io_sample_class = None
        self.io_event_ix = None

        self.last_valid_sample = None
        self.last_sample = None
        self.invalid_samples_run = []

        pos_filter_class, pos_filter_kwargs = POSITION_FILTER
        pos_filter_kwargs['event_type'] = MONOCULAR_EYE_SAMPLE
        pos_filter_kwargs['inplace'] = True
        pos_filter_kwargs['event_field_name'] = 'gaze_x'
        self.x_position_filter = pos_filter_class(**pos_filter_kwargs)
        pos_filter_kwargs['event_field_name'] = 'gaze_y'
        self.y_position_filter = pos_filter_class(**pos_filter_kwargs)

        vel_filter_class, vel_filter_kwargs = VELOCITY_FILTER
        vel_filter_kwargs['event_type'] = MONOCULAR_EYE_SAMPLE
        vel_filter_kwargs['inplace'] = True
        vel_filter_kwargs['event_field_name'] = 'velocity_x'
        self.x_velocity_filter = vel_filter_class(**vel_filter_kwargs)
        vel_filter_kwargs['event_field_name'] = 'velocity_y'
        self.y_velocity_filter = vel_filter_class(**vel_filter_kwargs)
        vel_filter_kwargs['event_field_name'] = 'velocity_xy'
        self.xy_velocity_filter = vel_filter_class(**vel_filter_kwargs)

        # function vars
        self.convertEvent = None
        self.isValidSample = None
        ###

        self.visual_angle_calc = VisualAngleCalc(DISPLAY_SIZE_MM,
                                                 DISPLAY_RES_PIX,
                                                 DEFAULT_EYE_DISTANCE)
        self.pix2deg = self.visual_angle_calc.pix2deg

    @property
    def filter_id(self):
        return 23

    @property
    def input_event_types(self):
        event_type_and_filter_ids = dict()
        event_type_and_filter_ids[BINOCULAR_EYE_SAMPLE] = [0, ]
        event_type_and_filter_ids[MONOCULAR_EYE_SAMPLE] = [0, ]
        return event_type_and_filter_ids

    def process(self):
        """
        """
        samples_for_processing = []
        for in_evt in self.getInputEvents():
            if self.sample_type is None:
                self.initializeForSampleType(in_evt)

            # If event is binocular, convert to monocular.
            # Regardless of type, convert pix to angle positions and calculate
            # unfiltered velocity data.
            current_mono_evt = self.convertEvent(self.last_sample, in_evt)

            is_valid = self.isValidSample(current_mono_evt)
            if is_valid:
                # If sample is valid (no missing pos data), first
                # check for a previous missing data run and handle.
                if self.invalid_samples_run:
                    if self.last_valid_sample:
                        samples_for_processing.extend(self.interpolateMissingData(current_mono_evt))
                        self._addVelocity(samples_for_processing[-1], current_mono_evt)
                    # Discard all invalid samples that occurred prior
                    # to the first valid sample.
                    del self.invalid_samples_run[:]

                # Then add current event to field filters. If a filtered event
                # is returned, add it to the to be processed sample list.
                filtered_event = self.addToFieldFilters(current_mono_evt)
                if filtered_event:
                    filtered_event, _ = filtered_event
                    samples_for_processing.append(filtered_event)
                self.last_valid_sample = current_mono_evt
            else:

                self.invalid_samples_run.append(current_mono_evt)


            self.last_sample = current_mono_evt

        # TODO: Parse filtered events, output as created.!!
        # .....

        # Add any new filtered samples to be output.
        for s in samples_for_processing:
            self.addOutputEvent(s)
        self.clearInputEvents()

    def reset(self):
        eventfilters.DeviceEventFilter.reset(self)
        self.last_valid_sample = None
        self.last_sample = None
        self.invalid_samples_run = []
        self.x_position_filter.clear()
        self.y_position_filter.clear()
        self.x_velocity_filter.clear()
        self.y_velocity_filter.clear()
        self.xy_velocity_filter.clear()

    def initializeForSampleType(self,in_evt):
        self.sample_type = MONOCULAR_EYE_SAMPLE  #in_evt[DeviceEvent.EVENT_TYPE_ID_INDEX]
        self.io_sample_class = EventConstants.getClass(self.sample_type)
        self.io_event_fields = self.io_sample_class.CLASS_ATTRIBUTE_NAMES
        self.io_event_ix = self.io_sample_class.CLASS_ATTRIBUTE_NAMES.index

        if in_evt[DeviceEvent.EVENT_TYPE_ID_INDEX] == BINOCULAR_EYE_SAMPLE:
            self.convertEvent = self._convertToMonoAveraged
            self.isValidSample = lambda x: x[self.io_event_ix('status')] != 22
        else:
            self.convertEvent = self._convertMonoFields
            self.isValidSample = lambda x: x[self.io_event_ix('status')] == 0

    def interpolateMissingData(self, current_sample):
        samples_for_processing = []
        invalid_sample_count = len(self.invalid_samples_run)
        gx_ix = self.io_event_ix('gaze_x')
        gy_ix = self.io_event_ix('gaze_y')
        ps_ix = self.io_event_ix('pupil_measure1')
        starting_gx = self.last_valid_sample[gx_ix]
        starting_gy = self.last_valid_sample[gy_ix]
        starting_ps = self.last_valid_sample[ps_ix]
        ending_gx = current_sample[gx_ix]
        ending_gy = current_sample[gy_ix]
        ending_ps = current_sample[ps_ix]
        x_interp = np.linspace(starting_gx, ending_gx, num=invalid_sample_count+2)[1:-1]
        y_interp = np.linspace(starting_gy, ending_gy, num=invalid_sample_count+2)[1:-1]
        p_interp = np.linspace(starting_ps, ending_ps, num=invalid_sample_count+2)[1:-1]
        print2err('>>>>')
        print2err('invalid_sample_count: ', invalid_sample_count)
        print2err('starting_gx, ending_gx: ', starting_gx,', ',ending_gx)
        print2err('x_interp: ', x_interp)
        print2err('starting_gy, ending_gy: ', starting_gx,', ',ending_gx)
        print2err('y_interp: ', y_interp)
        print2err('<<<<')

        prev_samp = self.last_valid_sample
        # interpolate missing sample values, adding to pos and vel filters
        for ix, curr_samp in enumerate(self.invalid_samples_run):
            curr_samp[gx_ix] = x_interp[ix]
            curr_samp[gy_ix] = y_interp[ix]
            curr_samp[ps_ix] = p_interp[ix]
            self._addVelocity(prev_samp, curr_samp)
            filtered_event = self.addToFieldFilters(curr_samp)
            if filtered_event:
                filtered_event, _ = filtered_event
                samples_for_processing.append(filtered_event)
            prev_samp = curr_samp
        return samples_for_processing

    def addToFieldFilters(self, sample):
        self.x_position_filter.add(sample)
        self.y_position_filter.add(sample)
        self.x_velocity_filter.add(sample)
        self.y_velocity_filter.add(sample)
        return self.xy_velocity_filter.add(sample)

    def _convertPosToAngles(self, mono_event):
        gx_ix = self.io_event_ix('gaze_x')
        gx_iy = self.io_event_ix('gaze_y')
        mono_event[gx_ix], mono_event[gx_iy] = self.pix2deg(mono_event[gx_ix], mono_event[gx_iy])

    def _addVelocity(self, prev_event, current_event):
        io_ix = self.io_event_ix

        dx = np_abs(current_event[io_ix('gaze_x')] - prev_event[io_ix('gaze_x')])
        dy = np_abs(current_event[io_ix('gaze_y')] - prev_event[io_ix('gaze_y')])
        dt = current_event[io_ix('time')] - prev_event[io_ix('time')]

        current_event[io_ix('velocity_x')] = dx/dt
        current_event[io_ix('velocity_y')] = dy/dt
        current_event[io_ix('velocity_xy')] = np.hypot(dx/dt, dy/dt)

    def _convertMonoFields(self, prev_event, current_event):
        if self.isValidSample(current_event):
            self._convertPosToAngles(self, current_event)
            if prev_event:
                self._addVelocity(prev_event, current_event)

    def _convertToMonoAveraged(self, prev_event, current_event):
        mono_evt=[]
        binoc_field_names = EventConstants.getClass(BINOCULAR_EYE_SAMPLE).CLASS_ATTRIBUTE_NAMES
        status = current_event[binoc_field_names.index('status')]
        for field in self.io_event_fields:
            if field in binoc_field_names:
                mono_evt.append(current_event[binoc_field_names.index(field)])
            elif field == 'eye':
                mono_evt.append(LEFT_EYE)
            else:
                if status == 0:
                    lfv = float(current_event[binoc_field_names.index('left_%s'%(field))])
                    rfv = float(current_event[binoc_field_names.index('right_%s'%(field))])
                    mono_evt.append((lfv+rfv)/2.0)
                elif status == 2:
                    mono_evt.append(float(current_event[binoc_field_names.index('left_%s'%(field))]))
                elif status == 20:
                    mono_evt.append(float(current_event[binoc_field_names.index('right_%s'%(field))]))
                elif status == 22:
                    # both eyes have missing data, so use data from left eye (does not really matter)
                    mono_evt.append(float(current_event[binoc_field_names.index('left_%s'%(field))]))
                else:
                    ValueError("Unknown Sample Status: %d"%(status))
        mono_evt[self.io_event_fields.index('type')] = MONOCULAR_EYE_SAMPLE
        if self.isValidSample(mono_evt):
            self._convertPosToAngles(mono_evt)
            if prev_event:
                self._addVelocity(prev_event, mono_evt)
        return mono_evt

    def _binocSampleValidEyeData(self, sample):
        evt_status = sample[self.io_event_ix('status')]
        if evt_status == 0:
            # both eyes are valid
            return BOTH_EYE
        elif evt_status == 20: # right eye data only
            return RIGHT_EYE
        elif evt_status == 2: # left eye data only
            return LEFT_EYE
        elif evt_status == 22: # both eye data missing
            return NO_EYE

'''
################################################################################
MONO_EYE = 0
LEFT_EYE = 0
RIGHT_EYE = 1


FIXATION_START = 1
FIXATION_END = 2
SACCADE_START = 3
SACCADE_END = 4
MISSING_START = 5
MISSING_END = 6


DISPLAY_SIZE_MM = (540, 300)
DISPLAY_RES_PIX = (1920, 1080)
DEFAULT_EYE_DISTANCE = 550

#TRACKER_FPS = 30
TRACKER_FPS = 60
#TRACKER_FPS = 120

# Buffer Sizes....
MAX_FILTER_WIN_SIZE = 10

SAMPLE_ARRAY_ROWS = TRACKER_FPS*60
print2err("\n*SAMPLE_ARRAY_ROWS: ", SAMPLE_ARRAY_ROWS)


VELOCITY_HISTORY_LENGTH = int(TRACKER_FPS * 15)
print2err("\n*VELOCITY_HISTORY_LENGTH: ", VELOCITY_HISTORY_LENGTH)

# Filtering Settings....
VELOCITY_FILTER_DURATION = 0.03333333 # in sec
VELOCITY_FILTER_WIN_SIZE = int(TRACKER_FPS * VELOCITY_FILTER_DURATION)  # in samples
if VELOCITY_FILTER_WIN_SIZE%2==0:
    VELOCITY_FILTER_WIN_SIZE+=1
if VELOCITY_FILTER_WIN_SIZE != 0 and VELOCITY_FILTER_WIN_SIZE < 3:
    VELOCITY_FILTER_WIN_SIZE = 3
VELOCITY_FILTER_TYPE = 'median'
print2err("\nVELOCITY_FILTER_DURATION: ", VELOCITY_FILTER_DURATION)
print2err("*VELOCITY_FILTER_WIN_SIZE: ", VELOCITY_FILTER_WIN_SIZE)
print2err("*VELOCITY_FILTER_TYPE: ", VELOCITY_FILTER_TYPE)

POSITION_FILTER_DURATION = 0.05 # in sec
POSITION_FILTER_WIN_SIZE = int(TRACKER_FPS * POSITION_FILTER_DURATION)  # in samples
if POSITION_FILTER_WIN_SIZE%2 == 0:
    POSITION_FILTER_WIN_SIZE += 1
if POSITION_FILTER_DURATION != 0 and POSITION_FILTER_WIN_SIZE < 3:
    POSITION_FILTER_WIN_SIZE = 3
POSITION_FILTER_TYPE = 'median'
print2err("\nPOSITION_FILTER_DURATION: ", POSITION_FILTER_DURATION)
print2err("*POSITION_FILTER_WIN_SIZE: ", POSITION_FILTER_WIN_SIZE)
print2err("*POSITION_FILTER_TYPE: ", POSITION_FILTER_TYPE)
# Heuristics

INTERP_MISSING_DATA = max(VELOCITY_FILTER_WIN_SIZE, POSITION_FILTER_WIN_SIZE)

MIN_PARSER_SAMPLE_BLOCK = TRACKER_FPS*2.0

MIN_BLINK_SAMPLES = 2

MIN_SACCADE_DURATION = 0.01
MIN_SACCADE_SAMPLES = int(max(TRACKER_FPS*MIN_SACCADE_DURATION,1))
#Thresholds

MIN_FIXATION_DURATION = 0.025
MIN_FIXATION_SAMPLES = int(max(TRACKER_FPS*MIN_FIXATION_DURATION,2))

MIN_EVENT_SAMPLES = dict(SAC=MIN_SACCADE_SAMPLES, FIX=MIN_FIXATION_SAMPLES, MIS=MIN_BLINK_SAMPLES)
print2err("*MIN_EVENT_SAMPLES: ", MIN_EVENT_SAMPLES)
VELOCITY_THRESHOLD = 30.0
#####################################################

PROC_SAMPLE_ID_INDEX = 0
PROC_SAMPLE_TIME_INDEX = 1
PROC_SAMPLE_X_INDEX = 2
PROC_SAMPLE_Y_INDEX = 3
PROC_SAMPLE_PS_INDEX = 4
PROC_SAMPLE_VX_INDEX = 5
PROC_SAMPLE_VY_INDEX = 6
PROC_SAMPLE_VXY_INDEX = 7
PROC_SAMPLE_AX_INDEX = 8
PROC_SAMPLE_AY_INDEX = 9
PROC_SAMPLE_VEL_THRESH_INDEX = 10
PROC_SAMPLE_VALID_INDEX = 11
PROC_SAMPLE_ARRAY_SIZE = PROC_SAMPLE_VALID_INDEX+1

class ParserDataCache(object):
    """
    Holds data needed for parsing of a single eye data stream.
    Binoc data will have 2.
    """
    def __init__(self, eye, iosample_class):
        self.eye_index = eye
        self.iosample_class = iosample_class
        self.iosample_type_id = iosample_class.EVENT_TYPE_ID
        self.io_ix = self.iosample_class.CLASS_ATTRIBUTE_NAMES.index
        self.current_sample_index = -1
        self.sample_array = np.zeros((SAMPLE_ARRAY_ROWS, PROC_SAMPLE_ARRAY_SIZE),
                                     dtype=np.float64)
        self.missing_data_sample_ixs = []

        self.last_velocity_filtered_index = 0
        self.last_position_filtered_index = 0

        self.velocity_history = np.zeros(VELOCITY_HISTORY_LENGTH, dtype=np.float64)
        self.velocity_history_index = -1
        self.velocity_threshold = 30.0

        self.last_parsed_index = 0
        self.prev_event_category = None

        self.iosample_ix_mapping = None
        if self.iosample_type_id == EventConstants.MONOCULAR_EYE_SAMPLE:
            self.iosample_ix_mapping = (self.io_ix('event_id'),
                                        self.io_ix('time'),
                                        self.io_ix('gaze_x'),
                                        self.io_ix('gaze_y'),
                                        self.io_ix('pupil_measure1'),
                                        self.io_ix('velocity_x'),
                                        self.io_ix('velocity_y'),
                                        self.io_ix('velocity_xy'),
                                        -1,
                                        -1,
                                        -1,
                                        self.io_ix('status'))
        elif self.iosample_type_id == EventConstants.BINOCULAR_EYE_SAMPLE:
            if self.eye_index == LEFT_EYE:
                self.iosample_ix_mapping = (self.io_ix('event_id'),
                                            self.io_ix('time'),
                                            self.io_ix('left_gaze_x'),
                                            self.io_ix('left_gaze_y'),
                                            self.io_ix('left_pupil_measure1'),
                                            self.io_ix('left_velocity_x'),
                                            self.io_ix('left_velocity_y'),
                                            self.io_ix('left_velocity_xy'),
                                            -1,
                                            -1,
                                            -1,
                                            self.io_ix('status'))
            else:
                self.iosample_ix_mapping = (self.io_ix('event_id'),
                                            self.io_ix('time'),
                                            self.io_ix('right_gaze_x'),
                                            self.io_ix('right_gaze_y'),
                                            self.io_ix('right_pupil_measure1'),
                                            self.io_ix('right_velocity_x'),
                                            self.io_ix('right_velocity_y'),
                                            self.io_ix('right_velocity_xy'),
                                            -1,
                                            -1,
                                            -1,
                                            self.io_ix('status'))

    def addSampleEvent(self, iosample, valid):
        return_samples = []
        eye_label='RIGHT'
        if self.eye_index==0:
            eye_label='LEFT'

        if self.current_sample_index < 0 and not valid:
            print2err("Dropping %s Parsing Sample. Not valid sample before it."%(eye_label))
            return []

        # Check sample index relative to SAMPLE_ARRAY_ROWS. If close to end,
        # shift and data earlier and update all index references.
        self.shiftSampleData()

        self.current_sample_index += 1
        ioix = self.iosample_ix_mapping
        #if self.eye_index==0:
            #print2err("Adding %s Parsing Sample ID: %d to index %d."%(eye_label,iosample[ioix[PROC_SAMPLE_ID_INDEX]],self.current_sample_index))
        if valid:
            self.sample_array[self.current_sample_index, :] = (
                                        iosample[ioix[PROC_SAMPLE_ID_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_TIME_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_X_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_Y_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_PS_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_VX_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_VY_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_VXY_INDEX]],
                                        np.NaN, np.NaN, np.NaN, valid)
            #if self.eye_index==0:
            #    print2err("%s Parsing Sample is Valid."%(eye_label))
        else:
            #if self.eye_index==0:
            #    print2err("%s Parsing Sample is INVALID."%(eye_label))

            self.sample_array[self.current_sample_index, :] = (
                                        iosample[ioix[PROC_SAMPLE_ID_INDEX]],
                                        iosample[ioix[PROC_SAMPLE_TIME_INDEX]],
                                        np.NaN, np.NaN, np.NaN, np.NaN, np.NaN,
                                        np.NaN, np.NaN, np.NaN, np.NaN, valid)
            self.missing_data_sample_ixs.append(self.current_sample_index)

        # Velocity Calc.
        if self.current_sample_index > 0 and valid:
            if not self.isPreviousSampleValid() and len(self.missing_data_sample_ixs)>0:
                # Missing data sample handling
                msamps = self.fillMissingDataGap()
                return_samples.extend(msamps)

            # Filter position Data
            self.filterPositionData()
            #self.last_position_filtered_index = self.current_sample_index
            #if self.eye_index==0:
            #    print2err("%s Sample, index %d Velocity Calc..."%(eye_label, self.current_sample_index))
            current_sample = self.getCurrentSample()
            prev_sample = self.getPreviousSample()
            dx = np_abs(current_sample[PROC_SAMPLE_X_INDEX]-prev_sample[PROC_SAMPLE_X_INDEX])
            dy = np_abs(current_sample[PROC_SAMPLE_Y_INDEX]-prev_sample[PROC_SAMPLE_Y_INDEX])
            dt = current_sample[PROC_SAMPLE_TIME_INDEX]-prev_sample[PROC_SAMPLE_TIME_INDEX]
            current_sample[PROC_SAMPLE_VX_INDEX] = dx / dt
            current_sample[PROC_SAMPLE_VY_INDEX] = dy / dt
            vxy = np.hypot(current_sample[PROC_SAMPLE_VX_INDEX],
                       current_sample[PROC_SAMPLE_VY_INDEX])
            current_sample[PROC_SAMPLE_VXY_INDEX] = vxy
            self.filterVelocityData()
            #self.last_velocity_filtered_index = self.current_sample_index

            vt = self.updateVelocityThreshold(vxy)
            if vt:
                current_sample[PROC_SAMPLE_VEL_THRESH_INDEX]=vt
            #if self.eye_index==0:
            #    print2err('vx: %.3f, vy: %.3f, vxy: %.3f '%(current_sample[PROC_SAMPLE_VX_INDEX],
            #           current_sample[PROC_SAMPLE_VY_INDEX], vxy))

            return_samples.append(current_sample)
            return return_samples
        return []

    def shiftSampleData(self):
        #Ideally, shift shen there are no indexes in the missing_data_sample_ixs
        if self.current_sample_index >= int(SAMPLE_ARRAY_ROWS*0.8):
            if len(self.missing_data_sample_ixs) == 0:
                print2err("$$ Shifting samples:\nPRE:")
                print2err("\tcurrent_sample_index: ", self.current_sample_index)
                print2err("\tlast_parsed_index: ", self.last_parsed_index)
                print2err("\tlast_velocity_filtered_index: ", self.last_velocity_filtered_index)
                print2err("\tlast_position_filtered_index: ", self.last_position_filtered_index)
                print2err("\tlen(missing_data_sample_ixs): ", len(self.missing_data_sample_ixs))

                shift_by = min(self.last_velocity_filtered_index,self.last_position_filtered_index, self.last_parsed_index)
                new_ci = self.current_sample_index - shift_by
                print2err("\tshift_by: ", shift_by)
                print2err("\tnew_ci: ", new_ci)
                self.sample_array[:new_ci] = self.sample_array[shift_by:self.current_sample_index]
                self.current_sample_index = new_ci
                self.last_parsed_index -= shift_by
                self.last_velocity_filtered_index -= shift_by
                self.last_position_filtered_index -= shift_by
                print2err("POST, shift by: ", shift_by)
                print2err("\tcurrent_sample_index: ", self.current_sample_index)
                print2err("\tlast_parsed_index: ", self.last_parsed_index)
                print2err("\tlast_velocity_filtered_index: ", self.last_velocity_filtered_index)
                print2err("\tlast_position_filtered_index: ", self.last_position_filtered_index)
                print2err("\tlen(missing_data_sample_ixs): ", len(self.missing_data_sample_ixs))
                print2err("\n\n")
        if self.current_sample_index >= SAMPLE_ARRAY_ROWS:
            print2err("********** PARSER FAILURE ************")
            print2err("current_sample_index: ", self.current_sample_index)
            print2err("last_parsed_index: ", self.last_parsed_index)
            print2err("last_velocity_filtered_index: ", self.last_velocity_filtered_index)
            print2err("last_position_filtered_index: ", self.last_position_filtered_index)
            print2err("len(missing_data_sample_ixs): ", len(self.missing_data_sample_ixs))
            print2err("**** ALL BUFFERED SAMPLES DROPPED ****")
            self.current_sample_index = -1
            self.last_parsed_index = 0
            self.last_velocity_filtered_index = 0
            self.last_position_filtered_index = 0

    def filterPositionData(self):
        findex = self.last_position_filtered_index
        cindex = self.current_sample_index
        if cindex-findex >= POSITION_FILTER_WIN_SIZE*2:
            x = self.sample_array[findex:cindex, PROC_SAMPLE_X_INDEX]
            y = self.sample_array[findex:cindex, PROC_SAMPLE_Y_INDEX]
            if POSITION_FILTER_TYPE == 'gauss':
                self.sample_array[findex:cindex, PROC_SAMPLE_X_INDEX] = gaussian_filter1d(x,POSITION_FILTER_WIN_SIZE)
                self.sample_array[findex:cindex, PROC_SAMPLE_Y_INDEX] = gaussian_filter1d(y,POSITION_FILTER_WIN_SIZE)
            elif POSITION_FILTER_TYPE == 'median':
                self.sample_array[findex:cindex, PROC_SAMPLE_X_INDEX] = medfilt(x,POSITION_FILTER_WIN_SIZE)
                self.sample_array[findex:cindex, PROC_SAMPLE_Y_INDEX] = medfilt(y,POSITION_FILTER_WIN_SIZE)
            elif POSITION_FILTER_TYPE == 'average':
                weights = np.asarray([1.0,]*POSITION_FILTER_WIN_SIZE)#kwargs.get('weights',[1.,2.,3.,2.,1.]))
                #weights= weights/np.sum(weights)
                self.sample_array[findex:cindex, PROC_SAMPLE_X_INDEX] = np.convolve(x, weights, 'same')
                self.sample_array[findex:cindex, PROC_SAMPLE_Y_INDEX] = np.convolve(y, weights, 'same')
            self.last_position_filtered_index = cindex

    def filterVelocityData(self):
        findex = self.last_velocity_filtered_index
        cindex = self.current_sample_index
        if cindex-findex >= VELOCITY_FILTER_WIN_SIZE*2:
            x = self.sample_array[findex:cindex, PROC_SAMPLE_VX_INDEX]
            y = self.sample_array[findex:cindex, PROC_SAMPLE_VY_INDEX]
            if POSITION_FILTER_TYPE=='gauss':
                self.sample_array[findex:cindex, PROC_SAMPLE_VX_INDEX] = gaussian_filter1d(x,VELOCITY_FILTER_WIN_SIZE)
                self.sample_array[findex:cindex, PROC_SAMPLE_VY_INDEX] = gaussian_filter1d(y,VELOCITY_FILTER_WIN_SIZE)
            elif POSITION_FILTER_TYPE=='median':
                self.sample_array[findex:cindex, PROC_SAMPLE_VX_INDEX] = medfilt(x,VELOCITY_FILTER_WIN_SIZE)
                self.sample_array[findex:cindex, PROC_SAMPLE_VY_INDEX] = medfilt(y,VELOCITY_FILTER_WIN_SIZE)
            elif POSITION_FILTER_TYPE=='average':
                weights = np.asarray([1.0,]*VELOCITY_FILTER_WIN_SIZE)#kwargs.get('weights',[1.,2.,3.,2.,1.]))
                #weights= weights/np.sum(weights)
                self.sample_array[findex:cindex, PROC_SAMPLE_VX_INDEX] = np.convolve(x, weights, 'same')
                self.sample_array[findex:cindex, PROC_SAMPLE_VY_INDEX] = np.convolve(y, weights, 'same')
            else:
                raise ValueError('Unknown Filter Type: %s. Must be one of %s'%(POSITION_FILTER_TYPE,str(['average','gauss','median'])))
            self.last_velocity_filtered_index = cindex


    def fillMissingDataGap(self):
        return_samples=[]
        invalid_sample_count = len(self.missing_data_sample_ixs)
        #if self.eye_index==0:
        #    print2err("MISSING SAMPLE GAP FILL: ",invalid_sample_count)
        start_valid_sample_index = self.missing_data_sample_ixs[0]-1
        last_valid_sample = self.sample_array[start_valid_sample_index]
        current_sample = self.getCurrentSample()
        starting_gx = last_valid_sample[PROC_SAMPLE_X_INDEX]
        starting_gy = last_valid_sample[PROC_SAMPLE_Y_INDEX]
        starting_ps = last_valid_sample[PROC_SAMPLE_PS_INDEX]
        ending_gx = current_sample[PROC_SAMPLE_X_INDEX]
        ending_gy = current_sample[PROC_SAMPLE_Y_INDEX]
        ending_ps = current_sample[PROC_SAMPLE_PS_INDEX]
        x_interp = np.linspace(starting_gx, ending_gx, num=invalid_sample_count+2)[1:-1]
        y_interp = np.linspace(starting_gy, ending_gy, num=invalid_sample_count+2)[1:-1]
        p_interp = np.linspace(starting_ps, ending_ps, num=invalid_sample_count+2)[1:-1]

        for i, sample_index in enumerate(self.missing_data_sample_ixs):
            #if self.eye_index==0:
            #    print2err("\tFill Sample index %d: ",sample_index)

            csample = self.sample_array[sample_index]
            csample[PROC_SAMPLE_X_INDEX] = x_interp[i]
            csample[PROC_SAMPLE_Y_INDEX] = y_interp[i]
            csample[PROC_SAMPLE_PS_INDEX] = p_interp[i]
            if sample_index > 0:
                #if self.eye_index==0:
                #    print2err("\tVel calc for missing data index %d: ",sample_index)
                psample = self.sample_array[sample_index-1]
                dx = np_abs(csample[PROC_SAMPLE_X_INDEX]-psample[PROC_SAMPLE_X_INDEX])
                dy = np_abs(csample[PROC_SAMPLE_Y_INDEX]-psample[PROC_SAMPLE_Y_INDEX])
                dt = csample[PROC_SAMPLE_TIME_INDEX]-psample[PROC_SAMPLE_TIME_INDEX]
                csample[PROC_SAMPLE_VX_INDEX] = dx / dt
                csample[PROC_SAMPLE_VY_INDEX] = dy / dt
                #if self.eye_index==0:
                #    print2err("\tVel calc for miss: ",csample[PROC_SAMPLE_VX_INDEX]," , ",csample[PROC_SAMPLE_VY_INDEX])
            return_samples.append(csample)

        self.missing_data_sample_ixs = []

        return return_samples

    def getCurrentSample(self):
        return self.sample_array[self.current_sample_index]

    def getCurrentSampleID(self):
        return self.sample_array[self.current_sample_index][PROC_SAMPLE_ID_INDEX]

    def isCurrentSampleValid(self):
        return self.sample_array[self.current_sample_index][PROC_SAMPLE_VALID_INDEX] > 0.0

    def getPreviousSample(self):
        if self.current_sample_index>=1:
            return self.sample_array[self.current_sample_index-1]
        return None

    def isPreviousSampleValid(self):
        if self.current_sample_index>=1:
            return self.sample_array[self.current_sample_index-1][PROC_SAMPLE_VALID_INDEX] > 0.0
        return None

    def getLastValidSample(self):
        if self.last_valid_sample_index >= 0:
            return self.sample_array[self.last_valid_sample_index]
        return None

    def canParse(self):
        return self.velocity_history_index > VELOCITY_HISTORY_LENGTH

    def getVelocityThreshold(self):
        return self.velocity_threshold

    def updateVelocityThreshold(self, v):
        #t1=getTime()
        self.velocity_history_index += 1
        vi = self.velocity_history_index%VELOCITY_HISTORY_LENGTH
        vel_array = self.velocity_history
        vel_array[vi] = v

        if self.velocity_history_index > VELOCITY_HISTORY_LENGTH:
            PT = vel_array.min()+vel_array.std()*3.0
            velocity_below_thresh = vel_array[vel_array < PT]
            PTd = 2.0
            pt_list = [PT,]
            while PTd >= 1.0:
                if len(pt_list) > 0:
                    PT = velocity_below_thresh.mean()+3.0*velocity_below_thresh.std()
                    velocity_below_thresh = vel_array[vel_array < PT]
                    PTd=np.abs(PT-pt_list[-1])
                pt_list.append(PT)
            self.velocity_threshold = PT
            #t2=getTime()
            #if self.eye_index==0:
            #    print2err("ADAPTED VELOCITY: iterations %d. Values: "%(len(pt_list)),pt_list)
            return PT
        return None

class EyeSamplePositionFilter(object):
    """
    Input: Non filtered eye tracker samples (one at a time)
    output: Eye tracker samples with the following changes:
        - position converted to visual angles
        - position filtered based on fiter settings ( 0 - N samples can be returned)
    Input and output samples are toi be in iohub event list format.
    """
    def __init__(self, filter_type, window_size):
        self.visual_angle_calc = VisualAngleCalc(DISPLAY_SIZE_MM,
                                                 DISPLAY_RES_PIX,
                                                 DEFAULT_EYE_DISTANCE)
        self.pix2deg = self.visual_angle_calc.pix2deg


        self.input_samples = deque(maxlen=window_size)
        self.x_pos_window = NumPyRingBuffer(window_size)
        self.y_pos_window = NumPyRingBuffer(window_size)

        self.missing_data_samples=[]

    def addSample(self, sample):
        pass

    def getAvailableSampleOutput(self):
        pass



class EyeSampleFilter(DeviceEventFilter):
    """
    General design:
        I) iohub sample event intake:
            1) Filter takes in 1 eye sample at a time
                a) if binocular, split into left and right sample data dicts
                   for filtering.
                b) if mono, create single sample data dict for filtering.
            <!! DONE TO HERE !!>
            2) sample is stored in internal list
            3) if sample is missing data:
                  a) store prev sample as last sample before gap
                  b) go to I.1.
            4) if sample is ok:
                  a) convert pix to angles
                  b) if prev sample was OK:
                        i) move sample to "angle_units_sample_list".
                  c) if prev sample was missing data:
                        i) interpolate x,y pos for samples during gap (in angle units)
                       ii) move each interpolated sample to "angle_units_sample_list"

        II) angle_units_sample_list processing:
            1) For each sample in angle_units_sample_list
                a) add to 'filter_pos_window_buffer'
                b) if 'filter_pos_window_buffer' is not full
                    i) go to II.1
                c) if 'filter_pos_window_buffer' is full:
                    i) Get pos filtered sample
                    ii) Add pos filtered sample to 'filtering_vel_accel_buffer'
            2) If angle_units_sample_list is empty:
                a) go to III.
        III) filtering_vel_accel_buffer processing:
            1) If not full, go to I.
            2) If full
                a) Get fully filtered sample from buffer
                b) If fully filtered sample is valid (i.e. was not interpolated):
                    i) Adjust adaptive vel (and accell?) thresholds.
                c) Add fully filtered sample to event_parser_sample_list
        IV) event_parser_sample_list processing:
            General notes:
               - this is the list ( no max length ) that events are parsed from.
               - event types: FIX, SACC, BLINK_MISSING
               - each event type has a START and END event version
               - samples are not removed from list until an END event is detected.
               - consecutive invalid sample length must be > a thresh to result
                 in BLINK_START / END events. If under threshold length, they are
                 included in saccade / fix parsing, using their interpolated values.
            Rest of sudo logic TBC....
    """
    MONOC_SAMPLE = EventConstants.MONOCULAR_EYE_SAMPLE
    BINOC_SAMPLE = EventConstants.BINOCULAR_EYE_SAMPLE
    def __init__(self):
        DeviceEventFilter.__init__(self)
        self.sample_type = None
        self.io_sample_class = None
        self.io_sample_events = OrderedDict()
        self.eye_data = [None, None]
        self.visual_angle_calc = VisualAngleCalc(DISPLAY_SIZE_MM,
                                                 DISPLAY_RES_PIX,
                                                 DEFAULT_EYE_DISTANCE)
        self.pix2deg = self.visual_angle_calc.pix2deg

        if self.input_event_types.get(self.MONOC_SAMPLE):
            from psychopy.iohub.devices.eyetracker import MonocularEyeSampleEvent
            self.io_sample_class = MonocularEyeSampleEvent
            self.ioevent_ix = self.io_sample_class.CLASS_ATTRIBUTE_NAMES.index
            self.sample_type = self.MONOC_SAMPLE
            self.process = self._handleMonoSamples
            # TODO: Determine left or right correctly if possible, else default to 'Right'
            self.eye_data = (ParserDataCache(MONO_EYE, self.io_sample_class),)

        elif self.input_event_types.get(self.BINOC_SAMPLE):
            from psychopy.iohub.devices.eyetracker import BinocularEyeSampleEvent
            self.io_sample_class = BinocularEyeSampleEvent
            self.ioevent_ix = self.io_sample_class.CLASS_ATTRIBUTE_NAMES.index
            self.sample_type = self.BINOC_SAMPLE
            self.process = self._handleBinocSamples
            self.eye_data = (ParserDataCache(LEFT_EYE, self.io_sample_class),
                             ParserDataCache(RIGHT_EYE, self.io_sample_class))
        else:
            print2err("EyeSampleFilter._input_event_types value is invalid: ",self._input_event_types)


    @property
    def filter_id(self):
        return 1

    @property
    def input_event_types(self):
        return {EventConstants.BINOCULAR_EYE_SAMPLE: (0,)}#, EventConstants.MONOCULAR_EYE_SAMPLE: (0,)}


    def _handleBinocSamples(self):
        #print2err("\n>>>>>>>>>>>>>>>>>>>")
        for in_evt in self.getInputEvents():
            t1=getTime()
            evt_id = in_evt[self.ioevent_ix('event_id')]
            evt_status = in_evt[self.ioevent_ix('status')]
            #print2err("Handling iosample id %d, status: %d"%(evt_id, evt_status))
            if evt_status == 0:
                # createFilterSample also converts pix to visual degrees.
                lgx_ix = self.ioevent_ix('left_gaze_x')
                lgy_ix = self.ioevent_ix('left_gaze_y')
                rgx_ix = self.ioevent_ix('right_gaze_x')
                rgy_ix = self.ioevent_ix('right_gaze_y')
                in_evt[lgx_ix], in_evt[lgy_ix] = self.pix2deg(in_evt[lgx_ix], in_evt[lgy_ix])
                in_evt[rgx_ix], in_evt[rgy_ix] = self.pix2deg(in_evt[rgx_ix], in_evt[rgy_ix])
                left_eye_samples = self.eye_data[LEFT_EYE].addSampleEvent(in_evt, 1)
                right_eye_samples = self.eye_data[RIGHT_EYE].addSampleEvent(in_evt, 1)
            elif evt_status == 20: # right eye data only
                rgx_ix = self.ioevent_ix('right_gaze_x')
                rgy_ix = self.ioevent_ix('right_gaze_y')
                in_evt[rgx_ix], in_evt[rgy_ix] = self.pix2deg(in_evt[rgx_ix], in_evt[rgy_ix])
                left_eye_samples = self.eye_data[LEFT_EYE].addSampleEvent(in_evt, 0)
                right_eye_samples = self.eye_data[RIGHT_EYE].addSampleEvent(in_evt, 1)
            elif evt_status == 2: # left eye data only
                lgx_ix = self.ioevent_ix('left_gaze_x')
                lgy_ix = self.ioevent_ix('left_gaze_y')
                in_evt[lgx_ix], in_evt[lgy_ix] = self.pix2deg(in_evt[lgx_ix], in_evt[lgy_ix])
                left_eye_samples = self.eye_data[LEFT_EYE].addSampleEvent(in_evt, 1)
                right_eye_samples = self.eye_data[RIGHT_EYE].addSampleEvent(in_evt, 0)
            elif evt_status == 22: # both eye data missing
                left_eye_samples = self.eye_data[LEFT_EYE].addSampleEvent(in_evt, 0)
                right_eye_samples = self.eye_data[RIGHT_EYE].addSampleEvent(in_evt, 0)
            else:
                print2err("ERROR: Sample status invalid: ", evt_status)

            # add iohub sample to dict so it can be merged later
            self.io_sample_events[in_evt[self.ioevent_ix('event_id')]] = [in_evt,0]

            for left_proc_samp in left_eye_samples:
                eid = left_proc_samp[PROC_SAMPLE_ID_INDEX]
                evt_and_proc_cnt = self.io_sample_events.get(eid)
                if evt_and_proc_cnt:
                    evt, proc_cnt = evt_and_proc_cnt
                    evt[self.ioevent_ix('left_gaze_x')] =  left_proc_samp[PROC_SAMPLE_X_INDEX]
                    evt[self.ioevent_ix('left_gaze_y')] =  left_proc_samp[PROC_SAMPLE_Y_INDEX]
                    evt[self.ioevent_ix('left_velocity_x')] =  left_proc_samp[PROC_SAMPLE_VX_INDEX]
                    evt[self.ioevent_ix('left_velocity_y')] =  left_proc_samp[PROC_SAMPLE_VY_INDEX]
                    evt[self.ioevent_ix('left_velocity_xy')] =  left_proc_samp[PROC_SAMPLE_VXY_INDEX]
                    # use pupil measure 2 field to hold current vel thresh
                    evt[self.ioevent_ix('left_pupil_measure2')] =  left_proc_samp[PROC_SAMPLE_VEL_THRESH_INDEX]
                    evt_and_proc_cnt[1]+=1
                    if evt_and_proc_cnt[1] == 2:
                        self.addOutputEvent(evt)
                        del self.io_sample_events[eid]

            for right_proc_samp in right_eye_samples:
                eid = right_proc_samp[PROC_SAMPLE_ID_INDEX]
                evt_and_proc_cnt = self.io_sample_events.get(eid)
                if evt_and_proc_cnt:
                    evt, proc_cnt = evt_and_proc_cnt
                    evt[self.ioevent_ix('right_gaze_x')] =  right_proc_samp[PROC_SAMPLE_X_INDEX]
                    evt[self.ioevent_ix('right_gaze_y')] =  right_proc_samp[PROC_SAMPLE_Y_INDEX]
                    evt[self.ioevent_ix('right_velocity_x')] =  right_proc_samp[PROC_SAMPLE_VX_INDEX]
                    evt[self.ioevent_ix('right_velocity_y')] =  right_proc_samp[PROC_SAMPLE_VY_INDEX]
                    evt[self.ioevent_ix('right_velocity_xy')] =  right_proc_samp[PROC_SAMPLE_VXY_INDEX]
                    evt[self.ioevent_ix('right_pupil_measure2')] =  right_proc_samp[PROC_SAMPLE_VEL_THRESH_INDEX]
                    evt_and_proc_cnt[1]+=1
                    if evt_and_proc_cnt[1] == 2:
                        self.addOutputEvent(evt)
                        del self.io_sample_events[eid]

            left_events = self.parse(self.eye_data[LEFT_EYE], LEFT_EYE)
            right_events = self.parse(self.eye_data[RIGHT_EYE], RIGHT_EYE)

            for left_event_type, left_sample_ix_list in left_events:
                start_sample = self.io_sample_events.get(left_sample_ix_list[0])[0]
                end_sample = self.io_sample_events.get(left_sample_ix_list[-1])[0]
                self.createParsedEvent(start_sample, etype=left_event_type, start_event=True, eye=LEFT_EYE)
                for eix in left_sample_ix_list:
                    smpl_and_cnt =self.io_sample_events.get(eix)
                    smpl_and_cnt[1]+=1
                    if smpl_and_cnt[1] == 4:
                        self.addOutputEvent(smpl_and_cnt[0])
                        del self.io_sample_events[eix]
                self.createParsedEvent(end_sample, etype=left_event_type, start_event=False, eye=LEFT_EYE)

            for right_event_type, right_sample_ix_list in right_events:
                start_sample = self.io_sample_events.get(right_sample_ix_list[0])[0]
                end_sample = self.io_sample_events.get(right_sample_ix_list[-1])[0]
                self.createParsedEvent(start_sample, etype=right_event_type, start_event=True, eye=RIGHT_EYE)
                for eix in right_sample_ix_list:
                    smpl_and_cnt =self.io_sample_events.get(eix)
                    smpl_and_cnt[1]+=1
                    if smpl_and_cnt[1] == 4:
                        self.addOutputEvent(smpl_and_cnt[0])
                        del self.io_sample_events[eix]
                self.createParsedEvent(end_sample, etype=right_event_type, start_event=False, eye=RIGHT_EYE)

        self.clearInputEvents()
        #print2err("<<<<<<<<<<<<<<<<<<<<")

    def createParsedEvent(self, sample, etype='??', start_event=True, eye=MONO_EYE):
        if start_event:
            print2err("TODO: Create START %s Event: Time %.3f, eye: %d"%(etype, sample[self.ioevent_ix['time']],eye))
        else:
            print2err("TODO: Create END %s Event: Time %.3f, eye: %d"%(etype, sample[self.ioevent_ix['time']],eye))

    def parse(self,eye_data,eye_index):
        """
        Filter and Parse Data Stream
        """
        # Only start parsing once we get adaptive velocity threshold values.
        vthresh = eye_data.getVelocityThreshold()
        if vthresh is None:
            return []
        # Do not parse when state has unprocessed missing data
        if len(eye_data.missing_data_sample_ixs)>0:
            return []

        events = []
        current_parser_index = eye_data.last_parsed_index
        parse_to = eye_data.current_sample_index
        if parse_to - current_parser_index < MIN_PARSER_SAMPLE_BLOCK:
            return []

        #print2err("**** PARSING ROUND STARTED *****")

        #print2err("Parse index range: ",(current_parser_index,parse_to),' ',parse_to - current_parser_index)

        parsing_event_types = dict(SAC=[],FIX=[],MIS=[])
        curr_event_category = None
        prev_event_category = eye_data.prev_event_category

        while current_parser_index <= parse_to:
            cevent = eye_data.sample_array[current_parser_index]

            valid = cevent[PROC_SAMPLE_VALID_INDEX]
            if valid:
                vx = cevent[PROC_SAMPLE_VX_INDEX]
                vy = cevent[PROC_SAMPLE_VY_INDEX]
                #if cevent[PROC_SAMPLE_VEL_THRESH_INDEX]:
                #    vthresh = cevent[PROC_SAMPLE_VEL_THRESH_INDEX]
                #else:
                #   cevent[PROC_SAMPLE_VEL_THRESH_INDEX] = vthresh

                #if eye_index == 0:
                #    print2err("Sample index %d, vel thresh %.3f, event thresh %.3f. vx, vy: "%(current_parser_index,vthresh,cevent[PROC_SAMPLE_VEL_THRESH_INDEX]), (vx,vy))
                if vx >= vthresh or vy >= vthresh:
                    parsing_event_types['SAC'].append(current_parser_index)
                    curr_event_category = 'SAC'
                else:
                    parsing_event_types['FIX'].append(current_parser_index)
                    curr_event_category = 'FIX'
            else:
                parsing_event_types['MIS'].append(current_parser_index)
                curr_event_category = 'MIS'

            #if eye_data.eye_index == 0:
            #    print2err("Sample index %d, evt categoty: %s"%(current_parser_index,curr_event_category))
            if prev_event_category and prev_event_category != curr_event_category:
                if MIN_EVENT_SAMPLES[prev_event_category] > len(parsing_event_types[prev_event_category]):
                    #event is too short, so add to current event type list head
                    parsing_event_types[prev_event_category].extend(parsing_event_types[curr_event_category])
                    parsing_event_types[curr_event_category] = parsing_event_types[prev_event_category]
                    parsing_event_types[prev_event_category] = []
                else:
                    #print2err("+++ Adding Event (eye %d): "%(eye_data.eye_index), (prev_event_category, len(parsing_event_types[prev_event_category])))
                    new_event = sorted(parsing_event_types[prev_event_category], key = lambda x: eye_data.sample_array[x][PROC_SAMPLE_TIME_INDEX])
                    parsing_event_types[prev_event_category] = []
                    events.append((prev_event_category, new_event))

            prev_event_category = curr_event_category

            current_parser_index += 1

        eye_data.curr_event_category = curr_event_category

        if len(events) > 1:
            evt_typ, exv_ix = events[-1]
            parsing_event_types[evt_typ].extend(exv_ix)
            events = events[:-1]

        last_index = SAMPLE_ARRAY_ROWS
        unused_sample_count = 0
        #print2err("parsing_event_types: ", parsing_event_types)
        for e in parsing_event_types.values():
            if e:
                last_index = min(last_index, *e)
                unused_sample_count+=len(e)
        eye_data.last_parsed_index = last_index


        #print2err("Unused clasified samples: ", unused_sample_count)
        #print2err("Updated last_parsed_index: ", eye_data.last_parsed_index)

        #print2err("****** PARSING ROUND DONE ******")

        return events
'''