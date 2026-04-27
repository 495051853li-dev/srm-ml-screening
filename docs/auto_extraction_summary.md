# 自动抽取阶段摘要

## 总体统计

- 二次筛选后原始候选数：222
- Top 20 抓取尝试数：20
- 成功获取可用于抽取文本的文献数：9
- 成功生成自动抽取草稿的文献数：6

## 全文获取情况

| paper_id | fetch_status | usable_for_extraction | fetch_notes |
| --- | --- | --- | --- |
| paper_0078 | success | yes | fetched_content_saved |
| paper_0079 | success | yes | fetched_content_saved |
| paper_0093 | success | yes | fetched_content_saved |
| paper_0128 | failed | no | doi_landing:403 |
| paper_0138 | failed | no | doi_landing:403 |
| paper_0143 | failed | no | doi_landing:403 |
| paper_0171 | failed | no | doi_landing:403 |
| paper_0179 | failed | no | doi_landing:403 |
| paper_0194 | success | yes | fetched_content_saved |
| paper_0203 | failed | no | doi_landing:403 |
| paper_0220 | failed | no | doi_landing:403 |
| paper_0221 | success | yes | fetched_content_saved |
| paper_0002 | success | yes | fetched_content_saved |
| paper_0159 | success | yes | fetched_content_saved |
| paper_0166 | success | yes | fetched_content_saved |
| paper_0080 | failed | no | doi_landing:403 |
| paper_0119 | failed | no | doi_landing:403 |
| paper_0023 | failed | no | doi_landing:403 |
| paper_0046 | failed | no | doi_landing:403 |
| paper_0047 | success | yes | fetched_content_saved |

## 字段抽取成功率较高的字段

- `active_metal_primary`：6/6
- `catalyst_family`：6/6
- `support_primary`：5/6
- `preparation_method`：2/6
- `coke_amount_mg_gcat`：0/6
- `coke_amount_wt_pct`：0/6
- `h2_yield_pct`：0/6
- `methane_conversion_pct`：0/6

## 最需要人工复核的字段

- `active_metal_secondary`：容易被双金属或文本上下文误触发
- `active_metal_*_loading_wt_pct`：负载量单位和归属对象需要人工核对
- `temperature_c`、`pressure_bar`、`steam_to_carbon_ratio`：出版商页面经常只给摘要，条件信息覆盖不稳定
- `methane_conversion_pct`、`h2_yield_pct`：摘要中可能只出现部分结果，不能替代全文核查
- `stability_duration_h`、`conversion_drop_pct_points`、`coke_amount_*`：通常最依赖全文和图表，自动抽取成功率较低

## 说明

- 自动抽取草稿只用于人工复核前的预填充，不得直接视为正式实验数据。
- 所有 `derived_*` 字段在本阶段均保持为空。