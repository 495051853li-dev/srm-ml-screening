# 第一批 SRM 文献录入计划

本文档用于指导当前仓库进入“第一批文献录入准备”阶段。目标不是一次性录入尽可能多的文章，而是先形成一批口径尽量一致、字段解释清楚、便于后续审计的数据。

前提说明：

- 当前模板、data dictionary、validator、README 和 `ml_field_roles.md` 视为已冻结的第一版录入基础设施。
- 本阶段只做文献筛选、人工提取和数据审计准备，不开始建模。
- 不修改已冻结的表头结构。

## 第一批建议优先录入哪类 SRM 文章

建议优先录入以下类型的文章：

- 明确研究对象为甲烷蒸汽重整（SRM）的原始实验研究论文
- 以 `Ni_based` 催化剂为主的文章
- 反应器类型相对常见且定义明确的文章：
  - `fixed_bed`
  - `packed_bed`
- 反应条件报告相对完整的文章：
  - 明确给出 `temperature_c`
  - 明确给出 `steam_to_carbon_ratio`
  - 明确给出 `pressure_bar`
  - 明确给出 `gas_hourly_space_velocity_h_inv` 或 `weight_hourly_space_velocity_h_inv`
  - 明确给出 `time_on_stream_h`
- 催化剂信息相对完整的文章：
  - 主活性金属清楚
  - 载体清楚
  - 至少一个活性金属负载字段可填
  - 制备方法有明确描述
- 至少报告一个核心性能指标的文章：
  - `methane_conversion_pct`
  - 或 `h2_yield_pct`
- 最好同时有稳定性或积碳信息的文章：
  - `stability_duration_h`
  - `conversion_drop_pct_points`
  - `coke_amount_mg_gcat`
  - `coke_amount_wt_pct`

建议暂时后置的文章：

- 仅综述转述、未回到原始实验数据的文献
- SRM 边界不清的文章，例如与 dry reforming、autothermal reforming 严重混杂且条件解释不清
- 只给定性结论、不提供核心数值的文章
- 反应条件缺失严重、无法判断可比性的文章
- 极端特殊的反应器或高度定制化测试协议文章

## 建议先录入多少篇

建议第一批先录入 **15 到 25 篇**。

更具体建议：

- 如果主要目的是验证录入流程和字段解释：先录入 `10` 篇
- 如果希望形成一批可用于第一轮清洗和审计的数据底稿：优先目标是 `20` 篇左右
- 不建议第一轮直接超过 `30` 篇

原因：

- 录到 15 到 25 篇时，通常已经足够暴露字段定义歧义、缺失模式和跨文献口径冲突
- 这时再修订 SOP、补充说明或完善审计规则，返工成本最低
- 如果一开始录得太多，后续一旦发现字段解释需要调整，返工会放大

## 为什么优先选择 Ni-based、条件相对接近、数据字段较完整的文章

### 为什么优先选择 Ni-based

- `Ni_based` 是 SRM 文献中最常见、最具代表性的催化剂大类之一
- 第一批先集中在同一大类，有利于减少组成空间过宽带来的异质性
- 有助于先建立一套围绕 Ni 基体系的标准化命名、负载量解释和支持体处理逻辑
- 后续如果扩展到 noble metal、perovskite-derived 等体系，也更容易比较边界

### 为什么优先选择条件相对接近的文章

- SRM 性能强烈依赖 `temperature_c`、`steam_to_carbon_ratio`、`pressure_bar`、`GHSV/WHSV` 和 `time_on_stream_h`
- 条件越接近，第一批数据越容易进行人工比较、异常值检查和标签解释
- 这能降低把条件差异误判为催化剂本征差异的风险
- 也有利于后续定义“第一版可比较子集”

### 为什么优先选择数据字段较完整的文章

- 第一批录入的目标是建立高质量模板使用习惯，而不是追求数量
- 字段较完整的文章更适合测试模板是否真正可用
- 这类文章更容易支持第一轮 dataset audit，包括缺失统计、一致性检查和标签分布预审

