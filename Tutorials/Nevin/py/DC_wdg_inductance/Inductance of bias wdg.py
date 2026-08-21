"""
Current-Controlled Variable Inductor -- Bias Winding Self-Inductance Sweep
============================================================================
Fixes the AC winding current (I_ac_wdg) at a constant value, sweeps the
DC bias current (I_bias) from ~0 to 3 A, and measures the SELF-INDUCTANCE
of the Bias_winding circuit itself (flux_linkage_bias / I_bias) at each
bias point -- NOT the center-leg L_ac from earlier scripts.

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

FEM_FILE = r"C:\Users\VICTUS\Desktop\Project\femm\E42_core_copy.FEM"

AC_CIRCUIT   = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"

I_ac_fixed = 100.0 / 24.0     # [A] -- fixed AC winding current, ~4.1667 A

Ibias_list = np.linspace(0.01, 3.0, 60)     # [A] -- same 0-3A / 60-step sweep as before

OUTPUT_CSV_FILE = "L_bias_vs_Ibias_results.csv"
OUTPUT_PNG_FILE = "L_bias_vs_Ibias_plot.png"
WORKING_COPY    = "E42_working_copy.fem"

# =====================================================================
# 2. OPEN FEMM AND LOAD THE MODEL
# =====================================================================
femm.openfemm()
femm.opendocument(FEM_FILE)
femm.mi_saveas(WORKING_COPY)   # sweep runs on a copy; original file untouched

# =====================================================================
# 3. SWEEP: I_bias  ->  L_bias  (with I_ac_wdg held fixed)
# =====================================================================
results = []   # each row: (I_bias, L_bias)

for Ib in Ibias_list:
    femm.mi_setcurrent(BIAS_CIRCUIT, float(Ib))
    femm.mi_setcurrent(AC_CIRCUIT, I_ac_fixed)

    femm.mi_analyze(1)
    femm.mi_loadsolution()

    # self-inductance of the BIAS winding circuit itself
    current_b, volt_drop_b, flux_linkage_b = femm.mo_getcircuitproperties(BIAS_CIRCUIT)
    L_bias = flux_linkage_b / Ib

    results.append((Ib, L_bias))
    print(f"I_bias = {Ib:6.3f} A  |  I_ac_wdg = {I_ac_fixed:6.3f} A (fixed)  |  "
          f"L_bias = {L_bias * 1e6:8.3f} uH")

    femm.mo_close()

femm.mi_close()
femm.closefemm()

# =====================================================================
# 4. SAVE CSV  (columns: I_bias, L_bias)
# =====================================================================
with open(OUTPUT_CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['I_bias_A', 'L_bias_H'])
    writer.writerows(results)

results_arr = np.array(results)
I_bias_arr, L_bias_arr = results_arr[:, 0], results_arr[:, 1]

# =====================================================================
# 5. PLOT
# =====================================================================
plt.figure(figsize=(7, 5))
plt.plot(I_bias_arr, L_bias_arr * 1e6, 'g-o', markersize=3)
plt.xlabel('I_bias [A]')
plt.ylabel('L_bias [uH]')
plt.title(f'Bias Winding Self-Inductance vs I_bias  (I_ac_wdg = {I_ac_fixed:.4f} A fixed)')
plt.grid(True, which='both')
plt.tight_layout()
plt.savefig(OUTPUT_PNG_FILE, dpi=150)
plt.show()

print(f"\nDone. Results saved to {os.path.abspath(OUTPUT_CSV_FILE)}")
print(f"Plot saved to {os.path.abspath(OUTPUT_PNG_FILE)}")