# 来源质量诊断报告

## 当前 ready_for_extraction 记录的来源类型

- `redirect_or_forbidden`: `13`
- `abstract_only`: `1`

## 真正可用于 experimental extraction 的记录数量

- 当前 ready_for_extraction 记录数：`14`
- 允许 experimental 抽取的记录数：`0`
- experimental 草稿记录数：`0`

## experimental 字段覆盖率低的主要原因

- 当前没有 `pdf_fulltext` 或 `html_fulltext` 来源进入 experimental 抽取。
- 多数来源实际是 `Redirecting`、DOI landing page 或摘要页，不包含完整实验表格、实验方法和性能结果。
- `abstract_only` 来源可以帮助识别催化剂体系，但不允许填写温度、S/C、GHSV、conversion、yield 等具体实验字段。
- 因不同温度、S/C、压力、GHSV 下的 SRM 结果不可直接比较，experimental 字段必须有原文数值和单位证据才允许填写。

当前关键 experimental 字段覆盖率：
- `temperature_c`: `0.0%`
- `pressure_bar`: `0.0%`
- `steam_to_carbon_ratio`: `0.0%`
- `gas_hourly_space_velocity_h_inv`: `0.0%`
- `methane_conversion_pct`: `0.0%`
- `h2_yield_pct`: `0.0%`
- `stability_duration_h`: `0.0%`
- `coke_amount_wt_pct`: `0.0%`

## 需要继续找 PDF / HTML fulltext 的来源

- `paper_id=paper_0101`; `source_quality_type=redirect_or_forbidden`; `journal=Applied Catalysis B: Environmental`; `journal_impact_factor=21.1`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0124`; `source_quality_type=redirect_or_forbidden`; `journal=Chemical Engineering Journal`; `journal_impact_factor=13.2`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0220`; `source_quality_type=redirect_or_forbidden`; `journal=ACS Catalysis`; `journal_impact_factor=13.1`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0194`; `source_quality_type=abstract_only`; `journal=Journal of Materials Chemistry A`; `journal_impact_factor=9.5`; `recommended_next_action=extract_metadata_then_find_fulltext_for_experimental_fields`
- `paper_id=paper_0166`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0159`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0191`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0180`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0150`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0193`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0099`; `source_quality_type=redirect_or_forbidden`; `journal=International Journal of Hydrogen Energy`; `journal_impact_factor=8.3`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0221`; `source_quality_type=redirect_or_forbidden`; `journal=Fuel Processing Technology`; `journal_impact_factor=7.7`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0157`; `source_quality_type=redirect_or_forbidden`; `journal=Fuel`; `journal_impact_factor=7.5`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0007`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of Catalysis`; `journal_impact_factor=6.5`; `recommended_next_action=find_pdf_or_open_access_fulltext`
- `paper_id=paper_0202`; `source_quality_type=redirect_or_forbidden`; `journal=Journal of the Energy Institute`; `journal_impact_factor=6.2`; `recommended_next_action=find_pdf_or_open_access_fulltext`

## 是否建议优先做 PDF 获取增强

- 建议优先增强 PDF / HTML fulltext 获取，而不是扩大候选池。
- 当前瓶颈不是候选文献数量，而是来源质量不足导致 experimental 字段无法可靠落值。
- 在 fulltext 获取率提高前，扩大到 top 50 / top 100 会主要增加空抽取和人工复核负担。
