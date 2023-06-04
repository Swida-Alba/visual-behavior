% statistics of GY Jail
% addpath('D:\GY_GUA\analyzer');
% addpath('D:\HumidityEntrainment\HE_codes');
tic;
warning off;
clear;
close all;

%% parameters
% directory = 'D:\GY_Gua\Jail\20230429_ALL';
% invalid_jails_input = {4,13};
directory = 'D:\GY_Gua\Jail\20230513';
invalid_jails_input = {7, 11};
% directory = 'D:\GY_Gua\Jail\20230430';
% invalid_jails_input = {};
freeze_threshold_time = 5; % in sec;
freeze_threshold_pixel = 0.1; % in pixel; noisy displacement less than this threshold will be filtered.
jump_threshold_low = 10; % lower threshold of the dynamic threshold for jump identification
jump_threshold_high = 15; % upper threshold of the dynamic threshold for jump identification
walk_threshold = 0.1; % in pixel

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
if exist(folder_visualstat,"dir") == 7
    rmdir(folder_visualstat,"s");
end
mkdir(folder_visualstat);
mkdir(folder_individual);

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

% assign patches to videos
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
        t1 = patch_t.x(1);
        t2 = patch_t.x(2);
        if t1 >= v_starts_relative(v) && t2 <= v_starts_relative(v) + validFrames(v)/real_fps(v)
            patch_t.x = patch_t.x - v_starts_relative(v);
            patches_v = cat(1, patches_v, {patch_t});
            if strcmp(patch_t.type,"Pulse")
                f0 = fix(patch_t.x(1,1) * real_fps(v));
                ft = fix(patch_t.x(2,end) * real_fps(v));
                onPulsing_v(f0:ft) = 1;
            elseif strcmp(patch_t.type,"Constant LED")
                f0 = fix(patch_t.x(1) * real_fps(v));
                ft = fix(patch_t.x(2) * real_fps(v));
                onConstLED_v(f0:ft) = 1;
            elseif strcmp(patch_t.type,"Looming")
                f0 = fix(patch_t.x(1) * real_fps(v));
                ft = fix(patch_t.x(2) * real_fps(v));
                onLooming_v(f0:ft) = 1;
            end
        end
    end
    video_patches{v} = patches_v;
    onConstLED{v} = onConstLED_v;
    onPulsing{v} = onPulsing_v;
    onLooming{v} = onLooming_v;
end
save(fullfile(folder_stat,"logInfo.mat"),"log_raw","log_info");
save(fullfile(folder_stat,"patches.mat"),"log_patches","video_patches","onLooming","onPulsing","onConstLED");

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
    count = fprintf("Calculating displacement in video %d......", v);
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
    [dist_smoothed_cb, ~, ~, loc_smoothed] = getDistance(movmedian(centers_filled,30,3));
    smoothed_distances_v = movmean(dist_smoothed_cb,10,2);
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
    count = fprintf("Classifying behaviors in video %d......", v);
    frmNum = validFrames(v);
    frzThresh = ceil(freeze_threshold_time * real_fps(v));
    
    jmp_value_v = filled_distances{v} - jump_threshold{v};
    jmp_v = jmp_value_v > 0; %%%%%%%% get jump points
    jmp_last_v = false(jail_N,frmNum);
    for j = 1:jail_N
        for f = 1:frmNum
            if jmp_v(j,f)
                jmp_last_v(j,f:min(f+59,frmNum)) = 1;
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
    freeze_interval_v = cell(jail_N,1);
    for j = 1:jail_N
        frz = [false, freeze_points_v(j,:), false];
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
    jump_value{v} = jmp_value_v;
    jump_points{v} = jmp_v;
    jump_last{v} = jmp_last_v;
    freeze_interval{v} = freeze_interval_v;
    freeze_points{v} = freeze_points_v;
    walk_points{v} = walk_points_v;
end
count = fprintf("Done. Saving data...");
save(fullfile(folder_stat,"recognized_behaviors.mat"),"jump_value","jump_points","jump_last","freeze_points","freeze_interval","walk_points");
fprintf([repmat('\b',1,count-6), 'Saved\n']);

%% statistics



%% visualize events and videos
if isempty(gcp('nocreate'))
    parpool(4);
end

count = 0;
for v = 1:video_N
    fprintf(repmat('\b',1,count));
    count = fprintf('plotting...video %d', v);
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
    
    % plot averaged locomotion and mark stimuli
    fig_avg = plotDistance(t_seq, "dist", mean(filled_distances_v,1,'omitnan'), "patches", patches_v);
    title("Average Moved Distances per Frame in Video "+v);
    pic_name = "Average_dist_v"+v;
    ylim([-10 50]);
    saveas(fig_avg,fullfile(folder_visualstat,pic_name));
    exportgraphics(fig_avg,fullfile(folder_visualstat,pic_name+".png"),'Resolution',600);
    close(fig_avg);

    % visualize jail states altogether
    fig_state = plotState(t_seq,patches_v,jump_points_v,freeze_points_v,walk_points_v);
    title("fly states in Video "+v);
    pic_name = "Jail_states_v"+v;
    saveas(fig_state, fullfile(folder_visualstat,pic_name));
    exportgraphics(fig_state,fullfile(folder_visualstat,pic_name+".png"),'Resolution',600);
    close(fig_state);

    parfor i = 1:length(valid_jails{v})
        % visualize locomotions and behavioral states of individual jails
        j = valid_jails_v(i);
        fig_jail = plotDistance(t_seq, ...
                                "dist", valid_distances_v(j,:), ...
                                "filled_dist", filled_distances_v(j,:), ...
                                "smoothed_dist", smoothed_distances_v(j,:), ...
                                "jump_threshold", jump_threshold_v(j,:), ...
                                "jump_points", jump_points_v(j,:), ...
                                "freeze_points", freeze_points_v(j,:), ...
                                "walk_points", walk_points_v(j,:), ...
                                "patches", patches_v);
        title("Moved Distances per Frame of Fly "+j+" in Video "+v);
        pic_name = "dist_v"+v+"j"+j;
        saveas(fig_jail,fullfile(folder_individual,pic_name));
        exportgraphics(fig_jail,fullfile(folder_individual,pic_name+".png"),'Resolution',600);
        close(fig_jail);
    end
end
fprintf('\nDone\n');

%%
toc;



