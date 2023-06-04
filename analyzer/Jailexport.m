addpath('D:\GY_GUA\analyzer');
addpath('D:\HumidityEntrainment\HE_codes');
tic;
warning off;
clear;
close all;

%% parameters
dirs = {'D:\GY_Gua\Jail\20230601'};

M = 4;
if isempty(gcp('nocreate'))
    parpool(M);
elseif gcp('nocreate').NumWorkers ~= M && gcp('nocreate').Connected == true
    delete(gcp('nocreate'));
    parpool(M);
else
    fprintf('parpool has been activated (Active workers: %d)\n',M);
end
for d = 1:length(dirs)
    directory = dirs{d};
    fprintf("current processing: %s\n", directory);
    print_step = 60;
    writeVideo_step = 1; % write one frame for each "writeVideo_step" frames.
    export_fps = 30;
    export_quality = 2; % 5 is recommended.
    export_format = 'MPEG-4';
    
    folder_roi = fullfile(directory,'ROI');
    folder_stat = fullfile(directory,'stat');
    folder_video = fullfile(directory,'video');
    
    load(fullfile(folder_stat,"videoInfo.mat"));
    load(fullfile(folder_stat,"recognized_behaviors.mat"));
    load(fullfile(folder_stat,"patches.mat"));
    
    parfor v = 1:video_N
        fprintf('Exporting marked events on video %d\n', v);
        LL_c = load(fullfile(folder_stat,"centers_"+v+".mat"));
        bboxes = LL_c.bboxes;
        LL_roi = load(fullfile(folder_roi,"roi_"+v+".mat"));
        roi_jail = LL_roi.roi_jail;
        walk_points_v = walk_points{v};
        jump_points_v = jump_points{v};
        jump_last_v = jump_last{v};
        freeze_points_v = freeze_points{v};
        onPulsing_v = onPulsing{v};
        onLooming_v = onLooming{v};
        onConstLED_v = onConstLED{v};
    
        myVideo = VideoReader(fullfile(folder_video,video_list{v}));
        file_export = fullfile(folder_video,"markedEvent_"+v+".mp4");
        if exist(file_export,'file')
            delete(file_export);
        end
        v_exp = VideoWriter(file_export,export_format);
        v_exp.Quality = export_quality;
        v_exp.FrameRate = export_fps;
        open(v_exp);
        
        frmNum = validFrames(v);
    %     frmNum = 12000;
        count = 0;
        file_timer = tic;
        pulsing_roi = repmat([0 250 10 100], 8);
        pulsing_roi(:,1) = linspace(50,200,8);
        for f = 1:writeVideo_step:frmNum
            if writeVideo_step == 1
                img_mark = readFrame(myVideo);
            else
                img_mark = read(myVideo,f);
            end
            
            if sum(jump_last_v(:,f))
                img_mark = markFlyOnImg(img_mark,roi_jail(jump_last_v(:,f),:), [240 193 218], 8);
            end
            if sum(jump_points_v(:,f))
                img_mark = markFlyOnImg(img_mark,roi_jail(jump_points_v(:,f),:), [213 129 174], 8);
            end
            
            if sum(freeze_points_v(:,f))
                img_mark = markFlyOnImg(img_mark,roi_jail(freeze_points_v(:,f),:), [120 190 220], 5);
            end
            if sum(walk_points_v(:,f))
                img_mark = markFlyOnImg(img_mark,roi_jail(walk_points_v(:,f),:), [220 180 120], 4);
            end
            
            img_mark = markFlyOnImg(img_mark,bboxes(:,:,f));

            if onLooming_v(f)
                img_mark = markFlyOnImg(img_mark,[100 100 50], [0 0 0], 50, "circle");
            end
            if onConstLED_v(f)
                img_mark = markFlyOnImg(img_mark,[100 250 50], [200 0 0], 50, "circle");
            end
            if onPulsing_v(f)
                img_mark = markFlyOnImg(img_mark,pulsing_roi, [200 0 0], 5);
            end
            writeVideo(v_exp,img_mark);
            if mod(f-1,print_step) == 0 || f == frmNum
                t_file = toc(file_timer);
                fps_file = f/t_file;
                fprintf(repmat('\b',1,count));
                count = fprintf('Video %d current frame: %d/%d......%.2f%%. Elapsed %.2f s at %.2f fps. Remaining %.2f s.',v, f, frmNum, f/frmNum*100, t_file, fps_file, (frmNum-f)/fps_file);
            end
        end
        fprintf('\n');
        close(v_exp);
    end
end
toc;