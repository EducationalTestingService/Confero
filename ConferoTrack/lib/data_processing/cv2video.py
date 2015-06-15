__author__ = 'Sol'

import cv2
import numpy as np

COUNT_FRAMES_IF_NEEDED = True

class OpenCVideo(object):
    def __init__(self, filename):
        self.reset()
        self.loadVideo(filename)
        self.filname=filename

    @property
    def frame_index(self):
        return self._next_frame_index

    @property
    def frame_time(self):
        return self._next_frame_sec

    @property
    def last_frame_index(self):
        return self._prev_frame_index

    @property
    def last_frame_time(self):
        return self._prev_frame_sec

    @property
    def total_frame_count(self):
        return self._total_frame_count

    @property
    def frame_rate(self):
        return self._video_frame_rate

    @property
    def ifi(self):
        return self._inter_frame_interval

    @property
    def resolution(self):
        return self._video_width,self._video_height

    def reset(self):
        self.duration = None
        self._video_stream = None
        self._total_frame_count = None
        self._video_width = None
        self._video_height = None
        # TODO: Read depth from video source
        self._video_frame_depth = 3
        self._video_frame_rate = None
        self._inter_frame_interval = None
        self._prev_frame_sec = None
        self._next_frame_sec = None
        self._next_frame_index = None
        self._prev_frame_index = None
        self._video_perc_done = None
        #self._video_track_clock = Clock()

    def loadVideo(self, filename):
        self.unload()
        self.reset()

        # Create Video Stream stuff
        self._video_stream = cv2.VideoCapture()
        self._video_stream.open(filename)
        if not self._video_stream.isOpened():
          raise RuntimeError( "Error when reading image file")

        self._total_frame_count = int(self._video_stream.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        if self._total_frame_count <= 0:
            if COUNT_FRAMES_IF_NEEDED:
                print "Invalid frame count read:", self._total_frame_count, ". Counting frames..."
                findex=1
                last_index=0
                while findex is not None:
                    findex=self.getNextFrameHeader()
                    if findex is not None:
                        last_index = findex
                        if findex%30==0:
                            print "Reading Frame ", findex,'\r',
                if last_index > 0:
                    self.unload()
                    self.reset()
                    self._video_stream = cv2.VideoCapture()
                    self._video_stream.open(filename)
                    if not self._video_stream.isOpened():
                        raise RuntimeError( "Error when reading image file: "+self.filname)
                    self._total_frame_count = last_index

            else:
                raise ValueError("Video file frame count must be > 0:", self._total_frame_count, self.filname)
        self.filename = filename
        self._video_width = self._video_stream.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
        self._video_height = self._video_stream.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)
        self._format = self._video_stream.get(cv2.cv.CV_CAP_PROP_FORMAT)
        # TODO: Read depth from video source
        self._video_frame_depth = 3
        self._video_frame_rate = self._video_stream.get(cv2.cv.CV_CAP_PROP_FPS)
        self._inter_frame_interval = 1.0/self._video_frame_rate
        self.duration = self._total_frame_count * self._inter_frame_interval

    def __str__(self):
        vstr = "OpenCV Video Object:\n"
        vstr += "\n\tPath:\t\t{0}".format(self.filename)
        vstr += "\n\tWidth:\t\t{0}".format(self._video_width)
        vstr += "\n\tHeight:\t\t{0}".format(self._video_height)
        vstr += "\n\tDepth:\t\t{0}".format(self._video_frame_depth)
        vstr += "\n\tFormat:\t\t{0}".format(self._format)
        vstr += "\n\tFrame Count:\t\t{0}".format(self._total_frame_count)
        vstr += "\n\tFPS:\t\t{0}".format(self._video_frame_rate)
        vstr += "\n\tFrame Interval:\t\t{0}".format(self._inter_frame_interval)
        vstr += "\n\tDuration:\t\t{0}".format(self.duration)
        return vstr

    def printFrameInfo(self):
            print "Frame\t%d\t\t%.3f\t\t%.3f"%(self._next_frame_index, self._next_frame_sec, self._video_perc_done)

    def getNextFrameHeader(self):
        # get next frame info ( do not decode frame yet)
        if self._video_stream.grab():
            self._prev_frame_index = self._next_frame_index
            self._prev_frame_sec = self._next_frame_sec
            self._next_frame_sec = self._video_stream.get(cv2.cv.CV_CAP_PROP_POS_MSEC)/1000.0
            self._next_frame_index = self._video_stream.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
            self._video_perc_done = self._video_stream.get(cv2.cv.CV_CAP_PROP_POS_AVI_RATIO)
            self._next_frame_displayed = False
            return self._next_frame_index

    def getNextFrameArray(self):
        # decode frame into np array and move to opengl tex
        ret, f = self._video_stream.retrieve()
        if ret:
            return f#cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        else:
            raise RuntimeError("Could not load video frame data.", self.filname)

    def seek(self, timestamp=None, frame_number=None):
        if timestamp:
            return self._video_stream.set(cv2.cv.CV_CAP_PROP_POS_MSEC,
                                             timestamp*1000.0)
        elif frame_number:
            return self._video_stream.set(cv2.cv.CV_CAP_PROP_POS_FRAMES,
                                            frame_number)

    @property
    def frametimes(self, start_frame=0):
        """
        Returns an array of frame index, frame time tuples.
        Also checks for any duplicate frame times or longer than expected IFI's.
        """
        cvid = self
        initial_frame = cvid.frame_index
        r = cvid.seek(frame_number=start_frame)
        if r is False:
            return None
        issue_count = 0
        frame_index = 1
        ifi = cvid.ifi
        usec_ifi = int(ifi * 1000000)

        frame_times = np.zeros((cvid.total_frame_count, 2), dtype=np.float32)
        while frame_index:
            frame_index = cvid.getNextFrameHeader()
            if frame_index:
                frame_time = cvid.frame_time
                frame_times[frame_index - 1][0] = frame_index - 1
                frame_times[frame_index - 1][1] = frame_time
                if frame_index == 1:
                    first_frame_index = frame_index
                    first_frame_time = frame_time
                elif cvid.last_frame_index:
                    index_diff = frame_index - cvid.last_frame_index
                    time_diff = frame_time - cvid.last_frame_time
                    usec_time_diff = int(round(time_diff * 1000000))
                    if index_diff != 1 or usec_time_diff != usec_ifi:
                        print 'checkVideoIFI alert:', frame_index, frame_time, \
                               index_diff, usec_time_diff, usec_ifi
                        issue_count += 1
        cvid.seek(frame_number=initial_frame)
        return frame_times


    def detectSyncTimeFrames(self, start_frame, color_list, sync_region, iterations,
                             max_frames_searched, color_thresh, std_thresh):
        """
        Returns an array of (frame_number, frame_time) tuples found at the start of
        the video file based on the args provided. If > max_frames_searched
        is reached, the alg with quit and return None.
        """
        cvid = self

        r = cvid.seek(frame_number=start_frame)
        if r is False:
            return None

        l, t, r, b = sync_region
        synctimes = []
        std_thresh = std_thresh
        color_thresh = color_thresh
        frame_index = -1
        for i in range(iterations * len(color_list)):
            target_color = color_list[i % len(color_list)]
            while 1:
                frame_index = cvid.getNextFrameHeader()
                if frame_index:
                    vframe = cvid.getNextFrameArray()
                    if vframe is not None:
                        fmean, fstd = vframe[t:b, l:r, :].mean(), vframe[t:b, l:r,
                                                                  :].std()
                        #print frame_index, fmean, fstd
                        if fstd < std_thresh and np.abs(
                                        fmean - target_color) < color_thresh:
                            #print 'HIT:',len(synctimes),frame_index, fmean, fstd
                            synctimes.append((frame_index, cvid.frame_time))
                            break
                        if frame_index > start_frame + max_frames_searched:
                            print "Error: Max frame index for detectSyncTimeFrames reached.:",self.filname,len(synctimes)
                            return synctimes, frame_index
                else:
                    print "Error: End of Video reached without detecting all sync frames:",self.filname,len(synctimes)
                    return synctimes, frame_index

        r = cvid.seek(frame_number=1)
        if r is False:
            print "Error: Could not seek to start of video."
        return synctimes, frame_index

    def unload(self):
        if self._video_stream:
            self._video_stream.release()
        self._video_stream = None

    def __del__(self):
        self.unload()
