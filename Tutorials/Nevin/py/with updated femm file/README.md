Add FEMM sweep script for controlled inductor L-vs-IL/i_bias map

Sweeps AC winding current (IL) and DC bias current (i_bias) over a
FEMM magnetostatic model of a tapped inductor, computing incremental
inductance via centered finite difference (+-0.1A) at each grid point.
