# 冻结规则与 analysis-ready 判定

本文件定义当前批量文献处理 pipeline 中，哪些记录可以进入 `analysis_ready_dataset.csv`，哪些记录只能保留在 `auto_draft`，以及哪些记录必须进入人工抽样复核。

## 一、记录分层

当前记录分为四层：

1. `auto_draft_only`
2. `requires_human_sample_review`
3. `analysis_ready`
4. `model_candidate_later`

这四层不是一步到位自动升级的，而是随着来源质量、字段覆盖率和 QC 状态逐步推进。

## 二、什么记录可以进入 analysis_ready_dataset.csv

当前建议进入 `analysis_ready_dataset.csv` 的记录，至少满足以下条件：

1. 催化剂身份最低信息完整
   - `active_metal_primary` 非空
   - `support_primary` 非空
   - `catalyst_family` 或 `catalyst_label_reported` 至少有一个可用

2. 反应条件不是完全缺失
   - 下列条件字段中至少 2 个可确认：
     - `temperature_c`
     - `pressure_bar`
     - `steam_to_carbon_ratio`
     - `gas_hourly_space_velocity_h_inv`
     - `weight_hourly_space_velocity_h_inv`
     - `time_on_stream_h`

3. 至少有 1 个核心性能字段可确认
   - `methane_conversion_pct`
   - `h2_yield_pct`
   - `h2_selectivity_pct`
   - `co_selectivity_pct`
   - `h2_co_ratio`

4. 当前抽取置信度不能太低
   - `extraction_confidence` 至少为 `low_to_medium` 或 `medium`

5. 不能违反硬性规则
   - `derived_*` 必须为空
   - 不允许猜测填写的实验值

说明：

- 进入 `analysis_ready_dataset.csv` 只表示“可分析准备”，不表示“可直接建模”。
- 这个子集适合做字段覆盖统计、子集差异分析、人工补录优先级排序。

## 三、什么记录只能保留在 auto_draft

以下情况的记录应保留在 `data/processed/srm_extraction_auto_draft.csv`，不能进入 `analysis_ready_dataset.csv`：

1. 只有文献信息和催化剂身份，没有足够条件字段
2. 性能字段全部缺失
3. 页面更像摘要页或落地页，实验正文证据不足
4. 抽取置信度为 `low`
5. 无法区分 `conversion / yield / selectivity` 的定义
6. 无法区分 `GHSV / WHSV / TOS` 的语义

这类记录不是无价值，而是仍适合作为：

- 后续继续抓取更强来源的对象
- 人工抽样复核对象
- 备选候选池

## 四、什么记录必须进入人工抽样复核

以下情况的记录应优先打上人工抽样复核标记：

1. `manual_review_required = yes`
2. `extraction_confidence = low`
3. 反应条件字段严重缺失，但题目/摘要看起来高度相关
4. 性能字段出现但定义不清
5. 期刊 IF 高、主题相关性高，但自动抽取覆盖率低
6. 同一篇文章中多个字段看起来彼此矛盾

人工抽样复核的目的：

- 不是把所有记录都人工重做
- 而是估计自动抽取误差类型
- 校正规则、识别系统性漏抽点

## 五、哪些字段缺失会导致不能冻结

以下字段的缺失会直接阻止记录进入当前 `analysis_ready` 冻结候选：

1. 催化剂身份核心字段缺失
   - `active_metal_primary`
   - `support_primary`

2. 条件字段过少
   - `temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`、`gas_hourly_space_velocity_h_inv`、`weight_hourly_space_velocity_h_inv`、`time_on_stream_h`
   - 如果上述字段总计少于 2 个，则不能冻结

3. 核心性能字段全空
   - `methane_conversion_pct`
   - `h2_yield_pct`
   - `h2_selectivity_pct`
   - `co_selectivity_pct`
   - `h2_co_ratio`

4. `derived_*` 被误填
   - 若 `derived_*` 非空，说明记录已污染，必须退回修正

## 六、如何区分“可分析但不可建模”和“可建模候选”

### 可分析但不可建模

满足以下特征的记录可以先保留在分析准备层，但不应直接进入建模：

- 有一部分催化剂身份字段
- 有部分条件字段
- 至少 1 个性能指标
- 但条件缺失仍较多，跨文献可比性不足
- 仍依赖人工解释字段定义
- 可能存在来源页不是正文的问题

这些记录适合：

- 统计覆盖率
- 做子集清点
- 观察 Ni-based / high-IF / journal_article 子集规模
- 设计下一轮人工复核和自动抽取改进策略

### 可建模候选

即使未来要进入建模，也至少还需要满足更严格条件：

1. 条件字段更完整
   - 最好明确 `temperature_c`、`steam_to_carbon_ratio`、`pressure_bar`
   - 至少一个空间速度字段或等效接触条件

2. 性能标签定义明确
   - 第一版主标签不能混用不同定义
   - 例如 `methane_conversion_pct` 与 `h2_yield_pct` 不应在同一版起步任务里同时当主标签

3. 同类样本可分层比较
   - 能够按条件做子集
   - 或能做明确的条件感知建模

4. 人工抽样 QC 通过
   - 自动抽取误差已知且可控

5. 明确排除泄漏字段
   - 例如 `journal_impact_factor`
   - `journal_quartile`
   - `publication_year`
   - `derived_*`

## 七、当前建议

当前阶段应把 `analysis_ready_dataset.csv` 看作“分析准备导出层”，而不是训练集。  
在没有更稳定的正文来源和更强的条件/性能抽取能力之前，不建议把当前自动草稿直接推进到建模。
