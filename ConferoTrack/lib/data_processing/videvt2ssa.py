# -*- coding: utf-8 -*-
from __future__ import division
from datetime import timedelta
from textwrap import dedent
import numpy as np
import os
from timeit import default_timer as getTime
from common import openDataStoreReader, getVideoFilesFromSessionPath, readAppSettingParameters
from psychopy.iohub import EventConstants
from cv2video import OpenCVideo

# The offset (in seconds) to apply to all event times so that they align with
# VLC playback using the SSA files created.
VLC_OFFSET_CORRECTION = 1.0

# If True, use mouse position, not gaze position, when creating SSA files.
PLOT_MOUSE = False
PRINT_STATUS = True
SAVE_TXT_FILE = True
SAVE_NPZ_FILE = True
SAVE_SSA_FILES = True

# garyfeng: Can choose to plot fixation or samples
USE_FIXATIONS = False
if USE_FIXATIONS:
    SAVE_TXT_FILE = False
    SAVE_NPZ_FILE = False
# moving average only for samples
SAMPLES_FOR_MOVING_AVERAGE = 5
# garyfeng: verbose: can be very long; better to redirect the output to a text file
PRINT_VERBOSE = True
INFO_ONLY = False
if INFO_ONLY:
    PRINT_VERBOSE = True
# end garyfeng

RESULT_DIR_ROOT = r"..\..\Results"

SYNC_AVG_COLOR_THRESH = 30.0
SYNC_STD_COLOR_THRESH = 60.0
FPS = 30.0

if PLOT_MOUSE:
    SAMPLE_EVENT_ID = EventConstants.MOUSE_MOVE
    EVENT_FILTER_ID=0
    X_COL='x_position'
    Y_COL='y_position'
else:
    EVENT_FILTER_ID = 23
    # garyfeng: use fixation start as the timestemp
    if USE_FIXATIONS:
        SAMPLE_EVENT_ID = EventConstants.FIXATION_START
    else:
        SAMPLE_EVENT_ID = EventConstants.MONOCULAR_EYE_SAMPLE
    X_COL='gaze_x'
    Y_COL='gaze_y'

def printf(*args):
    if PRINT_STATUS:
        for a in args:
            print a,
        print

def getVideoEventSyncMessages(session_folder):
    block_flash_msg_times = None
    hubdata = None
    try:
        hubdata = openDataStoreReader(session_folder)
        session_id = hubdata.getSessionMetaData()[0].session_id
        msgeventstable = hubdata.getEventTable(EventConstants.MESSAGE)

        rec_start_msg_idx = list(msgeventstable.get_where_list(
            '(session_id == %d) & (text == "RECORDING_STARTED")' % (
                session_id)))
        rec_stop_msg_idx = list(msgeventstable.get_where_list(
            '(session_id == %d) & (text == "RECORDING_STOPPED")' % (
                session_id)))

        # Ensure that start records are matched to correct stop records
        # garyfeng
        if PRINT_VERBOSE:
          printf("====================")
          printf("session_folder== %s" % (session_folder))
          printf("session_id== %d" % (session_id))
          printf("RECORDING_STARTED and RECORDING_STOPPED events in data table MessageEvent")
        rec_blocks_idx = []
        ei = 0
        for si in range(len(rec_start_msg_idx)):
            e1 = rec_stop_msg_idx[ei]
            s1 = rec_start_msg_idx[si]
            if si + 1 < len(rec_start_msg_idx):
                s2 = rec_start_msg_idx[si + 1]
                if s2 > e1:
                    rec_blocks_idx.append((s1, e1))
                    ei += 1
            else:
                rec_blocks_idx.append((s1, e1))
            # garyfeng: debugging
                if PRINT_VERBOSE:
                    printf(s1, e1)
        if PRINT_VERBOSE:
            printf("\n")
            printf("Timing for flashes")

        block_flash_msg_times = []
        for si, ei in rec_blocks_idx:
            cblock = []
            block_flash_msg_times.append(cblock)
            rec_block_msgs = msgeventstable.read(start=si, stop=ei + 1)
            for r in rec_block_msgs:
                msg_time, msg_text = r['time'], r['text']

                if msg_text[0] == '[' and msg_text[-1] == ']':
                    cblock.append((msg_time, msg_text))
                # garyfeng: debugging
                if PRINT_VERBOSE:
                    printf(msg_time, msg_text)
    except:
        import traceback

        traceback.print_exc()
        block_flash_msg_times = None
    finally:
        if hubdata:
            hubdata.close()

    return block_flash_msg_times

def getDataStoreRecordingBlockBounds(hubdata):
    session_id = hubdata.getSessionMetaData()[0].session_id

    msgeventstable = hubdata.getEventTable(EventConstants.MESSAGE)

    event_start_msg_idx = list(msgeventstable.get_where_list(
        '(session_id == %d) & (text == "START_EVENT_PERIOD")' % (
            session_id)))
    event_stop_msg_idx = list(msgeventstable.get_where_list(
        '(session_id == %d) & (text == "END_EVENT_PERIOD")' % (session_id)))

    # Ensure that start records are matched to correct stop records
    evt_blocks_idx = []
    ei = 0
    for si in range(len(event_start_msg_idx)):
        e1 = event_stop_msg_idx[ei]
        s1 = event_start_msg_idx[si]
        if si + 1 < len(event_start_msg_idx):
            s2 = event_start_msg_idx[si + 1]
            if s2 > e1:
                evt_blocks_idx.append((s1, e1))
                ei += 1
        else:
            evt_blocks_idx.append((s1, e1))
    return evt_blocks_idx


def getFixations(session_folder):
    """
    Return a numpy ndarray of size (total_event_count,4). Each row represents
    an event that occurred during the given screen capture video, between
    experiment message events defined by the app config settings:

        data_collection:
            recording_period:
                event_period:
                    start_msg: START_EVENT_PERIOD
                    end_msg: END_EVENT_PERIOD

    The elements of a row are video_id, frame_index, event_type, event_id, event_time

    """
    result_dtype = [('video_id', np.uint8),
                    ('frame_number', np.uint32),
                    ('frame_time', np.float32),
                    ('event_time', np.float32),
                    ('gaze_x', np.float32),
                    ('gaze_y', np.float32),
                    ('status', np.int)

                    ]
    hubdata = None
    try:
        hubdata = openDataStoreReader(session_folder)

        evt_blocks_idx = getDataStoreRecordingBlockBounds(hubdata)
        # garyfeng: debug
        if PRINT_VERBOSE:
            printf("=====================================")
            printf("getSamplesPerFrame\nevt_blocks_idx:", evt_blocks_idx)
        # garyfeng: end
        msgeventstable = hubdata.getEventTable(EventConstants.MESSAGE)
        # garyfeng: The following line does NOT seem to limit the data to the current session_id.
        # so we need to add a filter to the current session ID
        session_id = hubdata.getSessionMetaData()[0].session_id
        # garyfeng: end
        sampleeventstable = hubdata.getEventTable(SAMPLE_EVENT_ID)



        # Now match up frame start and end times for each video of the
        # current session, creating the events_by_video_frame np array rows
        # defined by result_dtype.
        video_events = []
        for vi, (si, ei) in enumerate(evt_blocks_idx):
            # garyfeng
            # debug
            if PRINT_VERBOSE:
                printf("getSamplesPerFrame: si, ei indices")
                printf("si", si)
                printf("ei",ei)
            # end garyfeng

            edge_msgs = msgeventstable[[si, ei]]
            rec_start_msg, rec_end_msg = edge_msgs[:]
            rec_block_start_time = rec_start_msg['time']
            rec_block_end_time = rec_end_msg['time']
            # garyfeng
            # debug
            if PRINT_VERBOSE:
                printf("getSamplesPerFrame")
                printf("rec_block_start_time", rec_block_start_time)
                printf("rec_block_end_time",rec_block_end_time)
            # end garyfeng

            #cond = "(time >= %f) & (time <= %f) " % (
            # garyfeng: adding condition to use only valid eye gaze
            # also adding the condition to restrict to only the current session_id
            cond = "(time >= %f) & (time <= %f) & (status == 0) & (session_id==%d)" % (
                rec_block_start_time, rec_block_end_time, session_id)
            if EVENT_FILTER_ID >= 0:
                 cond = cond + " & (filter_id == %d)" % (EVENT_FILTER_ID)
            # garyfeng: debug
            printf("getSamplesPerFrame: filter cond=", cond)
            # garyfeng: ;end
            event_count = 0
            filtered_sample_events = sampleeventstable.read_where(cond)
            fixation_count = filtered_sample_events.shape[0]
            video_frame_events = [[] for z in xrange(fixation_count+1)]
            printf("Total Fixations=", fixation_count)

            # frame_times = frame_times_per_session_video[vi]
            # frame_count = frame_times.shape[0]
            # frame_num = 0
            # fstart_time = int(frame_times[0][1] * 1000)
            # fend_time = int(frame_times[1][1] * 1000)
            # garyfeng
            # if PRINT_VERBOSE:
            #     printf("initial fstart_time", fstart_time)
            #     printf("initial fend_time", fend_time)
            # garyfeng: end

            frame_num=0
            for e in filtered_sample_events:
                evt_time = int(e['time'] * 1000)
                # garyfeng: debug
                if PRINT_VERBOSE:
                    printf(e['session_id'], e['event_id'], e['time'], e['gaze_x'], e['gaze_y'])
                # garyfeng: simply save the fixations using a filler frame_num
                frame_num +=1
                fstart_time=9999
                video_frame_events[frame_num].append((
                    vi, frame_num, fstart_time/1000.0,
                    e['time'], e[X_COL], e[Y_COL], e['status']))
                if PRINT_VERBOSE:
                    if(video_frame_events[frame_num]):
                        printf("        ", video_frame_events[frame_num])
                # end garyfeng

            # now have all mono samples per frame in the current video.
            # They are not sorted by time in each video, but by event type.
            # Resort events for each video in each frame.
            video_event_list = []
            for frame_events in video_frame_events:
                if frame_events:
                    video_event_list.extend(
                        sorted(frame_events, key=lambda x: x[-4]))

            video_events.extend(video_event_list)
        # Convert to numpy ndarray
        return np.array(video_events, dtype=result_dtype)
    except:
        import traceback
        traceback.print_exc()
    finally:
        if hubdata:
            hubdata.close()

