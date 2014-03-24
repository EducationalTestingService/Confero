UserMonitor
===========

Screen and User Event Capturing System for Windows. 

User Monitor consists of two python applications, controlling a total of 5 processes:

* datacollection: Handles the saving and streaming of user events and a screen capture video.
* webserver: Built in web server is used to access a web 2.x datacollection monitoring and control application.  

Data Collection Features
-------------------------

* Uses psychopy.iohub to record events from keyboard, eye tracker, and others.
* Events are available at run-time and are saved to a HDF5 based file.
* A screen capture process saves the state of a single screen to a video file.
* Computer audio is saved with the screen capture video.
* Remotely controlled by the data collection monitoring and control application.

Data Collection Monitoring and Control Interface Features:
-----------------------------------------------------------

* Web based user interface.
* Remotely open and close experiment sessions on the Data Collection application.
* Start and Stop recording of screen capture video and input device events multiple times during a single experiment session.
* Provides real-time display of screen capture video stream as well as the state of each input device when recording.
* Send text messages during data collection which are saved in the experiment data file.
* Overlay mouse position, gaze position, and the time since recording was last started on the screen video stream.

Installation
=============

TBC

Usage
======

TBC
