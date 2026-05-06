# Stage4.5 Fulltext Acquisition Strategy

## 目标

`stage4.5_fulltext_acquisition_enhancement` 的目标是提高可用 `pdf_fulltext` / `html_fulltext` 来源数量，为后续 stage5 实验字段抽取提供可靠输入。

当前策略不再只限制于 OA 来源。如果当前网络 IP 对出版社具有合法机构访问权限，流程可以保存当前会话直接返回的 publisher PDF 或 HTML fulltext。

## 合法来源范围

允许使用：

- `local_pdf`：用户手动合法下载并放入 `data/raw/pdfs/` 的 PDF。
- `oa_pdf` / `oa_html_fulltext`：OpenAlex、Unpaywall、Crossref 或 publisher 页面直接提供的开放全文。
- `institutional_pdf` / `institutional_html_fulltext`：当前机构 IP 或正常浏览会话可直接访问的 publisher PDF / HTML fulltext。
- `publisher_landing_page`、`doi_landing_page`、`crossref_link`、`openalex_location`、`unpaywall_location`：用于定位可用来源，但 landing page 本身通常不能进入实验字段抽取。

禁止使用：

- 绕过 paywall、登录、验证码、Cloudflare 或其他反爬虫访问控制。
- Sci-Hub、盗版 PDF 站点或任何非授权来源。
- 把摘要页、登录页、跳转页或目录页误标为 fulltext。
- 根据标题、摘要或来源页面编造实验条件、性能或积碳数据。

## 候选来源发现

运行：

```powershell
python src/discover_fulltext_sources.py --eligible data/processed/eligible_high_if_pool.csv --scored data/processed/candidate_papers_high_if_scored.csv --manifest data/processed/fulltext_fetch_manifest.csv --output data/processed/fulltext_source_candidates.csv --limit 20
```

输出：

- `data/processed/fulltext_source_candidates.csv`

关键字段：

- `candidate_source_type`：`local_pdf`, `oa_pdf`, `oa_html_fulltext`, `institutional_pdf`, `institutional_html_fulltext`, `publisher_landing_page`, `doi_landing_page`, `crossref_link`, `openalex_location`, `unpaywall_location`, `manual_required`
- `access_route`：`local_pdf`, `open_access`, `institutional_access`, `publisher_landing`, `doi_landing`, `manual_required`, `unknown`
- `institutional_access_possible`：表示该候选是否可能依赖当前机构 IP 直接访问。

如果设置 `UNPAYWALL_EMAIL` 环境变量或传入 `--unpaywall-email`，脚本会额外查询 Unpaywall；否则会跳过 Unpaywall live 查询。

## 授权全文抓取

运行：

```powershell
python src/fetch_fulltext_authorized.py --candidates data/processed/fulltext_source_candidates.csv --manifest data/processed/fulltext_fetch_manifest.csv --log data/processed/fulltext_candidate_fetch_log.csv --limit 20 --skip-existing --sleep 1.0 --timeout 30 --max-per-domain 5
```

抓取顺序：

1. 先检查本地 PDF。
2. 再检查 OpenAlex / Unpaywall / Crossref 发现的全文链接。
3. 再尝试 DOI landing page、publisher landing page 和 publisher PDF/HTML pattern。
4. 如果当前 IP 直接返回 PDF 或 fulltext HTML，则保存并标记为 OA 或 institutional success。
5. 如果返回摘要页、目录页、Redirecting、Access Denied、Forbidden、Captcha、Login Required 或 paywall 提示，则只记录状态，不继续规避。

## 抓取状态

支持状态：

- `success_local_pdf`
- `success_oa_pdf`
- `success_oa_html`
- `success_institutional_pdf`
- `success_institutional_html`
- `abstract_only`
- `publisher_landing_only`
- `doi_landing_only`
- `redirect_only`
- `forbidden`
- `paywall_or_login_required`
- `captcha_or_bot_blocked`
- `timeout`
- `no_useful_content`
- `parse_failed`
- `manual_required`
- `non_retryable_failure`
- `retryable_failure`

`success_*_pdf` 会被映射为 `source_quality_type=pdf_fulltext`。

`success_*_html` 会被映射为 `source_quality_type=html_fulltext`。

`abstract_only` 只允许 metadata 和非常有限的催化剂层面信息，不允许抽取具体反应条件和性能值。

`forbidden`、`paywall_or_login_required`、`captcha_or_bot_blocked`、`redirect_only` 不进入抽取池。

## 访问频率控制

`fetch_fulltext_authorized.py` 支持：

- `--sleep`：每次 HTTP 请求后的等待时间。
- `--timeout`：单次请求超时。
- `--max-per-domain`：单次运行中每个域名的最大请求数。
- `--limit`：限制处理论文数量。
- `--max-retries`：单个候选 URL 的有限重试次数。
- `--skip-existing`：跳过已成功的 fulltext 记录。
- `--retry-failed`：重跑失败记录。

单篇失败不会阻塞整体流程。

## 本地 PDF 补充

将合法获得的 PDF 放入：

```text
data/raw/pdfs/
```

推荐文件名包含 `paper_id`，例如：

```text
paper_0220.pdf
```

然后运行：

```powershell
python src/ingest_local_pdfs.py
```

成功解析的 PDF 会更新 `fulltext_fetch_manifest.csv` 并进入 stage5 ready pool。

## 什么时候重新运行 stage5

建议满足以下条件后再运行 stage5：

- `source_quality_classification.csv` 中有新的 `pdf_fulltext` 或 `html_fulltext`。
- `stage5_ready_pool_checked.csv` 中 `ready_for_experimental=yes` 的记录数增加。
- 对登录页、摘要页、跳转页等来源没有误标为 fulltext。

即使 stage5 可以运行，实验字段仍必须人工复核后才能进入正式表；不同温度、S/C、压力、GHSV 下的数据不能直接比较。
