function transitionMatrix = getTransitionMat(stateMat1, stateMat2)

[jail_N, state_N] = size(stateMat1);
transitionMatrix = zeros(state_N);
for j = 1:jail_N
    p1 = find(stateMat1(j,:));
    p2 = find(stateMat2(j,:));
    transitionMatrix(p1,p2) = transitionMatrix(p1,p2) + 1;
end
end