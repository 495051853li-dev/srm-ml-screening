# PDF 全文人工复核指南

## 复核目标

- 本指南面向当前 20 篇 `pdf_fulltext` 的 stage5 自动抽取草稿。
- 目标是确认催化剂组成、制备、反应条件、性能、稳定性和积碳字段是否可转入正式人工提取表。
- 当前阶段不开始机器学习，不把 `manual_review_required` 改为 `no`，也不填写任何 `derived_*` 字段。

## 建议优先复核顺序

| paper_id | 优先级 | 可否准备确认 | 题名 | 最优先核对字段 |
| --- | --- | --- | --- | --- |
| paper_0158 | high | yes | Differences in the Nature of Active Sites for Methane Dry Reforming and Methane Steam R... | h2_yield_pct, coke_amount_wt_pct |
| paper_0221 | high | yes | Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M... | gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0161 | high | yes | Kinetic assessment of Ni-based catalysts in low-temperature methane/biogas steam reforming | temperature_c, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0180 | high | yes | Hydrogen production by steam reforming of methane over nickel based structured catalyst... | temperature_c, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0208 | high | yes | Steam reforming of methane over nickel-aluminum spinel-derived catalyst | temperature_c, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0220 | high | yes | Structural Changes of Ni and Ni–Pt Methane Steam Reforming Catalysts During Activation,... | temperature_c, gas_hourly_space_velocity_h_inv, h2_yield_pct, coke_amount_wt_pct |
| paper_0150 | high | yes | Hydrogen production by steam reforming of methane over mixed Ni/MgAl + CrFe 3 O 4 catal... | temperature_c, steam_to_carbon_ratio, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0194 | high | yes | Ni-based bimetallic nano-catalysts anchored on BaZr<sub>0.4</sub>Ce<sub>0.4</sub>Y<sub>... | temperature_c, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct |
| paper_0101 | high | yes | Effect of nickel nano-particle sintering on methane reforming activity of Ni-CGO cermet... | active_metal_primary_loading_wt_pct, temperature_c, h2_yield_pct, coke_amount_wt_pct |
| paper_0166 | high | yes | Effect of Pt doping on activity and stability of Ni/MgAl2O4 catalyst for steam reformin... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0157 | medium | caution | Characterization and performance evaluation of Ni-based catalysts with Ce promoter for... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0159 | medium | caution | Effect of calcination temperature on stability and activity of Ni/MgAl2O4 catalyst for... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0199 | medium | caution | Hollow sphere Ni-based catalysts promoted with cerium for steam reforming of methane | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, h2_yield_pct, coke_amount_wt_pct |
| paper_0060 | medium | caution | Steam reforming of methane over unsupported nickel catalysts | preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, h2_yield_pct |
| paper_0153 | medium | caution | Recent Advances on the Design of Group VIII Base-Metal Catalysts with Encapsulated Stru... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0103 | medium_low | caution | H2 production by low pressure methane steam reforming in a Pd–Ag membrane reactor over... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0031 | medium_low | caution | Stoichiometric consideration of steam reforming of methane on Ni/Al2O3 catalyst at 650°... | temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct |
| paper_0037 | medium_low | caution | The kinetics of methane steam reforming over a Ni/α-Al2O catalyst | active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv |
| paper_0056 | medium_low | caution | Kinetic and modelling study of methane steam reforming over sulfide nickel catalyst on... | active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv |
| paper_0070 | medium_low | caution | Theoretical and experimental study of methane steam reforming reactions over nickel cat... | active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv |

## 每篇最优先核对的字段

- `paper_0158`：h2_yield_pct, coke_amount_wt_pct
- `paper_0221`：gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0161`：temperature_c, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0180`：temperature_c, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0208`：temperature_c, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0220`：temperature_c, gas_hourly_space_velocity_h_inv, h2_yield_pct, coke_amount_wt_pct
- `paper_0150`：temperature_c, steam_to_carbon_ratio, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0194`：temperature_c, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct, coke_amount_wt_pct
- `paper_0101`：active_metal_primary_loading_wt_pct, temperature_c, h2_yield_pct, coke_amount_wt_pct
- `paper_0166`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0157`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0159`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0199`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, h2_yield_pct, coke_amount_wt_pct
- `paper_0060`：preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, h2_yield_pct
- `paper_0153`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0103`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0031`：temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv, methane_conversion_pct, h2_yield_pct
- `paper_0037`：active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv
- `paper_0056`：active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv
- `paper_0070`：active_metal_primary_loading_wt_pct, preparation_method, temperature_c, steam_to_carbon_ratio, gas_hourly_space_velocity_h_inv

