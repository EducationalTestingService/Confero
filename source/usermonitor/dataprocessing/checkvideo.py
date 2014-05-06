SESSION_PATH = r'..\datacollection\results\first_exp\s1'
SYNC_TIME_BOX = 0, 0, 20, 20
SYNC_TRANSITION_COUNT = 15 # Each includes a cycle through colors
SYNC_COLORS = 255.0, 0.0
SHOW_VIDEO = True
SYNC_AVG_COLOR_THRESH = 30.0
SYNC_STD_COLOR_THRESH = 60.0
FPS=30.0
SYNC_FLASH_INTERVAL = 0.125+0.050 # extra 50 msec / flash is just padding.
MAX_SEARCH_FRAMES = int(SYNC_TRANSITION_COUNT*len(SYNC_COLORS)*SYNC_FLASH_INTERVAL*FPS)+90 # extra 3 seconds of frames to handle sleep time at runtime.

import numpy as np
from cv2video import OpenCVideo
import os
import sys
import cv2
import glob
import psychopy.iohub.datastore.util as dsutil
from psychopy.iohub import EventConstants
from timeit import default_timer as getTime

def getVideoFilesFromSessionPath(session_path):
    video_files = glob.glob(session_path+os.path.sep+'*.mkv')
    return video_files

def getVideoEventSyncMessages(session_folder):
    block_flash_msg_times = None
    hubdata = None
    try:
        exp_path, session_name = session_folder.rsplit(os.path.sep, 1)

        hubdata = dsutil.ExperimentDataAccessUtility(exp_path, 'iohub_events.hdf5', sessionCodes=[session_name])
        session_id = hubdata.getSessionMetaData()[0].session_id
        msgeventstable=hubdata.getEventTable(EventConstants.MESSAGE)

        rec_start_msg_idx = list(msgeventstable.get_where_list('(session_id == %d) & (text == "RECORDING_STARTED")'%(session_id)))
        rec_stop_msg_idx = list(msgeventstable.get_where_list('(session_id == %d) & (text == "RECORDING_STOPPED")'%(session_id)))

        # Ensure that start records are matched to correct stop records
        rec_blocks_idx = []
        ei=0
        for si in range(len(rec_start_msg_idx)):
            e1 = rec_stop_msg_idx[ei]
            s1 = rec_start_msg_idx[si]
            if si+1<len(rec_start_msg_idx):
                s2 =rec_start_msg_idx[si+1]
                if s2 > e1:
                    rec_blocks_idx.append((s1, e1))
                    ei += 1
            else:
                rec_blocks_idx.append((s1, e1))

        block_flash_msg_times=[]
        for si, ei in rec_blocks_idx:
            cblock = []
            block_flash_msg_times.append(cblock)
            rec_block_msgs = msgeventstable.read(start=si, stop=ei+1)
            for r in rec_block_msgs:
                msg_time, msg_text = r['time'], r['text']

                if msg_text[0] == '[' and msg_text[-1] == ']':
                    cblock.append((msg_time, msg_text))
    except:
        import traceback
        traceback.print_exc()
        block_flash_msg_times = None
    finally:
        if hubdata:
            hubdata.close()

    return block_flash_msg_times

