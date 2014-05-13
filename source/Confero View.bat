@echo off
call %~dp0..\..\..\scripts\env.bat
cd %~dp0\confero\view\
START "" python.exe start.py %*