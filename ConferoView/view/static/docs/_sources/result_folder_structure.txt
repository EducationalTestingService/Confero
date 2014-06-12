.. _results_folder:

===========================
Results File Organization
===========================

All data files created by Confero Track during experiment session recording
periods are saved within the ``CONFERO_TRACK_ROOT/Results`` folder on the
Confero Track computer. The ``CONFERO_TRACK_ROOT/Results`` folder will be
termed the ``CONFERO_RESULTS_ROOT`` in this document.

.. danger:: Do not delete, rename, edit, move, or reorganize any file or folder
   within the ``CONFERO_RESULTS_ROOT``. Doing so will jeopardise the data
   integrity of one or more experiment's results.

.. note:: Adding files that do not use the naming convention of any existing
   file type is OK.

Results Directory Hierarchy
============================

Confero Track organizes data files within the ``CONFERO_RESULTS_ROOT`` using
a nested directory structure:

* Each folder in the ``CONFERO_RESULTS_ROOT`` contains the data collected
  for an individual Experiment. An Experiment folder in the ``CONFERO_RESULTS_ROOT``
  is called an ``EXPERIMENT_RESULTS_FOLDER``; the folder name being the name of
  the experiment it represents.
* Each ``EXPERIMENT_RESULTS_FOLDER`` contains 0 - N Session folders, as well a
  a single file named ``iohub_events_.hdf5``.

  * Each Experiment Session folder ( or ``SESSION_DATA_FOLDER``) contains the
    files created for each recording period performed for that run of the experiment.
  * The ``iohub_events.hdf5`` file contains all the device events collected
    by the ioHub for every session of the experiment. This includes eye tracker,
    keyboard, mouse, and custom experiment message events.

Results Directory File Organization
====================================

The following diagram provides the full directory and file type hierarchy within
the ``CONFERO_RESULTS_ROOT``.

.. code-block:: yaml

    CONFERO_RESULTS_ROOT
      |
      -> ExperimentFolder1
      |     |
      |     |-- iohub_events_.hdf5
      |     |
      |     -> SessionFolder1
      |             |
      |             |-- validation_[year_month_day_hour_minute].png
      |             |-- validation_[year_month_day_hour_minute].png
      |             |
      |             |-- screen_capture_1.mkv
      |             |-- ffmpeg_stderr_1.txt
      |             |-- ffmpeg_stdout_1.txt
      |             |
      |             |-- screen_capture_N.mkv
      |             |-- ffmpeg_stderr_N.txt
      |             |-- ffmpeg_stdout_N.txt
      |             |
      |             |-- last_app_config.yaml
      |             |-- last_iohub_config_xxxx.yaml
      |
      |     -> SessionFolderN
      |             |
      |             | .....
      |
      -> ExperimentFolderN
      |     |
      |     | ....

Each ``SESSION_DATA_FOLDER`` contains a set of files for each recording period
performed while that session was open. A recording period is the time from when
the ``Start Recording Data`` button is pressed in the Confero View WebApp, until
the ``Stop Recording Data`` button is pressed or the Confero View WebApp is shut
down.

Experiment Session Folder File Types
=====================================

Files within a ``SESSION_DATA_FOLDER`` that are created for each recording period
are identified by having the current recording period count for the session appended
to the end of their file names.

.. cssclass:: table-hover
.. cssclass:: table-bordered

============================= ==================== ==============================
File Name                     Created              Description
============================= ==================== ==============================
validation_yy_mm_dd_hh_mm.png Each ET Validation   The figure displayed at the end of an Eye Tracker Validation. Each file name includes the date (yy_mm_dd) and time (hh_mm) when the image was created.
screen_capture_x.mkv          Each Rec. Period     The Screen Capture Video file for the recording period number x.
ffmpeg_stderr_x.txt           Each Rec. Period     Any output to stderr from the ffmpeg process which is saving the video file.
ffmpeg_stdout_x.txt           Each Rec. Period     Any output to stdout from the ffmpeg process which is saving the video file.
last_app_config.yaml          On Session Creation  A copy of the Confero Track's app_config.yaml file used for the session.
last_iohub_config_xxxx.yaml   On Session Creation  A copy of the iohub configuration file used by Confero Track for the session.
============================= ==================== ==============================