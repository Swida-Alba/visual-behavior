function [varargout] = mergePatches(patches,options)
arguments
    patches;
    options.led_y = [];
    options.loom_y = [];
end

patch_led = struct("x", [], "y", [], "color", '', "alpha", '');
patch_loom = struct("x", [], "y", [], "color", '', "alpha", '');
for p = 1:size(patches,1)
    patch_t = patches{p};
    if strcmp(patch_t.type,"Constant LED") || strcmp(patch_t.type,"Pulse")
        patch_led.x = cat(2, patch_led.x, patch_t.x);
        if isempty(options.led_y)
            patch_led.y = cat(2, patch_led.y, patch_t.y);
        else
            patch_led.y = cat(2, patch_led.y, repmat(options.led_y,1,size(patch_t.y,2)));
        end
        if strcmp(patch_led.color, ''); patch_led.color = patch_t.color; end
        if strcmp(patch_led.alpha, ''); patch_led.alpha = patch_t.alpha; end
    elseif strcmp(patch_t.type,"Looming")
        patch_loom.x = cat(2, patch_loom.x, patch_t.x);
        if isempty(options.loom_y)
            patch_loom.y = cat(2, patch_loom.y, patch_t.y);
        else
            patch_loom.y = cat(2, patch_loom.y, repmat(options.loom_y,1,size(patch_t.y,2)));
        end
        if strcmp(patch_loom.color, ''); patch_loom.color = patch_t.color; end
        if strcmp(patch_loom.alpha, ''); patch_loom.alpha = patch_t.alpha; end
    end
end
varargout = {patch_loom, patch_led};
end