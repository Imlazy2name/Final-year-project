import femm
import csv
import os
import time

# ============================================================
# CONFIGURATION -- HALF B: i_bias 1.00 -> 2.00 A
# (Half A, run separately, covers 0.00 -> 0.95 A -- together
#  these reconstruct a uniform 0.05A i_bias grid from 0 to 2.0A
#  with no gap or overlap at the 1.0A boundary.)
# ============================================================
FEMM_FILE    = r"C:\Users\lenovo\Desktop\Project_files\inductor_final\controlled_inductor_test_N16_tapped.fem"
MAIN_CIRCUIT = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"
OUTPUT_CSV   = r"C:\Users\lenovo\Desktop\Project_files\inductor_final\L_vs_IL_ibias_half_B.csv"

EXPECTED_DEPTH     = 14.6
PRECISION          = 1e-8
ACSOLVER           = 1      # 0 = successive approximation, 1 = Newton

# ------------------------------------------------------------
# Grid: fidelity-priority, no runtime cap.
#   i_bias: 0.10A step, 1.00 -> 2.00A (11 points)
#   IL:     0.5A step, -2.0 -> 7.0A (19 points)
#   IL:     0.25A step, -2.0 -> 7.0A (37 points)  -- curve is
#           smooth here, no sharp knee, so 0.25A resolves the
#           shape well without the cost of 0.05A on this axis.
# ------------------------------------------------------------
def build_range(start, stop, step):
    n = round((stop - start) / step)
    return [round(start + i * step, 6) for i in range(n + 1)]

ibias_values = build_range(1.00, 2.00, 0.10)
IL_values    = build_range(-2.0, 7.0, 0.5)

dI = 0.05

# ============================================================
# SAFETY CHECK: depth
# ============================================================
saved_depth_line = None
with open(FEMM_FILE, 'r') as f:
    for line in f:
        if line.strip().startswith('[Depth]'):
            saved_depth_line = line.strip()
            break

if saved_depth_line is None:
    raise RuntimeError("Could not find [Depth] line in .fem file -- aborting.")

saved_depth_value = float(saved_depth_line.split('=')[1].strip())
print(f"SAFETY CHECK: file reports {saved_depth_line}  (expected {EXPECTED_DEPTH} mm)")
assert abs(saved_depth_value - EXPECTED_DEPTH) < 1e-6, \
    f"DEPTH MISMATCH! File has {saved_depth_value} mm, expected {EXPECTED_DEPTH} mm."
print("Depth OK.\n")

total_points = len(ibias_values) * len(IL_values)
print(f"HALF B: i_bias {ibias_values[0]:.2f}-{ibias_values[-1]:.2f} A")
print(f"Grid: {len(ibias_values)} i_bias points x {len(IL_values)} IL points "
      f"= {total_points} L-points ({total_points * 2} FEMM solves)")
print("(No runtime cap -- fidelity priority. Checkpointing means nothing "
      "is lost if you need to stop partway.)\n")

# ============================================================
# CHECKPOINT SETUP -- write header once, then append one row's
# worth of results to disk immediately after each i_bias row
# completes. A kill/crash/sleep now only ever costs the CSV
# rows for the i_bias value currently in progress, never the
# whole run.
# ============================================================
FIELDNAMES = ["i_bias_A", "IL_A", "flux_linkage_Wb_t", "dL_H"]

file_exists = os.path.exists(OUTPUT_CSV)
already_done_ibias = set()
if file_exists:
    # Resume support: if this file already has completed rows from a
    # previous run of this exact script, skip those i_bias values.
    with open(OUTPUT_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            already_done_ibias.add(float(row["i_bias_A"]))
    print(f"Found existing checkpoint file with {len(already_done_ibias)} "
          f"completed i_bias rows -- these will be skipped.\n")
else:
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

# ============================================================
# OPEN FEMM, SET SOLVER + PRECISION, SWEEP
# ============================================================
femm.openfemm()
femm.opendocument(FEMM_FILE)

femm.mi_probdef(0, 'millimeters', 'planar', PRECISION, EXPECTED_DEPTH, 30, ACSOLVER)
print(f"Precision = {PRECISION:.0e}, depth = {EXPECTED_DEPTH} mm, "
      f"acsolver = {'Newton' if ACSOLVER == 1 else 'Successive approx'}\n")

start_time = time.time()
solve_count = 0

for ibias in ibias_values:
    if ibias in already_done_ibias:
        print(f"--- i_bias = {ibias:.2f} A already checkpointed, skipping ---")
        continue

    femm.mi_modifycircprop(BIAS_CIRCUIT, 1, ibias)
    print(f"\n--- i_bias = {ibias:.2f} A ---")

    row_results = []  # only this row's points -- flushed at end of row

    for IL in IL_values:
        print(f"  IL = {IL:6.2f} A ... ", end="", flush=True)
        t0 = time.time()

        femm.mi_modifycircprop(MAIN_CIRCUIT, 1, IL + dI)
        femm.mi_analyze(1)
        femm.mi_loadsolution()
        _, _, flux_plus = femm.mo_getcircuitproperties(MAIN_CIRCUIT)
        femm.mo_close()
        solve_count += 1

        femm.mi_modifycircprop(MAIN_CIRCUIT, 1, IL - dI)
        femm.mi_analyze(1)
        femm.mi_loadsolution()
        _, _, flux_minus = femm.mo_getcircuitproperties(MAIN_CIRCUIT)
        femm.mo_close()
        solve_count += 1

        dL = (flux_plus - flux_minus) / (2 * dI)
        flux_avg = (flux_plus + flux_minus) / 2.0

        row_results.append({
            "i_bias_A": ibias,
            "IL_A": IL,
            "flux_linkage_Wb_t": flux_avg,
            "dL_H": dL
        })

        print(f"done in {time.time()-t0:.1f}s  (dL = {dL*1e6:.3f} uH)")

    # --- CHECKPOINT: flush this completed row to disk NOW ---
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerows(row_results)

    elapsed = time.time() - start_time
    print(f"--- i_bias = {ibias:.2f} A row complete AND SAVED "
          f"({solve_count} solves so far, {elapsed:.1f}s elapsed) ---")

femm.closefemm()

print(f"\nDone. Results checkpointed incrementally to:\n{OUTPUT_CSV}")
print(f"Total FEMM solves: {solve_count}, total time: {time.time()-start_time:.1f}s")