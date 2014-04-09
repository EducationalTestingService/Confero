Screen Capture DirectShow Source Filter. 
x64 Edition Version 2.0.15

Author: Unreal Streaming Technologies. http://www.umediaserver.net

General-purpose filter that allows capturing of computer screen. 

Operating systems: All Windows OS.
You must have DirectX 8+ installed.

Any Windows application that works with video sources will pick this filter up and work with it: 
Video Editing and Video Capturing-Recording applications, 
Streaming servers (Windows Media Encoder, Unreal Media Server, VideoLan etc), 
Macromedia Flash plugin and others.

Desktop region to capture and frame rate can be configured.
Desktop Region to capture is full screen by default. The default frame rate is 10 frames/sec. 
The following are configuration registry settings:

HKLM\SOFTWARE\UNREAL\Live\UScreenCapture
DWORD: MonitorNum
DWORD: Left
DWORD: Right
DWORD: Top
DWORD: Bottom
DWORD: FrameRate
DWORD: ShowCursor
DWORD: CaptureLayeredWindows

MonitorNum            - is monitor to capture. Two monitors are supported. Value of 0 means capture from both monitors.
Left                  - is the x-coordinate of the upper left corner of the region to capture in pixels.
Right                 - is the x-coordinate of the lower right corner of the region to capture in pixels.
Top                   - is the y-coordinate of the upper left corner of the region to capture in pixels.
Bottom                - is the y-coordinate of the lower right corner of the region to capture in pixels.
FrameRate             - the valid range is 1 to 30.
ShowCursor            - 1 to capture cursor, 0 not to capture.
CaptureLayeredWindows - 1 to capture layered windows, 0 not to capture.

Filter reads these values on startup time; in case of invalid or missing values defaults are used.
Filter's property page writes settings to the registry. 
Capturing at high frame rates is very CPU intensive. 
Use high bitrate ULiveServer profiles to stream your desktop screen.

Windows Media Player can playback your screen using this filter.
Open the player, choose File->Open URL menu item. 
The following is the syntax for Open URL: (case insensitive)
USCREEN://monitornum=<xxx>&left=<xxx>&top=<xxx>&right=<xxx>&bottom=<xxx>&fps=<number of frames per second>&showcursor=<1 or 0>&capturelayeredwindows=<1 or 0>

For example:
USCREEN://monitornum=2&left=45&top=67&right=930&bottom=620&fps=7&showcursor=1&capturelayeredwindows=1

Notes for developers:

Except the registry, the filter can be configured in the following ways:
1. Via custom interface IUScreenCaptureSettings (the .h file is attached to the package)
2. Image size and frame rate can be set via IAMStreamConfig interface.
3. Via IFileSourceFilter interface.   
4. Property page can be displayed via ISpecifyPropertyPages interface.

You can create the filter specifying one of these interfaces, or QueryInterface from IBaseFilter.
Caution: Assign settings to the filter before you connect it to the other filters in the graph. 
Every time you change settings, all the filters in the graph will disconnect.

