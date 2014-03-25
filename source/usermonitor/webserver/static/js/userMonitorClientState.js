// Create client side app state
var umf_state = {
    ui_setting: {},

    monitored_devices: {},

    device_dom_nodes: {},

    active_overlay_types: [],

    toggleOverlayType: function(class_list,otype){
        var pressed = class_list.contains("active") == false;
        var i = this.active_overlay_types.indexOf(otype);
        if (pressed == true){
            if (i == -1)
                this.active_overlay_types.push(otype);
        }
        else if (i > -1){
            this.active_overlay_types.splice(i,1);
        }
    },

    getMouseDevicePos: function(){
        return this.monitored_devices.mouse.position;
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
        if (umf_state.monitored_devices && umf_state.active_overlay_types.length>0){
            var dres=umf_state.monitored_devices.display.resolution[0];
            var x_scale=video_canvas.width/dres[0];
            var y_scale=video_canvas.height/dres[1];
            var drawMouse = umf_state.active_overlay_types.indexOf('mouse') > -1;
            var drawGaze = umf_state.active_overlay_types.indexOf('gaze') > -1;
            var drawTime = umf_state.active_overlay_types.indexOf('time') > -1;

            if (drawMouse){
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
            if (drawGaze){
                var gp=umf_state.monitored_devices.eyetracker.gaze_position[0];
                if (gp){
                    if (gp[0] > -1000){
                        var gx=gp[0]+dres[0]/2.0;
                        var gy=dres[1]-(gp[1]+dres[1]/2.0);
                        var cx = gx*x_scale;
                        var cy = gy*y_scale;
                        var cradius = 20.0*x_scale;
                        var ccolor = "rgba(0,255,0,0.5)";
                        drawCanvasCircle(video_canvas, cx, cy, cradius, ccolor, 0);
                        console.log('draw gaze_position:',cx,cy);
                       }
                }
            }
            if (drawTime){
                var timeText="TIME TBD";
                var ctx = video_canvas.getContext("2d");
                ctx.font = "30px Arial";
                ctx.fillStyle = "rgba(255,0,255,0.75)";
                ctx.fillText(timeText,video_canvas.width *.05,video_canvas.height *.9);
            }
        }
    }