import femm
import csv
import os
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION  (tapped winding, N = 11)
# ============================================================
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FEMM_FILE    = r"C:\Users\VICTUS\Desktop\Project\femm\controlled_inductor_test_N11.fem"
OUTPUT_CSV   = os.path.join(BASE_DIR, "L_vs_IL_ibias_N11.csv")
OUTPUT_PNG   = os.path.join(BASE_DIR, "plot_L_vs_ibias_drift_with_IL_N11.png")

MAIN_CIRCUIT = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"

DEPTH        = 14.6     # mm (core depth)
PRECISION    = 1e-8
ACSOLVER     = 1        # 1 = Newton

# Uniform grid (ranges match the preliminary report, Section V-A)
IBIAS_START, IBIAS_STOP, IBIAS_STEP = 0.0, 2.0, 0.1    # A
IL_START,    IL_STOP,    IL_STEP    = -1.0, 6.0, 0.5   # A
dI = 0.05                                               # central-difference delta (A)


def build_range(start, stop, step):
    n = round((stop - start) / step)
    return [round(start + i * step, 6) for i in range(n + 1)]


ibias_values = build_range(IBIAS_START, IBIAS_STOP, IBIAS_STEP)
IL_values    = build_range(IL_START, IL_STOP, IL_STEP)

total_points = len(ibias_values) * len(IL_values)
print(f"Grid: {len(ibias_values)} i_bias x {len(IL_values)} IL "
      f"= {total_points} points ({2 * total_points} FEMM solves)\n")

# ============================================================
# SWEEP
# ============================================================
femm.openfemm()
femm.opendocument(FEMM_FILE)
femm.mi_probdef(0, 'millimeters', 'planar', PRECISION, DEPTH, 30, ACSOLVER)

results = []

for ibias in ibias_values:
    femm.mi_modifycircprop(BIAS_CIRCUIT, 1, ibias)
    print(f"--- i_bias = {ibias:.2f} A ---")

    for IL in IL_values:
        femm.mi_modifycircprop(MAIN_CIRCUIT, 1, IL + dI)
        femm.mi_analyze(1)
        femm.mi_loadsolution()
        _, _, flux_plus = femm.mo_getcircuitproperties(MAIN_CIRCUIT)
        femm.mo_close()

        femm.mi_modifycircprop(MAIN_CIRCUIT, 1, IL - dI)
        femm.mi_analyze(1)
        femm.mi_loadsolution()
        _, _, flux_minus = femm.mo_getcircuitproperties(MAIN_CIRCUIT)
        femm.mo_close()

        dL = (flux_plus - flux_minus) / (2 * dI)
        flux_avg = (flux_plus + flux_minus) / 2.0

        results.append({
            "i_bias_A": ibias,
            "IL_A": IL,
            "flux_linkage_Wb_t": flux_avg,
            "dL_H": dL,
        })
        print(f"  IL = {IL:6.2f} A  ->  dL = {dL * 1e6:.3f} uH")

femm.closefemm()

# ============================================================
# SAVE CSV
# ============================================================
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["i_bias_A", "IL_A", "flux_linkage_Wb_t", "dL_H"])
    writer.writeheader()
    writer.writerows(results)

print(f"\nDone. Saved to:\n{OUTPUT_CSV}")

# ============================================================
# PLOT: L vs i_bias -- drift with IL
# ============================================================
L_uH = {(r["i_bias_A"], r["IL_A"]): r["dL_H"] * 1e6 for r in results}

IL_to_plot = [IL for IL in IL_values if abs(IL - round(IL)) < 1e-9]   # -1, 0, 1 ... 6 A
colors = plt.get_cmap("coolwarm_r")(np.linspace(0, 1, len(IL_to_plot)))

fig, ax = plt.subplots(figsize=(9, 7))
for color, IL in zip(colors, IL_to_plot):
    L_curve = [L_uH[(ibias, IL)] for ibias in ibias_values]
    ax.plot(ibias_values, L_curve, color=color, marker="o",
            linewidth=2, label=f"IL = {IL:.1f} A")
ax.set_xlabel("i_bias (A)")
ax.set_ylabel("L (uH)")
ax.set_title("L vs i_bias -- drift with IL")
ax.grid(True, alpha=0.4)
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig(OUTPUT_PNG, dpi=150)

print(f"Plot saved to:\n{OUTPUT_PNG}")
plt.show()