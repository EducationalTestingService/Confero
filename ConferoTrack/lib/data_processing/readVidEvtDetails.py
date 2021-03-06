__author__ = 'Sol'
from psychopy.iohub import EventConstants
import os
from common import openDataStoreReader, Picker
import numpy as np

SESSION_PATH = r'..\..\Results\Default_Experiment\s1'
FRAME_EVENT_FILE = r'session_vframe_events.npz'
FILTERS = dict(event_type=[EventConstants.MONOCULAR_EYE_SAMPLE,], video_id=[0,], filter_id=[23,])
BATCH_SIZE = 100

def getEventDetails(session_path, frame_event_lookup_file, filters, batch_size):
    session_folder = os.path.normpath(os.path.abspath(session_path))
    datastore_reader = openDataStoreReader(session_folder)
    frame_events_lookup = np.load(os.path.join(session_folder, frame_event_lookup_file))['events']
    event_types = filters.get('event_type', np.unique(frame_events_lookup['event_type']))

    for etype in event_types:
        filters['event_type'] = [etype,]
        filtered_table_rows = Picker(frame_events_lookup).pick_data('event_table_row_index', **filters)
        event_table = datastore_reader.getEventTable(etype)
        while len(filtered_table_rows) > 0:
            row_nums = [int(i) for i in filtered_table_rows[:batch_size]]
            yield event_table[row_nums]
            filtered_table_rows = filtered_table_rows[batch_size:]
    datastore_reader.close()


if __name__ == '__main__':
        for event_details_batch in getEventDetails(SESSION_PATH, FRAME_EVENT_FILE, FILTERS, BATCH_SIZE):
            for event in event_details_batch:
                print EventConstants.getName(event['type']), event['time'], event['filter_id']