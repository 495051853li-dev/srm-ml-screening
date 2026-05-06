# Legal Fulltext Access Policy

## 允许的访问方式

本项目允许自动获取以下来源：

- 当前网络 IP 可直接访问的 publisher PDF 或 HTML fulltext。
- OpenAlex、Crossref、Unpaywall 或 publisher 页面中直接给出的合法 PDF / HTML 链接。
- DOI landing page、publisher landing page 和 Crossref link，用于定位合法全文来源。
- 用户手动下载并放入 `data/raw/pdfs/` 的合法 PDF。

这意味着流程不只限于 open access。如果机构订阅权限使出版社页面直接返回 PDF 或 HTML fulltext，脚本可以保存该内容并标记为 `institutional_pdf` 或 `institutional_html_fulltext`。

## 禁止的访问方式

本项目不会实现、调用或建议以下行为：

- 绕过 paywall。
- 绕过验证码、登录、Cloudflare 或其他反爬虫访问控制。
- 使用 Sci-Hub、盗版 PDF 站点或其他非授权来源。
- 对 403、captcha、login_required、paywall_or_login_required 响应进行规避尝试。
- 把登录页、摘要页、跳转页、目录页伪装成 fulltext。

遇到上述情况时，脚本只记录失败状态，并将论文加入人工合法获取清单。

## 状态解释

- `success_local_pdf`：本地合法 PDF 可用。
- `success_oa_pdf` / `success_oa_html`：开放全文可用。
- `success_institutional_pdf` / `success_institutional_html`：当前机构 IP 直接返回 publisher fulltext。
- `abstract_only`：只允许题录和非常有限的催化剂信息抽取，不允许实验字段抽取。
- `forbidden`、`paywall_or_login_required`、`captcha_or_bot_blocked`：停止自动尝试，进入人工合法获取流程。

## 数据使用提醒

全文访问权限只影响“是否能看到原文”，不改变数据质量要求。自动抽取结果仍必须人工复核，尤其是温度、S/C、压力、GHSV、转化率、H2 yield/selectivity、稳定性和积碳字段。

`journal_impact_factor` 可以用于当前文献筛选优先级，但不建议默认作为后续机器学习特征，以避免文献来源偏差泄漏。
