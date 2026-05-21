clear;

xbins = 0:10:100;

%normal data
normalData = [34; 45; 67; 37; 43; 42; 56; 55; 48; 49; 50; 33; 29; 25; 65; 59; 47; 41; 39; 20];

%shifted data
shiftedData = normalData + 2;

%% histogram making and visualization for two original histogram

figure
normalHistogram = histogram(normalData,xbins);
ylim ([0 10])
title ('Normal Data Histogram')

figure
shiftedHistogram = histogram(shiftedData,xbins);
ylim ([0 10])
title ('Shifted Data Histogram')

%% calculate the difference between two histogram
%your task: run adjustHistogram for normal histogram and shifted shifted

adjustedNormalData =         %complete the blank
adjustedShiftedData =        %complete the blank

%% visualize adjusted histogram
figure
adjustedNormalHistogram = histogram('BinEdges',xbins,'BinCounts',adjustedNormalData);
ylim ([0 0.5])
title ('Adjusted Normal Data Histogram');

figure
adjustedShiftedHistogram = histogram('BinEdges',xbins,'BinCounts',adjustedShiftedData);
ylim ([0 0.5])
title ('Adjusted Shifted Data Histogram');

%% distance calculation (using pdist)
D1 = pdist2(normalHistogram.Values,shiftedHistogram.Values,'euclidean')
D2 = pdist2(adjustedNormalHistogram.Values, adjustedShiftedHistogram.Values, 'euclidean')



%% function part

function [outputHistogram] = adjustHistogram(inputHistogram)
	temp = inputHistogram.Values;	
	value1 = temp;
	uptemp = temp(2:end)./2;
	downtemp = temp(1:(end-1))./2;
	temp(1:(end-1)) = temp(1:(end-1)) + uptemp;	
	temp(2:end) = temp(2:end) + downtemp;
	outputHistogram = temp./sum(temp);
end
