===============================
Release Notes
===============================

Initial Release
================

This is the first formal release of the Confero software, given a version of 0.9.

Release Date
-------------

June 25th, 2014

Contributors
-------------

Sol Simpson, Gary Feng

Change List
------------

Initial Release; future change lists will be based on this software version.

Known Issues
-------------

The following issues are known to exist with the software.
Each issue can be avoided, as described.

Multiple Web Browser Windows / Tabs Running Confero View WebApp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confero View does **not** support having more than one browser window / tab
open to the Confero View WebApp URL at the same time. The software will
malfunction if this occurs.

Using Other Browser Tabs / Windows when Recording Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When data is being recorded and viewed using the Confero View WebApp, **do not**
open other tabs or windows using the same browser program. This will cause
updating of the screen capture view to stall when the Confero View web page
is returned to.

Navigation and Refresh Browser Buttons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confero View WebApp is a *Single Page Web Application Design*. This means that
once it is opened, the app never reloads or posts. If The Back, Forward, or
Refresh buttons on the web browser UI are pressed, the Confero View webapp
will be restored to the starting state, while the track software is still
recording or such. The Confero software must be shut down completely and
restarted in this situation.