def getSamplesPerFrame(session_folder, frame_times_per_session_video):
    """
    Return a numpy ndarray of size (total_event_count,4). Each row represents
    an event that occurred during the given screen capture video, between
    experiment message events defined by the app config settings:

        data_collection:
            recording_period:
                event_period:
                    start_msg: START_EVENT_PERIOD
                    end_msg: END_EVENT_PERIOD

    The elements of a row are video_id, frame_index, event_type, event_id, event_time

    """
    result_dtype = [('video_id', np.uint8),
                    ('frame_number', np.uint32),
                    ('frame_time', np.float32),
                    ('event_time', np.float32),
                    ('gaze_x', np.float32),
                    ('gaze_y', np.float32),
                    ('status', np.int)

                    ]
    hubdata = None
    try:
        hubdata = openDataStoreReader(session_folder)

        evt_blocks_idx = getDataStoreRecordingBlockBounds(hubdata)
        # garyfeng: debug
        if PRINT_VERBOSE:
            printf("=====================================")
            printf("getSamplesPerFrame\nevt_blocks_idx:", evt_blocks_idx)
        # garyfeng: end
        msgeventstable = hubdata.getEventTable(EventConstants.MESSAGE)
        # garyfeng: The following line does NOT seem to limit the data to the current session_id.
        # so we need to add a filter to the current session ID
        session_id = hubdata.getSessionMetaData()[0].session_id
        # garyfeng: end
        sampleeventstable = hubdata.getEventTable(SAMPLE_EVENT_ID)



        # Now match up frame start and end times for each video of the
        # current session, creating the events_by_video_frame np array rows
        # defined by result_dtype.
        video_events = []
        for vi, (si, ei) in enumerate(evt_blocks_idx):
            # garyfeng
            # debug
            if PRINT_VERBOSE:
                printf("getSamplesPerFrame: si, ei indices")
                printf("si", si)
                printf("ei",ei)
            # end garyfeng

            edge_msgs = msgeventstable[[si, ei]]
            rec_start_msg, rec_end_msg = edge_msgs[:]
            rec_block_start_time = rec_start_msg['time']
            rec_block_end_time = rec_end_msg['time']
            # garyfeng
            # debug
            if PRINT_VERBOSE:
                printf("getSamplesPerFrame")
                printf("rec_block_start_time", rec_block_start_time)
                printf("rec_block_end_time",rec_block_end_time)
            # end garyfeng

            #cond = "(time >= %f) & (time <= %f) " % (
            # garyfeng: adding condition to use only valid eye gaze
            # also adding the condition to restrict to only the current session_id
            cond = "(time >= %f) & (time <= %f) & (status == 0) & (session_id==%d)" % (
                rec_block_start_time, rec_block_end_time, session_id)
            if EVENT_FILTER_ID >= 0:
                 cond = cond + " & (filter_id == %d)" % (EVENT_FILTER_ID)
            # garyfeng: debug
            printf("getSamplesPerFrame: filter cond=", cond)
            # garyfeng: ;end

            frame_times = frame_times_per_session_video[vi]
            frame_count = frame_times.shape[0]
            video_frame_events = [[] for z in xrange(frame_count)]
            event_count = 0
            filtered_sample_events = sampleeventstable.read_where(cond)
            frame_num = 0
            fstart_time = int(frame_times[0][1] * 1000)
            fend_time = int(frame_times[1][1] * 1000)
            # garyfeng
            if PRINT_VERBOSE:
                printf("initial fstart_time", fstart_time)
                printf("initial fend_time", fend_time)
            # garyfeng: end

            for e in filtered_sample_events:
                evt_time = int(e['time'] * 1000)
                # garyfeng: debug
                if PRINT_VERBOSE:
                    printf(e['session_id'], e['event_id'], e['time'], e['gaze_x'], e['gaze_y'])
                # garyfeng

                if evt_time >= fstart_time:
                    if evt_time < fend_time:
                        event_count += 1
                        video_frame_events[frame_num].append((
                            vi, frame_num, fstart_time/1000.0,
                            e['time'], e[X_COL], e[Y_COL], e['status']))
                    else:
                        # garyfeng
                        if PRINT_VERBOSE:
                            if(video_frame_events[frame_num]):
                                printf("        ", video_frame_events[frame_num])
                        # garyfeng
                        frame_num += 1
                        if frame_num + 1 < frame_count:
                            fstart_time = int(
                                frame_times[frame_num][1] * 1000)
                            fend_time = int(
                                frame_times[frame_num + 1][1] * 1000)
                        elif frame_num + 1 == frame_count:
                            fend_time = fend_time + (
                                fend_time - fstart_time)
                            fstart_time = fend_time
                        else:
                            break
                        if evt_time < fend_time:
                            event_count += 1
                            video_frame_events[frame_num].append((
                                vi, frame_num, fstart_time/1000.0,
                                e['time'],  e[X_COL], e[Y_COL], e['status']))

            # now have all mono samples per frame in the current video.
            # They are not sorted by time in each video, but by event type.
            # Resort events for each video in each frame.
            video_event_list = []
            for frame_events in video_frame_events:
                if frame_events:
                    video_event_list.extend(
                        sorted(frame_events, key=lambda x: x[-4]))

            video_events.extend(video_event_list)
        # Convert to numpy ndarray
        return np.array(video_events, dtype=result_dtype)
    except:
        import traceback
        traceback.print_exc()
    finally:
        if hubdata:
            hubdata.close()