def getEventsPerFrame(session_folder, frame_times_per_session_video):
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
    result_dtype = [('video_id', np.uint8),('frame_number', np.uint32), ('event_type', np.uint8),
                    ('event_id', np.uint32), ('time', np.float32)]
    hubdata = None
    try:
        exp_path, session_name = session_folder.rsplit(os.path.sep, 1)

        hubdata = dsutil.ExperimentDataAccessUtility(exp_path, 'iohub_events.hdf5', sessionCodes=[session_name])
        session_id = hubdata.getSessionMetaData()[0].session_id

        msgeventstable = hubdata.getEventTable(EventConstants.MESSAGE)

        event_start_msg_idx = list(msgeventstable.get_where_list('(session_id == %d) & (text == "START_EVENT_PERIOD")'%(session_id)))
        event_stop_msg_idx = list(msgeventstable.get_where_list('(session_id == %d) & (text == "END_EVENT_PERIOD")'%(session_id)))

        # Ensure that start records are matched to correct stop records
        evt_blocks_idx = []
        ei=0
        for si in range(len(event_start_msg_idx)):
            e1 = event_stop_msg_idx[ei]
            s1 = event_start_msg_idx[si]
            if si+1 < len(event_start_msg_idx):
                s2 = event_start_msg_idx[si+1]
                if s2 > e1:
                    evt_blocks_idx.append((s1, e1))
                    ei += 1
            else:
                evt_blocks_idx.append((s1, e1))

        # Now match up frame start and end times for each video of the
        # current session, creating the events_by_video_frame np array rows
        # defined by result_dtype.
        video_events=[]
        for vi, (si, ei) in enumerate(evt_blocks_idx):
            edge_msgs = msgeventstable[[si, ei]]
            rec_start_msg, rec_end_msg = edge_msgs[:]
            rec_block_start_time=rec_start_msg['time']
            rec_block_end_time=rec_end_msg['time']
            cond = "(time >= %f) & (time <= %f)"%(rec_block_start_time, rec_block_end_time)
            frame_times = frame_times_per_session_video[vi]
            frame_count = frame_times.shape[0]
            video_frame_events = [[] for z in xrange(frame_count)]
            event_count=0
            for event_id, event_iter in hubdata.getEventsByType(cond).iteritems():
                frame_num = 0
                fstart_time = frame_times[0][1]
                fend_time = frame_times[1][1]
                for e in event_iter:
                     evt_time = e['time']
                     if evt_time >= fstart_time:
                        if evt_time < fend_time:
                            event_count += 1
                            video_frame_events[frame_num].append((vi, frame_num, e['type'], e['event_id'], e['time']))
                        else:
                            frame_num += 1
                            if frame_num+1 < frame_count:
                                fstart_time = frame_times[frame_num][1]
                                fend_time = frame_times[frame_num+1][1]
                            elif frame_num+1 == frame_count:
                                fend_time = fend_time+(fend_time-fstart_time)
                                fstart_time = fend_time
                            else:
                                break

            # now have all events per frame in the current video.
            # They are not sorted by time in each video, but ny event type.
            # Resort events for each video in each frame.

            video_event_list = []
            for frame_events in video_frame_events:
                if frame_events:
                    video_event_list.extend(sorted(frame_events, key = lambda x: x[-1]))
        video_events.extend(video_event_list)
        # Convert to numpy ndarray
        return np.array(video_events, dtype=result_dtype)
    except:
        import traceback
        traceback.print_exc()
    finally:
        if hubdata:
            hubdata.close()

def checkVideoIFI(cvid, start_frame=0):
    """
    Checks for any duplicate frame times or longer than expected IFI's.
    """
    initial_frame=cvid.frame_index
    r = cvid.seek(frame_number=start_frame)
    if r is False:
        return None
    first_frame_index=None
    first_frame_time=None
    issue_count = 0
    frame_index = 1
    frame_time=None
    ifi = cvid.ifi
    usec_ifi = int(ifi*1000000)

    frame_times = np.zeros((cvid.total_frame_count,2), dtype=np.float32)
    while frame_index:
        frame_index = cvid.getNextFrameHeader()
        if frame_index:
            frame_time = cvid.frame_time
            frame_times[frame_index-1][0] = frame_index-1
            frame_times[frame_index-1][1] = frame_time
            if frame_index == 1:
                first_frame_index = frame_index
                first_frame_time = frame_time
            elif cvid.last_frame_index:
                index_diff = frame_index - cvid.last_frame_index
                time_diff = frame_time - cvid.last_frame_time
                usec_time_diff = int(time_diff*1000000)
                if index_diff != 1 or usec_time_diff != usec_ifi:
                    print 'checkVideoIFI alert:', frame_index, frame_time, index_diff, usec_time_diff, usec_ifi
                    issue_count += 1
    cvid.seek(frame_number=initial_frame)
    return issue_count, frame_times

