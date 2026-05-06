# Manual PDF Review Summary v0.1

## Scope

- This document records manual PDF review decisions for the current freeze v0.1 candidate layer.
- No formal master extraction table was modified.
- No machine learning was started.
- All `derived_*` fields remain blank.

## Updated candidate statuses

| paper_id | status | catalyst/support correction | transfer strategy |
| --- | --- | --- | --- |
| `paper_0060` | `ready_for_manual_transfer_after_check` | unsupported pure Ni / Inco Ni 255 / support=unsupported | one main activity/stability record plus separate coke/Table 2 note or separate coking record if confirmed. |
| `paper_0101` | `ready_for_manual_transfer_after_check` | Ni-CGO / NiO-CGO / support=CGO | split into at least three formal records before transfer. |
| `paper_0158` | `ready_for_manual_transfer_after_check` | nickel aluminate SRM catalyst set; split required: NiAl2O4-R; Ni2Al2O5-R; Ni2Al2O5-NR; commercial 50 wt% Ni/alpha-Al2O3-NR / support=nickel_aluminate_or_alpha-Al2O3_record_specific | split into catalyst-specific records, including NiAl2O4-R, Ni2Al2O5-R, Ni2Al2O5-NR, commercial 50 wt% Ni/alpha-Al2O3-NR. |
| `paper_0220` | `mechanistic_reference_not_for_baseline_ml` | 15 wt% Ni-1 wt% Pt/MgAlOx and 15 wt% Ni/MgAlOx under operando/dynamic reaction conditions / support=MgAlOx | do not transfer to baseline ML table; optionally keep in mechanistic/descriptor reference subset. |

## Paper-specific review notes

### paper_0060

- Status: `ready_for_manual_transfer_after_check`.
- Catalyst corrected to unsupported pure Ni / Inco Ni 255.
- `support_primary` corrected to `unsupported`; `active_metal_secondary` cleared.
- Suggested main record: 700 C, CH4:H2O=1:2, P=1 atm, GHSV=8500 h^-1, time-on-stream=100 h, methane conversion=98 +/- 2%.
- Coke data must reference Table 2 conditions separately and must not be mixed with the 100 h stability record.

### paper_0101

- Status: `ready_for_manual_transfer_after_check`.
- Catalyst corrected to Ni-CGO / NiO-CGO; support corrected to CGO / Ce0.9Gd0.1O1.95.
- Preparation method corrected to `glycine-nitrate-process`.
- Ni loading should be recorded as 40 vol.% Ni and must not be forced into wt%.
- Suggested formal transfer requires split records: baseline activity, S/C=1.5 stability, S/C=0.5 stability.
- GHSV/WHSV must preserve `7.5 x 10^4 ml/(g-cat h)`; do not write it as `7.5 h^-1`.

### paper_0158

- Status: `ready_for_manual_transfer_after_check`.
- Prior uncertainty/exclusion corrected; use SRM conditions only.
- Delete auto-extracted `temperature=300`, `pressure=8`, and `GHSV=52400` if they came from TEM/XPS/DRM contexts.
- SRM general conditions: 700 C, S/C=2.4, GHSV=65500 h^-1 dry basis, 12 h.
- Formal transfer should split catalyst-specific records such as NiAl2O4-R, Ni2Al2O5-R, Ni2Al2O5-NR, and commercial 50 wt% Ni/alpha-Al2O3-NR.
- Table 4 methane conversion is 6 h on-stream data; final conversion and coke data should be notes or separate stability/coking fields.

### paper_0220

- Status: `mechanistic_reference_not_for_baseline_ml`.
- `active_metal_secondary` corrected to Pt; support corrected to MgAlOx.
- Loading corrected to 15 wt% Ni and 1 wt% Pt.
- Not recommended as an ordinary steady-state `methane_conversion_pct` baseline ML training record.
- Keep as operando/dynamic reaction condition reference for later structure-performance descriptor analysis.

## ML boundary

- These reviewed rows are still not a machine-learning dataset.
- Records with split requirements must be manually expanded in the formal table after checking original PDF context.
- `journal_impact_factor`, review status fields, source quality fields, and `derived_*` must not be used as default ML inputs.
- Different temperature, S/C, pressure, GHSV/WHSV, and time-on-stream conditions must be stratified or normalized before analysis.