## 哪些字段必须优先保证完整

下面这些字段建议作为第一批录入时的优先完整字段。

### 追溯与分组

- `record_id`
- `paper_id`
- `doi`
- `condition_id`

### 催化剂身份

- `catalyst_label_reported`
- `catalyst_family`
- `active_metal_primary`
- `support_primary`

### 活性金属负载

- `active_metal_primary_loading_wt_pct`
- `active_metal_total_loading_wt_pct`
- `active_metal_loading_basis`

补充说明：

- 如果是双金属体系，优先补全 `active_metal_secondary` 和 `active_metal_secondary_loading_wt_pct`
- 历史兼容字段 `active_metal_loading_wt_pct` 可填，但不应替代更细化字段的优先地位

### 制备与预处理

- `preparation_method`
- `calcination_temperature_c`
- `reduction_temperature_c`

### 关键反应条件

- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `gas_hourly_space_velocity_h_inv` 或 `weight_hourly_space_velocity_h_inv`
- `time_on_stream_h`
- `reactor_type`

### 核心结果与解释

- `methane_conversion_pct` 或 `h2_yield_pct`
- `measured_value_basis`
- `digitized_from_plot`
- `performance_definition_notes`（若定义有特殊口径）

### QC 与可比性

- `comparable_within_study`
- `extraction_notes`

## 哪些字段可以暂时允许缺失

以下字段在第一批录入中可以允许缺失，不应为了补齐而猜测填写。

### 文献元数据

- `journal_impact_factor_year`
- `journal_impact_factor`
- `journal_quartile`
- `journal_metrics_source`
- `journal_metrics_notes`

### 组成与前驱体细节

- `active_metal_atomic_ratio_reported`
- `promoter_2`
- `promoter_2_loading_wt_pct`
- `support_secondary`
- `support_notes`
- `precursor_metal_source`
- `precursor_support_source`

### 制备细节

- `preparation_details`
- `calcination_time_h`
- `reduction_time_h`
- `reduction_gas`

### 进料细节

- `feed_ch4_vol_pct`
- `feed_h2o_vol_pct`
- `feed_co2_vol_pct`
- `feed_n2_vol_pct`
- `feed_h2_vol_pct`
- `balance_gas_identity`
- `contact_time_s`

### 扩展性能与稳定性字段

- `h2_selectivity_pct`
- `h2_production_rate_mmol_gcat_h`
- `h2_production_rate_mmol_gmetal_h`
- `co_selectivity_pct`
- `co2_selectivity_pct`
- `h2_co_ratio`
- `stability_duration_h`
- `conversion_drop_pct_points`
- `coking_test_method`
- `coke_amount_mg_gcat`
- `coke_amount_wt_pct`
- `carbon_balance_closure_pct`
- `sintering_evidence`
- `sulfur_tolerance_tested`
- `deactivation_mode_reported`
- `characterization_summary`

### 必须保持为空的字段

以下字段不是“允许缺失”，而是“原始提取阶段必须为空”：

- `derived_activity_score`
- `derived_stability_score`
- `derived_coking_resistance_score`
- `derived_overall_screening_score`

## 单篇文献录入检查清单

建议逐篇录入时至少执行以下检查。

### A. 文献纳入判断

- 是否为原始实验研究论文
- 是否明确属于 SRM 而非边界不清的混合重整
- 是否至少包含一个可拆分的“催化剂-条件-结果”记录

### B. 行级拆分

- 是否按不同温度拆分成不同记录
- 是否按不同 S/C 拆分成不同记录
- 是否按不同空速拆分成不同记录
- 是否为同一条件下的多条记录设置合理的 `condition_id`

### C. 催化剂身份

- `catalyst_label_reported` 是否已记录
- `active_metal_primary` 是否明确
- `support_primary` 是否明确
- 若为双金属，是否记录 `active_metal_secondary`
- 负载量是否明确区分 nominal / measured / unclear

