# paper_0221 深度复核包

## 论文基本信息

- 标题：Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M = Ni, Mg, Co) supports for enhanced catalyst stability
- 第一作者：Yi Lin
- 年份：2025
- 期刊：Fuel Processing Technology
- DOI：10.1016/j.fuproc.2025.108325
- 来源文件：`outputs\fulltext\paper_0221.html`
- 来源摘录置信度：`low`

## 当前自动抽取到的字段

- `catalyst_family`: Ni_based
- `active_metal_primary`: Ni
- `active_metal_primary_loading_wt_pct`: 10
- `support_primary`: Al2O3
- `preparation_method`: impregnation

## 当前缺失字段

- `active_metal_secondary`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `time_on_stream_h`
- `methane_conversion_pct`
- `h2_yield_pct`
- `stability_duration_h`
- `coke_amount_mg_gcat`
- `coke_amount_wt_pct`

## 最优先核对的 5 个字段

- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `time_on_stream_h`
- `methane_conversion_pct`

## 字段对应来源摘录

### `temperature_c`

- 来源文件：`outputs\fulltext\paper_0221.html`
- 当前值：``
- 摘录：Redirecting

### `pressure_bar`

- 来源文件：`outputs\fulltext\paper_0221.html`
- 当前值：``
- 摘录：Redirecting

### `steam_to_carbon_ratio`

- 来源文件：`outputs\fulltext\paper_0221.html`
- 当前值：``
- 摘录：Redirecting

### `time_on_stream_h`

- 来源文件：`outputs\fulltext\paper_0221.html`
- 当前值：``
- 摘录：Redirecting

### `methane_conversion_pct`

- 来源文件：`outputs\fulltext\paper_0221.html`
- 当前值：``
- 摘录：Redirecting

## 字段定义提醒

- `methane_conversion_pct`：确认是甲烷转化率，不要与产氢收率或选择性混淆。
- `h2_yield_pct`：确认分母定义，部分文章按理论产氢量，有些按转化甲烷计。
- `h2_selectivity_pct` 与 `co_selectivity_pct`：只在原文明确给出时填写，不要从文字印象推断。
- `stability_duration_h` 与 `conversion_drop_pct_points`：必须基于明确稳定性测试或端点。
- `active_metal_primary_loading_wt_pct`：区分 nominal / measured，不清楚时不要硬填。

## 建议的 reviewer action

- 优先核对反应条件与核心性能字段，必要时继续向论文全文或 PDF 深入查找

## 是否建议进入正式人工提取表

- 建议：`not_yet`，当前证据不足以直接转入正式表。

## 是否建议继续找 PDF / 全文

- 建议：`yes`。当前页面更像摘要页、跳转页或证据不足页面，建议继续寻找 PDF 或正文。