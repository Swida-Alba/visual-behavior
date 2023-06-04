function [varargout] = getStateMat(stateSeries,options)
arguments
    stateSeries; % M * frmNum * N logical array, corresponding to M kinds of states of N flies
    options.stateNames = ["Jump", "Freeze", "Walk"];
    options.BarOfFreeze = 0.95;
    options.BarOfWalk = 0.3;
end
[state_N, frmNum, jail_N] = size(stateSeries);
state_prop = zeros(jail_N, state_N+1);
state_winner = false(jail_N, state_N+1);
for j = 1:jail_N
    state_series = stateSeries(:,:,j);
    state_prop(j,:) = [sum(state_series,2)', sum(sum(state_series,1) == 0)] / frmNum;
    if state_prop(j,1) > 0 % if exist jump points, define the current state as "Jump"
        state_winner(j,1) = 1;
    elseif state_prop(j,2) > options.BarOfFreeze
        state_winner(j,2) = 1; %if no jump, but freeze points, define as "Freeze"
    elseif state_prop(j,3)/state_prop(j,4) > options.BarOfWalk
        state_winner(j,3) = 1; % else if walk more than "other" behaviors, define as "Walk"
    else
        state_winner(j,4) = 1; % else is defined as "Other"
    end
end
varargout = {state_winner, state_prop};
end