# 单篇 SRM 文献录入检查清单

本文档用于逐篇录入 SRM 文献时的核对。建议每完成一篇文献后都按本清单检查一次。

## 一、文献是否应纳入

- 这是否是一篇原始实验研究论文
- 研究对象是否明确属于甲烷蒸汽重整（SRM）
- 是否存在至少一个可提取的“催化剂-条件-结果”组合
- 是否不是仅从综述转引、而未回到原始数据来源

## 二、记录拆分是否正确

- 是否按不同催化剂拆成不同记录
- 是否按不同反应温度拆成不同记录
- 是否按不同 steam-to-carbon ratio 拆成不同记录
- 是否按不同空速拆成不同记录
- 是否按不同 time-on-stream 结果拆成不同记录
- 是否为同一测试条件相关记录填写了合理的 `condition_id`

## 三、文献与分组字段

- `record_id` 已填写且唯一
- `paper_id` 已填写
- `doi` 已填写或确认文献未提供
- `reference_type` 已填写
- `first_author` 已填写
- `publication_year` 已填写
- `journal` 已填写

## 四、催化剂身份字段

- `catalyst_label_reported` 已填写
- `catalyst_family` 已填写或可合理判断
- `active_metal_primary` 已填写
- `support_primary` 已填写
- 若为双金属体系，`active_metal_secondary` 已填写
- 若有主金属负载，`active_metal_primary_loading_wt_pct` 已填写
- 若有次金属负载，`active_metal_secondary_loading_wt_pct` 已填写
- 若有总负载，`active_metal_total_loading_wt_pct` 已填写
- `active_metal_loading_basis` 已标明 nominal / measured / unclear

## 五、制备与预处理字段

- `preparation_method` 已填写
- 若论文提供，`calcination_temperature_c` 已填写
- 若论文提供，`calcination_time_h` 已填写
- 若论文提供，`reduction_temperature_c` 已填写
- 若论文提供，`reduction_time_h` 已填写
- 若论文提供，`reduction_gas` 已填写
- 若存在关键工艺歧义，已写入 `preparation_details`

## 六、反应条件字段

- `reactor_type` 已填写
- `temperature_c` 已填写
- `pressure_bar` 已填写
- `steam_to_carbon_ratio` 已填写
- `gas_hourly_space_velocity_h_inv` 或 `weight_hourly_space_velocity_h_inv` 至少有一个已填写
- `time_on_stream_h` 已填写
- 若论文报告进料组成，相关 `feed_*` 字段已尽量填写
- 若进料未完全报告但平衡气体可判断，已填写 `balance_gas_identity`

## 七、核心结果字段

- 至少有一个核心输出已填写：
  - `methane_conversion_pct`
  - 或 `h2_yield_pct`
- 若论文报告，`h2_selectivity_pct` 已填写
- 若论文报告，`h2_production_rate_mmol_gcat_h` 或 `h2_production_rate_mmol_gmetal_h` 已填写
- 若论文报告，`co_selectivity_pct`、`co2_selectivity_pct`、`h2_co_ratio` 已填写
- `measured_value_basis` 已填写
- 若性能定义口径特殊，已写入 `performance_definition_notes`

## 八、稳定性与积碳字段

- `stability_test_performed` 已按论文内容填写
- 若有稳定性测试，`stability_duration_h` 已填写
- 若有明确退化端点，`conversion_drop_pct_points` 已填写
- 若有积碳评价方法，`coking_test_method` 已填写
- 若有定量积碳结果，`coke_amount_mg_gcat` 或 `coke_amount_wt_pct` 已填写
- 若有相关说明，`deactivation_mode_reported`、`sintering_evidence`、`characterization_summary` 已补充

## 九、质量控制字段

- 若数值来自图中读取，`digitized_from_plot` 已设为 `yes`
- 若是 peak / average / steady-state 等特殊口径，`measured_value_basis` 与原文一致
- `comparable_within_study` 已按文内可比性判断填写
- `analyst_qc_status` 已填写
- 所有歧义、换算假设、单位说明已写入 `extraction_notes`

## 十、必须避免的问题

- 没有凭空补任何实验数值
- 没有把不同条件下的数据混成同一行
- 没有把 nominal 和 measured loading 混写
- 没有把不同单位的积碳数据强行混成一个字段
- 没有把来源不清的推断写成实验测量值

## 十一、派生字段最终确认

以下字段在原始提取阶段必须为空：

- `derived_activity_score`
- `derived_stability_score`
- `derived_coking_resistance_score`
- `derived_overall_screening_score`

确认：

- 以上四个字段均为空
- 没有人工填写任何派生分数

## 十二、提交前最后一步

运行 validator：

```powershell
python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv
```

确认：

- 没有表头错误
- 没有字段类型错误
- 没有枚举值错误
- 没有派生字段被误填
