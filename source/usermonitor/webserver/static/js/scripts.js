function isFloat(n) {
    return n === +n && n !== (n|0);
}

function isInteger(n) {
    return n === +n && n === (n|0);
}

function resizeVideoDiv() {
    //var winwidth = window.innerWidth;
    var videoCanvas = document.getElementById('videoCanvas');
    var canvasDIV = document.getElementById('canvasDIV');
    var navbarDIV = document.getElementById('navbarDIV');

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

	canvasDIV.style.width = width+'px';
	canvasDIV.style.height = height+'px';
	videoCanvas.style.width = width+'px';
	videoCanvas.style.height = height+'px';

}

window.addEventListener('load', resizeVideoDiv, false);
window.addEventListener('resize', resizeVideoDiv, false);

///////////////////////////////////////////////////////////////////////////////
function updateNode(client_obj,element_id,device,key){
    if (element_id in client_obj.device_dom_nodes){
        var value = device[key][0];
        var after=device[key][1];
        if (isFloat(value))
            value=value.toFixed(3)+' '+after;
        else
            value=JSON.stringify(device[key][0])+' '+after;
        client_obj.device_dom_nodes[element_id].html(value);
    }
    else{
        var dom_node=$(element_id);
        if (dom_node.length > 0) {
            client_obj.device_dom_nodes[element_id]=dom_node;
            var value = device[key][0];
            var after=device[key][1];
            if (isFloat(value))
                value=value.toFixed(3)+' '+after;
            else
                value=JSON.stringify(device[key][0])+' '+after;
            dom_node.html(value);
        }
    }
}

function updateDOMContents(client_obj,device_name){
    var device = client_obj.monitored_devices[device_name];
    for(var key in device){
        var element_id = "#"+device_name+"_"+key;
        var subprops=device[key][0];
        if (typeof subprops.start_time != 'undefined'){
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
            //ui_server_websocket.send(ujson.encode([{'msg_type':'UI_GROWL','type':'info','text':'Data Collection Service Connected.'},]))
        }
       else{
          console.log("!! RX Unknown Msg:",msg);
       }
    }
  };
  return socket;
}







