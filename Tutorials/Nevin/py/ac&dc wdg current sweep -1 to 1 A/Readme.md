That's the only real change. Original:

```python
Iac_wdg_list = np.concatenate(([0.05], np.round(np.arange(0.2, 10.0 + 1e-9, 0.2), 2)))
```
→ one-sided, 0.05 A then 0.2 A steps up to 10 A.

New:
```python
_pos_half    = np.concatenate(([0.05], np.round(np.arange(0.2, 1.0 + 1e-9, 0.2), 2)))
_neg_half    = -_pos_half[::-1]
Iac_wdg_list = np.concatenate((_neg_half, _pos_half))
```
→ builds the positive half (0.05, then 0.2 A steps up to 1 A), mirrors it negative, and concatenates: `[-1, -0.8, -0.6, -0.4, -0.2, -0.05, 0.05, 0.2, 0.4, 0.6, 0.8, 1]`.

Everything downstream (the print statement's format width `%6.2f` instead of `%5.2f` to fit the minus sign) is the only other cosmetic tweak — the FEMM solve loop, CSV writing, snake ordering, and plotting logic are byte-for-byte identical.
