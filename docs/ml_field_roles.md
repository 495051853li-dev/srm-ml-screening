# SRM 字段角色说明

本文档用于说明当前 SRM 文献提取模板中所有字段在后续数据处理、质量控制与机器学习流程中的推荐角色。

适用范围：

- 适用于当前仓库中的文献提取模板、data dictionary 与 validator
- 适用于“先进行文献结构化提取，再进行数据冻结、筛选、建模”的工作流
- 不改变原始模板字段，只定义字段在后续流程中的默认职责

## 角色标签说明

- `metadata`：文献追溯、分组、来源信息，不直接描述催化剂本体或实验结果
- `measured_feature`：催化剂组成、制备、结构或其他可作为输入的实验测量/报告特征
- `condition_feature`：反应条件、操作条件、取样时点等条件变量
- `label_candidate`：可作为监督学习输出候选的性能、稳定性或积碳相关字段
- `qc`：用于质量控制、可信度分层、样本筛选或防泄漏检查的字段
- `notes`：自由文本说明、歧义记录、定义补充，不建议默认直接进模型
- `derived`：后续脚本生成的派生字段，原始提取阶段必须留空
- `exclude_by_default`：默认不建议进入模型输入，通常因为泄漏风险、来源偏差或语义不稳定

## 字段逐项角色标注

