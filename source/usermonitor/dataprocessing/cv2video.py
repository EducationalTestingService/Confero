__author__ = 'Sol'

import cv2

COUNT_FRAMES_IF_NEEDED = True

class OpenCVideo(object):
    def __init__(self, filename):
        self.reset()
        self.loadVideo(filename)

    @property
    def frame_index(self):
        return self._next_frame_index

    @property
    def frame_time(self):
        return self._next_frame_sec

    @property
    def total_frame_count(self):
        return self._total_frame_count

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
                        raise RuntimeError( "Error when reading image file")
                    self._total_frame_count = last_index

            else:
                raise ValueError("Video file frame count must be > 0:", self._total_frame_count)
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
            raise RuntimeError("Could not load video frame data.")

    def seek(self, timestamp=None, frame_number=None):
        if timestamp:
            return self._video_stream.set(cv2.cv.CV_CAP_PROP_POS_MSEC,
                                             timestamp*1000.0)
        elif frame_number:
            return self._video_stream.set(cv2.cv.CV_CAP_PROP_POS_FRAMES,
                                            frame_number)

    def unload(self):
        if self._video_stream:
            self._video_stream.release()
        self._video_stream = None

    def __del__(self):
        self.unload()
