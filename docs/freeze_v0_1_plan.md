# Freeze Dataset v0.1 Plan

## 当前为什么还不能机器学习

- 当前 stage5 输出仍是自动抽取草稿，所有实验字段都需要人工确认。
- 只有 20 篇 PDF fulltext，样本量太小，且不同温度、S/C、压力、GHSV、time-on-stream 下的性能不可直接比较。
- `methane_conversion_pct`、`h2_yield_pct`、选择性、稳定性和积碳字段的定义在不同论文中可能不同，直接混用会造成标签噪声。
- `journal_impact_factor`、`review_priority`、`source_quality`、`manual_review_status`、`derived_*` 等字段存在文献来源偏差或数据泄漏风险，不能默认入模。

## Freeze v0.1 最低纳入标准

记录进入 `freeze_candidate_v0_1.csv` 必须至少满足：

- `active_metal_primary` 非空。
- `support_primary` 非空。
- 有 `temperature_c`，或 PDF 证据中明确出现反应温度。
- 有 `steam_to_carbon_ratio`，或 PDF 证据中明确出现 feed H2O/CH4、S/C、steam-to-carbon 信息。
- 有 `methane_conversion_pct` 或 `h2_yield_pct` 作为标签候选。

这些标准只表示“值得人工确认”，不表示已经冻结。

## 本轮拆分结果

- `freeze_candidate_v0_1.csv`：`4` 条。
- `freeze_excluded_needs_review_v0_1.csv`：`16` 条。
- 最常见 blocking 字段：
- `methane_conversion_pct_or_h2_yield_pct`：`15` 条。
- `steam_to_carbon_ratio_or_feed_h2o_ch4_evidence`：`8` 条。
- `temperature_c_or_reaction_temperature_evidence`：`8` 条。

## 必须人工确认的字段

- 催化剂：`active_metal_primary`、`active_metal_secondary`、`active_metal_primary_loading_wt_pct`、`support_primary`、`promoter_1`、`preparation_method`。
- 工况：`temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`、`gas_hourly_space_velocity_h_inv`、`weight_hourly_space_velocity_h_inv`、`time_on_stream_h`。
- 性能：`methane_conversion_pct`、`h2_yield_pct`、`h2_selectivity_pct`、`h2_co_ratio`。
- 稳定性和积碳：`stability_duration_h`、`conversion_drop_pct_points`、`coke_amount_mg_gcat`、`coke_amount_wt_pct`。

## 第一版主标签建议

- 第一版最建议使用 `methane_conversion_pct` 作为主标签候选。
- 原因是它在当前草稿中比 `h2_yield_pct` 覆盖更好，且通常更直接对应 SRM 活性。
- `h2_yield_pct` 可以作为 fallback 或辅助分析字段，但不建议和 `methane_conversion_pct` 在第一版起步时同时作为主标签。
- `conversion_drop_pct_points` 必须结合 `stability_duration_h` 才能解释，后续可由脚本派生标准化退化速率，但原始提取阶段不新增人工派生字段。

## 为什么需要工况分层

- SRM 性能强烈依赖反应温度、S/C、压力、GHSV/WHSV、催化剂量和 time-on-stream。
- 不同工况下的 conversion 或 yield 不可直接作为同一标签比较。
- Freeze v0.1 应优先保留原始工况，后续探索时按相近工况分层，或只在条件足够接近的子集中比较。

## 默认不能作为 ML 输入的字段

- `journal_impact_factor`、`journal_quartile`、`journal_metrics_source`：只能用于文献筛选、偏差分析或敏感性分析。
- `derived_*`：必须留空，不能人工填写，属于高泄漏风险字段。
- `review_priority`、`source_quality_type`、`source_quality_score`、`manual_review_required`、`freeze_candidate_status`：只能用于流程控制和 QC，不能作为模型特征。
- `source_excerpt_*`、`reviewer_notes`、`evidence_summary`：只能作为审计证据或备注。

## 什么时候可以开始探索性分析

- 建议至少完成 `20-30` 条人工确认记录后，再做探索性统计。
- 探索性分析应限于字段覆盖率、催化剂族分布、工况分布、标签候选分布和缺失模式。
- 如果本轮候选不足 20 条，应先补 PDF 或人工复核 excluded 记录。

## 什么时候可以开始初步 baseline ML

- 建议至少积累 `100-200` 条人工确认的 condition-performance 记录后，再尝试非常保守的 baseline。
- 更稳妥的目标是 `300+` 条已确认且可分层的记录，尤其是 Ni-based、相近工况、同一主标签的子集。
- baseline ML 前必须先冻结数据版本、定义标签、划分训练/验证策略，并明确数据泄漏控制。

## 人工复核优先顺序

- `paper_0060`：优先确认 `active_metal_primary; support_primary; active_metal_primary_loading_wt_pct; temperature_c; pressure_bar; steam_to_carbon_ratio; methane_conversion_pct; stability_duration_h`。
- `paper_0101`：优先确认 `active_metal_primary; support_primary; preparation_method; temperature_c; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; methane_conversion_pct; stability_duration_h`。
- `paper_0158`：优先确认 `active_metal_primary; support_primary; active_metal_primary_loading_wt_pct; preparation_method; temperature_c; pressure_bar; steam_to_carbon_ratio; gas_hourly_space_velocity_h_inv; methane_conversion_pct; stability_duration_h`。
- `paper_0220`：优先确认 `active_metal_primary; support_primary; active_metal_primary_loading_wt_pct; preparation_method; temperature_c; steam_to_carbon_ratio; weight_hourly_space_velocity_h_inv; methane_conversion_pct; stability_duration_h`。
