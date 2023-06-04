% to track flies in the GY jail
% PARALLEL is currently unavailable
addpath('D:\GY_GUA\analyzer');
addpath('D:\HumidityEntrainment\HE_codes');
tic;
warning off;
clear;
close all;

%% input parameters
directory = 'D:\GY_Gua\Jail\20230601';
jail_dim = [3 5]; % [rowN colN]
v_start = 1; % video # to start tracking.
frmNum_valid = []; % valid frame number.
%======================== Format of frmNum_valid to input=================%
%{
frmNum_valid should be an N x 2 array, for valid frames are specified for N
videos, the 1st col is the video # to specify and the 2nd col is the frame 
number to specify.

e.g.:
[1, 15000;
 3, 45000;
 8, 75200]

the 1st, 3rd, 8th videos' valid frame numbers are specified
%}
%=========================================================================%


BG_smpN = 20;
intensity_thresh = 20;
print_step = 10; % step to print current progress, in frame 

% parameters for writing marked video
export_flag = 0; % if true, write marked video.
writeVideo_step = 1; % write one frame for each "writeVideo_step" frames.
export_fps = 30; 
export_quality = 5; % 5 is recommended.
export_format = 'MPEG-4';

disp(cat(2,'Current processing directory: ',directory));
folder_roi = fullfile(directory,'ROI');
folder_stat = fullfile(directory,'stat');
folder_video = fullfile(directory,'video');
mkdir(folder_roi);
mkdir(folder_stat);
jail_N = prod(jail_dim);

%% get video info
%
t_readVideo_all = tic;
fileT = dir(folder_video);
video_list = {};
videoFrames = [];
frmRates = [];
videoDurations = [];
sampleImgs = {};
video_N = 0;
for i = 1:length(fileT)
    name_i = fileT(i).name;
    if contains(name_i,'avi') && contains(name_i,'FE')
	    t_readVideo = tic;
        video_N = video_N + 1;
        video_list = cat(1,video_list,{name_i});
        vt = VideoReader(fullfile(folder_video,name_i));
        sampleImg = rgb2gray(read(vt,1));
        sampleImgs = cat(1,sampleImgs,{sampleImg});
        switch video_N
		    case 1
			    tchar = "st";
		    case 2
			    tchar = "nd";
		    case 3
			    tchar = "rd";
		    otherwise
			    tchar = "th";
        end
        % this line is added by ZHAO Yunzhi the boss of bosses
	    fprintf("\nAI_ HIGH! You have successfully started for the " + video_N + " " + tchar + " time\nNow, remember to keep going!\n                 -- From Dr. A. Hodgekin\n");
        frame = vt.NumFrames;
        frm_rate = vt.FrameRate;
        vt_duration = vt.Duration;
        videoFrames = cat(1,videoFrames,frame);
        frmRates = cat(1,frmRates,frm_rate);
        videoDurations = cat(1,videoDurations,vt_duration);
        clear('vt');
	    toc(t_readVideo);
    end
end
validFrames = videoFrames;
if ~isempty(frmNum_valid)
    for v = 1:size(frmNum_valid,1)
        validFrames(frmNum_valid(v,1)) = frmNum_valid(v,2);
    end
end
save(fullfile(folder_stat,'videoInfo.mat'),'video_list','video_N','videoFrames','validFrames','frmRates','videoDurations','sampleImgs','jail_dim','jail_N','intensity_thresh');
toc(t_readVideo_all);
%}
%% get board roi of each video
%
load(fullfile(folder_stat,'videoInfo.mat'));
count = 0;
fprintf('Draw a rectantle over the board and double click to crop\n');
fprintf('THEN similarly select the marker roi');
for v = v_start:video_N
    sampleImg = sampleImgs{v};
    fig = figure(1); imshow(sampleImg);  hold on
    set(fig,'OuterPosition',[400 200 1200 850],'Color',[1 1 1]);
    [~,roi_video] = imcrop(sampleImg);
    [~,roi_marker] = imcrop(sampleImg);
    close(fig);
    fprintf(repmat('\b',1,count));
    count=fprintf('current video NO. is : %d',v);
    save(fullfile(folder_roi,"roi_"+v+".mat"),'roi_video','roi_marker');
