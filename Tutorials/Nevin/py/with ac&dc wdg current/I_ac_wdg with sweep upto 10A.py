"""
Current-Controlled Variable Inductor -- 3D Sweep on User's FEMM Model
=======================================================================
Sweeps BOTH the bias current (I_bias, on Bias_winding) AND the actual
AC winding current (I_ac_wdg, on AC_winding), records the resulting
inductance L_ac = flux_linkage / I_ac_wdg at every (I_bias, I_ac_wdg)
combination, saves the results to CSV, and plots them as a SINGLE
continuous 3D line (snake/boustrophedon ordered along I_ac_wdg).

Axes:
    x = I_bias   [A]
    y = I_ac_wdg [A]
    z = L_ac     [uH]

REQUIREMENTS:
    - FEMM 4.2 installed on Windows (femm.info)
    - Python packages: pyfemm, pywin32, numpy, matplotlib
"""

import femm
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D   # noqa: F401 (registers 3D projection)
import csv
import os

# =====================================================================
# 1. USER-EDITABLE PARAMETERS
# =====================================================================

FEM_FILE = r"C:\Users\VICTUS\Desktop\Project\femm\E42_core.FEM"

AC_CIRCUIT   = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"

Ibias_list   = np.linspace(0.01, 3.0, 60)                                    # [A] -- 60 steps

# I_ac_wdg sweep: 0.05 A, then 0.2 A, 0.4 A, 0.6 A ... up to 10 A
Iac_wdg_list = np.concatenate(([0.05], np.round(np.arange(0.2, 10.0 + 1e-9, 0.2), 2)))

print(f"Sweep size: {len(Ibias_list)} x {len(Iac_wdg_list)} = "
      f"{len(Ibias_list) * len(Iac_wdg_list)} total FEMM solves.")

OUTPUT_CSV_FILE = "L_vs_bias_vs_Iac_3D_results.csv"
OUTPUT_PNG_FILE = "L_3D_plot_single_line.png"
WORKING_COPY    = "E42_working_copy.fem"

# =====================================================================
# 2. OPEN FEMM AND LOAD THE MODEL
# =====================================================================
femm.openfemm()
femm.opendocument(FEM_FILE)
femm.mi_saveas(WORKING_COPY)   # sweep runs on a copy; original file untouched

# =====================================================================
# 3. NESTED SWEEP: I_bias  x  I_ac_wdg  ->  L_ac
# =====================================================================
results = []   # each row: (I_bias, L_ac, I_ac_wdg)

for Iac in Iac_wdg_list:
    for Ib in Ibias_list:
        femm.mi_setcurrent(BIAS_CIRCUIT, float(Ib))
        femm.mi_setcurrent(AC_CIRCUIT, float(Iac))

        femm.mi_analyze(1)
        femm.mi_loadsolution()

        current, volt_drop, flux_linkage = femm.mo_getcircuitproperties(AC_CIRCUIT)
        L_ac = flux_linkage / Iac

        results.append((Ib, L_ac, Iac))
        print(f"I_ac_wdg = {Iac:5.2f} A  |  I_bias = {Ib:6.3f} A  |  "
              f"L_ac = {L_ac * 1e6:7.3f} uH")

        femm.mo_close()

femm.mi_close()
femm.closefemm()

# =====================================================================
# 4. SAVE CSV  (columns: I_bias, L_ac, I_ac_wdg)
# =====================================================================
with open(OUTPUT_CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['I_bias_A', 'L_ac_H', 'I_ac_wdg_A'])
    writer.writerows(results)

results_arr = np.array(results)
I_bias_arr = results_arr[:, 0]
L_arr      = results_arr[:, 1] * 1e6     # uH for readability
I_ac_arr   = results_arr[:, 2]

# =====================================================================
# 5. SNAKE (BOUSTROPHEDON) ORDERING FOR A SINGLE CONTINUOUS LINE
# =====================================================================
# Sweep I_bias ascending for the first I_ac_wdg level, then descending
# for the next, then ascending again ... so the line travels smoothly
# back and forth along the depth (I_ac_wdg) axis instead of jumping
# diagonally back to I_bias = 0 every time it steps to a new level.
unique_iac = np.unique(I_ac_arr)

x_list, y_list, z_list = [], [], []
for i, iac_val in enumerate(unique_iac):
    mask = (I_ac_arr == iac_val)
    xi = I_bias_arr[mask]
    yi = I_ac_arr[mask]
    zi = L_arr[mask]

    sort_idx = np.argsort(xi)
    xi, yi, zi = xi[sort_idx], yi[sort_idx], zi[sort_idx]

    if i % 2 == 1:
        xi, yi, zi = xi[::-1], yi[::-1], zi[::-1]

    x_list.append(xi)
    y_list.append(yi)
    z_list.append(zi)

x = np.concatenate(x_list)
y = np.concatenate(y_list)
z = np.concatenate(z_list)

# =====================================================================
# 6. PLOT -- single line, single color, no legend
# =====================================================================
fig = plt.figure(figsize=(9, 7))
ax = fig.add_subplot(projection='3d')

ax.plot(x, y, z, color='tab:blue', marker='o', markersize=2, linewidth=1.5)

ax.set_xlabel('I_bias [A]')
ax.set_ylabel('I_ac_wdg [A]')
ax.set_zlabel('L_ac [uH]')
ax.set_title('L_ac vs I_bias vs I_ac_wdg (single line)')

plt.tight_layout()
plt.savefig(OUTPUT_PNG_FILE, dpi=150)
plt.show()

print(f"\nDone. Results saved to {os.path.abspath(OUTPUT_CSV_FILE)}")
print(f"3D plot saved to {os.path.abspath(OUTPUT_PNG_FILE)}")