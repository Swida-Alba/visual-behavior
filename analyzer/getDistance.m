function [varargout] = getDistance(centers)
% reshape centers to a 3-D array: flyN x 2 x frameNumber.
[~,Imax] = max(size(centers));
[~,Imin] = min(size(centers));
Imiddle = setdiff([1 2 3], [Imax Imin]);
centers = permute(centers,[Imiddle, Imin, Imax]);

xy_diff = diff(centers,1,3);
xy_square = xy_diff .^ 2;
xy_sqsum = permute(sum(xy_square,2), [1 3 2]);
distances = [zeros(size(centers,1),1), xy_sqsum .^ 0.5];
azimuthAngles = [zeros(size(centers,1),1), permute(atan2d(xy_diff(:,2,:), xy_diff(:,1,:)),[1 3 2])];

xy_loc = permute(sum(centers .^ 2,2) .^ 0.5, [1 3 2]); % distances of each point to (0,0)
relative_locations = xy_loc - min(xy_loc,[],2);

sum_nanvalue = sum(isnan(distances), 2);
invalid_pos = (sum_nanvalue > size(distances,2) * 0.3); % a jail is invalid if the proportion of NaN is more than 30%.
invalidRow = find(invalid_pos)';

varargout = {distances, invalidRow, azimuthAngles, relative_locations};
end