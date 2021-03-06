.. _config_files_page:

======================
Confero Configuration
======================

When starting up, Confero View and Confero Track read configuration settings
from file(s) to customize some aspects of each applications functionality.

* For the computer running Confero View, the ``CONFERO_VIEW_ROOT\settings\``
  directory contains the configuration file used.
* For the computer running Confero Track, the ``CONFERO_TRACK_ROOT\settings\``
  directory contains the configuration file used.

Any configuration files used by Confero are `YAML`_ formatted, saved as text
files, and can be edited using any text editor. Since YAML syntax relies
heavily on the indentation level of each line, it is suggested that an
editor like `Notepad++`_ be used, as these types of editors have been designed
to keep white space formatting intact.

.. _YAML: http://www.yaml.org/
.. _Notepad++: http://notepad-plus-plus.org/

Confero View Config Settings
=============================

All configuration options for Confero View are in ``CONFERO_VIEW_ROOT\settings\app_config.yaml``

app_config.yaml
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../ConferoView/settings/app_config.yaml
    :language: yaml
    :linenos:

.. _confero_track_config:

Confero Track Config Settings
=============================

Confero Track uses three configuration files located in the
``CONFERO_TRACK_ROOT\settings\`` folder:


* app_config.yaml
* iohub_config_xxxx.yaml
* validation_config.yaml


app_config.yaml
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../ConferoTrack/settings/app_config.yaml
    :language: yaml
    :linenos:

iohub_config_xxxx.yaml
~~~~~~~~~~~~~~~~~~~~~~~~~~

The version of the iohub_config_xxxx.yaml file used when Confero Track starts
running is specified by the ``ioHub: config`` setting found in ``app_config.yaml``.

Each version of the iohub_config_xxxx.yaml should be identical except for the eye
tracker device configuration section. As an example, here are the
``iohub_config_tobii.yaml`` configuration options:

.. literalinclude:: ../../ConferoTrack/settings/iohub_config_tobii.yaml
    :language: yaml
    :linenos:

.. note:: For details on the configuration options of the iohub_config.yaml file, refer
   to the `ioHub Device Configuration`_ documentation within ioHub User Manual.

.. _ioHub Device Configuration: http://www.isolver-solutions.com/iohubdocs/iohub/api_and_manual/devices.html#available-iohub-device-and-deviceevent-types

validation_config.yaml
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../ConferoTrack/settings/validation_config.yaml
    :language: yaml
    :linenos: