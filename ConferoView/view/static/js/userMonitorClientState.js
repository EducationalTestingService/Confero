function DevicePropertyAlert(device_name, device_property, element_id, settings) {
    this.device_name = device_name;
    this.device_property = device_property;
    this.element_id = element_id;
    this.current_state = 'off';

    this.warning_growl_id = undefined;
    this.warning_condition = settings['warning'];
    this.last_warning_start_time = undefined;
    this.warning_min_length = undefined;
    this.warning_delay = undefined;
    this.warning_manual_hide = false;
    this.warning_auto_hide = false;

    if (this.warning_condition != undefined){
        this.warning_growl_id = this.device_name+"_"+this.device_property+"_warning_growl"
        this.warning_min_length = this.warning_condition['minimum_time_period'];
        if (this.warning_min_length == undefined)
            this.warning_min_length = 1000; // 1 sec
        else
            this.warning_min_length = this.warning_min_length*1000;

        if ('growl' in this.warning_condition){
            this.warning_delay = this.warning_condition['growl'].duration;
            if (this.warning_delay == undefined)
                this.warning_delay  = 1000*3;
            else if (this.warning_delay === 'MANUAL'){
                  this.warning_delay  = 1000*60*60;
                  this.warning_manual_hide = true;
            }
            else if (this.warning_delay === 'AUTO'){
                  this.warning_delay  = 1000*60*60;
                  this.warning_auto_hide = true;
            }
            else{
                this.warning_delay = this.warning_delay * 1000;
            }
        }
    }

    this.error_condition = settings['error'];
    this.last_error_start_time = undefined;
    this.error_min_length = undefined;
    this.error_delay = undefined;
    this.error_growl_id = undefined;
    this.error_manual_hide = false;
    this.error_auto_hide = false;
    if (this.error_condition != undefined){
        this.error_growl_id = this.device_name+"_"+this.device_property+"_error_growl"
        this.error_min_length = this.error_condition['minimum_time_period'];
        if (this.error_min_length == undefined)
            this.error_min_length = 1000; // 1 sec
        else
            this.error_min_length = this.error_min_length*1000;

        if ('growl' in this.error_condition){
            this.error_delay = this.error_condition['growl'].duration;
            if (this.error_delay == undefined)
                this.error_delay  = 1000*3;
            else if (this.error_delay === 'MANUAL'){
                  this.error_delay  = 1000*60*60;
                  this.error_manual_hide = true;
            }
            else if (this.error_delay === 'AUTO'){
                  this.error_delay  = 1000*60*60;
                  this.error_auto_hide = true;
            }
            else{
                this.error_delay = this.error_delay * 1000;
            }
        }
    }
};

DevicePropertyAlert.prototype.check = function (current_value) {
    var state = this.current_state;
    // - TODO: Do not reshow growl for warning or error if the growl for the
    // property is still visible from a previous check()
    // - TODO: Remove warning growl before showing error.
    // - TODO: update state when growl has been closed / hidden
    var now = new Date().getTime();

    if (this.error_condition != undefined){
        var error_thresh = this.error_condition.threshold;
        var err_lessthan_thresh = 'falling' in this.error_condition['edges'];
        var err_greaterthan_thresh = 'rising' in this.error_condition['edges'];

        if (state != 'error' && ((err_lessthan_thresh == true && current_value <= error_thresh) || (err_greaterthan_thresh == true && current_value >= error_thresh))){
            if (this.last_error_start_time == undefined){
                this.last_error_start_time = now;
                //console.log("Error time:",this.last_error_start_time);
            }
            else if (now-this.last_error_start_time >= this.error_min_length){
                this.last_warning_start_time = undefined;
                if (this.current_state === 'warning'){
                    this.last_warning_start_time = undefined;
                    $(this.element_id).removeClass('iohub-warning');
                    if (this.warning_auto_hide == true){
                        // Remove any growls if auto_hide is true
                        var growl_node = $("#"+this.warning_growl_id);
                        if (growl_node.length>0){
                            growl_node.alert("close");
                        }
                    }
                }
                $(this.element_id).removeClass('iohub-warning');
                $(this.element_id).addClass('iohub-error');
                this.current_state = 'error';
                this.showError();
                //console.log("ERROR.");
            }
        return true;
        }
    }

    if (this.warning_condition != undefined && this.last_error_start_time == undefined){
        var warn_thresh = this.warning_condition.threshold;
        var warn_lessthan_thresh = 'falling' in this.warning_condition['edges'];
        var warn_greaterthan_thresh = 'rising' in this.warning_condition['edges'];

        if (state === 'off' && ((warn_lessthan_thresh == true && current_value <= warn_thresh) || (warn_greaterthan_thresh == true && current_value >= warn_thresh))){
            if (this.last_warning_start_time == undefined){
                this.last_warning_start_time = now;
                //console.log("Warning time:",this.last_warning_start_time);
            }
            else if (now-this.last_warning_start_time >= this.warning_min_length){
                this.last_error_start_time = undefined;
                $(this.element_id).addClass('iohub-warning');
                this.showWarning();
                this.current_state = 'warning';
                //console.log("WARNING.");
            }
            return true;
        }
    }

    var athresh = undefined;
    var lessthan_thresh = undefined;
    var greaterthan_thresh = undefined;
    if (this.warning_condition != undefined){
        athresh = this.warning_condition.threshold;
        lessthan_thresh = 'falling' in this.warning_condition['edges'];
        greaterthan_thresh = 'rising' in this.warning_condition['edges'];
    }
    else if (this.error_condition != undefined){
        athresh = this.error_condition.threshold;
        lessthan_thresh = 'falling' in this.error_condition['edges'];
        greaterthan_thresh = 'rising' in this.error_condition['edges'];
    }

    if (state != 'off' && ((lessthan_thresh == true && current_value > athresh) || (greaterthan_thresh == true && current_value < athresh))){
        this.current_state = 'off';
        this.last_error_start_time = undefined;
        this.last_warning_start_time = undefined;
        $(this.element_id).removeClass('iohub-error');
        $(this.element_id).removeClass('iohub-warning');
        if (this.warning_auto_hide == true){
            // Remove any growls if auto_hide is true
            var growl_node = $("#"+this.warning_growl_id);
            if (growl_node.length>0){
                growl_node.alert("close");
            }
        }
        if (this.error_auto_hide == true){
            var growl_node = $("#"+this.error_growl_id);
            if (growl_node.length>0){
                growl_node.alert("close");
            }
        }
    }
    return false;
};
DevicePropertyAlert.prototype.showWarning = function () {
    this.current_state = 'warning';
    if (this.warning_condition != undefined && this.warning_condition.growl != undefined){
        if ($("#"+this.warning_growl_id).length > 0)
            return false;
        $.bootstrapGrowl(this.warning_condition.growl.text, {
          ele: 'body', // which element to append to
          type: 'warning', // (null, 'info', 'error', 'success')
          offset: {from: 'top', amount: 20}, // 'top', or 'bottom'
          align: 'right', // ('left', 'right', or 'center')
          width: 250, // (integer, or 'auto')
          delay: this.warning_delay, // Time while the message will be displayed. It's not equivalent to the *demo* timeOut!
          allow_dismiss: this.warning_manual_hide, // If true then will display a cross to close the popup.
          stackup_spacing: 10, // spacing between consecutively stacked growls.
          id: this.warning_growl_id
        });
    }
};
DevicePropertyAlert.prototype.showError = function () {
    this.current_state = 'error';

    if (this.error_condition != undefined && this.error_condition.growl != undefined){
        // Check if an error growl for this device / property is already visible.
        // If one is, do not show another.
        if ($("#"+this.error_growl_id).length > 0)
            return false;
        $.bootstrapGrowl(this.error_condition.growl.text, {
          ele: 'body', // which element to append to
          type: 'danger', // (null, 'info', 'error', 'success') success, info, warning, or danger
          offset: {from: 'top', amount: 20}, // 'top', or 'bottom'
          align: 'right', // ('left', 'right', or 'center')
          width: 250, // (integer, or 'auto')
          delay: this.error_delay, // Time while the message will be displayed. It's not equivalent to the *demo* timeOut!
          allow_dismiss: this.error_manual_hide, // If true then will display a cross to close the popup.
          stackup_spacing: 10, // spacing between consecutively stacked growls.
          id: this.error_growl_id
        });
        return true;
    }
    return false;
};