end

fprintf('\n');

%}
%% get background for each video
%
load(fullfile(folder_stat,'videoInfo.mat'));
for v = v_start:video_N
    fprintf('Grabbing background of video %d...',v);
    myVideo = VideoReader(fullfile(folder_video,video_list{v}));
    BG_smps = cell(1,BG_smpN);
    smpInterval = fix(validFrames(v) / BG_smpN);
    bg_candi = [];
    for i = 1:BG_smpN
        myVideo.CurrentTime = (1 + smpInterval * (i - 1)) / frmRates(v);
        BG_smps{i} = imadjust(rgb2gray(readFrame(myVideo)));
        bg_candi = cat(3,bg_candi,BG_smps{i});
    end
    bg = prctile(bg_candi,99,3);
%     fig2 = figure(2);imshow(bg,[0 255]);
    save(fullfile(folder_roi,"background_"+v+".mat"),'bg');
    fprintf('Done\n');
%     pause(1);
end
% close(fig2);
fprintf('\n');
%}
%% get jail locations
%
load(fullfile(folder_stat,'videoInfo.mat'));
for v = v_start:video_N
    sampleImg = sampleImgs{v};
    fig_chLoc = figure(3); imshow(sampleImg); 
    hold on;
    
    LL = load(fullfile(folder_roi,"background_"+v+".mat"));
    bg = LL.bg;
    LL = load(fullfile(folder_roi,"roi_"+v+".mat"));
    roi_video = LL.roi_video;
    roi_marker = LL.roi_marker;
    img_crop = imcrop(bg,roi_video);
    img_adj = medfilt2(img_crop,[20 20]);
    se = strel('square',200);
    bg_nr = imopen(img_adj,se);
    img_obj = img_adj - bg_nr;
    img_extract = img_obj > prctile(img_obj,40,'all');
    
    % figure(6); imshow(img_obj,[0 255]);
    % figure(4); mesh(img_obj);
    % figure(5); imshow(img_extract);
    
    CC = bwconncomp(img_extract);
    T = regionprops("table",CC,'Area','BoundingBox');
    boundings = T.BoundingBox(T.Area > 15000,:);
    boundings = sortrows(boundings,2);
    boundaries = [];
    for i = 1:jail_dim(2):jail_N
        bound_dim = boundings(i:i+jail_dim(2)-1,:);
        bound_dim = sortrows(bound_dim,1);
        boundaries = cat(1,boundaries,bound_dim);
    end
    roi_jail_temp = boundaries + [roi_video(1:2) 0 0];
    roi_F = -12; % pixel
    roi_jail = roi_jail_temp + [0, roi_F, 0, -roi_F];
%     roi_jail = roi_jail_temp + [roi_F, roi_F, -2*roi_F, -2*roi_F];
    
    for i = 1:jail_N
        rectangle('Position',roi_jail(i,:),'EdgeColor','#4B22DD','LineWidth',1.5);
        textprops = text(roi_jail(i,1)+roi_jail(i,3)/2,roi_jail(i,2)+roi_jail(i,4)/2,num2str(i),'VerticalAlignment','bottom'); 
        textprops.Color = '#D95319';
        textprops.FontSize = 18;
    end
    hold off;
    
    pause(2);
    save(fullfile(folder_roi,"roi_"+v+".mat"),'roi_video','roi_jail','jail_dim','roi_marker');
    saveas(fig_chLoc,fullfile(folder_roi,"jail_location_"+v+".png"));
