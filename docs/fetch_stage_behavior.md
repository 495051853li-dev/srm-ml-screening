# Stage4 Fetch Sources 行为说明

`stage4_fetch_sources` 是这套 SRM 批量文献处理 pipeline 的来源获取层。它的目标不是“尽可能深挖单篇论文”，而是为后续批量字段抽取提供一个稳定、可续跑、可审计的来源输入层。

当前 canonical 脚本：
- `src/fetch_sources_stage4.py`

兼容入口：
- `src/fetch_batch_sources.py`
- `src/fetch_priority_fulltext.py`

统一输出 manifest：
- `data/processed/fulltext_fetch_manifest.csv`

## 输入与输出

输入通常是高优先级候选池，例如：
- `data/processed/eligible_high_if_pool.csv`

脚本还会读取检索阶段的原始结果表，用于补充可尝试的 URL：
- `outputs/tables/openalex_raw_results.csv`
- `outputs/tables/crossref_raw_results.csv`

输出包括：
- `data/processed/fulltext_fetch_manifest.csv`
- `outputs/fulltext/` 下保存的本地 HTML / PDF / 其他可访问来源文件

## manifest 字段

`fulltext_fetch_manifest.csv` 至少包含以下字段：

- `paper_id`
- `doi`
- `title`
- `source_url`
- `attempted_url`
- `fetch_status`
- `fetch_attempts`
- `last_fetch_time`
- `retry_recommended`
- `failure_reason`
- `local_saved_path`
- `content_type`
- `content_length`
- `has_useful_text`
- `ready_for_extraction`
- `notes`

为兼容现有下游脚本，manifest 还保留了别名字段：
- `selected_url`
- `local_path`
- `has_text_content`
- `usable_for_extraction`
- `fetch_notes`

## fetch_status 定义

支持以下状态：

- `success`
  已抓取到本地文件，且文本信号足够强，`ready_for_extraction = yes`。

- `skipped_existing`
  该记录此前已经成功抓取且可用于抽取，本次运行直接跳过复用。

- `redirect_only`
  页面表面请求成功，但内容更像重定向页、网关页、机构登录页或空壳页，不能直接进入抽取。

- `forbidden`
  常见于 `403`，通常不建议自动反复重试。

- `timeout`
  请求超时，通常值得后续重试。

- `no_useful_content`
  请求成功但内容过弱，常见于摘要页、目录页或过短落地页。

- `parse_failed`
  本地保存或内容处理失败，通常值得后续重试或修复脚本后重跑。

- `retryable_failure`
  其他可重试失败，例如临时网络错误、`429`、`5xx`。

- `non_retryable_failure`
  其他不建议反复自动重试的失败，例如 `404`、无候选 URL。

## 断点续跑逻辑

Stage4 设计成 manifest 驱动，而不是一次性脚本。

默认规则：

- 已成功且 `has_useful_text = yes`、`ready_for_extraction = yes` 的记录，下次运行默认跳过。
- 已标记为 `forbidden`、`no_useful_content`、`non_retryable_failure` 的记录，下次运行默认不自动重试。
- 已标记为 `timeout`、`redirect_only`、`parse_failed`、`retryable_failure` 的记录，只有在显式使用 `--retry-failed` 时才会重试。
- 单篇失败不会阻塞整批继续处理。

这意味着：

- 可以多次运行同一批次而不需要清空 manifest。
- 可以先跑小批量试验，再逐步扩大到更大的批次。
- 可以把“失败重试”与“首次抓取”分开处理。

## 哪些失败值得重试

通常值得重试：

- `timeout`
- `redirect_only`
- `parse_failed`
- `retryable_failure`

通常不建议自动反复重试：

- `forbidden`
- `no_useful_content`
- `non_retryable_failure`

注意：
- `redirect_only` 不等于“完全没希望”，而是说明当前 URL 更像中转页。后续更适合换 PDF、开放获取页或正文页来源。
- `forbidden` 也不等于永远放弃，而是默认不要继续对同一 URL 做高频重试。

## 哪些失败应进入人工查找全文 / PDF

更适合进入人工补源或定向找 PDF 的情形：

- `forbidden`
- `redirect_only`
- `no_useful_content`
- 重复多次后仍然 `retryable_failure`

这些记录不应在自动层被编造来源或误标记为 `ready_for_extraction = yes`。

## 如何为 stage5 提供稳定输入

下游 `stage5_extract_fields` 应优先只读取：

- `fetch_status` 为 `success` 或 `skipped_existing`
- 且 `has_useful_text = yes`
- 且 `ready_for_extraction = yes`

这样可以减少：

- 对空页、重定向页做无意义抽取
- 因弱来源导致的大量伪缺失
- 将来源问题误判成字段缺失

## 命令行运行方式

推荐的小批量测试命令：

```powershell
python src/fetch_sources_stage4.py --input data/processed/eligible_high_if_pool.csv --output data/processed/fulltext_fetch_manifest.csv --limit 20 --skip-existing
```

重试可重试失败：

```powershell
python src/fetch_sources_stage4.py --input data/processed/eligible_high_if_pool.csv --output data/processed/fulltext_fetch_manifest.csv --limit 20 --skip-existing --retry-failed
```

如果输入是更大的 scored pool，但只想抓 ready 子集：

```powershell
python src/fetch_sources_stage4.py --input data/processed/candidate_papers_high_if_scored.csv --output data/processed/fulltext_fetch_manifest.csv --limit 50 --only-ready-pool --skip-existing
```
