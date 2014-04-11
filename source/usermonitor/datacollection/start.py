# -*- coding: utf-8 -*-
from dataCollection import DataCollectionRuntime
import psychopy
from psychopy import core
from psychopy.iohub import load, Loader
from psychopy.iohub import dump, Dumper
from websocket import create_connection
import socket
import ujson
import time
import os
import util
from weakref import proxy

def keyChainValue(cdict, *key_path):
    result = cdict.get(key_path[0])
    key_path = list(key_path[1:])
    for key in key_path:
        if not hasattr(result, 'get'):
            return result
        result = result.get(key)
    return result

def createWebsocketInterface(appcfg):
    address = keyChainValue(appcfg, 'experimenter_server', 'address')
    port = keyChainValue(appcfg, 'experimenter_server', 'port')
    sockopt = ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
    ws_url = "ws://{0}:{1}/data_websocket".format(address, port)
    ui_server_websocket = create_connection(ws_url, None, sockopt=sockopt)
    ui_server_websocket.settimeout(0)
    # Inform feedback webserver of experiment directory list
    avail_exp_list = DataCollectionRuntime.getActiveExperimentNames(
                                        appcfg.get("experiment_inactive_token"))
    msg_type = 'EXP_FOLDER_LIST'
    ui_server_websocket.send(ujson.encode([{'msg_type': msg_type,
                                            'data': avail_exp_list}, ]))
    return ui_server_websocket

def handleMsgRx(ws):
    try:
        server_msg = ws.recv()
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
            return 'EXIT_PROGRAM', None
        else:
            raise e
    return None, None

def main(configurationDirectory):
    pjoin = os.path.join
    abspath = os.path.abspath
    psplit = os.path.split
    pexists = os.path.exists
    pisdir = os.path.isdir

    app_conf = load(file(os.path.join(configurationDirectory,
                                    "..\\app_config.yaml"), u'r'),
                                    Loader=Loader)

    DataCollectionRuntime.results_root_folder = \
                                    app_conf.get('results_root_folder')
    if not (pexists(DataCollectionRuntime.results_root_folder)
            and pisdir(DataCollectionRuntime.results_root_folder)):
        DataCollectionRuntime.results_root_folder = abspath(pjoin(
            DataCollectionRuntime.script_dir,
            DataCollectionRuntime.results_root_folder))
    util.createPath(DataCollectionRuntime.results_root_folder)

    try:
        ws = createWebsocketInterface(app_conf)
    except socket.error, e:
        if e.errno == 10035:
            pass
        elif e.errno in [10054,10061]:
            print('WebSocket could not be connected to feedback server. '
                  'Is the server program running?')
            return 'EXIT_PROGRAM'
        else:
            raise e

    if ws is None:
        print ("Error creating websocket connection to feedback server.")
        return

    runtime = None
    cmd = None
    while 1:
        if cmd is None:
            cmd, data = handleMsgRx(ws)

        if cmd == 'EXPERIMENT_SELECTED':
            active_exp_name = data
            # Create Root Results Folder for all Experiments; if needed
            DataCollectionRuntime.active_exp_name = active_exp_name

            app_conf = load(file(pjoin(configurationDirectory,
                                            "..\\app_config.yaml"), u'r'),
                                            Loader=Loader)

            DataCollectionRuntime.results_root_folder = \
                                            app_conf.get('results_root_folder')
            if not (pexists(DataCollectionRuntime.results_root_folder)
                    and pisdir(DataCollectionRuntime.results_root_folder)):
                DataCollectionRuntime.results_root_folder = abspath(pjoin(
                    DataCollectionRuntime.script_dir,
                    DataCollectionRuntime.results_root_folder))
            util.createPath(DataCollectionRuntime.results_root_folder)

            cmd = None
            app_conf = None
        elif cmd == 'START_EXP_SESSION':
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            ### Update App Config Settings for this exp. session ###
            #
            # Read the default app config yaml file
            #
            app_conf_path = pjoin(configurationDirectory, "..\\app_config.yaml")
            app_conf = load(file(app_conf_path, u'r'), Loader=Loader)
            # Update the session code to be used
            #
            app_conf.setdefault('session_defaults', {})['code'] = data
            iohubconfpath = abspath(pjoin(configurationDirectory,
                                                         keyChainValue(app_conf,
                                                            'ioHub', 'config')))
            # Update the iohub config file relative path to use.
            #
            new_iohubconfig_rpath = '..\\last_'+psplit(iohubconfpath)[1]
            app_conf.get('ioHub', {})['config'] = new_iohubconfig_rpath
            # Create the name of the temp app config file to use when
            # starting the runtime. Save the app config, with changes, to the
            # new app conf file.
            #
            app_config_file_name = pjoin(configurationDirectory,
                                                "..\\last_app_config.yaml")
            dump(app_conf, file(app_config_file_name, 'w'), Dumper=Dumper)
            app_conf = None
            ##########################################################

            ### Update ioHub Config Settings for this exp. session ###
            #
            # Read the default iohub config yaml file
            #
            iohub_conf = load(file(iohubconfpath, u'r'), Loader=Loader)
            # Update the iohub data store file path and name as needed
            #
            dsfilename = iohub_conf.get('data_store', {}).get('filename')
            if dsfilename is None:
                dsfilename = 'events'
            dsfilepath = pjoin(DataCollectionRuntime.results_root_folder,
                                    DataCollectionRuntime.active_exp_name,
                                    dsfilename)
            iohub_conf.get('data_store', {})['filename'] = dsfilepath
            # save modified iohub_config for loading by upcoming session
            #
            dump(iohub_conf, file(pjoin(configurationDirectory,
                                new_iohubconfig_rpath), 'w'), Dumper = Dumper)
            iohub_conf = None
            # Create the experiment Session Runtime
            #
            runtime = DataCollectionRuntime(configurationDirectory,
                                            "..\\last_app_config.yaml")

            # Set the app web socket and send a msg indicating data collection
            # is ready
            #
            runtime.ui_server_websocket = proxy(ws)
            cmtype = "success"
            msg = {'msg_type': 'EXP_SESSION_STARTED', 'type': cmtype}
            runtime.sendToWebServer(msg)
            # Start the exp runtime
            #
            cmd, _ = runtime.start()
            # Experiment Session complete, close it out.
            #
            runtime.close()
            runtime = None
        elif cmd == "CLOSE_EXP_SESSION":            
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            cmd = None
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

