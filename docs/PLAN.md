# 当前任务计划

本文件记录当前仓库的主线任务：把 SRM 文献处理流程重构为一个可逐步扩展到成千上万篇候选文献的批量处理 pipeline，而不是以单篇论文深度复核为中心。

## 目标范围

当前主流程聚焦以下能力：

1. 大规模候选文献检索与主池构建
2. 基于相关性、期刊质量、可提取性的批量筛选
3. 对高优先池批量尝试获取摘要页、正文页、PDF 或其他可访问来源
4. 对可访问来源批量生成保守型自动字段抽取草稿
5. 自动生成批量 QC 汇总、记录级标记与分析准备导出
6. 为后续人工抽样复核、统计分析和机器学习准备打底

约束：

- 不开始建模
- 不生成虚假文献
- 不生成虚假实验数据
- 不修改正式主表 `data/processed/srm_literature_extraction_template.csv`
- `derived_*` 字段在自动草稿中必须保持为空
- `journal_impact_factor` 只作为当前文献筛选元数据，不能默认带入后续机器学习特征

## 批量 pipeline 结构

| Stage | 状态 | 主要输入 | 主要输出 | 验证方法 |
| --- | --- | --- | --- | --- |
| `stage1_search_candidates` | 已完成 | `candidate_papers.csv` 或 API 刷新结果 | `candidate_papers_master.csv` | 检查去重后总行数、DOI 去重、title+year 去重、非目标体系标记 |
| `stage2_enrich_journal_metrics` | 已完成 | `candidate_papers_master.csv` + `journal_metrics_lookup_curated.csv` | `candidate_papers_master_enriched.csv` | 检查期刊指标补全率与 `needs_manual_journal_check` |
| `stage3_score_and_filter` | 已完成 | `candidate_papers_master_enriched.csv` | `candidate_papers_high_if_scored.csv`、`eligible_high_if_pool.csv`、`backup_low_if_pool.csv`、`candidate_papers_top50.csv`、`candidate_papers_top100.csv` | 检查全量分层、第一批高 IF 池、top50/top100 |
| `stage4_fetch_sources` | 已完成 | `eligible_high_if_pool.csv` + OpenAlex/Crossref 原始结果 | `fulltext_fetch_manifest.csv` + `outputs/fulltext/` | 检查获取成功率、失败原因、可用于抽取的来源数 |
| `stage5_extract_fields` | 已完成 | `candidate_papers_high_if_scored.csv` + `fulltext_fetch_manifest.csv` | `srm_extraction_auto_draft.csv` | 检查草稿行数、`derived_*` 为空、`analyst_qc_status=pending` |
| `stage6_qc_and_freeze` | 已完成 | `srm_extraction_auto_draft.csv` + `candidate_papers_high_if_scored.csv` + `fulltext_fetch_manifest.csv` | `srm_extraction_qc_summary.csv`、`srm_extraction_record_flags.csv`、`docs/batch_qc_report.md` | 检查覆盖率、抽取成功率、人工抽样标记、冻结候选标记 |
| `stage7_analysis_ready_exports` | 已完成 | 自动草稿 + QC flags + scored candidates | `analysis_ready_dataset.csv`、`analysis_ready_ni_based_high_if.csv` | 检查分析准备导出是否成功生成、并确认不进入建模阶段 |

## 当前进度

- 旧的“单篇论文深度复核”主流程已暂停
- 新的批量 pipeline 总控脚本已建立：
  - [src/run_batch_literature_pipeline.py](D:/ML/srm/srm_ml_screening/src/run_batch_literature_pipeline.py)
- 已完成一轮端到端串行验证

当前批量结果摘要：

- 原始候选：`222` 条
- master candidate pool：`216` 条
- 非目标体系标记：`19` 条
- 成功补全期刊指标：`148` 条
- 需人工补期刊指标：`68` 条
- 高 IF 合格池：`15` 条
- 批量来源获取尝试：`15` 条
- 可用于抽取的来源：`14` 条
- 自动抽取草稿：`14` 条
- 当前 `analysis_ready` 导出：`0` 条

## 关键决策

1. 主流程转向“批量处理候选池”，单篇 review 只保留为抽样 QC 辅助。
2. `journal_impact_factor` 当前作为文献筛选的硬条件之一，但明确不作为默认 ML 特征。
3. 第一批正式抽取池优先使用 `journal_article`、`IF >= 6.0`、主题明确相关且更可能包含条件与性能字段的文章。
4. 自动抽取采用保守策略：
   - 能确认才填
   - 不能确认留空
   - 低置信度默认 `manual_review_required = yes`
5. `analysis_ready` 的门槛采用偏保守设定；当前导出为空，说明瓶颈在字段可抽取性，而不是 pipeline 串联失败。

## 每一步验证方法

### Stage 1

- 检查 `candidate_papers_master.csv` 是否存在
- 检查 `master_rows <= input_rows`
- 检查 DOI 去重与 title+year 去重统计是否合理

### Stage 2

- 检查 `candidate_papers_master_enriched.csv` 是否存在
- 检查 `needs_manual_journal_check` 分布
- 检查高频期刊是否已补齐期刊指标

### Stage 3

- 检查 `candidate_papers_high_if_scored.csv` 是否覆盖全量 master pool
- 检查 `eligible_high_if_pool.csv`、`backup_low_if_pool.csv`、`candidate_papers_top50.csv`、`candidate_papers_top100.csv`
- 检查 `final_priority_label` 是否只包含允许值

### Stage 4

- 检查 `fulltext_fetch_manifest.csv` 是否记录所有尝试
- 检查失败原因是否明确
- 检查 `outputs/fulltext/` 是否生成本地文件

### Stage 5

- 检查 `srm_extraction_auto_draft.csv` 是否生成
- 检查 `derived_*` 字段是否全部为空
- 检查 `analyst_qc_status` 是否默认 `pending`

### Stage 6

- 检查 `srm_extraction_qc_summary.csv` 字段覆盖率是否合理
- 检查 `srm_extraction_record_flags.csv` 是否生成人工抽样标记与冻结候选标记
- 检查 `docs/batch_qc_report.md` 是否生成

### Stage 7

- 检查 `analysis_ready_dataset.csv` 与 `analysis_ready_ni_based_high_if.csv` 是否生成
- 若导出为空，确认原因来自字段缺失/置信度不足，而不是脚本失败

## 阶段记录

### 2026-04-24

- 完成第一轮本地检索
- 生成 `candidate_papers.csv`
- 建立了第一版优先级排序、来源抓取和自动抽取草稿

### 2026-04-27

- 暂停旧的低质量候选优先复核路径
- 完成高 IF 优先筛选专项重排
- 将工作流重构为 7-stage 批量 pipeline
- 新增批量总控脚本与阶段脚本
- 完成一轮端到端串行验证
