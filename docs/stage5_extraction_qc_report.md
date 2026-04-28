# Stage5 抽取质控报告

## 总览

- ready pool 原始数量：`14`
- 通过二次检查数量：`1`
- metadata-ready 数量：`1`
- experimental-ready 数量：`0`
- 合并后的 stage5 草稿记录数：`1`

## Metadata 字段覆盖率

- `catalyst_label_reported`: 100.0%
- `catalyst_family`: 100.0%
- `active_metal_primary`: 100.0%
- `active_metal_secondary`: 100.0%
- `active_metal_primary_loading_wt_pct`: 0.0%
- `active_metal_secondary_loading_wt_pct`: 0.0%
- `active_metal_total_loading_wt_pct`: 0.0%
- `support_primary`: 100.0%
- `support_secondary`: 0.0%
- `promoter_1`: 0.0%
- `promoter_1_loading_wt_pct`: 0.0%
- `preparation_method`: 0.0%
- `calcination_temperature_c`: 0.0%
- `reduction_temperature_c`: 0.0%
- `reduction_time_h`: 0.0%
- `reduction_gas`: 0.0%

最容易抽取的 metadata 字段：
- `catalyst_label_reported`: 100.0%
- `catalyst_family`: 100.0%
- `active_metal_primary`: 100.0%
- `active_metal_secondary`: 100.0%
- `support_primary`: 100.0%

最难抽取的 metadata 字段：
- `active_metal_primary_loading_wt_pct`: 0.0%
- `active_metal_secondary_loading_wt_pct`: 0.0%
- `active_metal_total_loading_wt_pct`: 0.0%
- `support_secondary`: 0.0%
- `promoter_1`: 0.0%

## Experimental 字段覆盖率

- `reactor_type`: 0.0%
- `temperature_c`: 0.0%
- `pressure_bar`: 0.0%
- `steam_to_carbon_ratio`: 0.0%
- `feed_ch4_vol_pct`: 0.0%
- `feed_h2o_vol_pct`: 0.0%
- `feed_co2_vol_pct`: 0.0%
- `feed_n2_vol_pct`: 0.0%
- `gas_hourly_space_velocity_h_inv`: 0.0%
- `weight_hourly_space_velocity_h_inv`: 0.0%
- `contact_time_s`: 0.0%
- `time_on_stream_h`: 0.0%
- `methane_conversion_pct`: 0.0%
- `h2_yield_pct`: 0.0%
- `h2_selectivity_pct`: 0.0%
- `co_selectivity_pct`: 0.0%
- `h2_co_ratio`: 0.0%
- `stability_test_performed`: 0.0%
- `stability_duration_h`: 0.0%
- `conversion_drop_pct_points`: 0.0%
- `coking_test_method`: 0.0%
- `coke_amount_mg_gcat`: 0.0%
- `coke_amount_wt_pct`: 0.0%
- `measured_value_basis`: 0.0%

最容易抽取的 experimental 字段：
- `reactor_type`: 0.0%
- `temperature_c`: 0.0%
- `pressure_bar`: 0.0%
- `steam_to_carbon_ratio`: 0.0%
- `feed_ch4_vol_pct`: 0.0%

最难抽取的 experimental 字段：
- `reactor_type`: 0.0%
- `temperature_c`: 0.0%
- `pressure_bar`: 0.0%
- `steam_to_carbon_ratio`: 0.0%
- `feed_ch4_vol_pct`: 0.0%

## 重点人工复核记录

- `paper_0221`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0194`: `page_quality_label=metadata_only`; `not_ready_reason=contains_gate_marker_but_text_is_still_usable`
- `paper_0101`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0166`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0159`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0180`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0150`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0157`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0124`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0191`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0202`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0193`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0099`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`
- `paper_0007`: `page_quality_label=not_usable`; `not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`

## paper_0221 判定

- paper_0221 当前 `ready_for_extraction_checked=no`，`page_quality_label=not_usable`，`not_ready_reason=redirect_or_shell_page;weak_domain_signal;weak_experimental_signal`。
- 如果仍然只是 Redirecting 或仅有极弱页面文本，则不建议继续作为当前抽取池输入。

## 是否适合扩大到 top 50 / top 100

- 当前**不建议**直接扩大到 top 50 或 top 100。
- 主要原因是 stage4 当前保留下来的可用正文/摘要页仍然很少，experimental 抽取覆盖率过低。
- 更合理的下一步是继续提升来源质量，或为摘要页与正文页分别设计更清晰的抽取策略。