### D. 条件完整性

- `temperature_c` 是否已记录
- `steam_to_carbon_ratio` 是否已记录
- `pressure_bar` 是否已记录
- `gas_hourly_space_velocity_h_inv` 或 `weight_hourly_space_velocity_h_inv` 是否已记录
- `time_on_stream_h` 是否已记录

### E. 性能与口径

- 是否至少记录一个核心输出：
  - `methane_conversion_pct`
  - 或 `h2_yield_pct`
- `measured_value_basis` 是否已填写
- 若性能定义有特殊口径，是否已写入 `performance_definition_notes`
- 若数值来自图中读取，是否已标记 `digitized_from_plot = yes`

### F. 稳定性与积碳

- `stability_test_performed` 是否与论文一致
- 若有稳定性测试，是否填写 `stability_duration_h`
- 若填写 `conversion_drop_pct_points`，是否基于明确端点而非主观猜测
- 若填写积碳量，是否确认单位和归一化口径

### G. 质控与留痕

- `record_id` 是否唯一
- `paper_id` 是否与同篇其他记录一致
- `condition_id` 是否与同条件其他记录一致
- 是否不存在猜测填写
- 是否已将歧义写入 `extraction_notes`
- 是否确认所有 `derived_*` 字段仍为空

## 录入完成后如何做第一轮 dataset audit

第一轮 dataset audit 的目标是：在不开始建模的前提下，确认第一批数据是否具备进入“清洗与可比性审查”阶段的基础。

### 1. 先跑 validator

执行：

```powershell
python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv
```

确认：

- 无字段缺失或多余字段
- 无非法枚举值
- 无明显数值格式错误
- 所有 `derived_*` 字段仍为空

### 2. 做字段完整率检查

重点统计以下字段的非空率：

- `active_metal_primary`
- `support_primary`
- `active_metal_primary_loading_wt_pct`
- `preparation_method`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `gas_hourly_space_velocity_h_inv`
- `time_on_stream_h`
- `methane_conversion_pct`
- `h2_yield_pct`
- `measured_value_basis`

目标不是 100%，而是尽快识别：

- 哪些字段定义太理想化
- 哪些字段在真实文献中长期缺失
- 哪些字段需要在 SOP 中进一步说明

### 3. 做论文级和条件级去重检查

检查：

- `record_id` 是否唯一
- 同一 `paper_id` 下是否存在可疑重复记录
- 同一 `condition_id` 下是否出现应合并但未合并的重复行

### 4. 做可比性初筛

按以下字段观察分布：

- `temperature_c`
- `steam_to_carbon_ratio`
- `pressure_bar`
- `gas_hourly_space_velocity_h_inv`
- `time_on_stream_h`
- `reactor_type`

目标：

- 判断第一批是否已经形成一组“条件相对接近”的样本
- 识别是否混入了条件完全不同、应单独分层处理的文章

### 5. 做标签可用性初筛

检查以下字段的覆盖情况：

- `methane_conversion_pct`
- `h2_yield_pct`
- `conversion_drop_pct_points`
- `coke_amount_mg_gcat`
- `coke_amount_wt_pct`

判断：

- 第一版活性标签更适合从 `methane_conversion_pct` 还是 `h2_yield_pct` 起步
- 稳定性和积碳字段是否足以支持后续单独子任务

### 6. 做质量分层标记复查

重点复查：

- `digitized_from_plot`
- `measured_value_basis`
- `comparable_within_study`
- `analyst_qc_status`

目标：

- 形成“高可信子集”和“需谨慎解释子集”的初步边界

## 本阶段产出目标

如果第一批录入顺利，本阶段结束时应至少获得：

- 一批结构一致、可追溯的 SRM 原始提取记录
- 一份清楚的第一轮缺失情况判断
- 一份初步的可比性判断
- 一份需要补充说明或后续修订的字段问题清单

这一步仍然属于“数据准备与提取规范建设”阶段，不进入建模阶段。
