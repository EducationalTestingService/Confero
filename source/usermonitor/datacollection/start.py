# -*- coding: utf-8 -*-
from dataCollection import DataCollectionRuntime
import psychopy.iohub
from psychopy import core
from websocket import create_connection, WebSocketConnectionClosedException
import socket, ujson, time
from weakref import proxy

from psychopy.iohub import load, Loader, Dumper

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
    ui_server_websocket.send(ujson.encode([{'msg_type':'UI_GROWL','type':'success','text':'Data Collection Service Connected.'},]))
    #print("Websocket created: {0}.".format(ws_url), 'data_monitoring')
    return ui_server_websocket

def handleMsgRx(ws):
    try:
        server_msg=ws.recv()
        msg = ujson.loads(server_msg)
        if msg.get('type') == 'START_EXP_SESSION':
            return 'START_EXP_SESSION'
        elif msg.get('type') == 'EXIT_PROGRAM':
            return 'EXIT_PROGRAM'
        else:
            print('!!Unhandled Server Message:', msg)

    except socket.error, e:
        if e.errno == 10035:
            pass
        elif e.errno == 10054:
            print('WebSocket could not be connected to feedback server.')
            return 'EXIT_PROGRAM'
        else:
            raise e


def main(configurationDirectory):
    import os

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
    app_conf=None
    runtime = None
    cmd=None
    print("Data Collection Listener Started.")
    print("Waiting for Experiment Session Request....")
    print("")
    while 1:
        if cmd is None:
            cmd=handleMsgRx(ws)
        else:
            print("DAT_COL CMD: ",cmd)

        if cmd == 'START_EXP_SESSION':
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            print("Experiment Session Request Received.")
            time.sleep(0.5)
            runtime = DataCollectionRuntime(configurationDirectory,
                                        "..\\app_config.yaml")
            runtime.ui_server_websocket=proxy(ws)
            print("Starting Experiment Session...")
            print("")
            cmd = runtime.start()
            runtime.close()
            runtime=None
            print("")
        elif cmd == "CLOSE_EXP_SESSION":
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
            print("Experiment Session Closed.")
            cmd=None
        elif cmd == "EXIT_PROGRAM":
            if runtime:
                runtime.close()
                runtime._close()
                runtime = None
                core.quit()
            return

        time.sleep(0.1)
    print("Data Collection Service Stopped.")
if __name__ == "__main__":
    configurationDirectory = psychopy.iohub.module_directory(main)
    # run the main function, which starts the experiment runtime
    main(configurationDirectory)

