import numpy as np
from cv2video import OpenCVideo
import os
import sys
import cv2

VIDEO_FILE_PATH = r"..\datacollection\results\first_exp\latesttest\screen_capture_1.mkv"
SHOW_VIDEO = True

def detectSyncTimeFrames(cvid, start_frame, color_list=(255.0, 0.0), sync_region=(0, 0, 100, 100), iterations=3):
    """
    Returns an array of (frame_number, frame_time) tuples found at the start of the video file based
    on the args provided. If > 2 minutes of frames are serached, the alg with quit and return None.

    TODO: Also get sync frames for end of video, say start searching from 30*120
          frames before end of video.
    """

    r = cvid.seek(frame_number=start_frame)
    if r is False:
        return None

    l, t, r, b = sync_region
    synctimes=[]
    std_thresh = 10.0
    color_thresh = 10.0

    for i in range(iterations*len(color_list)):
        target_color = color_list[i%len(color_list)]
        while 1:
            frame_index = cvid.getNextFrameHeader()
            if frame_index:
                vframe = cvid.getNextFrameArray()
                if vframe is not None:
                    fmean, fstd = vframe[t:b, l:r, :].mean(), vframe[t:b, l:r, :].std()
                    print frame_index, fmean, fstd, target_color
                    if fstd < std_thresh and np.abs(fmean-target_color) < color_thresh:
                        synctimes.append((frame_index, cvid.frame_time))
                        print 'sync found:', (frame_index, cvid.frame_time)
                        break
                    if frame_index > start_frame+30*120:
                        print "Error: Max frame index for detectSyncTimeFrames reached."
                        return synctimes
            else:
                print "Error: End of Video reached without detecting all sync frames"
                return synctimes

    r = cvid.seek(frame_number=1)
    if r is False:
        print "Error: Could not seek to start of video."
        return synctimes
    return synctimes

def processFrame(cvid, frame):
    print "frame %d 100x100:\n\tcolor mean: %.3f\n\tstdev: %.3f"%(cvid.frame_index, frame[0:100, 0:100, :].mean(), frame[0:100, 0:100, :].std())

try:
    cvid = OpenCVideo(os.path.abspath(VIDEO_FILE_PATH))
    print cvid

    start_sync_frames = detectSyncTimeFrames(cvid, start_frame=1)
    print
    print 'start_sync_frames:', start_sync_frames
    end_sync_frames = detectSyncTimeFrames(cvid, start_frame=cvid.total_frame_count-(30*120))
    print
    print 'end_sync_frames:', end_sync_frames


    if SHOW_VIDEO:
        cv2.namedWindow('frame', flags = cv2.cv.CV_WINDOW_NORMAL)

    run = True
    while run:
        frame_index = cvid.getNextFrameHeader()
        #cvid.printFrameInfo()

        if frame_index:
            vframe = cvid.getNextFrameArray()
            if vframe is not None:
                processFrame(cvid, vframe)
                if SHOW_VIDEO:
                    cv2.imshow('frame', vframe)
            else:
                run = False
            if cv2.waitKey(1) & 0xFF == ord('q'):
                run = False
        else:
            run = False
except:
    import traceback
    traceback.print_exc()

cv2.destroyAllWindows()