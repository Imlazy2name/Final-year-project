import femm
import csv
import time

# ============================================================
# CONFIGURATION
# ============================================================
FEMM_FILE    = r"C:\Users\VICTUS\Desktop\Project\ritto's kalaveruthe\controlled_inductor_test_N16_tapped\controlled_inductor_test_N16_tapped.fem"
MAIN_CIRCUIT = "AC_winding"
BIAS_CIRCUIT = "Bias_winding"
OUTPUT_CSV   = r"C:\Users\VICTUS\Desktop\Project\ritto's kalaveruthe\controlled_inductor_test_N16_tapped\L_vs_IL_ibias_full_finerstep.csv"

EXPECTED_DEPTH     = 14.6
PRECISION          = 1e-8   # confirmed floor for this FEMM build
ACSOLVER           = 1      # 0 = successive approximation, 1 = Newton

IL_min, IL_max, IL_step = -1.0, 6.0, 0.1
ibias_min, ibias_max, ibias_step = 0.0, 2.0, 0.05

dI = 0.1

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

# ============================================================
# BUILD SWEEP POINTS
# ============================================================
def frange(start, stop, step):
    n = round((stop - start) / step)
    return [round(start + i * step, 6) for i in range(n + 1)]

IL_values    = frange(IL_min, IL_max, IL_step)
ibias_values = frange(ibias_min, ibias_max, ibias_step)

# Build the list of unique currents we actually need to solve at, per IL
# point: IL-dI and IL+dI. Since consecutive IL points are dI*2 apart when
# IL_step > 2*dI, these usually DON'T overlap between points, so a true
# forward-difference reuse only helps if dI is large relative to IL_step.
# With your values (IL_step=0.1, dI=0.1), points don't share solves --
# so we keep centered difference for correctness and rely on solver speed
# improvements (Newton) instead of trying to force reuse that isn't real.

print(f"Sweeping {len(ibias_values)} i_bias points x {len(IL_values)} IL points "
      f"= {len(ibias_values) * len(IL_values)} L points "
      f"({len(ibias_values) * len(IL_values) * 2} FEMM solves)")

# ============================================================
# OPEN FEMM, SET SOLVER + PRECISION, SWEEP
# ============================================================
femm.openfemm()
femm.opendocument(FEMM_FILE)

femm.mi_probdef(0, 'millimeters', 'planar', PRECISION, EXPECTED_DEPTH, 30, ACSOLVER)
print(f"Precision = {PRECISION:.0e}, depth = {EXPECTED_DEPTH} mm, "
      f"acsolver = {'Newton' if ACSOLVER == 1 else 'Successive approx'}\n")

results = []
start_time = time.time()
solve_count = 0

for ibias in ibias_values:
    femm.mi_modifycircprop(BIAS_CIRCUIT, 1, ibias)
    print(f"\n--- i_bias = {ibias:.2f} A ---")

    for IL in IL_values:
        print(f"  IL = {IL:5.2f} A ... ", end="", flush=True)
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

        results.append({
            "i_bias_A": ibias,
            "IL_A": IL,
            "flux_linkage_Wb_t": flux_avg,
            "dL_H": dL
        })

        print(f"done in {time.time()-t0:.1f}s  (dL = {dL*1e6:.3f} uH)")

    elapsed = time.time() - start_time
    print(f"--- i_bias = {ibias:.2f} A row complete "
          f"({solve_count} solves so far, {elapsed:.1f}s elapsed) ---")

femm.closefemm()

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["i_bias_A", "IL_A", "flux_linkage_Wb_t", "dL_H"])
    writer.writeheader()
    writer.writerows(results)

print(f"\nDone. {len(results)} points written to:\n{OUTPUT_CSV}")
print(f"Total FEMM solves: {solve_count}, total time: {time.time()-start_time:.1f}s")