# PDF Download Workflow

## 目的

`src/download_pdfs_from_table.py` 用于从表格驱动地尝试下载 PDF。它不局限于 OA 文章，会使用当前网络或机构访问权限访问 publisher PDF URL。

这个脚本不会绕过付费墙：
- 如果出版社在当前网络中直接返回 PDF，脚本会保存到 `data/raw/pdfs/`。
- 如果返回登录页、摘要页、HTML、403、跳转页或机构认证页，脚本只记录失败原因，不保存为 PDF。
- 只有通过 PDF 文件头或 PDF content-type 校验的响应才会保存。

## 推荐命令

先小批量测试：

```bash
python src/download_pdfs_from_table.py --input data/processed/manual_pdf_request_list.csv --limit 5 --ingest-after-download
```

扩大到更多记录：

```bash
python src/download_pdfs_from_table.py --input data/processed/manual_pdf_request_list.csv --limit 30 --ingest-after-download
```

如果你确认需要覆盖旧 PDF：

```bash
python src/download_pdfs_from_table.py --overwrite --limit 10 --ingest-after-download
```

## 输出

下载日志：
- `data/processed/pdf_download_log.csv`

PDF 保存目录：
- `data/raw/pdfs/`

如果加上 `--ingest-after-download`，脚本会继续调用：

```bash
python src/ingest_local_pdfs.py
```

成功解析的 PDF 会被标记为：
- `source_quality_type = pdf_fulltext`
- `ready_for_extraction = yes`

## 常见状态

- `downloaded_pdf`：已下载并通过 PDF 校验。
- `skipped_existing`：本地已有同名 PDF，默认不覆盖。
- `forbidden_or_login_required`：当前 HTTP session 没有拿到 PDF，可能需要浏览器登录或手动下载。
- `login_or_paywall_html`：返回的是登录/机构访问/订阅页面。
- `redirect_or_gate_html`：返回的是跳转壳或防机器人页面。
- `not_pdf_html`：返回 HTML 页面，不保存。
- `http_error`：服务器返回非 2xx 状态。

## 与 stage5 的关系

只有当 `fulltext_fetch_manifest.csv` 中出现 `pdf_fulltext` 或 `html_fulltext` 后，才建议重新运行 stage5 experimental extraction。

如果下载日志中大多是 `login_or_paywall_html` 或 `forbidden_or_login_required`，说明 Python HTTP session 没有继承浏览器登录态。此时可以在浏览器中手动下载 PDF 到 `data/raw/pdfs/`，再运行：

```bash
python src/ingest_local_pdfs.py
```
