@echo on
call %~dp0..\..\scripts\env.bat
cd %~dp0\source\usermonitor\datacollection\
START "" python.exe start.py %*
PAUSE