## 最容易定义混乱的字段

- `methane_conversion_pct`：必须确认是 CH4 转化率，不能把 H2 yield、carbon conversion 或 equilibrium conversion 当作转化率。
- `h2_yield_pct` 与 `h2_selectivity_pct`：必须确认作者定义，不能默认两者等价。
- `temperature_c`：必须确认是反应床层温度，不是焙烧、还原、蒸汽发生器或表征温度。
- `pressure_bar`：必须确认绝压/表压及单位换算；摘要中的 `1 atm`、`atmospheric pressure` 需要统一记录规则。
- `steam_to_carbon_ratio`：必须确认是 feed S/C，不是 H2O/CH4 分压比、进料摩尔比的中间计算值或讨论条件。
- `gas_hourly_space_velocity_h_inv` 与 `weight_hourly_space_velocity_h_inv`：必须确认 GHSV/WHSV 的定义、基准和单位，不能互换。
- `stability_duration_h` 与 `conversion_drop_pct_points`：必须一起解释，不能单独用 conversion drop 表示稳定性。
- `coke_amount_mg_gcat` 与 `coke_amount_wt_pct`：必须确认积碳测试方法、反应时长和归一化基准。

## 必须看原文单位和定义后才能确认的字段

- 反应条件：`temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`、`gas_hourly_space_velocity_h_inv`、`weight_hourly_space_velocity_h_inv`、`time_on_stream_h`。
- 性能标签候选：`methane_conversion_pct`、`h2_yield_pct`、`h2_selectivity_pct`、`h2_co_ratio`、`stability_duration_h`、`conversion_drop_pct_points`。
- 抗积碳相关：`coking_test_method`、`coke_amount_mg_gcat`、`coke_amount_wt_pct`。
- 组成相关：`active_metal_primary_loading_wt_pct`、`promoter_1_loading_wt_pct`，尤其要区分 nominal loading、ICP/EDS measured loading 和配方投料量。

## 暂时不适合转入正式表的记录

- `paper_0157`：`caution`；原因是缺失字段包括 `` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0159`：`caution`；原因是缺失字段包括 `` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0199`：`caution`；原因是缺失字段包括 `` / `temperature_c; pressure_bar; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_o...`。
- `paper_0060`：`caution`；原因是缺失字段包括 `promoter_1; preparation_method` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; h2...`。
- `paper_0153`：`caution`；原因是缺失字段包括 `promoter_1` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0103`：`caution`；原因是缺失字段包括 `` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0031`：`caution`；原因是缺失字段包括 `promoter_1` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0037`：`caution`；原因是缺失字段包括 `active_metal_primary_loading_wt_pct; promoter_1; preparation_method` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0056`：`caution`；原因是缺失字段包括 `active_metal_primary_loading_wt_pct; promoter_1; preparation_method` / `temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_on_stream_h; me...`。
- `paper_0070`：`caution`；原因是缺失字段包括 `active_metal_primary_loading_wt_pct; promoter_1; preparation_method` / `temperature_c; pressure_bar; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; weight_hourly_space_velocity_h_inv; time_o...`。

## 如何从 review pack 转入正式人工提取表

1. 先打开 `data/processed/pdf_fulltext_review_pack.csv`，按 `review_priority` 从 high 到 low 复核。
2. 对每篇论文，优先核对 `key_source_excerpt` 指向的 PDF 文本位置；证据不足时回到原 PDF 查看表格、图注和实验部分。
3. 只有当催化剂组成、关键工况和至少一个明确性能标签候选被人工确认后，才手动转入正式人工提取表。
4. 对无法确认单位、定义或数据来源的字段保持空白，并在正式表的 `extraction_notes` 或 `performance_definition_notes` 中说明。
5. `derived_activity_score`、`derived_stability_score`、`derived_coking_resistance_score`、`derived_overall_screening_score` 必须保持为空，不能人工填写。
6. 不同温度、S/C、压力和空速下的数据不要直接比较；正式入表时应保留原始工况，后续分析再分层或标准化。

## Stage5 QC 引用说明

- 已读取 `docs/stage5_extraction_qc_report.md` 作为背景；本复核包以最新 CSV 重新计算优先级和覆盖率。
