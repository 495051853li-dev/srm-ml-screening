# Stage5 字段抽取 QC 报告

## 总览

- ready pool 记录数：`20`
- `pdf_fulltext` 记录数：`20`
- experimental-ready 记录数：`20`
- metadata 草稿记录数：`20`
- experimental 草稿记录数：`20`
- 合并 stage5 草稿记录数：`20`

## Metadata 抽取置信度

- `medium`: `15`
- `low_to_medium`: `5`

## Experimental 抽取置信度

- `low`: `14`
- `very_low`: `5`
- `low_to_medium`: `1`

## Metadata 字段覆盖率

- `catalyst_label_reported`: `100.0%`
- `catalyst_family`: `100.0%`
- `active_metal_primary`: `100.0%`
- `active_metal_secondary`: `100.0%`
- `active_metal_primary_loading_wt_pct`: `80.0%`
- `active_metal_secondary_loading_wt_pct`: `10.0%`
- `active_metal_total_loading_wt_pct`: `0.0%`
- `support_primary`: `100.0%`
- `support_secondary`: `95.0%`
- `promoter_1`: `55.0%`
- `promoter_1_loading_wt_pct`: `20.0%`
- `preparation_method`: `80.0%`
- `calcination_temperature_c`: `5.0%`
- `reduction_temperature_c`: `0.0%`
- `reduction_time_h`: `80.0%`
- `reduction_gas`: `5.0%`

## Experimental 字段覆盖率

- `reactor_type`: `45.0%`
- `temperature_c`: `10.0%`
- `pressure_bar`: `80.0%`
- `steam_to_carbon_ratio`: `40.0%`
- `feed_ch4_vol_pct`: `0.0%`
- `feed_h2o_vol_pct`: `0.0%`
- `feed_co2_vol_pct`: `0.0%`
- `feed_n2_vol_pct`: `0.0%`
- `gas_hourly_space_velocity_h_inv`: `25.0%`
- `weight_hourly_space_velocity_h_inv`: `10.0%`
- `contact_time_s`: `0.0%`
- `time_on_stream_h`: `10.0%`
- `methane_conversion_pct`: `25.0%`
- `h2_yield_pct`: `0.0%`
- `h2_selectivity_pct`: `0.0%`
- `co_selectivity_pct`: `0.0%`
- `h2_co_ratio`: `0.0%`
- `stability_test_performed`: `75.0%`
- `stability_duration_h`: `75.0%`
- `conversion_drop_pct_points`: `0.0%`
- `coking_test_method`: `90.0%`
- `coke_amount_mg_gcat`: `0.0%`
- `coke_amount_wt_pct`: `0.0%`
- `measured_value_basis`: `50.0%`

## 人工复核重点

- experimental 字段仍按保守规则抽取，所有记录默认 `manual_review_required=yes`。
- `pressure_bar`、`temperature_c`、`steam_to_carbon_ratio`、`GHSV/WHSV`、`conversion/yield/selectivity` 必须人工核对原文上下文，避免把表征条件、预处理条件或摘要描述误当作反应性能。
- 不同温度、S/C、压力和空速下的数据不可直接比较，后续冻结和建模前必须按工况分层或标准化。
- `derived_*` 字段保持为空，不能作为人工提取输入。

## 下一步建议

- 当前已有一批 PDF fulltext，可以进入人工抽样复核阶段；不建议直接建模。
