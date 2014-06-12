===============================================
Configuring Confero View WebApp Notifications
===============================================

The Confero View WebApp supports a very flexible notification system which can be
used to define warning and / or error conditions that should be brought to the
attention of the experimenter during the real-time, remote, monitoring of
Confero Track.

Configuring a notification is sufficiently detailed to warrant a dedicated
section in this manual.

Notifications (or Alerts) are defined within the Confero View's app_config.yaml
file, within a section of the configuration file called *notifications*. Each
entry within the notifications section basically has the same set of
configuration options.

Notification Configuration Specification
==========================================

YAML Structure
----------------

A generic representation of the notifications config section is defined as follows:

.. code-block:: yaml

    notifications:

        device_label:

            # The list of valid device_status_field_name's is different for each
            # device supported by the notifications framework, and are given
            # further in this page.
            #
            device_status_field_name:

                 # If a Warning Alert is desired, add a warning section as follows
                 warning:
                      threshold: int or float
                      edges:
                          falling: bool
                          rising: bool
                      minimum_time_period: int or float
                      growl:
                          text: string
                          duration: int, float, or one of these constants: AUTO, MANUAL

                 # If an Error Alert is desired, add an error section as follows
                 error:
                      threshold: int or float
                      edges:
                          falling: bool
                          rising: bool
                      minimum_time_period: int or float
                      growl:
                          text: string
                          duration: int, float, or one of these constants: AUTO, MANUAL

            device_status_field_name_n:
                 # same configuration options as in the above
                 # device_status_field_name example
                 # .....

        device_label_n:
            # same configuration options as in the above
            # device_label example
            # .....


Device Label Options
--------------------

Each ``device_label`` entry in the ``notifications`` configuration must be one
of the following supported values:

.. cssclass:: table-hover
.. cssclass:: table-bordered

===================== ============= ==============================
Device Label          ioHub Device  Comments
===================== ============= ==============================
eyetracker            Eye Tracker   One of the eye trackers supported by the ioHub Common Eye Tracker Interface.
keyboard              Keyboard      The ioHub Keyboard device.
mouse                 Mouse         The ioHub Keyboard device.
input_computer        N/A           The computer Confero Track is running on. This is not an ioHub device.
server_computer       N/A           The computer Confero View is running on. This is not an ioHub device.
experiment_session    N/A           Not even a device really. Holds information about the currently open experiment session.
===================== ============= ==============================

Device Status Field Options
----------------------------

Each ``device_label`` has a different set of valid ``device_status_field_name``
entries that can be used when defining a notification.

eyetracker
~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
average_gaze_position     TBC
proportion_valid_samples  TBC
rms_noise                 TBC
stdev_noise               TBC
right_eye_gaze            TBC
right_eye_pos             TBC
right_eye_pupil           TBC
left_eye_gaze             TBC
left_eye_pos              TBC
left_eye_pupil            TBC
time                      TBC
model                     TBC
track_eyes                TBC
sampling_rate             TBC
========================= ======================================================

keyboard
~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
type                      TBC
last_event_time           TBC
key                       TBC
auto_repeated             TBC
modifiers                 TBC
========================= ======================================================

mouse
~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
type                      TBC
last_event_time           TBC
position                  TBC
buttons                   TBC
modifiers                 TBC
scroll                    TBC
========================= ======================================================

input_computer
~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
cpu_usage_all             TBC
memory_usage_all          TBC
up_time                   TBC
========================= ======================================================

server_computer
~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
cpu_usage_all             TBC
memory_usage_all          TBC
========================= ======================================================

experiment_session
~~~~~~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
code                      TBC
experiment_name           TBC
recording_counter         TBC
========================= ======================================================

Warning and Error Settings
----------------------------

A notification can contain a ``warning`` and / or an ``error`` property. Both
are defined by proving a set of possible configuration settings. The setting
options are the same for ``warning`` and ``error`` definitions.

.. cssclass:: table-hover
.. cssclass:: table-bordered

=================== =============== ========================= ==================
Property Name       Parent          Valid Values              Description
=================== =============== ========================= ==================
threshold           warning / error int, float                TBC
edges               warning / error N/A                       TBC
falling             edges           True, False               TBC
rising              edges           True, False               TBC
minimum_time_period warning / error int, float                TBC
growl               warning / error N/A                       TBC
text                growl           str, unicode              TBC
duration            growl           int, float, MANUAL, AUTO  TBC
=================== =============== ========================= ==================
