function log_patches = getPatches(log_info, t0, options)
arguments
    log_info;
    t0;
    options.led_ylim = [-10 -6];
    options.led_color = [1 0 0]; % red for CsChrimson
    options.led_alpha = 0.5;
    options.loom_ylim = [-6 -2];
    options.loom_color = [0 0 0]; % black
    options.loom_alpha = 0.8;
end
led_ylim = options.led_ylim;
led_color = options.led_color;
led_alpha = options.led_alpha;
loom_ylim = options.loom_ylim;
loom_color = options.loom_color;
loom_alpha = options.loom_alpha;

led_ys = [led_ylim(1), led_ylim(1), led_ylim(2), led_ylim(2)]';
loom_ys = [loom_ylim(1), loom_ylim(1), loom_ylim(2), loom_ylim(2)]';

log_N = size(log_info,1);

log_patches = {};
count = 0;
for i = 1:log_N
    patch_t = struct();
    evt = log_info{i,1};
    if strcmp(evt,"Light ON") % constant LED
        led_t1 = seconds(duration(log_info{i,2}-t0,"Format","hh:mm:ss.SSS"));
    elseif strcmp(evt,"Light OFF")
        led_t2 = seconds(duration(log_info{i,2}-t0,"Format","hh:mm:ss.SSS"));
        patch_t.x = [led_t1, led_t2, led_t2, led_t1]'; % x's of patch for LED
        patch_t.y = led_ys;
        patch_t.color = led_color;
        patch_t.alpha = led_alpha;
        patch_t.type = "Constant LED";
        patch_t.t1 = led_t1;
        patch_t.t2 = led_t2;
        log_patches = cat(1, log_patches, patch_t);
    elseif strcmp(evt,"r/v") % looming
        loom_t1 = seconds(duration(log_info{i+1,2}-t0,"Format","hh:mm:ss.SSS"));
        loom_t2 = seconds(duration(log_info{i+2,2}-t0,"Format","hh:mm:ss.SSS"));
        patch_t.x = [loom_t1, loom_t2, loom_t2, loom_t1]';
        patch_t.y = loom_ys;
        patch_t.color = loom_color;
        patch_t.alpha = loom_alpha;
        patch_t.type = "Looming";
        patch_t.t1 = loom_t1;
        patch_t.t2 = loom_t2;
        log_patches = cat(1, log_patches, patch_t);
        
    elseif strcmp(evt,"Frequency") % pulsing LED
        freq = log_info{i,2}; % frequency in Hz
        pw = log_info{i+1,2} / 1000; % pulse width in sec
        pul_t1 = seconds(duration(log_info{i+2,2}-t0,"Format","hh:mm:ss.SSS"));
        pul_t2 = seconds(duration(log_info{i+3,2}-t0,"Format","hh:mm:ss.SSS"));
        interval = 1 / freq; % in sec
        px = [];
        py = [];
        for tpul = pul_t1:interval:pul_t2
            pt2 = tpul + pw;
            px = cat(2, px, [tpul, pt2, pt2, tpul]');
            py = cat(2, py, led_ys);
        end
        patch_t.x = px;
        patch_t.y = py;
        patch_t.color = led_color;
        patch_t.alpha = led_alpha;
        patch_t.type = "Pulse";
        patch_t.frequency = freq;
        patch_t.pulseWidth = pw;
        patch_t.t1 = pul_t1;
        patch_t.t2 = pul_t2;
        log_patches = cat(1, log_patches, patch_t);
    end
    fprintf(repmat('\b',1,count));
    count = fprintf('building patches from log info....%d/%d  %.2f%%', i, log_N, i/log_N*100);
end
fprintf('\n');

end