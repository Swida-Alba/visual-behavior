function [varargout] = plotDistance(t_seq, options)
arguments
    t_seq;
    options.dist = [];
    options.filled_dist = [];
    options.smoothed_dist = [];
    options.jump_threshold = [];
    options.jump_points = [];
    options.freeze_points = [];
    options.walk_points = [];
    options.patches = [];
    options.visible = 'on';
    options.bg_color = [1 1 1];
end

fig_jail = figure('Visible',options.visible); hold on
set(fig_jail,'OuterPosition',[0 400 2000 500],'Position',[0 400 2000 500],'Color',options.bg_color);
set(gca,'TickDir','none');
legends_str = [];

if ~isempty(options.filled_dist)
    if ~isempty(options.jump_points)
        scatter(t_seq(options.jump_points), options.filled_dist(options.jump_points),8,'*',"MarkerEdgeColor",[110 30 30]/255);
        legends_str = cat(2,legends_str,"Jump");
    end
    plot(t_seq,options.filled_dist,"Color","#D95319");
    legends_str = cat(2,legends_str,"Filled movement");
end

if ~isempty(options.dist)
    plot(t_seq,options.dist,"Color","#0072BD");
    legends_str = cat(2,legends_str,"Movement");
end

if ~isempty(options.smoothed_dist)
    plot(t_seq,options.smoothed_dist,"Color","#A2142F","LineStyle","-","LineWidth",0.1);
    legends_str = cat(2,legends_str,"Smoothed movement");
end

if ~isempty(options.jump_threshold)
    plot(t_seq,options.jump_threshold,"Color","#7E2F8E","LineStyle","-","LineWidth",0.1);
    legends_str = cat(2,legends_str,"Jump threshold");
end

if ~isempty(options.freeze_points)
    plot(t_seq,options.freeze_points - 2,"Color",[120 190 220]/255,"LineWidth",2); % freezing marker
    legends_str = cat(2,legends_str,"Freezing");
end
if ~isempty(options.walk_points)
    plot(t_seq,options.walk_points - 2,"Color",[220 180 120]/255,"LineWidth",1.6); % walking marker
    legends_str = cat(2,legends_str,"Walking");
end

if ~isempty(options.patches)
    [patch_loom, patch_led] = mergePatches(options.patches);
    if size(patch_loom.x, 2) > 0
        patch(patch_loom.x, patch_loom.y, patch_loom.color, 'EdgeColor', 'none', 'FaceAlpha', patch_loom.alpha);
        legends_str = cat(2,legends_str,"Looming");
    end
    if size(patch_led.x, 2) > 0
        patch(patch_led.x,  patch_led.y,  patch_led.color,  'EdgeColor', 'none', 'FaceAlpha', patch_led.alpha);
        legends_str = cat(2,legends_str,"LED ON");
    end
end

legend(legends_str,"Location","northeastoutside","Box","off");
xlim([0, t_seq(end)]);
ylim([-10, 150]);
xlabel("Time/s");
ylabel("Pixels");
hold off

varargout = {fig_jail};
end