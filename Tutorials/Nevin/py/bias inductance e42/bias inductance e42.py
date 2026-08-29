"""
Current-Controlled Variable Inductor -- Bias Winding Incremental
Self-Inductance Sweep
============================================================================
Fixes I_ac_wdg at a constant value, sweeps I_bias from ~0 to 3 A, and
extracts the INCREMENTAL (small-signal) self-inductance of the combined
Bias_winding circuit at each point using a central-difference flux-
linkage perturbation. This avoids the low-I_bias blow-up that a plain
flux_linkage/I_bias secant calculation can produce when a large fixed
AC current induces mutual flux into the bias circuit.

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

FEM_FILE = r"C:\Users\VICTUS\Desktop\Project\femm\Inductor_with_E42_core - Copy.FEM"

AC_CIRCUIT   = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"

I_ac_fixed = 100.0 / 24.0     # [A] -- fixed AC winding current, ~4.1667 A

Ibias_list = np.linspace(0.01, 3.0, 60)     # [A] -- 60 steps, 0.01 - 3.0 A

dI = 0.005     # [A] -- small perturbation for the central-difference incremental inductance

OUTPUT_CSV_FILE_LBIAS = "Lbias_incremental_vs_Ibias_results.csv"
OUTPUT_PNG_FILE_LBIAS = "Lbias_incremental_vs_Ibias_plot.png"
WORKING_COPY_LBIAS    = "E42_working_copy_Lbias.fem"

# =====================================================================
# 2. OPEN FEMM AND LOAD THE MODEL
# =====================================================================
femm.openfemm()
femm.opendocument(FEM_FILE)
femm.mi_saveas(WORKING_COPY_LBIAS)   # sweep runs on a copy; original file untouched

# =====================================================================
# 3. SWEEP: I_bias  ->  L_bias (incremental)  (I_ac_wdg held fixed)
# =====================================================================
results = []   # each row: (I_bias, L_bias_diff)

for Ib in Ibias_list:
    Ib_minus = max(Ib - dI, 1e-4)
    Ib_plus  = Ib + dI

    femm.mi_setcurrent(AC_CIRCUIT, I_ac_fixed)

    femm.mi_setcurrent(BIAS_CIRCUIT, float(Ib_minus))
    femm.mi_analyze(1)
    femm.mi_loadsolution()
    _, _, flux_minus = femm.mo_getcircuitproperties(BIAS_CIRCUIT)
    femm.mo_close()

    femm.mi_setcurrent(BIAS_CIRCUIT, float(Ib_plus))
    femm.mi_analyze(1)
    femm.mi_loadsolution()
    _, _, flux_plus = femm.mo_getcircuitproperties(BIAS_CIRCUIT)
    femm.mo_close()

    delta_I = Ib_plus - Ib_minus
    L_bias_diff = (flux_plus - flux_minus) / delta_I

    results.append((Ib, L_bias_diff))
    print(f"I_bias = {Ib:6.3f} A  |  I_ac_wdg = {I_ac_fixed:6.3f} A (fixed)  |  "
          f"L_bias = {L_bias_diff * 1e6:8.3f} uH")

femm.mi_close()
femm.closefemm()

# =====================================================================
# 4. SAVE CSV  (columns: I_bias, L_bias_diff)
# =====================================================================
with open(OUTPUT_CSV_FILE_LBIAS, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['I_bias_A', 'L_bias_diff_H'])
    writer.writerows(results)

results_arr = np.array(results)
I_bias_arr, L_bias_arr = results_arr[:, 0], results_arr[:, 1]

# =====================================================================
# 5. PLOT
# =====================================================================
plt.figure(figsize=(7, 5))
plt.plot(I_bias_arr, L_bias_arr * 1e6, 'g-o', markersize=3)
plt.xlabel('I_bias [A]')
plt.ylabel('L_bias (incremental) [uH]')
plt.title(f'Bias Winding Incremental Self-Inductance vs I_bias  (I_ac_wdg = {I_ac_fixed:.4f} A fixed)')
plt.grid(True, which='both')
plt.tight_layout()
plt.savefig(OUTPUT_PNG_FILE_LBIAS, dpi=150)
plt.show()

print(f"\nDone. Results saved to {os.path.abspath(OUTPUT_CSV_FILE_LBIAS)}")
print(f"Plot saved to {os.path.abspath(OUTPUT_PNG_FILE_LBIAS)}")