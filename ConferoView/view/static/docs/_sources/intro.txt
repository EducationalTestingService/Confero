==========================
Introduction
==========================

**Confero** is a screen and user event capturing system for Windows.
Useful for general HCI research, Confero captures a video of the
user's computer desktop while saving all keyboard and mouse events.
Confero has built in support for several eye tracker models as well
as other computer input devices. A remote, web based, monitoring application
is provided allowing the status and performance of experiment to be
monitored in real-time, using a desktop or tablet browser.

Confero Track and View Applications
====================================

Confero consists of two applications which run in parallel, communicating via a
LAN connection and the Bonjour service. The Confero Track Application
provides the screen capture and data collection functionality,
while Confero View is providing web browser based real-time feedback
of participant and equipment performance as well as remote control of the
Confero Track Application.

System Architecture Diagram
============================

.. image:: /images/ConferoOverviewDiagram.png
   :align: center

Key Features
=============

Confero View
-------------

* Includes an embedded web server that renders the Confero View's
  user interface as a browser based web application,
  viewed using the Chrome web browser.

* Allows the researcher to monitor the progress and performance of the
  participant during data recording, including:

  * Real-time display of screen capture video stream
  * Overlay mouse and gaze position on the screen capture video.
  * View important information regarding the state of the two computers
    being used by Confero, as well as the devices being monitored.
  * Generates _warning_ and _error_ alerts, identifying possible issues
    during data collection.

* The researcher controls the Confero Track application via the Confero View
  UI, including support for:

  * Selecting which Experiment data will be collected for.
  * Creating and closing experiment sessions.
  * Starting and stopping recording of data during an experiment session.
  * Inserting custom text messages into the data during recording.
  * Stopping the Confero Track and Confero View applications.

Confero Track
--------------

* Runs on the Data Collection Computer; usually also the computer used to
  track eye movements.
* Does not have a user interface; runs in the background under the control
  of the Confero View Application.
* When instructed by Confero View, collects all user input event data,
  including keyboard, mouse, and eye tracker events.
* Captures the desktop of the participant's computer screen, saving the
  screen capture video to a file and sending it to Confero View for real-time
  display to the experimenter.
* When instructed by Confero View, performs eye tracker calibration and
  validation.Uses psychopy.iohub to record events from keyboard, mouse,
  eye tracker, and others.
* All collected data and screen capture video recordings are saved to
  the **Results** folder in the root Confero Track application directory.