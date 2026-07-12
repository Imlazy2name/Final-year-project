clc;
clear;
close all;

addpath('~/femm42/mfiles');
savepath;
openfemm;

opendocument('~/femm42/Projects/E42_Sim/E42_Sim.fem');


%Define the Diff eqn for LR circuit

I = 0; %Initial condition
V = 10;
R = 100;
i = 0.1;
dt = 0.001;
t_end = 0.5;
j = 0;

time = 0:dt:t_end;
current = zeros(size(time));

for t = 0:dt:t_end
    j = j + 1;
    mi_setcurrent('New Circuit:1', i);
    mi_analyze(0);
    mi_loadsolution();
    circ_prop = mo_getcircuitproperties('New Circuit');
    flux = circ_prop(3);
    L = flux/i;
    I = i;
    di = (V/L - I*R)*dt;
    i = I + di; 

    current(j) = i;


end 

figure; 
plot(time, current, 'b-', 'LineWidth', 2); 
grid on; 

xlabel('Time (seconds)');
ylabel('Current (Amperes)');
title('LR Circuit Transient Response via FEMM Co-Simulation');





