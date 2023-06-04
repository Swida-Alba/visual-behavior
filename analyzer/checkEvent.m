function [event, tstamp] = checkEvent(log)
    event_category = {
        'Starting playing';
        'Done playing';
        'r/v';
        'Real r/v';
        'Light ON';
        'Light OFF';
        'LED state';
        'LED Pulsing';
        'Frequency';
        'Pulse width';
        'Pulsing ON';
        'Pulsing OFF';
        'LED timer';
        'Feedback Light ON';
        'Feedback Light OFF';
        'Feedback Pulsing ON';
        'Feedback Pulsing OFF';
       };
    event_N = size(event_category,1);
    event = '';
    tstamp = false;
    TF = isstrprop(log,'digit');
    pos_digit = find(TF);
    if sum(TF) == 17 % containing time stamp
        t_str = log(pos_digit(1) : pos_digit(end)); % char array
        tstamp = tstr2time(t_str);
    end
    for i = 1:event_N
        curr_event = event_category{i};
        if startsWith(log,curr_event)
            event = curr_event;
            break
        end
    end
end