===============================
Stand Alone Python Scripts
===============================

The ``CONFERO_TRACK_ROOT/lib/`` folder contains various stand alone
python scripts that have been written to help with the process of accessing and
visualizing some of the data collected by the Confero system.

Data Processing
================

The ``CONFERO_TRACK_ROOT/lib/data_processing`` folder contains scripts related
to accessing the screen capture video frames, as well as iohub device events,
recorded during an experiment session.

videvt2ssa.py
--------------

The videvt2ssa.py creates .ssa files for the recordings preformed a single
experiment session.

This script must be run by first starting the ``Confero Data Processing.bat``
file located in the ``CONFERO_ROOT`` folder. When the .bat file runs, it will
open a cmd prompt in the ``CONFERO_TRACK_ROOT/lib/data_processing`` folder.

You can then run the script by typing:

.. code-block:: python

    python.exe videvt2ssa.py [experiment_folder_name] [session_folder_name]

where:

* [experiment_folder_name] is the folder in the ``CONFERO_TRACK_ROOT/Results``
  for the experiment containing the session folder.
* [session_folder_name] is the name of the session folder to use within the
  named experiment folder.

One .ssa file is created for each video file in the session folder, and is named
the same as the video file, but with a .ssa extension.

vidEvtLookupTable.py
----------------------

When this script is run, any screen capture video files in the session folder
defined by ``SESSION_PATH`` are processed resulting in:

* Synchronizing video frame times with the iohub event timebase, allowing each
  video frame time to be converted to an iohub event time.
* Creation a video frame iohub event lookup table, containing event id's grouped
  by frame number.
* Saving this lookup table to a session_vframe_events.txt or
  session_vframe_events.npz file within the ``SESSION_PATH`` of the source data.


readVidEvtDetails.py
----------------------

This script is a simple example of how to read a session_vframe_events.npz file
and the experiment's iohub_events.hdf5 file. By doing so, all the fields of
iohub events that occurred during the time period represented by each screen
capture video.

The script prints out some of the fields for each event read that occurred
during each frame index of the video(s).

By extending this script, custom event reading scripts can be created where the
association of the events to the correct screen capture video frame is important.


Data Plotting
==============

The ``CONFERO_TRACK_ROOT/lib/visualization`` folder contains scripts related
to plotting / viewing some aspect of the data collected during recording periods.

eyetrace_view.py
--------------------

This script was written to assist in visualizing the results of the online
eye sample stream parsing filter that has been (and will continue to be)
developed. The script draws a strip chart for each recording period of the
specified session. Several measures related to eye samples are plotted:

* Horizontal and vertical eye position in visual degrees.
* X and Y velocity ( degrees / second of motion)
* X and Y Velocity Adaptive Threshold value

Vertical bars are plotted representing saccade and blink events that have been
parsed.

The plot window that is displayed uses data from one recording period of the session,
starting with the first. When the plot window is closed, a new window is
shown using data from the next recording period of the session.


Javascript Event Access
=======================

A simple javascript library has been written which allows a web page being viewed by
the **participant** to access the device event data that is made available to the
Confero View program.

The ``CONFERO_TRACK_ROOT/lib/track_jsws`` folder contains the conferoviewevents.js
script containing the event access library. The folder also includes an example
html page that uses the library and prints out each event message received by
the browser.

The conferoviewevents.js library opens up interesting possibilities to a
researcher using Confero. For example, gaze control or gaze contingent
paradigms could be scripted from within the web page being viewed by the participant.
This can be done in parallel to the standard screen capturing and
remote status monitoring features of Confero.