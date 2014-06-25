.. _installation_page:

===============================
Initial Installation and Setup
===============================

This section describes how to install the Confero Track or Confero View
application on computers that have not previously had the Confero software
installed.

For instruction on how to start using the Confero software on a computer
that already has been setup to use one of the Confero Applications, please
see the :ref:`getting_started_page`  section of the manual.

.. note:: Before proceeding with this section, please ensure that the
  :ref:`hw_sw_requirements_page`  section of the user manual has been read.
  It is critical that the computers being used meet the hardware requirements
  for each application, and that the 3rd party software needed for each
  has also been downloaded.

The installation and setup of Confero Track and Confero View are
reviewed separately, since normally only one of the two applications is setup
on a specific computer.

Confero Software Distribution
===============================

An archived file, containing a folder called ``Confero``, contains all the
software needed to run the Confero Track or View applications. The contents
of this archive file is referred to as the ``Confero Software Distribution``.

The contents of the Confero software distribution is as follows

.. image:: /images/confero_distro_folder_contents.png
   :align: center

Distribution Contents
----------------------

* **ConferoView.bat**: The file used to launch the Confero View Application.
* **ConferoTrack.bat**: The file used to launch the Confero Track Application.
* **settings**: General settings folder for the Python environment used by Confero.
* **python-2.7.6**: The python 2.7 distribution used by Confero.
* **docs**: The folder containing the Confero User Manual you are currently reading.
* **dependancies**: A folder containing some of the 3rd party software
  installers required by one or both of the Confero Applications. These files
  are referenced later in this section of the document.
* **ConferoView**: The folder containing the Confero View software.
    * Confero View configuration files are located in the ``settings`` directory of this folder.
* **ConferoTrack**: The folder containing the Confero Track software.
    * Confero Track configuration files are located in the ``settings`` directory of this folder.
    * All screen video files and user event data is stored within the ``Results``
      folder of this directory.

Confero View Setup
====================

.. note:: All steps of the Confero View installation are to be performed on
  the computer that will be used by the experimenter for real-time monitoring
  and control of the Confero Track application.

Software Installation
----------------------

1. Open the Confero Software Distribution zip file, and copy the Confero
   folder that is in the archive to a folder of your choice. The full path to the
   copied Confero folder will be called the ``CONFERO_DISTRO_ROOT`` folder in this
   document.
2. The ``CONFERO_DISTRO_ROOT`` folder contains the software needed to run either
   of the Confero View or Track applications. The files that are specific to
   Confero View are located in the ``CONFERO_DISTRO_ROOT``/ConferoView folder.
   This folder will be referred to as ``CONFERO_VIEW_ROOT`` in this
   document.
3. Since only one of the two Confero applications should run on a specific
   computer, feel free to delete the following from the ``CONFERO_DISTRO_ROOT``
   since Confero View is being installed:

   * the ConferoTrack.bat file.
   * the ConferoTrack folder.

4. Install Bonjour for Windows. Start the bonjour installation exe and
   simply follow the instructions given.

.. note::  A copy of the installer can be found in the
   ``CONFERO_DISTRO_ROOT``/dependancies/Bonjour. Based on whether the OS
   being used is 32bit or 64bit, install the correct version of Bonjour.

5. Install the Chrome web browser (if not already installed).

Required Configuration Settings
--------------------------------

When starting, Confero View reads some configuration settings from the
``CONFERO_VIEW_ROOT\settings\app_config.yaml`` file. Most of these settings
do not need to be changed to simply test that the software is working.
However three setting **must** be changed / verified in order for
Confero View to function without invalid data being collected.

.. note:: For full details on Confero View configuration options, see the
  :ref:`config_files_page` section of the manual.

1. screen_capture: screen_resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``screen_capture: screen_resolution`` setting must be updated to match
the screen resolution of the **Confero Track** computer monitor being used for
data recording. For example, the following shows how to indicate that the
Confero Track screen resolution being used is 1920 by 1080 pixels.

.. code-block:: yaml

    screen_capture:
        screen_index: 0
        screen_resolution: [1920, 1080]

.. warning:: If the ``screen_capture: screen_resolution`` setting is incorrect,
  the software will generate bad data and /or not function correctly.

2. http_address
~~~~~~~~~~~~~~~~~

The ``http_address`` setting must either be set

* **AUTO**:  in which case bonjour will be used to auto detect the ip
  address of the **Confero View** computer.
* **[IP_FOR SERVER]**:  specify the ip address that Track should attempt
  to use to connect to the **Confero View** computer.

.. code-block:: yaml

    http_address: AUTO

.. warning:: If the ``http_address`` setting is incorrect, Confero Track will not find the Confero View Server.

3. http_port
~~~~~~~~~~~~~~~~~

The ``http_port`` setting must either be set

* **AUTO**:  in which case bonjour will be used to auto detect the port
  of the **Confero View** computer to be used.
* **[PORT_FOR SERVER]**:  specify the port that Track should attempt
  to use to connect to the **Confero View** computer.

.. code-block:: yaml

    http_port: AUTO

.. warning:: If the ``http_port`` setting is incorrect, Confero Track will not find the Confero View Server.

Starting Confero View
----------------------

To launch the Confero View application, double click on the
``CONFERO_DISTRO_ROOT\ConferoView.bat`` file.

By default, the Confero View Web UI should open in a tab of your Chrome browser.
If it does not, note the URL provided for the application and enter it manually
into a Chrome tab and press enter.

Confero Track Setup
====================

.. note:: All steps of the Confero Track installation are to be performed on
  the computer that will be used by the participant during data collection.

Software Installation
----------------------

