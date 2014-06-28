@echo off

set WINPYDIR=%~dp0\..\..\..\..\python-2.7.6
set WINPYVER=2.7.6.0
set HOME=%WINPYDIR%\settings
SET VS90COMNTOOLS=%VS100COMNTOOLS%
set PATH=%WINPYDIR%\Lib\site-packages\PyQt4;%WINPYDIR%\;%WINPYDIR%\DLLs;%WINPYDIR%\Scripts;%PATH%
cd %~dp0\..\lib\data_processing
python.exe videvt2ssa.py %1 %2