preamble = dedent('''
    [Script Info]
    Title: Eye Gaze Positions
    ScriptType: v4.00+
    WrapStyle: 0
    PlayResX: {0}
    PlayResY: {1}
    ScaledBorderAndShadow: yes

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Arial,72,&H000000FF,&H0000FF00,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n\n''')

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    #return ret[n - 1:] / n
    return ret / n

def createSSA(video_frame_evt_array, session_folder, mean_offset_per_vid):
    video_ids = np.unique(video_frame_evt_array['video_id'])
    swidth, sheight = APP_CONF.get('screen_capture',{}).get('screen_resolution')
    eye_num = 0
    # garyfeng: delay, arbitrarily set to 2 seconds. This looks about right. Need to figure out why.
    delay=0
    # end garyfeng

    for vid in video_ids:
        output_file_name = os.path.join(session_folder,"screen_capture_%d.ssa"%(vid+1))
        vid_frame_samples = video_frame_evt_array[video_frame_evt_array['video_id']==vid]

        vid_frame_samples['frame_time']-= (mean_offset_per_vid[vid]+delay)
        vid_frame_samples['event_time']-= (mean_offset_per_vid[vid]+delay)
        vid_frame_samples['gaze_x']+=swidth/2
        vid_frame_samples['gaze_y'] = sheight - (vid_frame_samples['gaze_y'] + sheight/2)

        # garyfeng: smoothing with moving_average, unless we are using fixations
        if not USE_FIXATIONS:
            vid_frame_samples['gaze_x'] = moving_average(vid_frame_samples['gaze_x'],SAMPLES_FOR_MOVING_AVERAGE)
            vid_frame_samples['gaze_y'] = moving_average(vid_frame_samples['gaze_y'],SAMPLES_FOR_MOVING_AVERAGE)
        # end garyfeng

        with open(output_file_name, 'w') as output_file:
            output_file.write(preamble.format(swidth, sheight))
            for i,frame_sample in enumerate(vid_frame_samples[:-1]):
                if frame_sample['status'] != 22:
                    next_frame_sample = vid_frame_samples[i+1]
                    # should be using event time as this was when fixations started
                    timestamp_start = timedelta(0, float(frame_sample['event_time']+VLC_OFFSET_CORRECTION))
                    timestamp_end = timedelta(0, float(next_frame_sample['event_time']+VLC_OFFSET_CORRECTION))
                    # timestamp_start = timedelta(0, float(frame_sample['frame_time']+VLC_OFFSET_CORRECTION))
                    # timestamp_end = timedelta(0, float(next_frame_sample['frame_time']+VLC_OFFSET_CORRECTION))
                    # garyfeng: skip if timestamp_start==timestamp_end
                    # why not take an average of all the samples in this frame??@@@@
                    if (timestamp_start==timestamp_end):
                        continue
                    # end garyfeng

                    # garyfeng: fixing a bug where timestamp doesn't have the trailing msc and microsec
                    #   when (I guess) the fraction is exactly 000000. for example:
                    # 0:36:05.965820
                    # 0:36:06
                    # Dialogue:0,0:36:05.96,0:3,Default,,0000,0000,0000,,{\pos(1086,208)\an5}+
                    # we detect this case and add trailing 0s
                    strStart = str(timestamp_start)
                    strEnd = str(timestamp_end)
                    if (len(strStart)<10):
                        strStart+=".000000"
                    if (len(strEnd)<10):
                        strEnd+=".000000"
                    # end garyfeng

                    # garyfeng: why not do it earlier with vid_frame_samples
                    #gaze_y = sheight - (frame_sample['gaze_y'] + sheight/2)
                    output_file.write('Dialogue:{0},{1},{2},Default,,0000,0000,0000,,{{\\pos({3},{4})\\an5}}+\n'.format(eye_num,
                                                                    unicode(strStart)[:-4],
                                                                    unicode(strEnd)[:-4],
                                                                    int(round(frame_sample['gaze_x'])),
                                                                    int(round(frame_sample['gaze_y']))
                                                                    )
                                     )
                    if PRINT_VERBOSE:
                        printf(strStart)
                        printf(strEnd)
                        printf('Dialogue:{0},{1},{2},Default,,0000,0000,0000,,{{\\pos({3},{4})\\an5}}+\n'.format(eye_num,
                                                                    unicode(timestamp_start)[:-4],
                                                                    unicode(timestamp_end)[:-4],
                                                                    int(round(frame_sample['gaze_x'])),
                                                                    int(round(frame_sample['gaze_y']))
                                                                    )
                        )