| field_name | role | short_reason | default_use_in_ml | notes_if_any |
| --- | --- | --- | --- | --- |
| record_id | metadata | 行级唯一标识，用于追溯和去重 | no | 仅用于数据管理，不进入模型 |
| paper_id | metadata | 论文级分组标识，适合做分组切分 | no | 强烈建议用于按论文分组的 train/test split，防止泄漏 |
| reference_type | metadata | 来源类型描述的是文献，不是催化剂本体 | no | 可用于文献筛选，不建议默认进模型 |
| first_author | metadata | 作者信息用于追溯和偏差分析 | no | 不应进入模型，容易学习到研究团队偏差 |
| publication_year | exclude_by_default | 反映时间背景与文献年代，但不是催化剂本体特征 | no | 仅建议用于时间分层、偏差分析或敏感性分析，不建议默认入模 |
| title | exclude_by_default | 自由文本且强烈依赖文献来源 | no | 易引入来源偏差和文本噪声 |
| journal | metadata | 期刊信息属于文献来源元数据 | no | 用于筛选和偏差分析，不建议默认进模型 |
| journal_impact_factor_year | metadata | 期刊指标对应年份，属于文献元数据 | no | 不建议默认作为 ML 特征 |
| journal_impact_factor | exclude_by_default | 反映发表载体，不反映催化剂本征性质 | no | 可用于偏差分析和对照实验，默认排除 |
| journal_quartile | exclude_by_default | 期刊分区是来源属性而非材料属性 | no | 可用于敏感性分析，不建议默认进模型 |
| journal_metrics_source | metadata | 记录期刊指标来源 | no | 仅用于元数据追溯 |
| journal_metrics_notes | notes | 对期刊指标检索过程的说明 | no | 备注字段，不进模型 |
| doi | metadata | 论文唯一标识之一 | no | 用于追溯与去重，不进模型 |
| condition_id | metadata | 同一论文内条件级分组标识 | no | 适合用于分组、去重和条件切片管理 |
| catalyst_label_reported | metadata | 保留论文原始样品名称 | caution | 可用于追溯，不建议直接进模型，除非后续标准化编码 |
| catalyst_family | measured_feature | 催化剂大类可作为粗粒度组成特征 | yes | 建议 one-hot 或分类型编码 |
| active_metal_primary | measured_feature | 主活性金属是核心组成特征 | yes | 第一版输入中建议保留 |
| active_metal_secondary | measured_feature | 次活性金属描述双金属体系 | caution | 缺失较多时需要明确缺失编码 |
| active_metal_primary_loading_wt_pct | measured_feature | 主活性金属负载量是关键组成特征 | yes | 优先于更旧的总括字段使用 |
| active_metal_secondary_loading_wt_pct | measured_feature | 次活性金属负载量用于双金属体系 | caution | 单金属体系应为空，不应强行填 0 |
| active_metal_total_loading_wt_pct | measured_feature | 总活性金属负载量有助于统一比较 | caution | 可与主/次金属负载并行保留，但避免重复编码 |
| active_metal_atomic_ratio_reported | notes | 原文报告的原子比适合保真记录 | caution | 如后续标准化，可转成结构化数值特征 |
| active_metal_loading_wt_pct | measured_feature | 历史兼容字段，保留旧版抽取结果 | caution | 默认不建议进入第一版模型输入，优先使用 `active_metal_primary_loading_wt_pct`、`active_metal_secondary_loading_wt_pct` 和 `active_metal_total_loading_wt_pct` |
| active_metal_loading_basis | qc | 区分 nominal、measured 或 unclear | caution | 很重要，但更适合作为分层/QC 辅助变量 |
| promoter_1 | measured_feature | 第一助剂是组成特征的一部分 | yes | 建议标准化命名 |
| promoter_1_loading_wt_pct | measured_feature | 助剂负载量可作为输入 | caution | 常缺失，需明确缺失策略 |
| promoter_2 | measured_feature | 第二助剂描述更复杂体系 | caution | 缺失较多，需谨慎编码 |
| promoter_2_loading_wt_pct | measured_feature | 第二助剂负载量 | caution | 常缺失，需谨慎使用 |
| support_primary | measured_feature | 主载体是核心组成特征 | yes | 第一版输入中建议保留 |
| support_secondary | measured_feature | 次载体或混合氧化物组分 | caution | 建议后续做标准化映射 |
| support_notes | notes | 载体相、结构、混合氧化物等说明 | no | 文本信息有价值，但不建议默认入模 |
| precursor_metal_source | measured_feature | 金属前驱体会影响制备结果 | caution | 可作为制备特征，但命名需标准化 |
| precursor_support_source | measured_feature | 载体前驱体来源影响材料形成 | caution | 常缺失，可先保留不优先入模 |
| preparation_method | measured_feature | 制备路线对催化性能影响大 | yes | 第一版输入中建议保留 |
| preparation_details | notes | 工艺细节信息量大但自由文本多 | no | 建议后续拆分后再考虑入模 |
| calcination_temperature_c | measured_feature | 焙烧温度影响结构与分散 | yes | 第一版输入中建议保留 |
| calcination_time_h | measured_feature | 焙烧时间影响结构演变 | caution | 可保留，视缺失率决定是否入模 |
| reduction_temperature_c | measured_feature | 还原温度影响活性位形成 | yes | 第一版输入中建议保留 |
| reduction_time_h | measured_feature | 还原时间影响预处理状态 | caution | 可保留，视缺失率决定是否入模 |
| reduction_gas | measured_feature | 还原气氛影响表面状态 | caution | 分类值需标准化 |
| reactor_type | condition_feature | 反应器类型影响传质和可比性 | caution | 建议保留作条件控制变量 |
| catalyst_mass_g | condition_feature | 装填量影响归一化与反应条件解释 | caution | 更适合作为条件辅助变量 |
| particle_size_um | condition_feature | 颗粒尺寸影响外扩散和床层行为 | caution | 可用，但往往缺失或报告不一致 |
| temperature_c | condition_feature | 反应温度是最关键条件变量之一 | yes | 第一版输入中建议保留 |
| pressure_bar | condition_feature | 反应压力影响转化与选择性 | yes | 第一版输入中建议保留 |
| steam_to_carbon_ratio | condition_feature | S/C 是 SRM 最关键条件变量之一 | yes | 第一版输入中建议保留 |
| feed_ch4_vol_pct | condition_feature | 进料甲烷组成决定操作窗口 | caution | 与其他 feed 字段一起考虑 |
| feed_h2o_vol_pct | condition_feature | 蒸汽组成影响平衡和积碳 | caution | 与 S/C 相关但不完全等价 |
| feed_co2_vol_pct | condition_feature | 共进 CO2 会改变体系边界 | caution | 若研究目标限定纯 SRM，可用于过滤 |
| feed_n2_vol_pct | condition_feature | 惰性稀释影响表观结果 | caution | 常作为进料辅助条件 |
| feed_h2_vol_pct | condition_feature | 共进 H2 会影响平衡与活性解释 | caution | 用于区分测试协议 |
| balance_gas_identity | condition_feature | 记录未完全展开的平衡气体身份 | caution | 主要用于条件解释，不是核心输入 |
| gas_hourly_space_velocity_h_inv | condition_feature | GHSV 强烈影响性能表观值 | yes | 第一版输入中建议保留 |
| weight_hourly_space_velocity_h_inv | condition_feature | WHSV 是另一种常见空速定义 | caution | 与 GHSV 并存时需避免重复解释 |
| contact_time_s | condition_feature | 接触时间影响可比性 | caution | 可用，但定义来源可能不一致 |
| time_on_stream_h | condition_feature | 性能对应的 TOS 对稳定性解释关键 | yes | 第一版输入中建议保留 |
| methane_conversion_pct | label_candidate | 最常见的活性输出指标之一 | caution | 可作为第一版主标签候选，但必须显式控制条件 |
| h2_yield_pct | label_candidate | 更接近产氢目标的输出指标 | caution | 很适合作为主标签候选，但需注意定义差异 |
| h2_selectivity_pct | label_candidate | 选择性输出，可作为辅助任务 | caution | 文献覆盖率可能较低 |
| h2_production_rate_mmol_gcat_h | label_candidate | 工程上更直接的产氢性能指标 | caution | 单位与归一化口径需统一 |
| h2_production_rate_mmol_gmetal_h | label_candidate | 归一到金属质量的性能指标 | caution | 跨文献定义和可比性更复杂 |
| co_selectivity_pct | label_candidate | 副产物相关输出 | caution | 适合做多目标分析，不一定是首版主标签 |
| co2_selectivity_pct | label_candidate | 碳去向相关输出 | caution | 常见定义不完全一致 |
| h2_co_ratio | label_candidate | 合成气比相关输出指标 | caution | 适合做辅助标签，不一定做首版主标签 |
| performance_definition_notes | notes | 记录性能指标定义口径差异 | no | 对后续标签清洗非常重要，但不直接入模 |
| stability_test_performed | qc | 区分是否做了稳定性实验 | caution | 更适合作为样本筛选条件 |
| stability_duration_h | label_candidate | 稳定性测试时长本身是重要输出或筛选轴 | caution | 可作稳定性任务辅助标签或筛选条件 |
| conversion_drop_pct_points | label_candidate | 稳定性退化的直接量化指标 | caution | 很适合稳定性任务，但必须结合测试时长解释 |
| coking_test_method | notes | 积碳评价方法差异很大 | no | 用于解释不同 coke 指标口径 |
| coke_amount_mg_gcat | label_candidate | 定量积碳输出指标之一 | caution | 第一版抗积碳任务可优先考虑 |
| coke_amount_wt_pct | label_candidate | 常见积碳输出指标之一 | caution | 与 mg/gcat 不能直接混用 |
| carbon_balance_closure_pct | qc | 反映实验数据质量与可信度 | caution | 更适合作为质量筛选条件 |
| sintering_evidence | qc | 是否观察到烧结，更像结果证据/QC 信息 | caution | 可用于误差分析，不建议首版默认入模 |
| sulfur_tolerance_tested | qc | 是否测试硫耐受，更多是实验覆盖信息 | caution | 适合作为数据分层字段 |
| deactivation_mode_reported | notes | 失活机制通常为自由文本总结 | no | 更适合备注和后续人工归类 |
| characterization_summary | notes | 表征证据摘要是高信息量文本 | no | 默认不进模型，后续可再结构化 |
| measured_value_basis | qc | 区分 fresh、steady-state、peak 等 | caution | 优先用于样本过滤、质量分层和误差分析，不建议默认作为第一版模型输入特征 |
| digitized_from_plot | qc | 标记是否来自图中数字化 | caution | 优先用于样本过滤、质量分层和误差分析，不建议默认作为第一版模型输入特征 |
| extraction_notes | notes | 人工提取中的歧义与说明 | no | 仅用于审计和复核 |
| comparable_within_study | qc | 是否在同文献内可直接比较 | caution | 优先用于样本过滤、质量分层和误差分析，不建议默认作为第一版模型输入特征 |
| analyst_qc_status | qc | 人工质控状态字段 | no | 不应进入模型，属于工作流状态 |
| derived_activity_score | derived | 后续脚本生成的活动性派生分数 | no | 原始提取阶段必须留空，不能人工填写，不能默认作为训练输入 |
| derived_stability_score | derived | 后续脚本生成的稳定性派生分数 | no | 原始提取阶段必须留空，不能人工填写，不能默认作为训练输入 |
| derived_coking_resistance_score | derived | 后续脚本生成的抗积碳派生分数 | no | 原始提取阶段必须留空，不能人工填写，不能默认作为训练输入 |
| derived_overall_screening_score | derived | 后续脚本生成的综合筛选分数 | no | 原始提取阶段必须留空，不能人工填写，不能默认作为训练输入 |

