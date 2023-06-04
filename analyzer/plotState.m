function [varargout] = plotState(t_seq, patches, jump_points, freeze_points, walk_points, options)
arguments
    t_seq;
    patches;
    jump_points;
    freeze_points;
    walk_points;
    options.Visible = 'on';
    options.palettes = {[110 30 30]/255; [120 190 220]/255; [220 180 120]/255; [220 220 220]/255};
end
jail_N = size(jump_points,1);
jump_points = double(jump_points);
jump_points(jump_points == 0) = nan;
[patch_loom, patch_led] = mergePatches(patches,"loom_y",[-1 -1 0 0]',"led_y",[-2 -2 -1 -1]');
fig_state = figure("Visible",options.Visible); hold on
set(fig_state,'OuterPosition',[0 400 2000 500],'Position',[0 400 2000 500]);
set(gca,'TickDir','none');

legends_str = [];
legend_subset = [];
if size(patch_loom.x, 2) > 0
    hp0 = patch(patch_loom.x, patch_loom.y, patch_loom.color, 'EdgeColor', 'none', 'FaceAlpha', patch_loom.alpha);
    legends_str = cat(2,legends_str,"Looming");
    legend_subset = cat(2, legend_subset, hp0);
end
if size(patch_led.x, 2) > 0
    hp1 = patch(patch_led.x,  patch_led.y,  patch_led.color,  'EdgeColor', 'none', 'FaceAlpha', patch_led.alpha);
    legends_str = cat(2,legends_str,"LED ON");
    legend_subset = cat(2, legend_subset, hp1);
end

for j = 1:jail_N
    h1 = plot(t_seq, freeze_points(j,:) + j - 1, "Color", options.palettes{2}, "LineWidth", 5); % freezing marker
    h2 = plot(t_seq, walk_points(j,:) + j - 1, "Color", options.palettes{3}, "LineWidth", 4); % walking marker
    h3 = plot(t_seq, jump_points(j,:) + j - 1, '*', "MarkerEdgeColor", options.palettes{1}, "LineWidth", 1, "MarkerSize", 8); % jump
end
legends_str = cat(2,legends_str,["Freezing", "Walking", "Jump"]);
legend_subset = cat(2, legend_subset, [h1 h2 h3]);

legend(legend_subset,legends_str,"Location","northeastoutside","Box","off");
ylim([-2 jail_N]);
xlim([0 t_seq(end)]);
varargout = {fig_state};
end