// Create client side app state
var umf_state = {
    experiment_name_list: [],

    active_experiment_name: '',

    existing_session_names: [],

    ui_setting: {},

    monitored_devices: {},

    device_dom_nodes: {},

    mouse_overlay_enabled: false,
    gaze_overlay_enabled: false,

    device_alerts: {},

    initRuntimeAlerts: function(alert_dict){
       this.device_alerts = {};
//       console.log("alert_dict:",alert_dict);
       for (var device_name in alert_dict){
           var device_properties = alert_dict[device_name];
//           console.log("device_properties:",device_properties);
           for (var device_property in device_properties){
                var prop_node_id = "#"+device_name+'_'+device_property;
                var dom_node=$(prop_node_id);
                if (dom_node.length > 0) {
//                    console.log('********** prop_node_id has a dom node!!')
                    // create alert obj's that can be checked
                    // as the value for this prop changes...
                    this.device_alerts[prop_node_id] = new DevicePropertyAlert(device_name, device_property, prop_node_id, device_properties[device_property]);
                }
           }
       }
//       console.log(this.device_alerts);
    },

    fillVideoCanvas: function(){
          var canvas = document.getElementById('videoCanvas');
          var context = canvas.getContext('2d');
          context.fillStyle="rgba(209, 207, 176,1)";
          context.fillRect(0,0,canvas.width,canvas.height);
        }
};

function drawCanvasCircle(canvas, centerX, centerY, radius, color, lineWidth){
      var context = canvas.getContext('2d');
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
      context.fillStyle = color;
      context.fill();
      if (lineWidth > 0){
        context.lineWidth = lineWidth;
        context.strokeStyle = color;
        context.stroke();
        }
    }


function onDecodeWsVideoFrame(jsmpg_obj,video_canvas){
        // draw any overlay graphics on the realtime screen cap feed
        if (umf_state.monitored_devices && (umf_state.mouse_overlay_enabled == true || umf_state.gaze_overlay_enabled == true)){
            var dres=umf_state.monitored_devices.display.resolution[0];
            var x_scale=video_canvas.width/dres[0];
            var y_scale=video_canvas.height/dres[1];

            if (umf_state.mouse_overlay_enabled == true){
                var mp=umf_state.monitored_devices.mouse.position[0];
                if (mp){
                    var gx=mp[0]+dres[0]/2.0;
                    var gy=dres[1]-(mp[1]+dres[1]/2.0);
                    var cx = gx*x_scale;
                    var cy = gy*y_scale;
                    var cradius = 20.0*x_scale;
                    var ccolor = "rgba(255,0,0,0.5)";
                    drawCanvasCircle(video_canvas, cx, cy, cradius, ccolor, 0);
                }
            }
            if (umf_state.gaze_overlay_enabled == true){
                var gp=umf_state.monitored_devices.eyetracker.average_gaze_position[0];
                if (gp){
                    if (gp[0] > -1000){
                        var gx=gp[0]+dres[0]/2.0;
                        var gy=dres[1]-(gp[1]+dres[1]/2.0);
                        var cx = gx*x_scale;
                        var cy = gy*y_scale;
                        var cradius = 20.0*x_scale;
                        var ccolor = "rgba(0,255,0,0.5)";
                        drawCanvasCircle(video_canvas, cx, cy, cradius, ccolor, 0);
                        //console.log('draw gaze_position:',cx,cy);
                       }
                }
            }
        }
    }