## 分类原则补充说明

- 文献信息字段默认归入 `metadata`，其职责是追溯、分组、偏差分析与样本筛选，不是默认建模输入。
- 催化剂组成、前驱体、制备和预处理字段优先归入 `measured_feature`。
- 反应条件、进料组成、空速和时间相关字段优先归入 `condition_feature`。
- `methane_conversion_pct`、`h2_yield_pct`、`conversion_drop_pct_points`、`coke_amount_mg_gcat`、`coke_amount_wt_pct` 等字段优先视为 `label_candidate`。
- `analyst_qc_status`、`digitized_from_plot`、`comparable_within_study`、`measured_value_basis` 等字段优先视为 `qc`。
- `extraction_notes`、`characterization_summary`、`support_notes`、`performance_definition_notes` 等字段优先视为 `notes`。
- 所有 `derived_*` 字段都属于 `derived`，并且：
  - 原始提取阶段必须留空
  - 不能人工填写
  - 不能默认作为训练输入
  - 只能由后续脚本根据已冻结的实验测量数据自动生成
- `journal_impact_factor_year`、`journal_impact_factor`、`journal_quartile`、`journal_metrics_source`、`journal_metrics_notes` 属于文献元数据或默认排除字段，不建议默认作为机器学习特征。
- `active_metal_loading_wt_pct` 是历史兼容字段，默认不建议进入第一版模型输入；若更细化的主/次/总活性金属负载字段可用，应优先使用这些字段。
- `publication_year` 默认归为 `exclude_by_default`，仅建议用于时间分层、偏差分析或敏感性分析，不建议默认入模。
- `measured_value_basis`、`digitized_from_plot`、`comparable_within_study` 优先用于样本过滤、质量分层和误差分析，不建议默认作为第一版模型输入特征。

