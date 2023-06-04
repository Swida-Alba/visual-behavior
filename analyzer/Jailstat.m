% statistics of GY Jail
% last modified on May 16th, 2023. data collected before should be analyzed
% by Jailstat_0.m

% addpath('D:\GY_GUA\analyzer');
% addpath('D:\HumidityEntrainment\HE_codes');
tic;
warning off;
clear;
close all;

%% parameters
directory = 'D:\GY_Gua\Jail\20230601';
invalid_jails_input = {};
freeze_threshold_time = 5; % in sec;
freeze_threshold_pixel = 0.05; % in pixel; noisy displacement less than this threshold will be filtered.
jump_threshold_low = 10; % lower threshold of the dynamic threshold for jump identification
jump_threshold_high = 15; % upper threshold of the dynamic threshold for jump identification
walk_threshold = 0.1; % in pixel
state_palettes = {[110 30 30]/255; [120 190 220]/255; [220 180 120]/255; [220 220 220]/255}; % for behaviors, ["Jump", "Freeze", "Walk", "Others"]
state_names = ["Jump", "Freeze", "Walk", "Others"];
heatmap_cmap = parula;

%==================== Format of invalid_jails_input ======================%
% invalid_jails_input = {video #1, jail array 1;
%                        video #2, jail array 2};
% e.g. 
% invalid_jails_input = {1, [2 4];
%                        4, [13]};
%=========================================================================%

disp(cat(2,'Current processing directory: ',directory));
if ~exist(directory,"dir")
    error("Not Found Directory!");
end
folder_roi = fullfile(directory,'ROI');
folder_stat = fullfile(directory,'stat');
folder_video = fullfile(directory,'video');
folder_visualstat = fullfile(directory,'visualstat');
folder_individual = fullfile(folder_visualstat,'individual');
folder_stimulus = fullfile(folder_visualstat,'stimulus');
if exist(folder_visualstat,"dir") == 7
    rmdir(folder_visualstat,"s");
end
mkdir(folder_visualstat);
mkdir(folder_individual);
mkdir(folder_stimulus);

%% get real recording fps
LL_vinfo = load(fullfile(folder_stat,"videoInfo.mat"));
videoFrames = LL_vinfo.videoFrames;
validFrames = LL_vinfo.validFrames;
video_list = LL_vinfo.video_list;
video_N = LL_vinfo.video_N;
jail_N = LL_vinfo.jail_N;

[real_durations, v_starts, v_ends] = getVideoDuration(folder_video);
real_fps = videoFrames ./ seconds(real_durations);
v_starts_relative = seconds(duration(v_starts - v_starts(1),"Format","hh:mm:ss.SSS"));

invalid_jails = cell(1, video_N);
valid_jails = cell(1, video_N);
for v = 1:video_N
    invalid_jails{v} = [];
end
if ~isempty(invalid_jails_input)
    for i = 1:size(invalid_jails_input,1)
        invalid_jails{invalid_jails_input{i,1}} = invalid_jails_input{i,2};
    end
end
for v = 1:video_N
    valid_jails{v} = setdiff(1:jail_N,invalid_jails{v});
end
save(fullfile(folder_stat,"videoInfo_supp.mat"),"real_fps","real_durations","v_starts","v_ends","freeze_threshold_time","jump_threshold_low");

%% load log files
file_list = dir(directory);
log_list = {};
fileIDs = [];
for i = 1:length(file_list)
    file_name = file_list(i).name;
    if contains(file_name,'_log.txt')
        log_list = cat(1,log_list,file_name);
    end
end
fileN = length(log_list);

log_raw = {};
for i = 1:fileN
    log_i = {};
    fid = fopen(fullfile(directory,log_list{i}));
    while ~feof(fid)
        log_i = cat(1,log_i,fgetl(fid));
    end
    fclose(fid);
    log_raw = cat(1,log_raw,log_i);
end
log_N = size(log_raw,1);

log_info = cell(log_N,2);
for i = 1:log_N
    log_i = log_raw{i};
    [event, tstamp] = checkEvent(log_i);
    log_info{i,1} = event;
    TF = isstrprop(log_i,'digit');
    pos_digit = find(TF);
    log_len = length(log_i);
    if event == "Real r/v"
        pos_ms = strfind(log_i,'ms');
        log_info{i,2} = str2double(log_i(pos_digit(1) : pos_ms-2));
    elseif isdatetime(tstamp)
        log_info{i,2} = tstamp;
    else
        log_info{i,2} = str2double(log_i(pos_digit(1) : pos_digit(end)));
    end
end
log_patches = getPatches(log_info, v_starts(1), "loom_alpha", 0.5);

% assign patches to videos and adjust time to relative video time.
video_patches = cell(1, video_N);
onConstLED = cell(1, video_N);
onPulsing = cell(1, video_N);
onLooming = cell(1, video_N);
for v = 1:video_N
    patches_v = {};
    frmNum = validFrames(v);
    onConstLED_v = false(1,frmNum);
    onPulsing_v = false(1,frmNum);
    onLooming_v = false(1,frmNum);
    for i = 1 : length(log_patches)
        patch_t = log_patches{i};
        if patch_t.t1 >= v_starts_relative(v) && patch_t.t2 <= v_starts_relative(v) + validFrames(v)/real_fps(v)
            patch_t.x = patch_t.x - v_starts_relative(v);
            patch_t.t1 = patch_t.t1 - v_starts_relative(v);
            patch_t.t2 = patch_t.t2 - v_starts_relative(v);
            patches_v = cat(1, patches_v, {patch_t});
            f1 = fix(patch_t.t1 * real_fps(v));
            f2 = fix(patch_t.t2 * real_fps(v));
            if strcmp(patch_t.type,"Pulse")
                onPulsing_v(f1:f2) = 1;
            elseif strcmp(patch_t.type,"Constant LED")
                onConstLED_v(f1:f2) = 1;
            elseif strcmp(patch_t.type,"Looming")
                onLooming_v(f1:f2) = 1;
            end
        end
    end
    video_patches{v} = patches_v;
    onConstLED{v} = onConstLED_v;
    onPulsing{v} = onPulsing_v;
    onLooming{v} = onLooming_v;
end
save(fullfile(folder_stat,"logInfo.mat"),"log_raw","log_info");

%% calculate displacement
raw_distances = cell(1, video_N);
valid_distances = cell(1, video_N);
filled_distances = cell(1, video_N);
smoothed_distances = cell(1, video_N);
smoothed_distances_cb = cell(1, video_N);
filtered_distances = cell(1, video_N);
jump_threshold = cell(1,video_N);
locations = cell(1,video_N);
locations_filled = cell(1,video_N);
locations_smoothed = cell(1,video_N);

count = 0;
for v = 1:video_N
    fprintf(repmat('\b',1,count));
    count = fprintf("Calculating displacement in video %d...", v);
    LL = load(fullfile(folder_stat,"centers_"+v+".mat"));
    centers = LL.centers;
    centers_filled = LL.centers_filled;
    frmNum = validFrames(v);
    [raw_distances_v, invalidIndex, ~, locations_v] = getDistance(centers);
    
    invalid_jails{v} = union(invalid_jails{v}, invalidIndex);
    valid_jails{v} = setdiff(1:jail_N,invalid_jails{v});
    valid_distances_v = raw_distances_v;
    valid_distances_v(invalid_jails{v},:) = nan;
    [filled_distances_v, ~, ~, locations_filled_v] = getDistance(centers_filled);
    filled_distances_v(invalid_jails{v},:) = nan;
    [dist_smoothed_cb, ~, ~, loc_smoothed] = getDistance(movmedian(centers_filled,30,3)); % center-based smoothing
    smoothed_distances_v = movmedian(dist_smoothed_cb,30,2);
    jump_threshold_v = movmedian(filled_distances_v,[300 0],2) + 3*movstd(filled_distances_v,[300 0],0,2,'omitnan') + jump_threshold_low;
    jump_threshold_v = [zeros(jail_N,1)*nan, jump_threshold_v(:,1:end-1)];
    jump_threshold_v(jump_threshold_v > jump_threshold_high) = jump_threshold_high;
    filtered_distances_v = max(0,dist_smoothed_cb - freeze_threshold_pixel,'includenan');
    
    locations{v} = locations_v;
    locations_filled{v} = locations_filled_v;
    locations_smoothed{v} = loc_smoothed;
    raw_distances{v} = raw_distances_v;
    valid_distances{v} = valid_distances_v;
    smoothed_distances{v} = smoothed_distances_v;
    smoothed_distances_cb{v} = dist_smoothed_cb; % center based smoothing.
    filled_distances{v} = filled_distances_v;
    filtered_distances{v} = filtered_distances_v;
    jump_threshold{v} = jump_threshold_v;
end
count = fprintf("Done. Saving data...");
save(fullfile(folder_stat,"valid_jails.mat"),"valid_jails","invalid_jails");
save(fullfile(folder_stat,"distances.mat"),"raw_distances","valid_distances","filled_distances","smoothed_distances_cb","filtered_distances","jump_threshold","locations","locations_filled","locations_smoothed");
fprintf([repmat('\b',1,count-6), 'Saved\n']);

%% identify specific behaviors
jump_points = cell(1,video_N);
jump_last = cell(1,video_N);
jump_value = cell(1,video_N);
freeze_points = cell(1,video_N);
freeze_interval = cell(1,video_N);
walk_points = cell(1,video_N);
count = 0;
for v = 1:video_N
    fprintf(repmat('\b',1,count));
    count = fprintf("Classifying behaviors in video %d...", v);
    frmNum = validFrames(v);
    frzThresh = ceil(freeze_threshold_time * real_fps(v));
    
    jump_value_v = filled_distances{v} - jump_threshold{v};
    jump_points_v = jump_value_v > 0; %%%%%%%% get jump points
    jump_last_v = false(jail_N,frmNum);
    for j = 1:jail_N
        for f = 1:frmNum
            if jump_points_v(j,f)
                jump_last_v(j,f:min(f+59,frmNum)) = 1;
            end
        end
    end

    
    walk_points_v = smoothed_distances{v} > walk_threshold;
    dist_for_freeze = movsum(filtered_distances{v}, [0 frzThresh], 2); % using centers to identify is better.
    freeze_points_v = dist_for_freeze == 0;
    for j = 1:jail_N
        for f = (frmNum-frzThresh+1) : -1 : 1
            if freeze_points_v(j,f)
                freeze_points_v(j,f:f+frzThresh-1) = 1;
            end
        end
    end
    freeze_points_v(walk_points_v) = 0; % exclude overlapping
    freeze_interval_v = cell(jail_N,1);
    for j = 1:jail_N
        frz = [0, freeze_points_v(j,:), 0];
        fint_j = [];
        for f = 2:frmNum+2
            if ~frz(f-1) && frz(f)
                p0 = f-1;
            elseif frz(f-1) && ~frz(f)
                pt = f-2;
                fint_j = cat(1,fint_j,[p0 pt]);
            end
        end
        freeze_interval_v{j} = fint_j;
    end
    jump_value{v} = jump_value_v;
    jump_points{v} = jump_points_v;
    jump_last{v} = jump_last_v;
    freeze_interval{v} = freeze_interval_v;
    freeze_points{v} = freeze_points_v;
    walk_points{v} = walk_points_v;
end
count = fprintf("Done. Saving data...");
save(fullfile(folder_stat,"recognized_behaviors.mat"),"jump_value","jump_points","jump_last","freeze_points","freeze_interval","walk_points");
fprintf([repmat('\b',1,count-6), 'Saved\n']);

%% statistics
fprintf("Calculating state transitions...");
delta_t1 = 3;
delta_t2 = 3;
transition_matrices = cell(3, video_N);
for v = 1:video_N
    patches_v = video_patches{v};
    jump_points_v = jump_points{v};
    freeze_points_v = freeze_points{v};
    walk_points_v = walk_points{v};
    stateSeries = permute(cat(3, jump_points_v, freeze_points_v, walk_points_v), [3 2 1]); % M * frmNum * N logical array, corresponding to M kinds of states of N flies
    state_N = 3;
    TM_led = struct('M12',zeros(state_N+1),'M23',zeros(state_N+1),'M13',zeros(state_N+1)); % transition matrix
    TM_loom = struct('M12',zeros(state_N+1),'M23',zeros(state_N+1),'M13',zeros(state_N+1));
    TM_pulse = struct('M12',zeros(state_N+1),'M23',zeros(state_N+1),'M13',zeros(state_N+1));
    for p = 1 : size(patches_v,1)
        patch_t = patches_v{p};
        t1 = patch_t.t1 - 1;
        t2 = patch_t.t2 - 1;
        t0 = t1 - delta_t1;
        t3 = t2 + delta_t2;
        fp = fix([t0 t1 t2 t3] * real_fps(v)); % [f0 f1 f2 f3]
        % 3 time stages, [t0, t1], (t1, t2), [t2, t3], of [jump, freeze, walk, other] behavior states.
        stage_N = 3;
        states = zeros(length(valid_jails{v}), 4, stage_N);
        for stage = 1:stage_N
            stateSeries_stage = stateSeries(:,fp(stage):fp(stage+1),valid_jails{v}); % remove invalid jails directly, instead of using NaN as placeholder
            state = getStateMat(stateSeries_stage);
            states(:,:,stage) = state;
        end
        % get transition matrix
        M12 = getTransitionMat(states(:,:,1),states(:,:,2));
        M23 = getTransitionMat(states(:,:,2),states(:,:,3));
        M13 = getTransitionMat(states(:,:,1),states(:,:,3));
        patch_t.TransitionMat_12 = M12;
        patch_t.TransitionMat_23 = M23;
        patch_t.TransitionMat_13 = M13;
        patches_v{p} = patch_t;

        if strcmp(patch_t.type,"Constant LED")
            TM_led.M12 = TM_led.M12 + M12;
            TM_led.M23 = TM_led.M23 + M23;
            TM_led.M13 = TM_led.M13 + M13;
        elseif strcmp(patch_t.type,"Looming")
            TM_loom.M12 = TM_loom.M12 + M12;
            TM_loom.M23 = TM_loom.M23 + M23;
            TM_loom.M13 = TM_loom.M13 + M13;
        elseif strcmp(patch_t.type,"Pulse")
            TM_pulse.M12 = TM_pulse.M12 + M12;
            TM_pulse.M23 = TM_pulse.M23 + M23;
            TM_pulse.M13 = TM_pulse.M13 + M13;
        end
    end
    transition_matrices{1,v} = TM_led;
    transition_matrices{2,v} = TM_loom;
    transition_matrices{3,v} = TM_pulse;
    video_patches{v} = patches_v;
end
stim_category = {"Constant LED"; "Looming"; "Pulse"}; %#ok<CLARRSTR> 
transition_matrices = cat(2,transition_matrices,stim_category);
count = fprintf("Saving data..."); 
save(fullfile(folder_stat,"transition_matrices.mat"),"transition_matrices");
save(fullfile(folder_stat,"patches.mat"),"log_patches","video_patches","onLooming","onPulsing","onConstLED");
fprintf(repmat('\b',1,count)); fprintf('Saved\n');


%% visualize events and state transitions
M = 6;
if isempty(gcp('nocreate'))
    parpool(M);
elseif gcp('nocreate').NumWorkers ~= M && gcp('nocreate').Connected == true
    delete(gcp('nocreate'));
    parpool(M);
else
    fprintf('parpool has been activated (Active workers: %d)\n',M);
end

fprintf('Visualizing statistics...');
parfor v = 1:video_N
    t_seq = (1:validFrames(v)) / real_fps(v);
    valid_jails_v = valid_jails{v};
    patches_v = video_patches{v};

    valid_distances_v = valid_distances{v};
    filled_distances_v = filled_distances{v};
    smoothed_distances_v = smoothed_distances{v};

    jump_points_v = jump_points{v};
    jump_threshold_v = jump_threshold{v};
    freeze_points_v = double(freeze_points{v});
    freeze_points_v(freeze_points_v == 0) = nan;
    walk_points_v = double(walk_points{v});
    walk_points_v(walk_points_v == 0) = nan;

    TM_led = transition_matrices{1,v};
    TM_loom = transition_matrices{2,v};
    TM_pulse = transition_matrices{3,v};
    
    % plot averaged locomotion and mark stimuli
    fig_avg = plotDistance(t_seq, "dist", mean(filled_distances_v,1,'omitnan'), "patches", patches_v);
    title("Average Moved Distances per Frame in Video "+v);
    pic_name = "v"+v+"_Average_locomotion";
    ylim([-10 50]);
    saveas(fig_avg,fullfile(folder_visualstat,pic_name));
    exportgraphics(fig_avg,fullfile(folder_visualstat,pic_name+".png"),'Resolution',600);
    close(fig_avg);

    % visualize jail states altogether
    fig_state = plotState(t_seq,patches_v,jump_points_v,freeze_points_v,walk_points_v,"palettes",state_palettes);
    title("fly states in Video "+v);
    pic_name = "v"+v+"_Jail_states";
    saveas(fig_state, fullfile(folder_visualstat,pic_name));
    exportgraphics(fig_state,fullfile(folder_visualstat,pic_name+".png"),'Resolution',600);
    close(fig_state);
    
    % state transitions
    sp_rowN = 3;
    sp_colN = 4;
    fig_TM = figure();
    set(fig_TM,'OuterPosition',[0 0 1800 1000],'Position',[0 0 1800 1000]);
    sgtitle("State Transitions");
    no_legend = 1;
    for i = 1:3
        TM = transition_matrices{i,v};
        M12 = TM.M12;
        if sum(M12,"all") == 0
            continue
        end
        M23 = TM.M23;
        M13 = TM.M13;
        M12_prop = M12 / sum(M12,'all');
        M23_prop = M23 / sum(M23,'all');
        M13_prop = M13 / sum(M13,'all');
        subplot(sp_rowN,sp_colN,(i-1)*sp_colN+1);
        heatmap(state_names,state_names,M12,"XLabel","After","YLabel","Before"); grid off;
        title(stim_category{i}+": Pre -> Stim");
        subplot(sp_rowN,sp_colN,(i-1)*sp_colN+2);
        heatmap(state_names,state_names,M23,"XLabel","After","YLabel","Before"); grid off;
        title(stim_category{i}+": Stim -> Post");
        subplot(sp_rowN,sp_colN,(i-1)*sp_colN+3);
        heatmap(state_names,state_names,M13,"XLabel","After","YLabel","Before"); grid off;
        title(stim_category{i}+": Pre -> Post");

        subplot(sp_rowN,sp_colN,(i-1)*sp_colN+4);
        X = categorical({'Pre','Stim','Post'});
        X = reordercats(X,{'Pre','Stim','Post'});
        y_pre = sum(M12_prop,2);
        y_stim = sum(M12_prop,1)';
        y_post = sum(M13_prop,1)';
        Y = cat(2,y_pre,y_stim,y_post);
        b = bar(X,Y,'stacked');
        b(1).FaceColor = [110 30 30]/255;
        b(2).FaceColor = [120 190 220]/255;
        b(3).FaceColor = [220 180 120]/255;
        b(4).FaceColor = [220 220 220]/255;
        title("Frequencies of states under "+stim_category{i});
        ylim([0 1]);
        if no_legend
            legend(state_names,"Box","off","Position",[0.865,0.22+(3-i)*0.3,0.05,0.084],"Units","normalized");
            no_legend = 0;
        end
    end
    pic_name = "v"+v+"_Transition_matrix";
    saveas(fig_TM,fullfile(folder_visualstat,pic_name));
    exportgraphics(fig_TM,fullfile(folder_visualstat,pic_name+".png"),'Resolution',600);
    close(fig_TM);
end
fprintf("Done\n");

%% visualize locomotions and behavioral states of individual jails
count = 0;
for v = 1:video_N
    fprintf(repmat('\b',1,count));
    count = fprintf("Plotting individual locomotions in video %d...", v);
    t_seq = (1:validFrames(v)) / real_fps(v);
    patches_v = video_patches{v};
    valid_jails_v = valid_jails{v};

    valid_distances_noNaN = valid_distances{v}(valid_jails_v,:);
    filled_distances_noNaN = filled_distances{v}(valid_jails_v,:);
    smoothed_distances_noNaN = smoothed_distances{v}(valid_jails_v,:);
    jump_threshold_noNaN = jump_threshold{v}(valid_jails_v,:);
    jump_points_noNaN = jump_points{v}(valid_jails_v,:);
    freeze_points_noNaN = double(freeze_points{v}(valid_jails_v,:));
    freeze_points_noNaN(freeze_points_noNaN == 0) = NaN;
    walk_points_noNaN = double(walk_points{v}(valid_jails_v,:));
    walk_points_noNaN(walk_points_noNaN == 0) = NaN;

    parfor i = 1:length(valid_jails_v)
        j = valid_jails_v(i);
        fig_jail = plotDistance(t_seq, ...
                                "dist", valid_distances_noNaN(i,:), ...
                                "filled_dist", filled_distances_noNaN(i,:), ...
                                "smoothed_dist", smoothed_distances_noNaN(i,:), ...
                                "jump_threshold", jump_threshold_noNaN(i,:), ...
                                "jump_points", jump_points_noNaN(i,:), ...
                                "freeze_points", freeze_points_noNaN(i,:), ...
                                "walk_points", walk_points_noNaN(i,:), ...
                                "patches", patches_v);
        title("Moved Distances per Frame of Fly "+j+" in Video "+v);
        pic_name = "v"+v+"j"+j+"_locomotion";
        saveas(fig_jail,fullfile(folder_individual,pic_name));
        exportgraphics(fig_jail,fullfile(folder_individual,pic_name+".png"),'Resolution',600);
        close(fig_jail);
    end
end
fprintf('Done\n');

%% visualize state transitions under each stimulus
count = 0;
for v = 1:video_N
    fprintf(repmat('\b',1,count));
    count = fprintf("Visualizing state transitions in video %d...", v);
    patches_v = video_patches{v};
    stim_N = length(patches_v);
    parfor i = 1:stim_N
        patch_t = patches_v{i};
        stim = patch_t.type;
        t1 =  patch_t.t1;
        M12 = patch_t.TransitionMat_12;
        M23 = patch_t.TransitionMat_23;
        M13 = patch_t.TransitionMat_13;
        M12_prop = M12 / sum(M12,'all');
        M23_prop = M23 / sum(M23,'all');
        M13_prop = M13 / sum(M13,'all');

        fig_TMi = figure();
        set(fig_TMi,'OuterPosition',[0 400 1600 300],'Position',[0 400 1600 300]);
        sgtitle("State Transitions of "+stim+" at "+num2str(t1,'%.3f')+"in video "+v);
        
        subplot(1,4,1);
        heatmap(state_names,state_names,M12,"XLabel","After","YLabel","Before"); grid off;
        title("Pre -> Stim");
        subplot(1,4,2);
        heatmap(state_names,state_names,M23,"XLabel","After","YLabel","Before"); grid off;
        title("Stim -> Post");
        subplot(1,4,3);
        heatmap(state_names,state_names,M13,"XLabel","After","YLabel","Before"); grid off;
        title("Pre -> Post");

        subplot(1,4,4);
        X = categorical({'Pre','Stim','Post'});
        X = reordercats(X,{'Pre','Stim','Post'});
        y_pre = sum(M12_prop,2);
        y_stim = sum(M12_prop,1)';
        y_post = sum(M13_prop,1)';
        Y = cat(2,y_pre,y_stim,y_post);
        b = bar(X,Y,'stacked');
        for k = 1:4
            b(k).FaceColor = state_palettes{k};
        end
        title("Frequencies of states");
        ylim([0 1]);
        legend(state_names,"Position",[0.865,0.5,0.05,0.25],"Units","normalized");
        pic_name = "v"+v+"_"+stim+"_"+fix(t1)+"s";
        saveas(fig_TMi,fullfile(folder_stimulus,pic_name));
        exportgraphics(fig_TMi,fullfile(folder_stimulus,pic_name+".png"),'Resolution',600);
        close(fig_TMi);
    end
end
fprintf('Done\n');

%%
toc;



