# 批量抽取 QC 报告

## 总体状态

- 高优先候选池规模：15
- 已尝试批量获取来源：15
- 可用于自动抽取的来源：14
- 已生成自动抽取草稿：14

## 字段覆盖率说明

- 输出文件：[data/processed/srm_extraction_qc_summary.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_qc_summary.csv)
- `coverage_rate` 表示该字段在当前自动抽取草稿中的非空比例
- `high_confidence_ratio` 当前按“非空值中来自 `extraction_confidence = medium` 的比例”近似计算

## 抽取成功率

- 批量来源获取成功率：93.33%
- 自动抽取成稿率（相对可用来源）：100.00%

按文献类型统计：

- `journal_article`: 15 条尝试，14 条可用于抽取

## 子集差异

- `IF >= 6.0` 候选规模：84
- `IF < 6.0` 候选规模：64
- `IF >= 6.0` 当前来源获取尝试：15，其中可用于抽取：14
- `IF < 6.0` 当前来源获取尝试：0，其中可用于抽取：0
- `Ni-based` 候选规模：75
- 当前自动抽取主池仍集中在 `IF >= 6.0` 高优先候选，这属于文献筛选策略，不代表期刊 IF 可进入后续模型

## 记录级标记

- 输出文件：[data/processed/srm_extraction_record_flags.csv](D:/ML/srm/srm_ml_screening/data/processed/srm_extraction_record_flags.csv)
- `human_sample_review_flag = yes`：优先用于人工抽样 QC
- `analysis_ready_flag = yes`：可进入分析准备导出候选
- `freeze_recommendation = candidate_for_analysis_freeze`：适合进入冻结候选子集
- 当前 `analysis_ready_flag = yes` 记录数：0

## 风险提醒

- 不同温度、S/C、压力、GHSV、TOS 下的文献数据默认不可直接比较
- `journal_impact_factor` 只是当前文献筛选元数据，不应带入后续机器学习特征
- 自动抽取草稿仍有漏抽和定义误判风险，尤其是 `conversion / yield / selectivity`、`GHSV / WHSV`、`stability duration / TOS` 等字段
