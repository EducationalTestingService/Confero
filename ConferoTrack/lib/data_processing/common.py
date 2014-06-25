__author__ = 'Sol'

import glob
import os
import psychopy.iohub.datastore.util as dsutil
import numpy as np
from psychopy.iohub import load, Loader
from psychopy.iohub import dump, Dumper

class Picker:
    def __init__(self, data):
        self._data = data
        self._calculate_pick_mask = self._calculate_pick_mask_meth1

    def pick_data(self, colname, **kwargs):
        return self._data[colname][self._calculate_pick_mask(kwargs)]

    def pick_mask(self, **kwargs):
        return self._calculate_pick_mask(kwargs)

    def _calculate_pick_mask_meth1(self, kwargs):
        # Begin with all true
        mask = np.ones(self._data.shape, dtype=bool)

        for colname, ok_value_list in kwargs.items():
            # OR together all records with _data['colname'] in ok_value_list
            one_col_mask = np.zeros_like(mask)
            for ok_value in ok_value_list:
                one_col_mask = one_col_mask | (self._data[colname] == ok_value)

            # AND together the full mask with the results from this column
            mask = mask & one_col_mask

        return mask

    def _calculate_pick_mask_meth2(self, kwargs):
        mask = reduce(np.logical_and,
                        [reduce(np.logical_or,
                                [self._data[colname] == ok_value
                                    for ok_value in ok_value_list]) \
                            for colname, ok_value_list in kwargs.items()])





def getVideoFilesFromSessionPath(session_path):
    video_files = glob.glob(session_path + os.path.sep + '*.mkv')
    return video_files


def openDataStoreReader(session_folder):
    exp_path, session_name = session_folder.rsplit(os.path.sep, 1)
    hubdata = dsutil.ExperimentDataAccessUtility(exp_path,
                                                     'iohub_events.hdf5',
                                                     sessionCodes=[
                                                         session_name])
    return hubdata


def readAppSettingParameters(session_folder):
    #recording_period:
    #    start_msg: RECORDING_STARTED
    #    event_period:
    #        start_msg: START_EVENT_PERIOD
    #        end_msg: END_EVENT_PERIOD
    #    end_msg: RECORDING_STOPPED
    return load(file(os.path.join(session_folder,
                                      'last_app_config.yaml'), u'r'),
                                                        Loader=Loader)

