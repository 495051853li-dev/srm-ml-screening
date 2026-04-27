# 第一批人工复核指南

本指南用于配合 `data/processed/srm_extraction_review_pack.csv` 对当前 6 篇自动抽取草稿进行逐篇人工复核。

参考来源：

- `docs\first_batch_screening_report.md`
- `docs\auto_extraction_summary.md`

## 复核顺序

建议优先按以下顺序复核：

1. `paper_0078` - A Plate-Type Anodic Alumina Supported Nickel Catalyst for Methane Steam Reforming。优先级：`high`，自动抽取置信度：`low_to_medium`。
2. `paper_0221` - Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M = Ni, Mg, Co) supports for enhanced catalyst stability。优先级：`high`，自动抽取置信度：`low_to_medium`。
3. `paper_0002` - Mechanism of the steam reforming of methane over a coprecipitated nickel-alumina catalyst。优先级：`medium`，自动抽取置信度：`low`。
4. `paper_0079` - A novel catalyst with plate-type anodic alumina supports, Ni/NiAl2O4/γ-Al2O3/alloy, for steam reforming of methane。优先级：`medium`，自动抽取置信度：`low`。
5. `paper_0093` - Ni@SiO<sub>2</sub>yolk-shell nanoreactor catalysts: High temperature stability and recyclability。优先级：`medium`，自动抽取置信度：`low`。
6. `paper_0194` - Ni-based bimetallic nano-catalysts anchored on BaZr<sub>0.4</sub>Ce<sub>0.4</sub>Y<sub>0.1</sub>Yb<sub>0.1</sub>O<sub>3−δ</sub> for internal steam reforming of methane in a low-temperature proton-conducting ceramic fuel cell。优先级：`medium`，自动抽取置信度：`low`。

排序依据：

- 优先处理 `review_priority = high` 的记录
- 在同优先级内，优先处理自动抽取置信度相对更高的记录
- 这样可以先把最有可能快速转成正式人工提取结果的文献处理掉

## 每篇最优先核对的 5 个字段

### paper_0078 - A Plate-Type Anodic Alumina Supported Nickel Catalyst for Methane Steam Reforming

- `active_metal_primary_loading_wt_pct`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `time_on_stream_h`

### paper_0221 - Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M = Ni, Mg, Co) supports for enhanced catalyst stability

- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `time_on_stream_h`
- `methane_conversion_pct`

### paper_0002 - Mechanism of the steam reforming of methane over a coprecipitated nickel-alumina catalyst

- `active_metal_primary_loading_wt_pct`
- `preparation_method`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`

### paper_0079 - A novel catalyst with plate-type anodic alumina supports, Ni/NiAl2O4/γ-Al2O3/alloy, for steam reforming of methane

- `preparation_method`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`
- `time_on_stream_h`

### paper_0093 - Ni@SiO<sub>2</sub>yolk-shell nanoreactor catalysts: High temperature stability and recyclability

- `active_metal_primary_loading_wt_pct`
- `preparation_method`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`

### paper_0194 - Ni-based bimetallic nano-catalysts anchored on BaZr<sub>0.4</sub>Ce<sub>0.4</sub>Y<sub>0.1</sub>Yb<sub>0.1</sub>O<sub>3−δ</sub> for internal steam reforming of methane in a low-temperature proton-conducting ceramic fuel cell

- `support_primary`
- `preparation_method`
- `temperature_c`
- `pressure_bar`
- `steam_to_carbon_ratio`

## 最容易定义混乱的字段

- `active_metal_primary_loading_wt_pct`：要区分主金属负载、总负载和 nominal / measured basis
- `steam_to_carbon_ratio`：需确认是否为真正的 S/C，而不是由进料体积分数间接推断
- `pressure_bar`：要注意原文可能使用 atm、kPa 或 MPa
- `methane_conversion_pct` 与 `h2_yield_pct`：要确认是瞬时值、稳态值、峰值还是平均值
- `stability_duration_h` 与 `conversion_drop_pct_points`：必须确认是否来自明确稳定性测试，而不是摘要性描述
- `coke_amount_mg_gcat` 与 `coke_amount_wt_pct`：不要混用不同归一化口径
- `preparation_method`：摘要里经常只给部分制备信息，必要时需继续追全文

## 如何把复核后的结果转入正式人工提取表

1. 以 `srm_extraction_review_pack.csv` 作为复核底稿，不要直接把自动草稿当作正式数据。
2. 打开 `source_file_path` 对应的本地页面，结合 `source_excerpt` 快速定位信息。
3. 只把已经人工确认的字段转写到正式人工提取表 `data/processed/srm_literature_extraction_template.csv`。
4. 无法确认的字段继续留空，不要猜测填写。
5. `derived_*` 字段保持为空。
6. 每完成一小批转写后，运行 validator：

```powershell
python src/validate_extraction_dataset.py --input data/processed/srm_literature_extraction_template.csv
```


## 复核后如何转入正式人工提取表

1. 先打开 `review_ready_for_entry.csv` 或 `batch1_entry_candidates.csv`，确认本条记录是否真的具备转入条件。
2. 必须人工确认后才能转入的字段：
- `active_metal_primary`
- `support_primary`
- `preparation_method`
- `temperature_c`
- `steam_to_carbon_ratio`
- 至少一个核心性能字段：`methane_conversion_pct` 或 `h2_yield_pct`
- `measured_value_basis`
3. 可以暂时留空的字段：
- `active_metal_secondary`
- `active_metal_secondary_loading_wt_pct`
- `pressure_bar`
- `time_on_stream_h`
- `stability_duration_h`
- `coke_amount_mg_gcat`
- `coke_amount_wt_pct`
- 其他原文未明确报告的扩展字段
4. 以下情况建议暂不纳入正式表：
- 当前来源只是跳转页、摘要页或二级页面，缺少可核对证据
- 反应条件和性能字段同时大面积缺失
- 主题边界不清，无法确认是否为第一批重点 SRM 文章
- 关键数值只能靠猜测或主观推断补齐
5. 转入时仍然遵守原始提取规则：
- 不写入任何 `derived_*` 字段
- 无法确认的值保持为空
- 每转入一小批后运行 validator


## 建议的人工复核节奏

- 先完成前 3 篇高优先级文献
- 再检查一次字段缺失模式是否一致
- 如果发现某类字段持续无法从摘要页获得，就把这类字段统一标记为“需要进一步全文查找”