def saveVideoEventFiles(video_frame_evt_array, session_folder, mean_offset_per_video):
    if SAVE_TXT_FILE:
        import datetime

        printf("Saving session_vframe_events.txt...")
        header = "Created on %s UTC.\nProcessing session folder: %s\n" % (
            datetime.datetime.utcnow().isoformat(), session_folder)
        header += "video_id    frame_number    frame_time    event_time    gaze_x    gaze_y    status\n"
        fmt = ['%d', '%d', '%.3f', '%.3f',  '%.3f',  '%.3f', '%d']
        np.savetxt(
            os.path.join(session_folder, 'session_vframe_events.txt'),
            video_frame_evt_array, header=header, delimiter='    ', fmt=fmt)

    if SAVE_NPZ_FILE:
        printf("Saving session_vframe_events.npz...")
        np.savez(os.path.join(session_folder, 'session_vframe_events.npz'),
                 events=video_frame_evt_array)


    if SAVE_SSA_FILES:
        printf("Saving SSA files...")
        createSSA(video_frame_evt_array,session_folder, mean_offset_per_video)

if __name__ == '__main__':
    global SESSION_FOLDER,SYNC_TIME_BOX,SYNC_TRANSITION_COUNT,SYNC_FLASH_INTERVAL , MAX_SEARCH_FRAMES
    import sys

    try:
        if len(sys.argv)==3:
            experiment_folder = sys.argv[1]
            session_folder = sys.argv[2]
        else:
            print "Usage:"
            print "python.exe videvt2ssa.py [exp_folder] [session_folder]"
            print
            print "Exiting"
            sys.exit(0)

        SESSION_FOLDER = os.path.normpath(os.path.abspath(os.path.join(RESULT_DIR_ROOT,experiment_folder,session_folder)))
        print "SESSION_FOLDER: ", SESSION_FOLDER

        APP_CONF = readAppSettingParameters(SESSION_FOLDER)
        sync_conf = APP_CONF.get('video_event_sync')

        SYNC_TIME_BOX = sync_conf.get('region')
        SYNC_TRANSITION_COUNT = sync_conf.get('cycle_count')
        SYNC_COLORS = sync_conf.get('colors')
        # extra 50 msec / flash is just padding.
        SYNC_FLASH_INTERVAL = sync_conf.get('phase_duration') +0.05
        MAX_SEARCH_FRAMES = int(SYNC_TRANSITION_COUNT * len(
            SYNC_COLORS) * SYNC_FLASH_INTERVAL * FPS) + 90  # extra 3 seconds of frames to handle sleep time at runtime.

        proc_start_time = getTime()
        session_folder = SESSION_FOLDER
        _, session_name = session_folder.rsplit(os.sep, 1)

        # A list of lists. list len = # of recording blocks (videos) in session,
        # Each element of the list is a list of exp message sync frame times.
        flash_msg_times_per_video = getVideoEventSyncMessages(session_folder)


        # Returns a list of str's, each being the abs path to a video file
        # in the given session folder.
        session_video_paths = getVideoFilesFromSessionPath(session_folder)

        session_rec_block_frame_events = []
        mean_offsets_per_video=[]
        for rec_video_index, vpath in enumerate(session_video_paths):
            t1 = getTime()
            cvid = OpenCVideo(os.path.abspath(vpath))
            t2 = getTime()

            _, video_file_name = os.path.split(vpath)
            printf()
            printf('===============================')
            printf('Processing:', vpath)
            printf('Video Load Time (sec):', t2 - t1)
            printf("Frame count:", cvid.total_frame_count)
            printf("Duration (sec, minutes):", cvid.duration,
                   cvid.duration / 60.0)
            printf("Resolution:", cvid.resolution)
            printf("Size (Mb):", os.path.getsize(vpath) / 1024 / 1024)

            #check for IFI issues
            t1 = getTime()
            printf()
            if INFO_ONLY:
                printf("== INFO ONLY, NOT generating SSA ==")
            else:
                if not USE_FIXATIONS:
                    video_frame_times = cvid.frametimes
                #printf("== NOT reading video frames ==")
                t2 = getTime()
                printf('cvid.frametimes duration:', t2 - t1)
            printf()

            printf('Find Video Start Sync Flashes....')
            # Get Video frame time to Event time offset and drift info
            _flash_msg_times = flash_msg_times_per_video[rec_video_index]
            # garyfeng
            if PRINT_VERBOSE:
                printf("_flash_msg_times")
                printf(_flash_msg_times)

            t1 = getTime()
            start_sync_frames, last_frame_checked = cvid.detectSyncTimeFrames(start_frame=1,
                                                                         color_list=SYNC_COLORS,
                                                                         sync_region=SYNC_TIME_BOX,
                                                                         iterations=SYNC_TRANSITION_COUNT,
                                                                         max_frames_searched=MAX_SEARCH_FRAMES,
                                                                         color_thresh=SYNC_AVG_COLOR_THRESH,
                                                                         std_thresh=SYNC_STD_COLOR_THRESH)
            t2 = getTime()
            printf('Video Start detectSyncTimeFrames duration:', t2 - t1)
            printf()

            # printf('Find Video End Sync Flashes....')
            # vendstart = cvid.total_frame_count - MAX_SEARCH_FRAMES
            # vendstart = max(vendstart, last_frame_checked + 20)
            # t1 = getTime()
            # end_sync_frames, _ = cvid.detectSyncTimeFrames(
            #                                           start_frame=vendstart,
            #                                           color_list=SYNC_COLORS,
            #                                           sync_region=SYNC_TIME_BOX,
            #                                           iterations=SYNC_TRANSITION_COUNT,
            #                                           max_frames_searched
            #                                           =MAX_SEARCH_FRAMES,
            #                                           color_thresh=SYNC_AVG_COLOR_THRESH,
            #                                           std_thresh=SYNC_STD_COLOR_THRESH)
            # t2 = getTime()
            # printf('Video End detectSyncTimeFrames duration:', t2 - t1)
            # printf()

            start_sync_times = _flash_msg_times[:len(start_sync_frames)]
            #end_sync_times = _flash_msg_times[len(start_sync_frames):]

            start_times = np.asarray([(tt[0][1], tt[1][0]) for tt in
                                      zip(start_sync_frames, start_sync_times)])
            #end_times = np.asarray([(tt[0][1], tt[1][0]) for tt in
            #                        zip(end_sync_frames, end_sync_times)])

            svidtimes, smsgtimes = start_times[:, 0], start_times[:, 1]
            #evidtimes, emsgtimes = end_times[:, 0], end_times[:, 1]

            start_offsets = smsgtimes - svidtimes
            #end_offsets = emsgtimes - evidtimes

            # garyfeng
            if PRINT_VERBOSE:
                printf("smsgtimes: starting timestamp on the eye-tracker clock")
                printf(smsgtimes)
                printf("svidtimes: starting timestamp on the video clock")
                printf(svidtimes)
                printf("offset: eye-tracker - video timestamp")
                printf(start_offsets)

            printf()
            printf('Session %s, Recording %d' % (
                session_name, rec_video_index + 1))
            printf()
            printf('Start Sync Offsets:')
            printf('    Min Offset:', start_offsets.min())
            printf('    Max Offset:', start_offsets.max())
            printf('    Offset Range:', start_offsets.max() - start_offsets.min())
            printf('    Mean Offset:', start_offsets.mean())
            #garyfeng: median is more appropriate here due to possible extreme values.
            printf('    Median Offset:', np.median(start_offsets))
            printf('    Stdev Offset:', start_offsets.std())
            printf()
            # printf('End Sync Offsets:')
            # printf('    Min Offset:', end_offsets.min())
            # printf('    Max Offset:', end_offsets.max())
            # printf('    Offset Range:', end_offsets.max() - end_offsets.min())
            # printf('    Mean Offset:', end_offsets.mean())
            # printf('    Stdev Offset:', end_offsets.std())
            # printf()
            # printf('Timing Translation:')
            # min_video_offset_diff = end_offsets.min() - start_offsets.min()
            # max_video_offset_diff = end_offsets.max() - start_offsets.max()
            # mean_video_offset_diff = end_offsets.mean() - start_offsets.mean()
            # mean_video_offset = (
            #                         end_offsets.mean() + start_offsets.mean() ) / 2.0
            #garyfeng: median is more appropriate here due to possible extreme values.
            mean_video_offset =  np.median(start_offsets)

            # printf('    Min Video Drift:', min_video_offset_diff)
            # printf('    Max Video Drift:', max_video_offset_diff)
            # printf('    Mean Video Drift:', mean_video_offset_diff)
            printf('    Median Video Offset:', mean_video_offset)


            # Convert video frame times to event time base.
            # Drift seems to be ~ 1 frame (i.e. 33 msec @ 30 fps) over 40 minute
            # video, so not worrying about drift correction in time base right now.
            # Should keep an eye on this as more videos are tested.
            if not INFO_ONLY:
                mean_offsets_per_video.append(mean_video_offset)
                if not USE_FIXATIONS:
                    video_frame_times[:, 1] += mean_video_offset
                    # Save corrected array data to a npz file so it can just be re-used
                    # later instead of recalculated each time session video times are
                    # needed.
                    session_rec_block_frame_events.append(video_frame_times)
                    #np.savez(os.path.join(session_folder,video_file_name+'.npz'),frame_event_times=video_frame_times)

        # Now put it all together, creating a events_frame table that holds
        # the event index info for each event that occurred within each frame
        # of the video.
        # Get event summary info indexed by video frame and video index
        #     result_dtype = [('video_id', np.uint8),('frame_number', np.uint32), ('event_type', np.uint8),
        #            ('event_id', np.uint32), ('time', np.float32)]
        if not INFO_ONLY:
            print 'mean_offsets_per_video:',mean_offsets_per_video
            t1 = getTime()
            if USE_FIXATIONS:
                video_frame_sample_array = getFixations(session_folder)
            else:
                video_frame_sample_array = getSamplesPerFrame(session_folder,
                                                session_rec_block_frame_events)



            t2 = getTime()
            printf()
            printf("getEventsPerFrame Duration:", t2 - t1)
            printf()

            saveVideoEventFiles(video_frame_sample_array, session_folder, mean_offsets_per_video)

        proc_end_time = getTime()
        printf()
        printf("FProcessing Complete. Total time to run: ",
               proc_end_time - proc_start_time)
    except:
        import traceback

        traceback.print_exc()
