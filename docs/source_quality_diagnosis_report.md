# 来源质量诊断报告

## 当前来源质量分层

- 分层记录数：`15`
- `redirect_or_forbidden`: `13`
- `abstract_only`: `1`
- `pdf_fulltext`: `1`

## ready_for_extraction 记录的来源类型

- ready_for_extraction=yes 记录数：`2`
- `abstract_only`: `1`
- `pdf_fulltext`: `1`

## 真正可用于 experimental extraction 的记录数量

- 允许 metadata + experimental 抽取的记录数：`1`
- 当前 experimental 草稿记录数：`0`

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
- `temperature_c`: `0.0%`
- `pressure_bar`: `0.0%`
- `steam_to_carbon_ratio`: `0.0%`
- `gas_hourly_space_velocity_h_inv`: `0.0%`
- `methane_conversion_pct`: `0.0%`
- `h2_yield_pct`: `0.0%`
- `stability_duration_h`: `0.0%`
- `coke_amount_wt_pct`: `0.0%`

## 需要继续寻找 PDF / HTML fulltext 的来源

- `paper_id=paper_0101`; `source_quality_type=redirect_or_forbidden`; `journal=Applied Catalysis B: Environmental`; `journal_impact_factor=21.1`; `priority_score=88.5`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0124`; `source_quality_type=redirect_or_forbidden`; `journal=Chemical Engineering Journal`; `journal_impact_factor=13.2`; `priority_score=85.5`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0194`; `source_quality_type=abstract_only`; `journal=Journal of Materials Chemistry A`; `journal_impact_factor=9.5`; `priority_score=91.0`; `recommended_next_action=extract_metadata_then_find_fulltext_for_experimental_fields`
- `paper_id=paper_0159`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=88.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0166`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=88.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0191`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=85.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0150`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=84.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0180`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=84.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0099`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0193`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0221`; `source_quality_type=redirect_or_forbidden`; `journal=Fuel Processing Technology`; `journal_impact_factor=7.7`; `priority_score=91.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0157`; `source_quality_type=redirect_or_forbidden`; `journal=Fuel`; `journal_impact_factor=7.5`; `priority_score=81.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0007`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0202`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of the Energy Institute`; `journal_impact_factor=6.2`; `priority_score=78.0`; `recommended_next_action=find_pdf_or_open_access_fulltext`

## 人工 PDF 优先清单

- 待人工合法下载 PDF 的优先记录数：`23`
- `paper_id=paper_0158`; `journal=ACS Catalysis`; `journal_impact_factor=13.1`; `priority_score=98.5`; `doi=10.1021/acscatal.6b01133`
- `paper_id=paper_0153`; `journal=ACS Catalysis`; `journal_impact_factor=13.1`; `priority_score=91.5`; `doi=10.1021/acscatal.5b01221`
- `paper_id=paper_0194`; `journal=Journal of Materials Chemistry A`; `journal_impact_factor=9.5`; `priority_score=91.0`; `doi=10.1039/d0ta11359j`
- `paper_id=paper_0221`; `journal=Fuel Processing Technology`; `journal_impact_factor=7.7`; `priority_score=91.0`; `doi=10.1016/j.fuproc.2025.108325`
- `paper_id=paper_0101`; `journal=Applied Catalysis B: Environmental`; `journal_impact_factor=21.1`; `priority_score=88.5`; `doi=10.1016/j.apcatb.2010.10.026`
- `paper_id=paper_0056`; `journal=Chemical Engineering Journal`; `journal_impact_factor=13.2`; `priority_score=88.5`; `doi=10.1016/j.cej.2005.06.004`
- `paper_id=paper_0037`; `journal=Chemical Engineering Journal`; `journal_impact_factor=13.2`; `priority_score=88.5`; `doi=10.1016/s1385-8947(00)00367-3`
- `paper_id=paper_0166`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=88.0`; `doi=10.1016/j.ijhydene.2017.06.096`
- `paper_id=paper_0159`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=88.0`; `doi=10.1016/j.ijhydene.2016.05.109`
- `paper_id=paper_0103`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=85.0`; `doi=10.1016/j.ijhydene.2010.06.049`
- `paper_id=paper_0180`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=84.0`; `doi=10.1016/j.ijhydene.2019.04.287`
- `paper_id=paper_0150`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=84.0`; `doi=10.1016/j.ijhydene.2015.06.104`
- `paper_id=paper_0161`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=82.0`; `doi=10.1016/j.ijhydene.2016.07.245`
- `paper_id=paper_0208`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=81.0`; `doi=10.1016/j.ijhydene.2023.09.167`
- `paper_id=paper_0031`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `priority_score=81.0`; `doi=10.1016/s0360-3199(99)00011-7`

## 是否建议优先做 PDF 获取增强

- 建议继续优先增强合法 PDF / HTML fulltext 获取，而不是扩大候选池。
- 当前瓶颈不是候选文献数量，而是可用于实验字段抽取的全文来源数量。
- 当 `pdf_fulltext` 或 `html_fulltext` 达到一批稳定样本后，再重新运行 stage5 的 metadata 与 experimental 抽取更合理。