def detectSyncTimeFrames(cvid, start_frame, color_list, sync_region, iterations, max_frames_searched, color_thresh, std_thresh):
    """
    Returns an array of (frame_number, frame_time) tuples found at the start of the video file based
    on the args provided. If > 2 minutes of frames are serached, the alg with quit and return None.

    TODO: Also get sync frames for end of video, say start searching from 30*120
          frames before end of video.
    """
    print 'STARTING: detectSyncTimeFrames: ',start_frame,iterations*len(color_list)
    r = cvid.seek(frame_number=start_frame)
    if r is False:
        return None

    l, t, r, b = sync_region
    synctimes=[]
    std_thresh = std_thresh
    color_thresh = color_thresh
    frame_index = -1
    for i in range(iterations*len(color_list)):
        target_color = color_list[i%len(color_list)]
        while 1:
            frame_index = cvid.getNextFrameHeader()
            if frame_index:
                vframe = cvid.getNextFrameArray()
                if vframe is not None:
                    fmean, fstd = vframe[t:b, l:r, :].mean(), vframe[t:b, l:r, :].std()
                    #print frame_index, fmean, fstd
                    if fstd < std_thresh and np.abs(fmean-target_color) < color_thresh:
                        #print 'HIT:',len(synctimes),frame_index, fmean, fstd
                        synctimes.append((frame_index, cvid.frame_time))
                        break
                    if frame_index > start_frame+max_frames_searched:
                        print "Error: Max frame index for detectSyncTimeFrames reached."
                        return synctimes,frame_index
            else:
                print "Error: End of Video reached without detecting all sync frames"
                return synctimes,frame_index
    r = cvid.seek(frame_number=1)
    if r is False:
        print "Error: Could not seek to start of video."
    return synctimes, frame_index

def processFrame(cvid, frame):
    print "frame %d 100x100:\n\tcolor mean: %.3f\n\tstdev: %.3f"%(cvid.frame_index, frame[0:100, 0:100, :].mean(), frame[0:100, 0:100, :].std())

