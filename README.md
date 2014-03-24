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

Important: The following installation instructions must be followed for both the computer that will be used to collect experiment data from, as well as the computer that will run the feedback and control web server.

Python Package Dependancies
----------------------------

The following python packages must be installed in the python distribution being used to run UserMonitor applications. All packages must be for Python 2.7 32-bit (even if Windows is 64bit)

* All dependancies needed for PsychoPy http://www.psychopy.org/installation.html#dependencies
* All dependancies needed for ioHub http://www.isolver-solutions.com/iohubdocs/iohub/installation.html#python-2-7-package-list-with-urls
* PsychoPy 1.80.01 package itself http://sourceforge.net/projects/psychpy/files/
* Tornado 3.2 http://www.lfd.uci.edu/~gohlke/pythonlibs/#tornado
* Websocket-client https://pypi.python.org/pypi/websocket-client/
* If freetype.dll is not already available on your system, download it from here http://goo.gl/dbUjHV and place in your root python directory, or another folder that is in your system PATH.

Eye Tracker Client Library (if needed)
---------------------------------------

If using an eye tracker, ensure any dependancies specific to the eye tracker being used have been installed.
See the docs for the eye tracker being used with iohub for more details: http://www.isolver-solutions.com/iohubdocs/iohub/api_and_manual/device_details/eyetracker.html#eye-tracking-hardware-implementations

UserMonitor Project Files
--------------------------

Download the latest version of the UserMonitor github repo: https://github.com/isolver/UserMonitor/archive/master.zip

Follow these steps to setup UserMonitor for the first time:

1. Unpack the master.zip archive to a location of your choice.
2. Rename the folder that was unpacked from usermonitor-master to UserMonitor.
3. Open the UserMonitor folder.
4. Unpack the bin.zip file into the current directory. After unpacking bin.zip, there should be a bin folder in the top level UserMonitor directory.
5. Install the dshow filters used for screen capturing by running the Setup Screen Capturer Recorder v0.10.0.exe installer found in the UserMonitor/ dependancies folder.
6. Configure the Screen Capturer Recorder filter by running: Start->All Programs->Screen Capturer Recorder->configure by setting specific screen capture numbers. For each question asked, remove any text in the textbox field and continue, other than for the capture width and height settings, which should equal the pixel resolution of the monitor that will be used for screen capturing.
7. Edit the <Path_to_UserMonitor_root_folder>/source/usermonitor/iohub_config.yaml as necessary.
8. Edit the <Path_to_UserMonitor_root_folder>/source/usermonitor/app_config.yaml as necessary.

Usage
======

To start the UserMonitor Applications:

User Monitor Feedback and Control Application
----------------------------------------------

From the computer being used to run the User Monitor Feedback and Control application, run the following python script from a command prompt: 

python.exe <Path_to_UserMonitor_root_folder>/source/usermonitor/webserver/start.py

When the application starts, your web browser should automatiocally open running the User Monitor Feedback and Control Application web GUI. You can not use this application, until the data collection application has also been started (next step)

Data Collection Application
----------------------------------------------

From the computer being used to run the data collection application, which is the computer the participant will be interacting with, run the following python script from a command prompt: 

python.exe <Path_to_UserMonitor_root_folder>/source/usermonitor/datacollection/start.py

When the application starts the cmd window can be minimized.

Collecting Data
----------------

To learn how to use the User Monitor Feedback and Control Application GUI to control the Data Collection application, including openning and closing participant sessions and starting / stopping recording of data, please see the Help documentation available via the User Monitor Feedback and Control Application GUI.