## 建议的第一版 ML 输入与输出

这一节给的是“第一版最稳妥”的建议，不追求覆盖全部字段，而是优先降低泄漏风险、减少口径混乱、保留最核心可解释变量。

### 第一版建议保留的输入字段集合

建议作为第一版输入的字段：

- `catalyst_family`
- `active_metal_primary`
- `active_metal_secondary`
- `active_metal_primary_loading_wt_pct`
- `active_metal_secondary_loading_wt_pct`
- `active_metal_total_loading_wt_pct`
- `promoter_1`
- `promoter_1_loading_wt_pct`
- `promoter_2`
- `promoter_2_loading_wt_pct`
- `support_primary`
- `support_secondary`
- `preparation_method`
- `calcination_temperature_c`
- `calcination_time_h`
- `reduction_temperature_c`
- `reduction_time_h`
- `reduction_gas`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `feed_ch4_vol_pct`
- `feed_h2o_vol_pct`
- `feed_co2_vol_pct`
- `feed_n2_vol_pct`
- `feed_h2_vol_pct`
- `gas_hourly_space_velocity_h_inv`
- `weight_hourly_space_velocity_h_inv`
- `contact_time_s`
- `time_on_stream_h`
- `reactor_type`

使用建议：

- 其中 `temperature_c`、`steam_to_carbon_ratio`、`pressure_bar`、`gas_hourly_space_velocity_h_inv`、`time_on_stream_h` 是第一版最重要的条件输入。
- 如果样本量较小，可进一步收缩输入集合，优先保留组成字段和最关键条件字段。
- `active_metal_loading_wt_pct` 属于历史兼容字段，第一版若已使用更细化字段，应默认不再作为主输入。

