# -*- coding: utf-8 -*-
from dataCollection import DataCollectionRuntime
import psychopy.iohub
from psychopy import core
from websocket import create_connection, WebSocketConnectionClosedException
import socket, ujson, time
from weakref import proxy

from psychopy.iohub import load, Loader, dump, Dumper

def keyChainValue(cdict, *key_path):
    result = cdict.get(key_path[0])
    key_path = list(key_path[1:])
    for key in key_path:
        if not hasattr(result, 'get'):
            return result
        result = result.get(key)
    return result

def createWebsocketInterface(appcfg):
    address = keyChainValue(appcfg,'experimenter_server','address')
    port = keyChainValue(appcfg,'experimenter_server','port')

    sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
    ws_url = "ws://{0}:{1}/data_websocket".format(address, port)
    ui_server_websocket =create_connection(ws_url, None, sockopt=sockopt)
    ui_server_websocket.settimeout(0)
    
    
    # Inform feedback webserver of experiment directory list
    avail_exp_list = DataCollectionRuntime.getActiveExperimentNames(appcfg.get("experiment_inactive_token"))
    msg_type = 'EXP_FOLDER_LIST'
    ui_server_websocket.send(ujson.encode([{'msg_type': msg_type,
                                            'data': avail_exp_list}, ]))

    # Show web server ui a notification that data a data collection process has started  
    #ui_server_websocket.send(ujson.encode([{'msg_type': 'UI_GROWL',
    #                                        'type': 'success',
    #                                        'text': 'Data Collection Service '
    #                                                'Connected.'}, ]))
    return ui_server_websocket

def handleMsgRx(ws):
    try:
        server_msg=ws.recv()
        msg = ujson.loads(server_msg)
        mtype = msg.get('type')

        if mtype == 'START_EXP_SESSION':
            return 'START_EXP_SESSION', msg.get('code')
        elif mtype == 'EXPERIMENT_SELECTED':
            return 'EXPERIMENT_SELECTED', msg.get('name')
        elif mtype == 'EXIT_PROGRAM':
            return 'EXIT_PROGRAM', None
        else:
            print('!!Unhandled Server Message:', msg)

    except socket.error, e:
        if e.errno == 10035:
            pass
        elif e.errno == 10054:
            print('WebSocket could not be connected to feedback server.')
            return 'EXIT_PROGRAM',None
        else:
            raise e
    return None, None

def main(configurationDirectory):
    import os
    import util
    app_conf=load(file(os.path.join(configurationDirectory,
                                    "..\\app_config.yaml"), u'r'),
                                    Loader=Loader)

    try:
        ws = createWebsocketInterface(app_conf)
    except socket.error, e:
        if e.errno == 10035:
            pass
        elif e.errno in [10054,10061]:
            print('WebSocket could not be connected to feedback server. Is the server program running?')
            return 'EXIT_PROGRAM'
        else:
            raise e


    if ws is None:
        print ("Error creating websocket connection to feedback server.")
        return

    runtime = None
    cmd=None
    active_exp_name=None
    while 1:
        if cmd is None:
            cmd,data=handleMsgRx(ws)

        if cmd == 'EXPERIMENT_SELECTED':
            active_exp_name=data
            print "ACTIVE EXPERIMENT_NAME:",active_exp_name
            # Create Root Results Folder for all Experiments; if needed
            DataCollectionRuntime.results_root_folder=app_conf.get('results_root_folder')
            if not os.path.exists(DataCollectionRuntime.results_root_folder) or not os.path.isdir(DataCollectionRuntime.results_root_folder):
                DataCollectionRuntime.results_root_folder = os.path.abspath(os.path.join(DataCollectionRuntime.script_dir, DataCollectionRuntime.results_root_folder, active_exp_name))
            util.createPath(DataCollectionRuntime.results_root_folder)

        elif cmd == 'START_EXP_SESSION':
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            print("Experiment Session Request Received. Session Code Requested:",data)
            app_conf.get('session_defaults',{})['code']=data
            app_config_file_name = os.path.join(configurationDirectory, "..\\last_app_config.yaml")
            dump(app_conf, file(app_config_file_name, 'w'), Dumper=Dumper)
            time.sleep(0.5)
            runtime = DataCollectionRuntime(configurationDirectory,
                                            "..\\last_app_config.yaml")
            runtime.ui_server_websocket=proxy(ws)            
            cmtype="success"
            msg={'msg_type':'EXP_SESSION_STARTED', 'type':cmtype}
            runtime.sendToWebServer(msg)
            
            cmd,_ = runtime.start()
            runtime.close()
            runtime=None
        elif cmd == "CLOSE_EXP_SESSION":            
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            cmd=None
        elif cmd == "EXIT_PROGRAM":
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
                core.quit()
            return None

        time.sleep(0.1)
    print("Data Collection Service Stopped.")
if __name__ == "__main__":
    configurationDirectory = psychopy.iohub.module_directory(main)
    # run the main function, which starts the experiment runtime
    main(configurationDirectory)

