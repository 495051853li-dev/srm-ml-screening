# 来源质量诊断报告

## 当前来源质量分层

- 分层记录数：`26`
- `pdf_fulltext`: `20`
- `redirect_or_forbidden`: `6`

## ready_for_extraction 记录的来源类型

- ready_for_extraction=yes 记录数：`20`
- `pdf_fulltext`: `20`

## 真正可用于 experimental extraction 的记录数量

- 允许 metadata + experimental 抽取的记录数：`20`
- 当前 experimental 草稿记录数：`20`

## fulltext candidate fetch 诊断

- 已记录 candidate_url 尝试数：`94`
- `local_candidate_not_fetched`: `60`
- `redirect_only`: `26`
- `success`: `3`
- `forbidden`: `3`
- `non_retryable_failure`: `2`

candidate_url 获取后的来源质量：
- `local_pdf_candidate`: `60`
- `redirect_or_forbidden`: `29`
- `abstract_only`: `3`
- `no_useful_content`: `2`

## experimental 字段覆盖率低的主要原因

- 多数来源实际是 DOI landing page、Redirecting 页面、受限页面、导航壳或摘要页，不包含完整实验方法、反应条件和性能数据表。
- `abstract_only` 只能用于题录、催化剂体系和有限催化剂层面信息，不能填写温度、S/C、GHSV、conversion、yield 等具体实验字段。
- 不同温度、S/C、压力、GHSV 下的 SRM 性能不可直接比较；实验字段必须有原文数值、单位和上下文证据才允许进入草稿。

当前关键 experimental 字段覆盖率：
- `temperature_c`: `10.0%`
- `pressure_bar`: `80.0%`
- `steam_to_carbon_ratio`: `40.0%`
- `gas_hourly_space_velocity_h_inv`: `25.0%`
- `methane_conversion_pct`: `25.0%`
- `h2_yield_pct`: `0.0%`
- `stability_duration_h`: `75.0%`
- `coke_amount_wt_pct`: `0.0%`

## 需要继续寻找 PDF / HTML fulltext 的来源

- `paper_id=paper_0124`; `source_quality_type=redirect_or_forbidden`; `journal=Chemical Engineering Journal`; `journal_impact_factor=13.2`; `priority_score=85.5`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0191`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=85.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0099`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0193`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0007`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0202`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of the Energy Institute`; `journal_impact_factor=6.2`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`

## 人工 PDF 优先清单

- 待人工合法下载 PDF 的优先记录数：`4`
- `paper_id=paper_0006`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=81.0`; `doi=10.1016/0021-9517(84)90107-6`
- `paper_id=paper_0004`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=81.0`; `doi=10.1016/0021-9517(81)90010-5`
- `paper_id=paper_0003`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=81.0`; `doi=10.1016/0021-9517(78)90142-2`
- `paper_id=paper_0005`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=78.0`; `doi=10.1016/0021-9517(81)90332-8`

## 是否建议优先做 PDF 获取增强

- 建议继续优先增强合法 PDF / HTML fulltext 获取，而不是扩大候选池。
- 当前瓶颈不是候选文献数量，而是可用于实验字段抽取的全文来源数量。
- 当 `pdf_fulltext` 或 `html_fulltext` 达到一批稳定样本后，再重新运行 stage5 的 metadata 与 experimental 抽取更合理。
