# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals
"""
Created on Tue Feb 18 14:18:20 2014

@author: Sol
"""

import subprocess, psutil, os

def keyChainValue(cdict, *key_path):
    result = cdict.get(key_path[0])
    key_path = list(key_path[1:])
    for key in key_path:
        if not hasattr(result, 'get'):
            return result
        result = result.get(key)
    return result

def startSubProcess(*args):
    cmd_line=' '.join([str(a) for a in args])
    p=subprocess.Popen(cmd_line, stdin=subprocess.PIPE)
    return psutil.Process(p.pid)
    
def startNodeWebStreamer(app_config):
    script_dir = os.path.dirname(__file__)

    stream_scale = keyChainValue(app_config,
                          'screen_capture',
                          'http_stream',
                          'ffmpeg_settings',
                          'scale')
    STREAM_SECRET = keyChainValue(app_config,
                          'screen_capture',
                          'http_stream',
                          'uri')
    STREAM_PORT = keyChainValue(app_config,
                          'screen_capture',
                          'http_stream',
                          'write_port')
    WEBSOCKET_PORT = keyChainValue(app_config,
                          'screen_capture',
                          'http_stream',
                          'read_port')
    STREAM_HOST= keyChainValue(app_config,
                          'screen_capture',
                          'http_stream',
                          'host')
    screen_cap_width, screen_cap_height = keyChainValue(app_config,
                                  'screen_capture',
                                  'screen_resolution')

    VID_WIDTH = int(screen_cap_width*stream_scale)-int(screen_cap_width*stream_scale)%2
    VID_HEIGHT = int(screen_cap_height*stream_scale)-int(screen_cap_width*stream_scale)%2
    node_js_path = keyChainValue(app_config,'nodejs_path')
    npath = os.path.join(script_dir, node_js_path, 'node.exe')
    jpath = os.path.join(script_dir,node_js_path, 'stream-server.js')
    nodejs = os.path.abspath(npath)
    jsscript = os.path.abspath(jpath)
    print("Starting Video Streaming Server:", STREAM_HOST, STREAM_PORT)
    return startSubProcess(nodejs, jsscript, STREAM_SECRET, STREAM_PORT,
                           WEBSOCKET_PORT, VID_WIDTH, VID_HEIGHT, STREAM_HOST)
    
def quiteSubprocs(procs):
    def on_terminate(*args):
        print("process {} terminated".format(args))
    
    for p in procs:
       p.terminate()
    gone, alive = psutil.wait_procs(procs=procs, timeout=3, callback=on_terminate)
    for p in alive:
        p.kill()
