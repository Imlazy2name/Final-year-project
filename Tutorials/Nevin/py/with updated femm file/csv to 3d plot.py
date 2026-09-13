import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# ============================================================
# LOAD CSV FILE
# ============================================================

file = r"C:\Users\VICTUS\Desktop\Project\ritto's kalaveruthe\controlled_inductor_test_N16_tapped\L_vs_IL_ibias_full_finerstep.csv"

df = pd.read_csv(file)

# ============================================================
# GET DATA
# ============================================================

I_bias = df["i_bias_A"]
I_ac_wdg = df["IL_A"]

# Convert inductance from H to µH
L_ac = df["dL_H"] * 1e6

# ============================================================
# CREATE 3D PLOT
# ============================================================

fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection="3d")

# Unique IL values
IL_values = sorted(df["IL_A"].unique())

# Plot one line for each IL value
for IL in IL_values:

    data = df[df["IL_A"] == IL].sort_values("i_bias_A")

    ax.plot(
        data["i_bias_A"],
        data["IL_A"],
        data["dL_H"] * 1e6,
        marker="o",
        markersize=3,
        linewidth=1.5
    )

# ============================================================
# AXIS LABELS
# ============================================================

ax.set_xlabel("I_bias [A]", fontsize=14, labelpad=12)
ax.set_ylabel("I_ac_wdg [A]", fontsize=14, labelpad=12)
ax.set_zlabel("L_ac [µH]", fontsize=14, labelpad=12)

# ============================================================
# TITLE
# ============================================================

ax.set_title(
    "L_ac vs I_bias vs I_ac_wdg (single line)",
    fontsize=18,
    pad=20
)

# ============================================================
# VIEW ANGLE
# ============================================================

ax.view_init(
    elev=25,
    azim=-60
)

# ============================================================
# GRID
# ============================================================

ax.grid(True)

plt.tight_layout()
plt.show()