### 第一版建议排除的字段集合

建议默认从第一版模型输入中排除：

- `record_id`
- `paper_id`
- `reference_type`
- `first_author`
- `publication_year`
- `title`
- `journal`
- `journal_impact_factor_year`
- `journal_impact_factor`
- `journal_quartile`
- `journal_metrics_source`
- `journal_metrics_notes`
- `doi`
- `condition_id`
- `catalyst_label_reported`
- `support_notes`
- `preparation_details`
- `active_metal_atomic_ratio_reported`
- `performance_definition_notes`
- `coking_test_method`
- `deactivation_mode_reported`
- `characterization_summary`
- `extraction_notes`
- `analyst_qc_status`
- `digitized_from_plot`
- `comparable_within_study`
- 所有 `derived_*`

### 第一版最稳妥的 label_candidate

如果目标是“先做一版稳妥、可解释的 SRM 筛选模型”，建议优先考虑以下标签：

- 首选活性标签：
  - `methane_conversion_pct`
  - 或 `h2_yield_pct`

- 首选稳定性标签：
  - `conversion_drop_pct_points`

- 首选抗积碳标签：
  - `coke_amount_mg_gcat`
  - 或 `coke_amount_wt_pct`

更稳妥的顺序建议：

- 如果想先做单任务、且追求文献覆盖率，优先考虑 `methane_conversion_pct`
- 如果想更贴近产氢目标，可优先考虑 `h2_yield_pct`
- `methane_conversion_pct` 和 `h2_yield_pct` 不建议同时作为第一版起步主标签，建议先选其中一个作为主任务输出，另一个保留为辅助分析目标
- 如果做稳定性任务，`conversion_drop_pct_points` 必须结合 `stability_duration_h` 一起解释，否则退化程度不可直接比较
- 后续可以由脚本进一步派生标准化退化速率字段，但原始提取阶段不新增人工填写字段
- 如果做抗积碳任务，`coke_amount_mg_gcat` 和 `coke_amount_wt_pct` 不应混合成同一个标签

### 第一版不建议进入模型的字段及原因

- 文献来源字段：
  - `paper_id`、`first_author`、`journal`、`doi`、`title`
  - 原因：会引入明显的来源偏差和泄漏风险

- 期刊指标字段：
  - `journal_impact_factor_year`、`journal_impact_factor`、`journal_quartile`、`journal_metrics_source`、`journal_metrics_notes`
  - 原因：它们属于文献元数据，主要用于文献筛选、数据分层、偏差分析和敏感性分析，不建议默认作为 ML 输入特征；若使用，也只能作为对照实验字段

- 质控状态字段：
  - `analyst_qc_status`、`digitized_from_plot`、`comparable_within_study`、`measured_value_basis`
  - 原因：更适合做过滤和质量分层，不是催化剂本体属性

- 自由文本说明字段：
  - `support_notes`、`preparation_details`、`characterization_summary`、`extraction_notes`、`performance_definition_notes`
  - 原因：自由文本难以直接结构化，容易引入录入风格噪声

- 派生字段：
  - `derived_activity_score`
  - `derived_stability_score`
  - `derived_coking_resistance_score`
  - `derived_overall_screening_score`
  - 原因：这些字段属于高泄漏风险字段，原始提取阶段必须留空，不能人工填写，不能默认作为训练输入

## 使用建议

- 在正式建模前，建议先根据本文件把字段分成输入层、标签层、QC 过滤层和备注层。
- 建议优先按 `paper_id` 分组切分数据，避免同一论文的相似样本同时出现在训练集和测试集中。
- 建议先在条件较接近的子集上做第一版模型，避免模型把条件差异误学成催化剂本征规律。
