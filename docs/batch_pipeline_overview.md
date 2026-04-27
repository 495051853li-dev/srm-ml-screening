# SRM 批量文献处理 Pipeline 总览

本仓库当前的主流程不是“围绕单篇论文做深度复核”，而是一个面向大规模文献池的批量处理 pipeline。目标是把候选文献逐步推进到：

1. 可批量筛选
2. 可批量抽取
3. 可批量质控
4. 可逐步扩展
5. 可导出为分析准备数据

这套 pipeline 的核心设计原则是：

- 主流程面向候选池批量推进，而不是卡在单篇论文上
- 单篇 review 只保留为抽样 QC 或人工兜底旁路
- `journal_impact_factor` 只作为当前文献筛选元数据，不作为默认 ML 特征
- 不因为单篇抓取失败、单篇抽取失败而阻塞全流程
- 不在自动层伪造实验值

## Stage 结构

### `stage1_search_candidates`

输入：

- `data/processed/candidate_papers.csv`
- 或通过 `src/run_literature_pipeline.py` 刷新 OpenAlex / Crossref 检索结果

输出：

- `data/processed/candidate_papers_master.csv`

作用：

- 构建 master candidate pool
- 强化 DOI 去重
- 强化 `title + year` 模糊去重
- 保留非目标体系标记
- 保留文献类型标记

规则：

- DOI 去重优先于标题模糊去重
- 非目标体系要保留标记，不直接删除原始候选来源
- master pool 是“可继续演化的候选主池”，不是正式分析数据集

### `stage2_enrich_journal_metrics`

输入：

- `data/processed/candidate_papers_master.csv`
- `data/processed/journal_metrics_lookup_curated.csv`

输出：

- `data/processed/candidate_papers_master_enriched.csv`

作用：

- 补全期刊元数据
- 写入：
  - `journal_impact_factor_year`
  - `journal_impact_factor`
  - `journal_quartile`
  - `journal_metrics_source`
  - `journal_metrics_notes`
- 对缺失项标记 `needs_manual_journal_check`

执行规则：

- 当前以本地 curated 映射表优先，不依赖外部实时查询作为硬前提
- 外部查询可以作为后续补充机制，但不是本 stage 成功运行的必要条件
- 对未覆盖期刊必须显式保留空值，并打上 `needs_manual_journal_check = yes`

### `stage3_score_and_filter`

输入：

- `data/processed/candidate_papers_master_enriched.csv`

输出：

- `data/processed/candidate_papers_high_if_scored.csv`
- `data/processed/eligible_high_if_pool.csv`
- `data/processed/backup_low_if_pool.csv`
- `data/processed/candidate_papers_top50.csv`
- `data/processed/candidate_papers_top100.csv`

作用：

- 对全量候选批量打分：
  - `relevance_score`
  - `extractability_score`
  - `journal_quality_score`
  - `priority_score`
  - `likely_ni_based`
  - `likely_contains_conditions`
  - `likely_contains_performance`
  - `final_priority_label`
- 形成第一批高 IF 合格池和备选池

筛选规则：

- 优先 `journal_article`
- 优先 `journal_impact_factor >= 6.0`
- `review` 保留但不进入第一批正式抽取池
- `IF` 缺失时保留候选，但标记 `needs_manual_journal_check`
- 不因为摘要相似或标题相似就直接升为高优先，仍需同时考虑相关性、期刊质量和可提取性

### `stage4_fetch_sources`

输入：

- `data/processed/eligible_high_if_pool.csv`
- `outputs/tables/openalex_raw_results.csv`
- `outputs/tables/crossref_raw_results.csv`

输出：

- `data/processed/fulltext_fetch_manifest.csv`
- `outputs/fulltext/`

作用：

- 批量尝试获取 DOI 落地页、开放获取页面、可访问 PDF 或其他可访问来源

执行规则：

- 必须支持断点续跑
- 必须跳过已完成项
- 必须保留失败记录
- 必须记录失败原因分类
- 单篇失败不能阻塞全流程

建议的失败原因分类：

- `no_candidate_url`
- `request_error:<ExceptionType>`
- `http_403`
- `http_404`
- `http_5xx`
- `insufficient_text_signal`
- `redirect_only`
- `unsupported_content_type`

