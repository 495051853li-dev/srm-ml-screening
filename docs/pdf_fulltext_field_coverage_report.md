# PDF 全文字段覆盖率报告

## 数据范围

- PDF fulltext stage5 合并草稿记录数：`20`
- metadata 抽取草稿记录数：`20`
- experimental 抽取草稿记录数：`20`
- 覆盖率仅表示字段非空，不代表已经人工确认正确。

## Metadata 字段覆盖率

| 字段 | 非空数 | 覆盖率 |
| --- | --- | --- |
| catalyst_label_reported | 20 | 100.0% |
| catalyst_family | 20 | 100.0% |
| active_metal_primary | 20 | 100.0% |
| active_metal_secondary | 20 | 100.0% |
| active_metal_primary_loading_wt_pct | 16 | 80.0% |
| active_metal_secondary_loading_wt_pct | 2 | 10.0% |
| active_metal_total_loading_wt_pct | 0 | 0.0% |
| support_primary | 20 | 100.0% |
| support_secondary | 19 | 95.0% |
| promoter_1 | 11 | 55.0% |
| promoter_1_loading_wt_pct | 4 | 20.0% |
| preparation_method | 16 | 80.0% |
| calcination_temperature_c | 1 | 5.0% |
| reduction_temperature_c | 0 | 0.0% |
| reduction_time_h | 16 | 80.0% |
| reduction_gas | 1 | 5.0% |

## Experimental 字段覆盖率

| 字段 | 非空数 | 覆盖率 |
| --- | --- | --- |
| reactor_type | 9 | 45.0% |
| temperature_c | 2 | 10.0% |
| pressure_bar | 16 | 80.0% |
| steam_to_carbon_ratio | 8 | 40.0% |
| feed_ch4_vol_pct | 0 | 0.0% |
| feed_h2o_vol_pct | 0 | 0.0% |
| feed_co2_vol_pct | 0 | 0.0% |
| feed_n2_vol_pct | 0 | 0.0% |
| gas_hourly_space_velocity_h_inv | 5 | 25.0% |
| weight_hourly_space_velocity_h_inv | 2 | 10.0% |
| contact_time_s | 0 | 0.0% |
| time_on_stream_h | 2 | 10.0% |
| methane_conversion_pct | 5 | 25.0% |
| h2_yield_pct | 0 | 0.0% |
| h2_selectivity_pct | 0 | 0.0% |
| co_selectivity_pct | 0 | 0.0% |
| h2_co_ratio | 0 | 0.0% |
| stability_test_performed | 15 | 75.0% |
| stability_duration_h | 15 | 75.0% |
| conversion_drop_pct_points | 0 | 0.0% |
| coking_test_method | 18 | 90.0% |
| coke_amount_mg_gcat | 0 | 0.0% |
| coke_amount_wt_pct | 0 | 0.0% |
| measured_value_basis | 10 | 50.0% |

## 催化剂组成字段覆盖情况

| 字段 | 非空数 | 覆盖率 |
| --- | --- | --- |
| active_metal_primary | 20 | 100.0% |
| active_metal_secondary | 20 | 100.0% |
| active_metal_primary_loading_wt_pct | 16 | 80.0% |
| support_primary | 20 | 100.0% |
| promoter_1 | 11 | 55.0% |
| preparation_method | 16 | 80.0% |

## 反应条件字段覆盖情况

| 字段 | 非空数 | 覆盖率 |
| --- | --- | --- |
| temperature_c | 2 | 10.0% |
| pressure_bar | 16 | 80.0% |
| steam_to_carbon_ratio | 8 | 40.0% |
| gas_hourly_space_velocity_h_inv | 5 | 25.0% |
| weight_hourly_space_velocity_h_inv | 2 | 10.0% |
| time_on_stream_h | 2 | 10.0% |

## 性能与稳定性字段覆盖情况

| 字段 | 非空数 | 覆盖率 |
| --- | --- | --- |
| methane_conversion_pct | 5 | 25.0% |
| h2_yield_pct | 0 | 0.0% |
| h2_selectivity_pct | 0 | 0.0% |
| h2_co_ratio | 0 | 0.0% |
| stability_duration_h | 15 | 75.0% |
| conversion_drop_pct_points | 0 | 0.0% |
| coke_amount_mg_gcat | 0 | 0.0% |
| coke_amount_wt_pct | 0 | 0.0% |

## 当前最缺失的字段

- `coke_amount_mg_gcat`：非空 `0/20`，覆盖率 `0.0%`
- `coke_amount_wt_pct`：非空 `0/20`，覆盖率 `0.0%`
- `conversion_drop_pct_points`：非空 `0/20`，覆盖率 `0.0%`
- `h2_co_ratio`：非空 `0/20`，覆盖率 `0.0%`
- `h2_selectivity_pct`：非空 `0/20`，覆盖率 `0.0%`
- `h2_yield_pct`：非空 `0/20`，覆盖率 `0.0%`
- `temperature_c`：非空 `2/20`，覆盖率 `10.0%`
- `time_on_stream_h`：非空 `2/20`，覆盖率 `10.0%`
- `weight_hourly_space_velocity_h_inv`：非空 `2/20`，覆盖率 `10.0%`
- `gas_hourly_space_velocity_h_inv`：非空 `5/20`，覆盖率 `25.0%`
- `methane_conversion_pct`：非空 `5/20`，覆盖率 `25.0%`
- `steam_to_carbon_ratio`：非空 `8/20`，覆盖率 `40.0%`

## 是否达到探索性分析门槛

- 结论：可以进入非常有限的人工复核后探索性统计，例如字段缺失模式、催化剂族分布、可用标签候选分布。
- 限制：这些记录仍未完成单位和定义确认，不应直接比较不同工况下的性能。

## 是否达到初步机器学习门槛

- 结论：未达到。当前只有 20 篇 PDF fulltext，experimental 字段置信度整体偏低，且多数性能、选择性、积碳字段覆盖不足。
- 风险：如果直接建模，模型很可能学习到文献来源、测试条件或抽取噪声，而不是催化剂本征规律，存在明显数据泄漏和工况混杂风险。
- 建议：先把 review pack 中 high/medium 记录人工确认，再扩充 PDF fulltext 数量，并建立按温度、S/C、压力、GHSV 分层的分析策略。
