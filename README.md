Confero Software Suite
========================

Screen and User Event Capturing System for Windows.





The Confero Software Suite consists of two python applications and a web brower based UI:

* **Confero Track** : Performs screen capturing and data collection; running in the background on the eye tracker PC.
* **Confero View** : A web interface for monitoring data collected by, and controlling, **Confero Track**.
* **Confero Server** : The web server application that **Confero Track** and **Confero View** connect to. The **Confero Server** facilitates data exchange and control between the two other Confero applications.

Confero Track Features
-------------------------

* Uses psychopy.iohub to record events from keyboard, mouse, eye tracker, and others.
* Events are available at run-time and are saved to a HDF5 based file.
* A screen capture process saves the state of a single screen to a video file.
* Computer audio is saved with the screen capture video.
* Remotely controlled by the **Confero View** application.

Confero View Features:
------------------------

* Web based user interface.
* Remotely open and close experiment sessions on **Confero Track**.
* Start and Stop recording of screen capture video and input device events, multiple times, during a single experiment session.
* Provides real-time display of screen capture video stream as well as the state of each input device when recording.
* Send text messages during data collection which are saved in the experiment data file.
* Overlay mouse position, gaze position, and the time since recording was last started on the screen video stream.

Installation
=============

Important: The following installation instructions must be followed for both the
computer that will be used to run **Confero Track**, as well as the computer that
will run the **Confero Server** and **Confero View** aplications.

The Confero software may be installed anywere on the computer. A convenient location is C:\Confero, which in most cases will allow all users on the computer to access Confero. Note that this also expose all the program files and data to all users. You may risk accidental deletions or misconfigurations. Decide your installation path according to your application. 

In the remainder of the document we refer to the Confero root directory as CONFERO_ROOT. In the above example, CONFERO_ROOT = c:\ .

The document assumes you are installing from a distribution package (distro), in the form of a ZIP or an EXE file. 

* unzip the distro to a temporary directory
* check to see if your CONFERO_ROOT directoy already exists; if so, rename or move the directory
* move the Confero directory to the CONFERO_ROOT path. In the above example, we move Confero to C:\, so that CONFERO_ROOT= c:\Confero
* Proceed with the following steps in setting up.

Python Package Dependancies (if needed)
----------------------------

** If you are installing from a distribution package (either as a ZIP file or an EXE file), all the dependencies should have been included. Skip this section. **

The following python packages must be installed in the python distribution
being used to run Confero Application Suite. All packages must
be for Python 2.7 32-bit (even if Windows is 64bit)

* All dependencies needed for PsychoPy http://www.psychopy.org/installation.html#dependencies
* All dependencies needed for ioHub http://www.isolver-solutions.com/iohubdocs/iohub/installation.html#python-2-7-package-list-with-urls
* PsychoPy 1.80.01 package itself http://sourceforge.net/projects/psychpy/files/
* Tornado 3.2 http://www.lfd.uci.edu/~gohlke/pythonlibs/#tornado
* Websocket-client https://pypi.python.org/pypi/websocket-client/
* If freetype.dll is not already available on your system, download it from here http://goo.gl/dbUjHV and place in your root python directory, or another folder that is in your system PATH.

Eye Tracker Client Library (if needed)
---------------------------------------

** This is only necessary if you are using an eye-tracker that is not currently included in the distribution (EyeLink or Tobii remote series) **

If using an eye tracker, ensure any dependencies specific to the eye tracker
being used have been installed. See the docs for the eye tracker being used
with iohub for more details: http://www.isolver-solutions.com/iohubdocs/iohub/api_and_manual/device_details/eyetracker.html#eye-tracking-hardware-implementations

Program Depandencies
------------------------

The following programs should be installed and configured before running Confero.

** Screen Capturer Recorder **

The setup program is included in the **dependancies** folder. Use the version of program provided. After installation, the program needs to be set up for **each user** separately on the computer. To configure:

1. Go to menu Start >> All Programs >> Screen Capturer Recorder >> configure >> configure by setting specific screen capture numbers
2. Follow the onscreen instruction to go through the process. Leave BLANK, not 0, for default values. The most important parameters are the size of the monitor, and which monitor to record if you have multiple monitors. To find out the specific numbers, use Control Panel >> Display or other programs to view the display setting.

** Bonjour **

Bonjour is used to automatically recognize and configure the IPs of the Track and View programs. Use the version provided; use either the 32bit or 64bit version depending on your Windows OS. You may need to reinstall it if you experience problems with Bonjour. 


Configure Confero
--------------------


UserMonitor Project Files
--------------------------

Download the latest version of the Confero Application Suite from it's
github repo: https://github.com/isolver/UserMonitor/archive/master.zip

** BELOW TEXT NEEDS UPDATING**

Follow these steps to setup Confero for the first time:

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

License
========

GNU General Public License (GPL version 3 or any later version)
