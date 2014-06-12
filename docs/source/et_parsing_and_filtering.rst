===============================
Eye Tracker Sample Processing
===============================


Eye Event Parsing
==================

Confero Track uses the eye samples received from the eye tracker device
being used and generates eye events by parsing the sample data. ioHub
Fixation , Saccade, and Blink event types are generated online as the eye sample
data is being collected. For details on the ioHub Eye Track Event Types,
refer to the `ioHub eye event documentation`_.

.. _ioHub eye event documentation: http://www.isolver-solutions.com/iohubdocs/iohub/api_and_manual/device_details/eyetracker.html#eyetracker-event-types

.. note::The event parser implementation is an ongoing development effort, as the parser
         logic is tried to be improved. The parser is designed to work with
         monocular and binocular eye data,but only binocular input samples have been
         tested so far..

If binocular input samples are being used, they are converted to monocular
samples for parsing. If both left and right eye position data is available
for a sample, the positions are averaged together. If only one of the two eyes
has valid data, then that eye data is used for the sample. So the only case
where a sample will be tagged as missing data is when both eyes do not have
valid eye position / pupil size data.

The online event parser uses an adaptive velocity threshold algorithm. The threshold
is updated for every sample received from the eye tracker.

The online parser does not currently use any 'heuristics' when determining if
an event has started or finished. Therefore there are not any parameters to
configure for the event parser itself.

Eye Sample Filtering
=====================

The filtered monocular sample stream that is created and used as the eye sample
input to the event parser does have configurable settings. These settings are
specified in the ``CONFERO_TRACK_ROOT\settings\app_config.yaml`` file; in the
event_filters section of the file. Please refer to the :ref:`confero_track_config`
section of the manual to review the filter setting defaults.

The sample filtering process can apply two different types of filtering to the
filtered sample stream that is created. One filter can be applied to the
positional data of the samples, namely the gaze position and eye angle sample fields
( the POSITION_FILTER ). The other filter can be applied to the velocity
measure that is calculated using the filtered sample positional fields ( the VELOCITY_FILTER ).
These filters are called ``event field filter's``, because they can operate on a single
iohub event (or sample) field, using the value of that field as the filters data input stream.

Event Field Filter Types
=========================

The POSITION_FILTER and VELOCITY_FILTER can be set to one of five different
``event field filter`` algorithms. Each filtering algorithm has different configuration
parameters that can be set.


eventfilters.PassThroughFilter
---------------------------------

The PassThroughFilter is a NULL filter. In other words, the filter does
not do any filtering.

Parameters:
~~~~~~~~~~~

None

Example:
~~~~~~~~~~

Velocity data is calculated from (filtered) sample positions, but is not
filtered itself.

.. code-block:: yaml

    VELOCITY_FILTER = eventfilters.PassThroughFilter, {}

eventfilters.MovingWindowFilter
--------------------------------

The MovingWindowFilter is a standard averaging filter. Any data within the
window buffer are simply averaged together to give the filtered value for a
given event field.

Parameters:
~~~~~~~~~~~

* **length**: The size of the moving window in samples. Minimum of 2 required.
* **knot_pos**: The index within the moving window that should be used to extract
  a sample from and apply the current window filtered value.

Example:
~~~~~~~~~

The MovingWindowFilter is applied to x and y gaze data fields of eye samples. The
window size is three, and each sample position is filtered using data from the
previous and next samples as well as itself.

.. code-block:: yaml

    POSITION_FILTER = eventfilters.MovingWindowFilter, {length: 3, knot_pos:'center'}

eventfilters.MedianFilter
-----------------------------

MedianFilter applies the median value of the filter window to the knot_pos
window sample.

Parameters:
~~~~~~~~~~~~

* **length**: The size of the moving window in samples. Minimum of 3 is
  required and the length must be odd.
* **knot_pos**: The index within the moving window that should be used to extract
  a sample from and apply the current window filtered value.

Example:
~~~~~~~~~

Sample position fields are filtered by the median value of three samples, those
being the current sample and the two following samples (so the current sample is
at index 0.

.. code-block:: yaml

    POSITION_FILTER = eventfilters.MedianFilter, {length: 3, knot_pos: 0}


eventfilters.WeightedAverageFilter
-----------------------------------

WeightedAverageFilter is similar to the standard MovingWindowFilter field filter,
however each element in the window is assigned a weighting factor that is used
during averaging.

Parameters:
~~~~~~~~~~~~

* **weights**: A list of weights to be applied to the window values. The window
  length is == len(weights). The weight values are all normalized to sum to 1
  before being used in the filter. For example, a weight list of (25,50,25)
  will be converted to (0.25,0.50,0.25) for use in the filter, with window
  value index i being multiplied by weight list index i.
* **knot_pos**: The index within the moving window that should be used to extract
  a sample from and apply the current window filtered value.

Example:
~~~~~~~~

A weighted average window filter will be applied to x and y velocity fields.
The length of the window is 3 samples, and the filtered sample index retrieved
is 1, the same as using 'center' in this case. The filtered sample index will
count toward 1/2 the weighted average, with the previous and next samples
contributing 1/4 of the weighted average each.

.. code-block:: yaml

    VELOCITY_FILTER = eventfilters.WeightedAverageFilter, {weights: (25,50,25), knot_pos: 1}


eventfilters.StampFilter
--------------------------

A variant of the filter proposed by Dr. David Stampe (1993 ???). A window of
length 3 is used, with the knot_pos centered, or at index 1. If the current
3 values in the window list are monotonic, then the sample is not filtered.
If the values are non-monotonic, then v[1] = (v[0]+v[2])/2.0

Parameters:
~~~~~~~~~~~~

* **levels**: The number of iterations (recursive) that should be applied to the
  windowed data. Minimum value is 1. The number of levels equals
  the number of samples the filtered sample will be delayed
  compared to the non filtered sample time.

Example:
~~~~~~~~~

Data is filtered once, similar to what a 'normal' filter level would be in the
eyelink<tm> system. Level = 2 would be similar to the 'extra' filter level
setting of eyelink<tm>.

.. code-block:: yaml

    POSITION_FILTER = eventfilters.StampFilter, {level: 1}
