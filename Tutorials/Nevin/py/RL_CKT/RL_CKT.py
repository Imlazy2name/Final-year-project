"""
Series RL circuit transient — FEMM/Python co-simulation
=========================================================

Model:            V -- R -- L(I) -- (back to V)     [series loop]

  - L(I) is NOT a fixed number. It is the AC_winding inductance of the
    E42 core, obtained on-the-fly from FEMM at every time step:
        L(I) = flux_linkage(I) / I
    FEMM solves the real nonlinear magnetostatic problem (N87 BH curve
    included in the .FEM file), so L(I) naturally drops as the core
    saturates.
  - Bias_winding is forced to 0 A the whole time (left unexcited, as
    required).
  - AC_winding is the only excited circuit and acts as the inductor.

Two solutions are produced and plotted together:
  1. "FEMM" solution   : dI/dt = (V - I*R) / L_femm(I)   <- nonlinear, real core
  2. "Equation" solution: classic linear RL step response
        I(t) = (V/R) * (1 - exp(-t/tau)),   tau = L0/R
     using L0 = the *unsaturated* (low-current) inductance that FEMM
     itself reports, so the two curves start from the same physics and
     only diverge once saturation kicks in. R = 2 ohm (fixed, chosen
     to push steady-state current up around 12 A so the core actually
     saturates with this winding's 12 turns).

Plots produced:
  (a) Current   vs time   — FEMM (nonlinear) vs Equation (linear)
  (b) Inductance vs time  — FEMM L(I(t)) vs Equation's constant L0

Requirements (run this on Windows, with FEMM installed):
    pip install pyfemm matplotlib numpy
    (FEMM itself: https://www.femm.info/wiki/Download)

Usage:
    python rl_femm_cosim.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import femm

# ---------------------------------------------------------------------
# USER-ADJUSTABLE PARAMETERS
# ---------------------------------------------------------------------
FEM_FILE = r"C:\Users\VICTUS\Desktop\Project\femm\E42_core_copy.FEM"   # path to your .FEM file

AC_CIRCUIT   = "AC_winding"     # excited winding -> the series inductor
BIAS_CIRCUIT = "Bias_winding"   # kept at 0 A throughout

V_SOURCE   = 24.0     # [V] DC step voltage applied at t=0  (assumed)
R          = 2.0      # [ohm] fixed series resistance (lowered so steady-
                       #       state current ~12 A -> NI ~144 A-turns,
                       #       well past this core's saturation knee)
I_PROBE    = 0.05     # [A] small test current used ONLY to measure the
                       #      unsaturated inductance L0 once, up front
                       #      (keep this well below saturation onset)

N_STEPS    = 40        # number of time steps across the transient (reduced)
T_SPAN_TAU = 6          # simulate for 6*tau (~99.75% of final value),
                        # tau is computed from L0 and the fixed R above

FLOOR_I    = 1e-6      # [A] tiny numerical-only floor, just to avoid a
                        #      divide-by-zero at I=0. NOT a physical
                        #      quantity -> keep this far smaller than
                        #      any real current in the transient, so
                        #      FEMM is essentially always evaluated at
                        #      the actual inductor current.

OUT_CSV = "rl_femm_cosim_results.csv"
OUT_PNG_I = "current_vs_time.png"
OUT_PNG_L = "inductance_vs_time.png"


# ---------------------------------------------------------------------
# FEMM HELPERS
# ---------------------------------------------------------------------
def femm_init():
    femm.openfemm()
    femm.opendocument(FEM_FILE)
    # Work on our own analysis copy so the source file is untouched
    base = os.path.splitext(os.path.basename(FEM_FILE))[0]
    femm.mi_saveas(base + "_cosim_tmp.fem")


def femm_get_L(current_A):
    """
    Set AC_winding = current_A, Bias_winding = 0 A, solve, and return
    the winding inductance L = flux_linkage / current  [H].
    For current_A == 0 this is undefined, so the caller should avoid
    calling with exactly 0 (use I_PROBE as the smallest value instead).
    """
    femm.mi_modifycircprop(AC_CIRCUIT, 1, current_A)   # property 1 = TotalAmps_re
    femm.mi_modifycircprop(BIAS_CIRCUIT, 1, 0.0)        # bias stays unexcited

    femm.mi_analyze(1)     # 1 = run silently
    femm.mi_loadsolution()

    # [current, volts, flux_linkage]
    _, _, flux_linkage = femm.mo_getcircuitproperties(AC_CIRCUIT)
    femm.mo_close()

    L = flux_linkage / current_A
    return L


# ---------------------------------------------------------------------
# MAIN CO-SIMULATION
# ---------------------------------------------------------------------
def main():
    femm_init()

    # --- 1) Measure the unsaturated inductance L0 from FEMM itself ---
    L0 = femm_get_L(I_PROBE)
    print(f"Unsaturated inductance from FEMM: L0 = {L0*1e3:.4f} mH "
          f"(measured at {I_PROBE} A)")

    # --- 2) Fixed R -> time constant and sim span follow from it ---
    tau = L0 / R
    T_END = T_SPAN_TAU * tau
    dt = T_END / N_STEPS

    print(f"Fixed R = {R:.1f} ohm  (V = {V_SOURCE} V) -> tau = L0/R = {tau*1e6:.3f} us")
    print(f"Simulating t = 0 .. {T_END*1e6:.3f} us in {N_STEPS} steps (dt = {dt*1e9:.1f} ns)")

    # --- 3) Time-marching co-simulation: dI/dt = (V - I*R) / L_femm(I) ---
    t_arr   = np.linspace(0, T_END, N_STEPS + 1)
    I_femm  = np.zeros(N_STEPS + 1)
    L_femm  = np.zeros(N_STEPS + 1)
    L_femm[0] = L0   # L at I=0 is taken as the unsaturated value

    I_femm[0] = 0.0

    for n in range(N_STEPS):
        I_n = I_femm[n]

        # inductance at the *actual* operating point (tiny floor only
        # to guard against exact I=0 -> divide by zero)
        I_eval = I_n if I_n > FLOOR_I else FLOOR_I
        L_n = femm_get_L(I_eval)

        # predictor (explicit Euler)
        dIdt_n = (V_SOURCE - I_n * R) / L_n
        I_pred = I_n + dt * dIdt_n

        # corrector (Heun's method) using L at the predicted point
        I_eval_p = I_pred if I_pred > FLOOR_I else FLOOR_I
        L_pred = femm_get_L(I_eval_p)
        dIdt_p = (V_SOURCE - I_pred * R) / L_pred

        I_next = I_n + dt * 0.5 * (dIdt_n + dIdt_p)

        I_femm[n + 1] = I_next
        L_femm[n + 1] = L_pred

        print(f"  step {n+1:3d}/{N_STEPS}: t={t_arr[n+1]*1e3:7.3f} ms   "
              f"I={I_next:7.4f} A   L={L_pred*1e3:7.4f} mH")

    femm.closefemm()

    # --- 4) Analytical / equation solution using constant L0 ---
    I_eq    = (V_SOURCE / R) * (1 - np.exp(-t_arr / tau))
    L_eq    = np.full_like(t_arr, L0)

    # --- 5) Save results ---
    header = "t_s,I_femm_A,L_femm_H,I_equation_A,L_equation_H"
    data = np.column_stack([t_arr, I_femm, L_femm, I_eq, L_eq])
    np.savetxt(OUT_CSV, data, delimiter=",", header=header, comments="")
    print(f"\nSaved results to {OUT_CSV}")

    # --- 6) Plot: Current vs time ---
    plt.figure(figsize=(7, 5))
    plt.plot(t_arr * 1e3, I_femm, "-o", ms=3, label="FEMM co-simulation (nonlinear L)")
    plt.plot(t_arr * 1e3, I_eq, "--", label="Equation (constant L0, linear RL)")
    plt.xlabel("Time (ms)")
    plt.ylabel("Current (A)")
    plt.title("Series RL circuit — Current vs Time")
    plt.legend()
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    plt.savefig(OUT_PNG_I, dpi=150)

    # --- 7) Plot: Inductance vs time ---
    plt.figure(figsize=(7, 5))
    plt.plot(t_arr * 1e3, L_femm * 1e3, "-o", ms=3, label="FEMM L(I(t)) (nonlinear)")
    plt.plot(t_arr * 1e3, L_eq * 1e3, "--", label="Equation L0 (constant)")
    plt.xlabel("Time (ms)")
    plt.ylabel("Inductance (mH)")
    plt.title("Series RL circuit — Inductance vs Time")
    plt.legend()
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    plt.savefig(OUT_PNG_L, dpi=150)

    print(f"Saved plots to {OUT_PNG_I} and {OUT_PNG_L}")
    plt.show()


if __name__ == "__main__":
    main()