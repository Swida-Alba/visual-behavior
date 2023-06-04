function tstamp = tstr2time(t_str) % convert time string as yyyyMMddHHmmssSSS to datetime object.
    t_str_format = [t_str(1:4), '-', t_str(5:6), '-', t_str(7:8), ' ', t_str(9:10), ':', t_str(11:12), ':', t_str(13:14), '.', t_str(15:17)];
    tstamp = datetime(t_str_format,'InputFormat','yyyy-MM-dd HH:mm:ss.SSS','Format','yyyy-MM-dd HH:mm:ss.SSS');
end