end
close(fig_chLoc);
%}
%% track fly in the jail
%
load(fullfile(folder_stat,'videoInfo.mat'));
for v = v_start:video_N
    fprintf("Reading video %d......", v);
    LL_bg = load(fullfile(folder_roi,"background_"+v+".mat"));
    bg = LL_bg.bg;
    LL_roi = load(fullfile(folder_roi,"roi_"+v+".mat"));
    roi_jail = LL_roi.roi_jail;
    roi_marker = LL_roi.roi_marker;
    myVideo = VideoReader(fullfile(folder_video,video_list{v}));
    frmNum = validFrames(v);
    centers = zeros(jail_N,2,frmNum) * nan;
    bboxes = zeros(jail_N,4,frmNum) * nan;
    areas = zeros(jail_N,frmNum) * nan;
    MIs = zeros(jail_N,frmNum) * nan; % MaxIntensity
    marker_value = zeros(1,frmNum) * nan;
    
    % build the video file to save exported marked locations
    if export_flag
        file_export = fullfile(folder_video,"marked_"+v+".mp4");
        if exist(file_export,'file')
            delete(file_export);
        end
        v_exp = VideoWriter(file_export,export_format);
        v_exp.Quality = export_quality;
        v_exp.FrameRate = export_fps;
        open(v_exp);
    end
    fprintf("Done.\n");

    count = 0;
    file_timer = tic;
    for f = 1:frmNum
        img_f_rgb = readFrame(myVideo);
        img_f = imadjust(rgb2gray(img_f_rgb));
%         img_obj = medfilt2(bg - img_f - 20,[8 5]);
        img_obj = imgaussfilt(bg - img_f - 30, 4);
%         img_obj = bg - img_f - 20;
%         figure(7); imshow(img_obj,[]);
        
        % get marker intensity
        img_marker = imcrop(img_obj, roi_marker);
        marker_value(f) = mean(img_marker,"all");
        for j = 1:jail_N
            img_jail = imcrop(img_obj,roi_jail(j,:));
%             img_jail_on = img_jail > prctile(img_jail,99.5,"all");
            img_jail_on = img_jail > 0.3*max(img_jail,[],"all");
            
            isFlyFound = false;
            T = regionprops(img_jail_on,img_jail,'Area','BoundingBox','Centroid','MaxIntensity');
            if length(T) > 1
                T = struct2table(T);
                T = sortrows(T,'MaxIntensity','descend');
                center_fj = T.Centroid(1,:) + roi_jail(j,1:2);
                bbox_fj = T.BoundingBox(1,:) + [roi_jail(j,1:2),0,0];
                area_fj = T.Area(1);
                MI_fj = T.MaxIntensity(1);
                if T.MaxIntensity(1) > intensity_thresh && T.Area(1) < 600 && T.BoundingBox(1,3) < 40 && T.BoundingBox(1,4) < 35
                    isFlyFound = true;
                end
            elseif length(T) == 1
                center_fj = T.Centroid + roi_jail(j,1:2);
                bbox_fj = T.BoundingBox + [roi_jail(j,1:2),0,0];
                area_fj = T.Area;
                MI_fj = T.MaxIntensity;
                if T.MaxIntensity > intensity_thresh && T.Area < 600 && T.BoundingBox(3) < 40 && T.BoundingBox(4) < 35
                    isFlyFound = true;
                end
            else
                bbox_fj = [nan nan nan nan];
                area_fj = nan;
                MIs_fj = nan;
            end
            areas(j,f) = area_fj;
            MIs(j,f) = MI_fj;
            if isFlyFound
                centers(j,:,f) = center_fj;
                bboxes(j,:,f) = bbox_fj;
            end
        end
        if export_flag && mod(f-1,writeVideo_step) == 0
            img_mark = markFlyOnImg(img_f_rgb,bboxes(:,:,f));
            writeVideo(v_exp,img_mark);
        end
        t_file = toc(file_timer);
        fps_file = f/t_file;
        if mod(f-1,print_step) == 0 || f == frmNum
            fprintf(repmat('\b',1,count));
            count = fprintf('current frame: %d/%d......%.2f%%. Elapsed %.2f s at %.2f fps. Remaining %.2f s.',f,frmNum, f/frmNum*100, t_file, fps_file, (frmNum-f)/fps_file);
        end
    end
    fprintf('\n');
    centers_filled = fillmissing(centers,'linear',3);
    parsave(fullfile(folder_stat,"centers_"+v+".mat"),centers,centers_filled,bboxes,areas,MIs,marker_value);
    if export_flag
        close(v_exp);
    end
    t_file = toc(file_timer);
    fps = frmNum/t_file;
    fprintf('Tracked fly...... file %d/%d rate: %.2f fps. Elapsed %.2f s\n', v, video_N, fps, t_file);
end
%}

toc;
