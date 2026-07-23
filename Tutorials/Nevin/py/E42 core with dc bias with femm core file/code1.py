"""
Current-Controlled Variable Inductor -- Bias Sweep on User's FEMM Model
=========================================================================
Opens an EXISTING .FEM file (built graphically by the user in the FEMM
GUI), sweeps the DC bias current, and extracts the small-signal AC
inductance (L_ac) seen by the center-leg winding as a function of both
I_bias and H_bias.

This script does NOT rebuild geometry -- it uses whatever core shape,
materials, circuits, and turns are already defined in the .FEM file.

REQUIREMENTS:
    - FEMM 4.2 installed on Windows (femm.info)
    - Python packages: pyfemm, pywin32, numpy, matplotlib
"""

import femm
import numpy as np
import matplotlib.pyplot as plt
import csv
import os

# =====================================================================
# 1. USER-EDITABLE PARAMETERS
# =====================================================================

# Path to your FEMM file (use a raw string or double backslashes on Windows)
FEM_FILE = r"C:\Users\VICTUS\Desktop\Project\femm\E42_core.FEM"

# Circuit names -- must exactly match the names inside your .FEM file
AC_CIRCUIT   = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"

# Winding data (read from your file: n3 = 12 turns/side, n1 = n2 = 90 turns/side)
n1_plus_n2 = 90 + 90     # total bias ampere-turn count (both legs), for H_bias calc
l1_mm      = 14.8        # outer-leg length [mm] -- window height in your geometry

# Excitation
I_ac_probe  = 0.05                          # [A] small-signal AC probe current
Ibias_list  = np.linspace(0.01, 3.0, 30)    # [A] bias current sweep -- edit range as needed

OUTPUT_CSV_FILE = "L_vs_bias_results.csv"
OUTPUT_PNG_FILE = "L_vs_bias_plots.png"
WORKING_COPY    = "E42_working_copy.fem"    # sweep runs on a copy, so your original is untouched

# =====================================================================
# 2. OPEN FEMM AND LOAD THE MODEL
# =====================================================================
femm.openfemm()
femm.opendocument(FEM_FILE)

# Save a working copy immediately so repeated mi_analyze() calls (which
# write .ans solution files) never touch your original geometry file.
femm.mi_saveas(WORKING_COPY)

# =====================================================================
# 3. BIAS-CURRENT SWEEP
# =====================================================================
results = []   # (I_bias, H_bias, L_ac)

for Ib in Ibias_list:
    femm.mi_setcurrent(BIAS_CIRCUIT, float(Ib))
    femm.mi_setcurrent(AC_CIRCUIT, I_ac_probe)

    femm.mi_analyze(1)               # 1 = suppress solver window
    femm.mi_loadsolution()

    current, volt_drop, flux_linkage = femm.mo_getcircuitproperties(AC_CIRCUIT)
    L_ac = flux_linkage / I_ac_probe

    l1_m = l1_mm / 1000.0
    H_bias = n1_plus_n2 * Ib / (2.0 * l1_m)

    results.append((Ib, H_bias, L_ac))
    print(f"I_bias = {Ib:6.3f} A  |  H_bias = {H_bias:8.1f} A/m  |  "
          f"L_ac = {L_ac * 1e6:7.3f} uH")

    femm.mo_close()

femm.mi_close()
femm.closefemm()

# =====================================================================
# 4. SAVE + PLOT RESULTS
# =====================================================================
with open(OUTPUT_CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['I_bias_A', 'H_bias_A_per_m', 'L_ac_H'])
    writer.writerows(results)

results = np.array(results)
I_bias_arr, H_bias_arr, L_arr = results[:, 0], results[:, 1], results[:, 2]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

ax1.plot(I_bias_arr, L_arr * 1e6, 'b-o', markersize=3)
ax1.set_xlabel('I_bias [A]')
ax1.set_ylabel('L_ac [uH]')
ax1.set_title('L_ac vs Bias Current')
ax1.grid(True, which='both')

ax2.plot(H_bias_arr, L_arr * 1e6, 'r-o', markersize=3)
ax2.set_xlabel('H_bias [A/m]')
ax2.set_ylabel('L_ac [uH]')
ax2.set_title('L_ac vs H_bias')
ax2.set_xscale('log')
ax2.grid(True, which='both')

plt.tight_layout()
plt.savefig(OUTPUT_PNG_FILE, dpi=150)
plt.show()

print(f"\nDone. Results saved to {os.path.abspath(OUTPUT_CSV_FILE)}")
print(f"Plot saved to {os.path.abspath(OUTPUT_PNG_FILE)}")
