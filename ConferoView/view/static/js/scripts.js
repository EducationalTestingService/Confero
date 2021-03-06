function isFloat(n) {
    return n === +n && n !== (n|0);
}

function isInteger(n) {
    return n === +n && n === (n|0);
}

function resizeVideoDiv() {
    //var winwidth = window.innerWidth;
    var videoCanvas = document.getElementById('videoCanvas');
    var navbarDIV = document.getElementById('navbarDIV');
//    var statusPanelGroup = document.getElementById('statusPanelGroup');
    var ratio = videoCanvas.height/videoCanvas.width;

    var width = navbarDIV.clientWidth*.65;//#.innerHeight;
    var height=videoCanvas.height;
    if (width > videoCanvas.width){
        width=videoCanvas.width;
    }
    else if ( width < 600 ){
          width  = navbarDIV.clientWidth;
          height = width * ratio;
        }
    else{
    	height = width * ratio;
    }

	videoCanvas.style.width = width+'px';
	videoCanvas.style.height = height+'px';

//    var statusPanelWidth = navbarDIV.clientWidth - videoCanvas.style.width;
//	statusPanelGroup.style.width = statusPanelWidth+'px';
}

window.addEventListener('load', resizeVideoDiv, false);
window.addEventListener('resize', resizeVideoDiv, false);

///////////////////////////////////////////////////////////////////////////////
function updateNode(client_obj,element_id,device,key){
    var value = device[key][0];
    var after=device[key][1];
    if (value === null)
        value = '';
    else if (isFloat(value))
        value=value.toFixed(3);
    else if (isInteger(value))
        ;//value=value.toFixed(3);
    else
        value=JSON.stringify(value)

    if (element_id in client_obj.device_dom_nodes){
        client_obj.device_dom_nodes[element_id].html(value+' '+after);
    }
    else{
        var dom_node=$(element_id);
        if (dom_node.length > 0) {
            client_obj.device_dom_nodes[element_id]=dom_node;
            dom_node.html(value+' '+after);
        }
    }

    // check if any warning or error alerts should be displayed.
    if (element_id in client_obj.device_alerts){
        client_obj.device_alerts[element_id].check(value);
    }

}

function updateDOMContents(client_obj,device_name){
    var device = client_obj.monitored_devices[device_name];
    for(var key in device){
        var element_id = "#"+device_name+"_"+key;
        var subprops=device[key][0];
        if (subprops != null && typeof subprops.start_time != 'undefined'){
            for(var subkey in subprops){
                var sub_element_id = element_id+"_"+subkey;
                updateNode(client_obj,sub_element_id,subprops,subkey);
            }
        }
        else{
            updateNode(client_obj,element_id,device,key);
        }
    }
}
function changeButtonStates(enable_list, disable_list, activate_list, deactivate_list){
    for(var i = 0, size = enable_list.length; i < size ; i++){
       var e = enable_list[i];
       $('#'+e).removeClass('disabled');
    }

    for(var i = 0, size = disable_list.length; i < size ; i++){
       var e = disable_list[i];
       $('#'+e).addClass('disabled');
    }

    for(var i = 0, size = activate_list.length; i < size ; i++){
       var e = activate_list[i];
       $('#'+e).addClass('active');
    }

    for(var i = 0, size = deactivate_list.length; i < size ; i++){
       var e = deactivate_list[i];
       $('#'+e).removeClass('active');
    }
}