1. Open the Confero Software Distribution zip file, and copy the Confero
   folder that is in the archive to a folder of your choice. The full path to the
   copied Confero folder will be called the ``CONFERO_DISTRO_ROOT`` folder in this
   document.
2. The ``CONFERO_DISTRO_ROOT`` folder contains the software needed to run either
   of the Confero View or Track applications. The files that are specific to
   Confero Track are located in the ``CONFERO_DISTRO_ROOT``/ConferoTrack folder.
   This folder will be referred to as ``CONFERO_TRACK_ROOT`` in this
   document.
3. Since only one of the two Confero applications should run on a specific
   computer, feel free to delete the following from the ``CONFERO_DISTRO_ROOT``
   since only Confero Track is being installed on the current computer:

   * the ConferoView.bat file.
   * the ConferoView folder.

4. Install Bonjour for Windows. Start the bonjour installation exe and
   simply follow the instructions given.

.. note::  A copy of the installer can be found in the
   ``CONFERO_DISTRO_ROOT``/dependancies/Bonjour. Based on whether the OS
   being used is 32bit or 64bit, install the correct version of Bonjour.

5. Install the Screen Capture Recorder software. Start the
   ``Setup Screen Capture Recorder vx.xx.xx.exe`` file and follow the
   instructions provided.

.. note::  A copy of the Screen Capture Recorder installer can be found in the
   ``CONFERO_DISTRO_ROOT``/dependancies/ folder, with a file name like
   ``Setup Screen Capturer Recorder vx.xx.xx``

.. note:: By default, the Screen Capture Recorder software is configured to
  capture the full area of the Confero Track primary display. This is generally
  the desired configuration of the screen capturing software, so no
  extra configuration is needed.

.. warning:: However if your setup requires non-default
  settings for the Screen Capture Recorder software, run the configuration
  utility provided with the Screen Capture Recorder software.

Required Configuration Settings
--------------------------------

When starting, Confero Track reads some configuration settings from the
``CONFERO_TRACK_ROOT\settings\app_config.yaml`` file. Most of these settings
do not need to be changed to simply test that the software is working.
However, four settings **must** be changed in order for Confero Track to function
without invalid data being collected.

.. note:: For full details on Confero View configuration options, see the
  :ref:`config_files_page` section of the manual.

1. screen_capture: screen_resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``screen_capture: screen_resolution`` setting must be updated to match
the screen resolution being used for data recording. For example, the following
shows how to indicate that a screen resolution of 1920 by 1080 pixels is used
during data recording.

.. code-block:: yaml

    screen_capture:
        screen_index: 0
        screen_resolution: [1920, 1080]

.. warning:: If the ``screen_capture: screen_resolution`` setting is incorrect,
  the software will generate bad data and /or not function correctly.

2. iohub: config
~~~~~~~~~~~~~~~~~~

Additionally, the ``iohub: config`` setting must be updated based on the eye
tracker model being used during data recording. The app_config.yaml file includes
a line that can be used to specify any one of the supported eye tracker devices.
Only one of the provided values for this setting can be *active*. The *active*
selection *will not* start with a **#** symbol. The other, *inactive*, option
lines *will* start with a **#** symbol.

For example, the following excerpt from the config file shows a setup that
is using the Tobii eye tracking system during data collection.

.. code-block:: yaml

    ioHub:
        config: ..\..\settings\iohub_config_tobii.yaml
        #config: ..\..\settings\iohub_config_eyelink.yaml

To use an eyelink eye tracker instead, the section of the config file would
look like the following.

.. code-block:: yaml

    ioHub:
        #config: ..\..\settings\iohub_config_tobii.yaml
        config: ..\..\settings\iohub_config_eyelink.yaml

.. warning:: If the ``iohub: config`` setting is incorrect,
  the Confero Track software will fail to run correctly when started.

3. http_address
~~~~~~~~~~~~~~~~~

The ``http_address`` setting must either be set

* **AUTO**:  in which case Bonjour will be used to auto detect the ip
  address of the **Confero View** computer.
* **[IP_FOR SERVER]**:  specify the ip address that Track should attempt
  to use to connect to the **Confero View** computer.

.. code-block:: yaml

    view_server:
        address: AUTO

.. warning:: If the ``view_server : address`` setting is incorrect, Confero Track will not find the Confero View Server.

4. http_port
~~~~~~~~~~~~~~~~~

The ``http_port`` setting must either be set

* **AUTO**:  in which case Bonjour will be used to auto detect the port
  of the **Confero View** computer to be used.
* **[PORT_FOR SERVER]**:  specify the port that Track should attempt
  to use to connect to the **Confero View** computer.

.. code-block:: yaml

    view_server:
        port: AUTO

.. warning:: If the ``view_server:port`` setting is incorrect, Confero Track will not find the Confero View Server.

Starting Confero Track
----------------------

To launch the Confero Track application, double click on the
``CONFERO_DISTRO_ROOT\ConferoTrack.bat`` file.

.. warning:: Ensure that Confero View software is already running on the
  other computer before starting the Confero Track software. Otherwise the
  Confero Track application may exit because it could not connect to the
  Confero View application before timing out.

The Confero Track application does not have a GUI interface. A command prompt
window will appear and text should be printed indicating that the Confero Track
application found, and connected to, the Confer View application
running on the other computer.

Hardware Setup
==============

The only hardware related setup required for Confero is the connection of both
the Confero View and Confero Track applications to the same LAN network using
a wired 100/1000 network port.

The setup of the eye tracking hardware that will be used to record eye position
data during data collection is beyond the scope of this document. Please refer
to the eye tracker installation and setup materials for information in this area.