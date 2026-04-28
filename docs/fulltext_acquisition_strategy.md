# Stage4.5 Fulltext Acquisition Strategy

## 目标

`stage4.5_fulltext_acquisition_enhancement` 的目标是提高可用 `pdf_fulltext` / `html_fulltext` 来源数量，为后续 stage5 实验字段抽取提供可靠输入。这个阶段不做建模，不生成实验数据，也不绕过付费墙。

## 输入与输出

输入文件：
- `data/processed/eligible_high_if_pool.csv`
- `data/processed/candidate_papers_high_if_scored.csv`
- `data/processed/fulltext_fetch_manifest.csv`
- `outputs/tables/openalex_raw_results.csv`
- `outputs/tables/crossref_raw_results.csv`
- `data/raw/pdfs/`

输出文件：
- `data/processed/fulltext_source_candidates.csv`
- `data/processed/fulltext_candidate_fetch_log.csv`
- `data/processed/fulltext_fetch_manifest.csv`
- `data/processed/local_pdf_ingest_log.csv`
- `data/processed/manual_pdf_request_list.csv`

## 合法来源优先级

优先尝试以下合法来源：
- DOI resolver URL，用于发现 publisher landing page。
- OpenAlex / Crossref 已记录的 URL，仅使用本地已有元数据。
- 确定性 publisher landing page 或 PDF URL pattern，例如 ACS 和 RSC 的 DOI 规则。
- 用户手动放入 `data/raw/pdfs/` 的合法 PDF。

不允许：
- 绕过付费墙。
- 使用破解、token、institutional bypass 或非授权访问。
- 根据摘要或标题编造实验条件、性能或全文内容。

## 来源质量分类

`pdf_fulltext` 和 `html_fulltext` 可以进入 metadata + experimental 抽取。

`abstract_only` 只允许题录、催化剂体系和有限催化剂层面的抽取，不允许填写温度、S/C、GHSV、conversion、yield 等具体实验字段。

`doi_landing_page` 只作为题录或来源定位信息，不进入实验字段抽取。

`redirect_or_forbidden`、`navigation_shell`、`no_useful_content` 不进入抽取，应优先寻找 PDF / HTML fulltext。

## 人工 PDF 补充方式

将合法获得的 PDF 放入：

```text
data/raw/pdfs/
```

推荐文件名包含 `paper_id` 或 DOI，例如：

```text
paper_0220.pdf
10.1021_acscatal.3c05847.pdf
paper_0220_10.1021_acscatal.3c05847.pdf
```

然后运行：

```bash
python src/ingest_local_pdfs.py
```

成功解析并判定为 `pdf_fulltext` 的 PDF 会更新 `data/processed/fulltext_fetch_manifest.csv`，并标记 `ready_for_extraction=yes`。

## 自动 PDF 下载方式

如果当前网络或机构 IP 对出版社有访问权限，可以使用表格驱动的 PDF 下载脚本：

```bash
python src/download_pdfs_from_table.py --input data/processed/manual_pdf_request_list.csv --limit 5 --ingest-after-download
```

这个脚本不局限于 OA 文章，会尝试 publisher PDF URL。它仍然遵守边界：只保存服务器实际返回的 PDF；登录页、摘要页、403、跳转页或 HTML 不会被保存为 PDF。

本轮下载测试结果：
- `paper_0220` 已成功保存为 `data/raw/pdfs/paper_0220.pdf`。
- `ingest_local_pdfs.py` 已将 `paper_0220` 标记为 `source_quality_type=pdf_fulltext`。
- `stage5_ready_pool_checked.csv` 当前有 `1` 条 `ready_for_experimental=yes` 记录。
- 后续候选主要返回 `403`、登录/机构访问页、跳转页或 HTML，脚本不会误存为 PDF。

## 什么时候重新运行 stage5

建议满足以下条件后再重新运行 stage5：
- 至少有一批 `pdf_fulltext` 或 `html_fulltext` 记录。
- `fulltext_fetch_manifest.csv` 中这些记录的 `source_quality_type` 明确为 `pdf_fulltext` 或 `html_fulltext`。
- `source_quality_diagnosis_report.md` 显示允许 experimental extraction 的记录数不再为 0。

在此之前，扩大候选池只会增加空抽取和人工复核负担。

## 当前小批量测试结果

本轮仅对 `eligible_high_if_pool.csv` 中当前可用的 15 篇高优先记录运行，没有扩大候选池。

结果摘要：
- 生成 `fulltext_source_candidates.csv` 候选来源 `126` 条。
- 其中 `local_pdf_candidate` 为 `60` 条，用于人工合法 PDF 补充，不进行网络抓取。
- 实际 candidate fetch 记录中：`success=3`、`redirect_only=26`、`forbidden=3`、`non_retryable_failure=2`、`local_candidate_not_fetched=60`。
- 加入表格驱动 PDF 下载器后，当前 `pdf_fulltext=1`、`html_fulltext=0`、`abstract_only=1`。
- `fulltext_fetch_manifest.csv` 中 `ready_for_extraction=yes` 为 `2` 条，其中 `1` 条允许 experimental extraction。
- `manual_pdf_request_list.csv` 当前包含 `23` 条优先人工找 PDF 的记录。

结论：当前已经验证自动 PDF 下载链路可用，但 `pdf_fulltext` 数量仍太少，暂不建议扩大到大规模 experimental extraction。下一步更适合继续批量尝试下载或人工补充合法 PDF / HTML fulltext，尤其是 `manual_pdf_request_list.csv` 中高 IF、Ni-based、SRM 相关性高的记录。