// Create websocket
function createWebSocket(client_obj,video_server_host){
  var socket = new WebSocket('ws://'+video_server_host+':8888/ui_websocket');

  // Handle any errors that occur.
  socket.onerror = function(error) {
    console.log('WebSocket Error: ' + error);
  };

  // Handle messages sent by the server.
  socket.onmessage = function(json_msg_list) {
    var msg_list = JSON.parse(json_msg_list.data);

    for(var i = 0, size = msg_list.length; i < size ; i++){
       var msg = msg_list[i];
       if(msg.msg_type === 'DataCollection'){
          delete msg['msg_type'];
          //console.log(msg);
          for (var key in msg) {
            client_obj.monitored_devices[key]=msg[key];
            updateDOMContents(client_obj,key);
          }
          //console.log('----');
       }
       else if (msg.msg_type === 'UI_GROWL'){
            $.bootstrapGrowl(msg.text,{type:msg.type});
        }
       else if (msg.msg_type === 'EYETRACKER_CALIBRATION_COMPLETE'){
            if (msg.type === 'success')
                $.bootstrapGrowl("Calibration Successful.",{type:msg.type});
            else if (msg.type === 'error ')
                $.bootstrapGrowl("Calibration Failed.",{type:msg.type});

            changeButtonStates(['startCalibrationButton',
                                'startValidationButton',
                                'startRecordButton',
                                'closeSessionButton',
                                'submitExperimentMessage'],
                                ['newSessionButton'],
                                [],
                                ['startCalibrationButton']
            );
            $('#startCalibrationButton').removeClass('active');
        }
       else if (msg.msg_type === 'EYETRACKER_VALIDATION_COMPLETE'){
            if (msg.type === 'success')
                $.bootstrapGrowl("Validation Successful.",{type:msg.type});
            else if (msg.type === 'error')
                $.bootstrapGrowl("Validation Failed.",{type:msg.type});

            changeButtonStates(['startCalibrationButton',
                                'startValidationButton',
                                'startRecordButton',
                                'closeSessionButton',
                                'submitExperimentMessage'],
                                ['newSessionButton'],
                                [],
                                ['startValidationButton']
            );
            $('#startValidationButton').removeClass('active');
        }
       else if (msg.msg_type === 'EXP_SESSION_STARTED'){
            if (msg.type === 'success')
                $.bootstrapGrowl("Experiment Session Started.",{type:msg.type});
            else if (msg.type === 'error')
                $.bootstrapGrowl("Experiment Session Could not be Started.",{type:msg.type});

           changeButtonStates(['startCalibrationButton',
                        'startValidationButton',
                        'closeSessionButton',
                        'submitExperimentMessage',
                        'startRecordButton'
                       ],
                       ['newSessionButton',
                        'stopRecordButton'
                       ],[],[]);
        }
       else if (msg.msg_type === 'EXP_SESSION_CLOSED'){
            umf_state.fillVideoCanvas();
            if (msg.type === 'success')
                $.bootstrapGrowl("Experiment Session Closed.",{type:msg.type});
            else if (msg.type === 'error')
                $.bootstrapGrowl("Experiment Session Could not be Closed.",{type:msg.type});
            changeButtonStates(['newSessionButton'],
                       ['closeSessionButton',
                        'startRecordButton',
                        'startCalibrationButton',
                        'startValidationButton',
                        'stopRecordButton',
                        'submitExperimentMessage'
                       ],[],[]);
        }
       else if (msg.msg_type === 'RECORDING_STARTED'){
            if (msg.type === 'success')
                $.bootstrapGrowl("Data Recording Started.",{type:msg.type});
            else if (msg.type === 'error')
                $.bootstrapGrowl("Data Recording Could not be Started.",{type:msg.type});
            changeButtonStates([
                        'submitExperimentMessage',
                        'stopRecordButton',
                        'gazeOverlayButton',
                        'mouseOverlayButton'
                       ],
                       ['startRecordButton',
                        'startCalibrationButton',
                        'startValidationButton',
                        'closeSessionButton'
                       ],[],[]);
        }
       else if (msg.msg_type === 'RECORDING_STOPPED'){
            umf_state.fillVideoCanvas()
            if (msg.type === 'success')
                $.bootstrapGrowl("Data Recording Stopped.",{type:msg.type});
            else if (msg.type === 'error')
                $.bootstrapGrowl("Data Recording Could not be Stopped.",{type:msg.type});
            changeButtonStates(['startCalibrationButton',
                        'startValidationButton',
                        'closeSessionButton',
                        'startRecordButton',
                        'submitExperimentMessage'
                       ],
                       ['gazeOverlayButton',
                        'mouseOverlayButton'],[],[]);
        }
       else if (msg.msg_type === 'EXP_FOLDER_LIST'){
            client_obj.experiment_name_list=msg.data;
            $('#experimentSelectionContent')[0].innerHTML="<span>Select the experiment results folder to save sessions into:</span>";
            $('#experimentSelectionModalButton')[0].innerHTML='Start';
            $('#experimentSelectionModalButton').removeClass('disabled');

            var exp_picker=$('#experimentSelectionList')
            exp_picker.prop('disabled',false);
            exp_data=msg.data;
            if (exp_data.length > 0) {
                for (var i= 0, size = exp_data.length; i < size; i++){
                   exp_picker.append("<option data-subtext='"+exp_data[i][1].length+" sessions'>"+exp_data[i][0]+"</option>");
                }

                exp_picker.selectpicker('refresh');
            }
        }
       else if (msg.msg_type === 'RUNTIME_NOTIFICATION_SETTINGS'){
           client_obj.initRuntimeAlerts(msg.data);
           //client_obj.runtime_alerts=msg.data;

       }
       else if (msg.msg_type === 'DATA_COLLECT_CONFIG'){
           ;
       }
       else{
          console.log("!! RX Unknown Msg:",msg);
       }
    }
  };
  return socket;
}





