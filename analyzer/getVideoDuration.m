function [varargout] = getVideoDuration(videoDir, prefix, videoFormat)
arguments
    videoDir;
    prefix = 'FE';
    videoFormat = 'avi';
end
videoFileStruct = dir(videoDir);
well = length(char(prefix));
fileN = length(videoFileStruct);

t_starts = [];
t_ends = [];
for f = 1:fileN
    fname = char(videoFileStruct(f).name);
    if contains(fname,prefix) && contains(fname,['.' videoFormat])
        datenum_end = videoFileStruct(f).datenum;
        t_end = datetime(datenum_end,"ConvertFrom","datenum","Format","yyyy-MM-dd HH:mm:ss.SSS");
        t_ends = cat(1,t_ends,t_end);

        tstamp_str = fname(well+2:end-4);
        if length(tstamp_str) ~= 17
            error('WRONG TIMESTAMP!!!');
        end
        t_start = tstr2time(tstamp_str);
        t_starts = cat(1,t_starts,t_start);
    end
end
durations = t_ends - t_starts;

varargout = {durations, t_starts, t_ends};
end