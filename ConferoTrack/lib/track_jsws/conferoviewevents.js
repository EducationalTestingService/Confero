/**
 * Created by Sol on 30/05/2014.
 */
var conferotrack = {
    conferoview_ip: undefined,
    monitored_devices: undefined,
    socket :undefined,// new WebSocket('ws://'+conferoview_ip+':8888/track_client_ws');


    connect: function(conferoview_ip, monitored_devices){
        this.socket = new WebSocket('ws://'+conferoview_ip+':8888/track_client_ws');
        this.conferoview_ip = conferoview_ip;
        this.monitored_devices = monitored_devices;

        this.socket.onopen = function(){
            this.send(JSON.stringify({type: 'device_filter',device_list: conferotrack.monitored_devices}));
            };

        // Handle any errors that occur.
        this.socket.onerror = function(error) {
			// garyfeng: raise an error when not connected
			jQuery(document).trigger('on_confero_connection_error',{conferoIP:this.conferoview_ip, msg:"Confero Track not Connected"});
            console.log('ConferoEventListener WebSocket Error: ' + error);
            };

        // Handle messages sent by the server.
        this.socket.onmessage = function(json_msg_list) {
            var msg_list = JSON.parse(json_msg_list.data);

            for(var i = 0, size = msg_list.length; i < size ; i++){
                var msg = msg_list[i];
                var msg_type = msg.msg_type;
                if (msg_type === undefined)
                    msg_type = msg.type;

               if(msg_type === 'DataCollection'){
                  delete msg['msg_type']
                  for (e in msg)
                    jQuery(document).trigger('on_confero_event',{device_name:e, data:msg[e]});
               }
               else{
                  console.log("!! ConferoEventListener.onmessage RX Unknown Msg:",msg);
               }
            }
            };
    },

    setMonitoredDevices: function (monitored_devices) {
        this.monitored_devices = monitored_devices;
        this.socket.send({type: 'device_filter',device_list: monitored_devices});
    },

    getMonitoredDevices : function () {
        return this.monitored_devices;
    },

    logEvent: function(text, category, time){
       // Text must be between 1 and 128 chars.
       // Category can be between 0 and 32 characters
       // Time is specified in sec.msec format. If -1, the time of the msg is
       // created when the track app receives the msg and logs it into iohub
       if (text === undefined)
        return undefined;
       if (category === undefined)
        category = 'JS_EVENT'
       if (time === undefined)
        time = -1
       this.send({type: 'JS_EVENT', text:text, category: category, time: time});
    },

    send : function (msg) {
        var sendmsg=JSON.stringify(msg);
		// garyfeng: check if the socket is ready; raise an error if not 
		if (this.socket.readyState !=1){
			// socket is not ready
			jQuery(document).trigger('on_confero_send_error',{conferoIP:this.conferoview_ip, msg:sendmsg});
			return
		}
        
        this.socket.send(sendmsg);
    }
};