建议的断点续跑策略：

- 以 `paper_id` 为最小运行单元
- 若 manifest 中已有成功记录，默认跳过
- 若 manifest 中已有失败记录，可由后续显式重试策略决定是否重跑

详细行为说明见：

- `docs/fetch_stage_behavior.md`

### `stage5_extract_fields`

输入：

- `data/processed/candidate_papers_high_if_scored.csv`
- `data/processed/fulltext_fetch_manifest.csv`

输出：

- `data/processed/srm_extraction_auto_draft.csv`

作用：

- 批量生成保守型自动抽取草稿

逻辑拆分：

1. `extract_metadata_fields`
   - 负责抽取或回填：
     - `paper_id`
     - `first_author`
     - `publication_year`
     - `title`
     - `journal`
     - `doi`
     - 以及文献来源与抽取方法相关字段

2. `extract_experimental_fields`
   - 负责抽取：
     - 催化剂组成
     - 载体/助剂
     - 制备与还原
     - 反应条件
     - 活性/稳定性/积碳相关字段

执行规则：

- 能确认才填
- 不能确认就留空
- 低置信度必须标记 `manual_review_required = yes`
- `analyst_qc_status` 默认 `pending`
- 所有 `derived_*` 字段必须保持为空

### `stage6_qc_and_freeze`

输入：

- `data/processed/srm_extraction_auto_draft.csv`
- `data/processed/candidate_papers_high_if_scored.csv`
- `data/processed/fulltext_fetch_manifest.csv`

输出：

- `data/processed/srm_extraction_qc_summary.csv`
- `data/processed/srm_extraction_record_flags.csv`
- `docs/batch_qc_report.md`

作用：

- 统计字段覆盖率
- 统计高置信度比例
- 统计抽取成功率
- 对记录做：
  - `human_sample_review_flag`
  - `analysis_ready_flag`
  - `freeze_recommendation`

冻结规则概述：

- `analysis_ready_flag = yes` 不等于“可建模”，它只表示“达到当前分析准备导出门槛”
- `freeze_recommendation = candidate_for_analysis_freeze` 表示：
  - 催化剂身份字段达到最低要求
  - 条件字段达到最低要求
  - 至少一个核心性能字段非空
  - 抽取置信度不为极低
- 若条件字段或性能字段缺失严重，则记录只能保留在 `auto_draft`

当前建议的 `analysis_ready_flag` 最低门槛：

- `core_identity_count >= 2`
- `key_condition_count >= 2`
- `key_performance_count >= 1`
- `extraction_confidence in {medium, low_to_medium}`

更详细的冻结规则见：

- `docs/freeze_rules.md`

### `stage7_analysis_ready_exports`

输入：

- 自动抽取草稿
- QC record flags
- scored candidate metadata

输出：

- `data/processed/analysis_ready_dataset.csv`
- `data/processed/analysis_ready_ni_based_high_if.csv`

作用：

- 只做分析准备数据导出
- 不开始建模

执行规则：

- 导出数据必须保留 QC 标记与来源相关字段
- `analysis_ready_dataset.csv` 可以用于统计性梳理和人工补录计划
- `analysis_ready_ni_based_high_if.csv` 只是高优先 Ni-based 子集导出，不表示已经适合训练模型

## 如何运行

全流程运行：

```powershell
python src/run_batch_literature_pipeline.py
```

如果需要先刷新 OpenAlex / Crossref 检索再重建 master pool：

```powershell
python src/run_batch_literature_pipeline.py --refresh-search
```

只重跑某一个或某几个 stage：

```powershell
python src/run_batch_literature_pipeline.py --stages stage3_score_and_filter
python src/run_batch_literature_pipeline.py --stages stage4_fetch_sources stage5_extract_fields
python src/run_batch_literature_pipeline.py --stages stage6_qc_and_freeze stage7_analysis_ready_exports
```

## 当前主线与旁路

当前主线：

- 批量候选池构建
- 高 IF 优先筛选
- 批量来源获取
- 批量自动抽取
- 批量 QC
- 分析准备导出

旁路：

- 单篇深度复核文档
- 单篇 review sheet
- 人工逐篇复核包

这些旁路文件仍可保留，但只适合作为抽样 QC 或人工兜底，不再是主流程。
