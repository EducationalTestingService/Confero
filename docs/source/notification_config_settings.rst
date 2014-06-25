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
average_gaze_position     The pixel position of the eye on the screen, averaged over the last 0.25 seconds
proportion_valid_samples  The invalid sample count / total sample count over the last second.
rms_noise                 The root mean square noise estimate of the eye sample data.
stdev_noise               The standard deviation of the gaze position estimate.
right_eye_gaze            The last read pixel position of the eye on the screen. 0,0 is screen center.
right_eye_pos             The last read eye position in the eye trackers 3D coordinate space (only on Tobii).
right_eye_pupil           The last read size of the pupil. For Tobii, it is the mm diameter. For eyelink, it is the area in arbitrary units.
left_eye_gaze             Not Used, as the sample parser filter outputs mono samples that are placed in the right eye data fields.
left_eye_pos              Not Used
left_eye_pupil            Not Used
time                      The current eye tracker time.
model                     The model of the eye tracker being used. This is read from the iohub_config.yaml
track_eyes                The eyes being tracked; or BINOCULAR_AVERAGED when the sample parser is enabled (default)
sampling_rate             The current sampling rate of the eye tracker.
========================= ======================================================

keyboard
~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
type                      The iohub event type constant for the last event.
last_event_time           The time of the last event (in seconds).
key                       The last key that way pressed.
auto_repeated             The number of auto repeat events that the OS has created for the key press
modifiers                 Any iohub modifier constants that were pressed at the same time as the key press.
========================= ======================================================

mouse
~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
type                      The iohub event type constant for the last event.
last_event_time           The time of the last event (in seconds).
position                  The position of the mouse, in pixels. (0,0) is screen center
buttons                   The iohub string constants for any mouse buttons pressed for / during the event.
modifiers                 Any iohub modifier constants that were pressed at the same time as the mouse event.
scroll                    The current scroll position of the mouse device.
========================= ======================================================

input_computer
~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
cpu_usage_all             The total CPU used on the Confero Track computer, averaged over the last 0.5 seconds.
memory_usage_all          The total amount of RAM used on the computer, averaged over the last 0.5 seconds.
up_time                   The time since the confero software started on the computer.
========================= ======================================================

server_computer
~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
cpu_usage_all             The total CPU used on the Confero View computer, averaged over the last 0.5 seconds.
memory_usage_all          The total amount of RAM used on the computer, averaged over the last 0.5 seconds.
========================= ======================================================

experiment_session
~~~~~~~~~~~~~~~~~~~~

.. cssclass:: table-hover
.. cssclass:: table-bordered

========================= ======================================================
device_status_field_name  Description
========================= ======================================================
code                      The code of the currently open experiment session.
experiment_name           The experiment folder name being used to save session data.
recording_counter         The number of times recording has been started / stopped for the current session.
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
threshold           warning / error int, float                The value used to trigger a warning or error.
edges               warning / error N/A
falling             edges           True, False               If True, an alert will occur when the field value goes below threshold.
rising              edges           True, False               If True, an alert will occur when the field value goes above threshold.
minimum_time_period warning / error int, float                The alert is only generated when the threshold has been crossed for this many seconds.
growl               warning / error N/A                       Use if a alert balloon should be displayed when triggered.
text                growl           str, unicode              The text to display in the alert balloon.
duration            growl           int, float, MANUAL, AUTO  If MANUAL, the growl must be closed by the operator. If AUTO, the growl is removed when the alert condition ends. If a number, the growl is displayed for that number of seconds.
=================== =============== ========================= ==================
