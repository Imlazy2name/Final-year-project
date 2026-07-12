clc;
clear;
close all;
addpath('C:\femm42\mfiles');
savepath;
openfemm;
opendocument('C:\Users\VICTUS\Desktop\Project\femm\E42_Sim\E42_Sim.FEM');

% Define the Diff eqn for LR circuit
I = 0; % Initial condition
V = 10;
R = 100;
i = 1e-5;
dt = 0.0001;
t_end = 0.05;
j = 0;

time = 0:dt:t_end;

% --- Pre-allocate arrays for tracking data ---
current = zeros(size(time));
inductance = zeros(size(time));
flux_linkage = zeros(size(time));

for t = 0:dt:t_end
    j = j + 1;
    mi_setcurrent('New Circuit:1', i);
    mi_analyze(0);
    mi_loadsolution();
    
    circ_prop = mo_getcircuitproperties('New Circuit');
    flux = circ_prop(3);
    L = flux/i;
    
    % --- Store values in arrays ---
    current(j) = i;
    inductance(j) = L;
    flux_linkage(j) = flux;
    
    % Numerical integration step
    I = i;
    di = ((V - I*R) / L) * dt;
    i = I + di; 
end 

% ==========================================
%                  PLOTS
% ==========================================

% Graph 1: Current vs Time
figure(1); 
plot(time, current, 'b-', 'LineWidth', 2); 
grid on; 
xlabel('Time (seconds)');
ylabel('Current (Amperes)');
title('LR Circuit: Current vs Time');

% Graph 2: Inductance vs Time
figure(2); 
plot(time, inductance, 'r-', 'LineWidth', 2); 
grid on; 
xlabel('Time (seconds)');
ylabel('Inductance (Henries)');
title('LR Circuit: Inductance vs Time');

% Graph 3: Flux vs Time
figure(3); 
plot(time, flux_linkage, 'm-', 'LineWidth', 2); 
grid on; 
xlabel('Time (seconds)');
ylabel('Flux Linkage (Webers)');
title('LR Circuit: Flux Linkage vs Time');