if __name__ == '__main__':
    try:
        session_folder = os.path.normpath(os.path.abspath(SESSION_PATH))
        _, session_name = session_folder.rsplit(os.sep, 1)

        # A list of lists. list len = # of recording blocks (videos) in session,
        # Each element of the list is a list of exp message sync frame times.
        flash_msg_times_per_video = getVideoEventSyncMessages(session_folder)


        # Returns a list of str's, each being the abs path to a video file
        # in the given session folder.
        session_video_paths = getVideoFilesFromSessionPath(session_folder)

        session_rec_block_frame_events=[]

        for rec_video_index, vpath in enumerate(session_video_paths):
            t1=getTime()
            cvid = OpenCVideo(os.path.abspath(vpath))
            t2=getTime()

            _, video_file_name = os.path.split(vpath)
            print '==============================='
            print 'Processing:', vpath
            print 'Load Time (sec):', t2-t1
            print "Frame count:",cvid.total_frame_count
            print "Duration (sec, minutes):", cvid.duration, cvid.duration/60.0
            print "Resolution:", cvid.resolution
            print "Size (Mb):", os.path.getsize(vpath)/1024/1024

            #check for IFI issues
            t1 = getTime()
            ic, video_frame_times = checkVideoIFI(cvid)
            t2 = getTime()
            print
            print 'checkVideoIFI duration:', t2-t1
            print "checkVideoIFI Issue Count:", ic
            print


            print 'Find Video Start Sync Flashes....'
            # Get Video frame time to Event time offset and drift info
            _flash_msg_times = flash_msg_times_per_video[rec_video_index]

            t1=getTime()
            start_sync_frames,last_frame_checked = detectSyncTimeFrames(cvid, start_frame=1,
                                                     color_list=SYNC_COLORS,
                                                     sync_region=SYNC_TIME_BOX,
                                                     iterations=SYNC_TRANSITION_COUNT,
                                                     max_frames_searched=MAX_SEARCH_FRAMES,
                                                     color_thresh=SYNC_AVG_COLOR_THRESH,
                                                     std_thresh=SYNC_STD_COLOR_THRESH)
            t2 = getTime()
            print
            print 'Video Start detectSyncTimeFrames duration:', t2-t1


            print 'Find Video End Sync Flashes....'
            vendstart = cvid.total_frame_count-MAX_SEARCH_FRAMES
            vendstart = max(vendstart, last_frame_checked+20)
            t1 = getTime()
            end_sync_frames, _ = detectSyncTimeFrames(cvid, start_frame=vendstart,
                                                     color_list=SYNC_COLORS,
                                                     sync_region=SYNC_TIME_BOX,
                                                     iterations=SYNC_TRANSITION_COUNT,
                                                     max_frames_searched=MAX_SEARCH_FRAMES,
                                                     color_thresh=SYNC_AVG_COLOR_THRESH,
                                                     std_thresh=SYNC_STD_COLOR_THRESH)
            t2 = getTime()
            print
            print 'Video End detectSyncTimeFrames duration:', t2-t1

            start_sync_times = _flash_msg_times[:len(start_sync_frames)]
            end_sync_times = _flash_msg_times[len(start_sync_frames):]

            start_times = np.asarray([(tt[0][1],tt[1][0]) for tt in zip(start_sync_frames, start_sync_times)])
            end_times = np.asarray([(tt[0][1],tt[1][0]) for tt in zip(end_sync_frames, end_sync_times)])

            svidtimes, smsgtimes = start_times[:, 0], start_times[:, 1]
            evidtimes, emsgtimes = end_times[:, 0], end_times[:, 1]

            start_offsets = smsgtimes-svidtimes
            end_offsets = emsgtimes-evidtimes

            print
            print 'Session %s, Recording %d'%(session_name, rec_video_index+1)
            print
            print 'Start Sync Offsets:'
            print '\tMin Offset:', start_offsets.min()
            print '\tMax Offset:', start_offsets.max()
            print '\tOffset Range:', start_offsets.max()-start_offsets.min()
            print '\tMean Offset:', start_offsets.mean()
            print '\tStdev Offset:', start_offsets.std()
            print
            print 'End Sync Offsets:'
            print '\tMin Offset:', end_offsets.min()
            print '\tMax Offset:', end_offsets.max()
            print '\tOffset Range:', end_offsets.max()-end_offsets.min()
            print '\tMean Offset:', end_offsets.mean()
            print '\tStdev Offset:', end_offsets.std()

            print 'Timing Translation:'
            min_video_offset_diff = end_offsets.min() - start_offsets.min()
            max_video_offset_diff = end_offsets.max() - start_offsets.max()
            mean_video_offset_diff = end_offsets.mean() - start_offsets.mean()
            mean_video_offset = ( end_offsets.mean() + start_offsets.mean() ) / 2.0
            print '\tMin Video Drift:', min_video_offset_diff
            print '\tMax Video Drift:', max_video_offset_diff
            print '\tMean Video Drift:', mean_video_offset_diff
            print '\tMean Video Offset:', mean_video_offset
            print '---------------'

            # Convert video frame times to event time base.
            # Drift seems to be ~ 1 frame (i.e. 33 msec @ 30 fps) over 40 minute
            # video, so not worrying about drift correction in time base right now.
            # Should keep an eye on this as more videos are tested.
            video_frame_times[:,1] += mean_video_offset

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

        video_frame_evt_array = getEventsPerFrame(session_folder, session_rec_block_frame_events)
        print
        print "Events By Frame:"
        for e in video_frame_evt_array:
            ename = EventConstants.getName(e['event_type'])
            print e[0], e[1], ename, e[3], e[4]
        np.savez(os.path.join(session_folder, 'session_vframe_events.npz'), events=video_frame_evt_array)

    except:
        import traceback
        traceback.print_exc()
