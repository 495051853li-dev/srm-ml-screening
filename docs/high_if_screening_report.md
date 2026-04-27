# 高 IF 优先筛选报告

## 任务目标

本轮筛选暂停了以低质量候选文献为主的复核路径，改为在候选文献层重新执行“高质量优先筛选”。新的核心原则是：

- `journal_impact_factor` 仅作为当前第一批文献筛选的硬指标使用
- `journal_impact_factor` 不作为后续机器学习输入特征
- 第一批正式抽取优先考虑 `journal_article`、明确 SRM 相关、可提取性较高、且 `journal_impact_factor >= 6.0` 的文章
- `review` 即使影响因子较高，也仅保留为背景参考，不进入第一批正式抽取

## 总体统计

- 原始候选文献：222 篇
- 成功补全期刊 IF 的候选文献：148 篇
- 仍需人工补期刊指标核查：74 篇
- `IF >= 6.0` 且主题明确相关的 `journal_article`：54 篇
- 最终进入第一批高优先池：15 篇
- 备选低 IF / 需人工补期刊指标池：182 篇

## 第一批高优先池

当前第一批高优先池保存在：

- [data/processed/first_batch_priority_papers_if6plus.csv](D:\ML\srm\srm_ml_screening\data\processed\first_batch_priority_papers_if6plus.csv)

前 20 条如下：

| paper_id | year | journal | IF | Ni-based | title |
| --- | ---: | --- | ---: | --- | --- |
| paper_0220 | 2024.0 | ACS Catalysis | 13.1 | yes | Structural Changes of Ni and Ni–Pt Methane Steam Reforming Catalysts During Activation, Reaction, and Deactivation Under Dynamic Reaction Conditions |
| paper_0101 | 2010.0 | Applied Catalysis B: Environmental | 21.1 | yes | Effect of nickel nano-particle sintering on methane reforming activity of Ni-CGO cermet anodes for internal steam reforming SOFCs |
| paper_0221 | 2025.0 | Fuel Processing Technology | 7.7 | yes | Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M = Ni, Mg, Co) supports for enhanced catalyst stability |
| paper_0194 | 2021.0 | Journal of Materials Chemistry A | 9.5 | yes | Ni-based bimetallic nano-catalysts anchored on BaZr<sub>0.4</sub>Ce<sub>0.4</sub>Y<sub>0.1</sub>Yb<sub>0.1</sub>O<sub>3−δ</sub> for internal steam reforming of methane in a low-temperature proton-conducting ceramic fuel cell |
| paper_0166 | 2017.0 | International Journal of Hydrogen Energy | 8.3 | yes | Effect of Pt doping on activity and stability of Ni/MgAl2O4 catalyst for steam reforming of methane at ambient and high pressure condition |
| paper_0159 | 2016.0 | International Journal of Hydrogen Energy | 8.3 | yes | Effect of calcination temperature on stability and activity of Ni/MgAl2O4 catalyst for steam reforming of methane at high pressure condition |
| paper_0180 | 2019.0 | International Journal of Hydrogen Energy | 8.3 | yes | Hydrogen production by steam reforming of methane over nickel based structured catalysts supported on calcium aluminate modified SiC |
| paper_0150 | 2015.0 | International Journal of Hydrogen Energy | 8.3 | yes | Hydrogen production by steam reforming of methane over mixed Ni/MgAl + CrFe 3 O 4 catalysts |
| paper_0157 | 2016.0 | Fuel | 7.5 | yes | Characterization and performance evaluation of Ni-based catalysts with Ce promoter for methane and hydrocarbons steam reforming process |
| paper_0124 | 2011.0 | Chemical Engineering Journal | 13.2 | no | Thermal and hydrothermal stability of a metal monolithic anodic alumina support for steam reforming of methane |
| paper_0191 | 2020.0 | International Journal of Hydrogen Energy | 8.3 | no | Supported catalysts for induction-heated steam reforming of methane |
| paper_0202 | 2023.0 | Journal of the Energy Institute | 6.2 | no | Hydrogen production by steam reforming of methane over hollow, bulk, and co-precipitated Ni–Ce–Al2O3 catalysts: Optimization via design of experiments |
| paper_0193 | 2020.0 | International Journal of Hydrogen Energy | 8.3 | no | Ultracompact methane steam reforming reactor based on microwaves susceptible structured catalysts for distributed hydrogen production |
| paper_0099 | 2010.0 | International Journal of Hydrogen Energy | 8.3 | no | Catalytic performance of Ni catalysts for steam reforming of methane at high space velocity |
| paper_0007 | 1985.0 | Journal of Catalysis | 6.5 | no | Carbon deposition and methane steam reforming on silica-supported Ni$z.sbnd;Cu catalysts |

## 备选池说明

备选池保存在：

- [data/processed/backup_low_if_papers.csv](D:\ML\srm\srm_ml_screening\data\processed\backup_low_if_papers.csv)

这些记录通常满足“主题相关”，但因为以下原因没有进入第一批高优先池：

- 期刊 IF 低于 6.0
- 期刊 IF 缺失，需人工核查
- 摘要/元数据中条件或性能信号偏弱
- 文献类型是 `review`

## 被降级的原先优先文献

以下文献在旧版“可提取性优先”排序里优先级较高，但在新的“高 IF 优先”逻辑下被降级：

| paper_id | year | journal | IF | Ni-based | title |
| --- | ---: | --- | ---: | --- | --- |
| paper_0078 | 2008.0 | JOURNAL OF CHEMICAL ENGINEERING OF JAPAN |  | yes | A Plate-Type Anodic Alumina Supported Nickel Catalyst for Methane Steam Reforming |
| paper_0079 | 2008.0 | Applied Catalysis A General | 4.8 | yes | A novel catalyst with plate-type anodic alumina supports, Ni/NiAl2O4/γ-Al2O3/alloy, for steam reforming of methane |
| paper_0093 | 2009.0 | Journal of Materials Chemistry |  | yes | Ni@SiO<sub>2</sub>yolk-shell nanoreactor catalysts: High temperature stability and recyclability |
| paper_0128 | 2012.0 | ChemCatChem |  | yes | Perovskite NaCeTi<sub>2</sub>O<sub>6</sub>‐Supported Ni Catalysts for CH<sub>4</sub> Steam Reforming |
| paper_0138 | 2013.0 | Catalysts | 4.0 | yes | Ni-Based Catalysts for Low Temperature Methane Steam Reforming: Recent Results on Ni-Au and Comparison with Other Bi-Metallic Systems |
| paper_0143 | 2014.0 | ChemCatChem |  | yes | Methane Steam Reforming over a Ni/NiAl<sub>2</sub>O<sub>4</sub> Model Catalyst—Kinetics |
| paper_0171 | 2018.0 | Angewandte Chemie International Edition |  | yes | Dual‐Function Cobalt–Nickel Nanoparticles Tailored for High‐Temperature Induction‐Heated Steam Methane Reforming |
| paper_0179 | 2019.0 | ACS Applied Energy Materials | 5.6 | yes | Hydrogen Production via Low-Temperature Steam–Methane Reforming Using Ni–CeO<sub>2</sub>–Al<sub>2</sub>O<sub>3</sub> Hybrid Nanoparticle Clusters as Catalysts |
| paper_0203 | 2023.0 | Energies | 3.2 | yes | Hydrogen-Rich Syngas Production via Dry and Steam Reforming of Methane in Simulated Producer Gas over ZSM-5-Supported Trimetallic Catalysts |
| paper_0002 | 1973.0 | Journal of the Chemical Society Faraday Transactions 1 Physical Chemistry in Condensed Phases |  | yes | Mechanism of the steam reforming of methane over a coprecipitated nickel-alumina catalyst |
| paper_0080 | 2008.0 | Energy & Fuels | 5.3 | yes | Effect of Ce<sub><i>x</i></sub>Zr<sub>1-<i>x</i></sub>O<sub>2</sub> Promoter on Ni-Based SBA-15 Catalyst for Steam Reforming of Methane |
| paper_0119 | 2011.0 | ChemCatChem |  | yes | Progresses in the Preparation of Coke Resistant Ni‐based Catalyst for Steam and CO<sub>2</sub> Reforming of Methane |
| paper_0023 | 1996.0 | Industrial & Engineering Chemistry Research | 3.9 | no | Simultaneous Carbon Dioxide and Steam Reforming of Methane to Syngas over NiO−CaO Catalyst |
| paper_0046 | 2003.0 | AIChE Journal |  | no | Steam reforming of methane and water‐gas shift in catalytic wall reactors |
| paper_0047 | 2003.0 | Applied Catalysis A General | 4.8 | yes | Steam reforming of methane over nickel catalysts at low reaction temperature |

详细降级原因：

- `paper_0078`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0079`: 期刊 IF=4.8，低于第一批高质量门槛 6.0
- `paper_0093`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0128`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0138`: 期刊 IF=4.0，低于第一批高质量门槛 6.0
- `paper_0143`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0171`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0179`: 期刊 IF=5.6，低于第一批高质量门槛 6.0
- `paper_0203`: 期刊 IF=3.2，低于第一批高质量门槛 6.0
- `paper_0002`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0080`: 期刊 IF=5.3，低于第一批高质量门槛 6.0
- `paper_0119`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0023`: 期刊 IF=3.9，低于第一批高质量门槛 6.0
- `paper_0046`: 期刊 IF 未能可靠补全，暂列人工核查或备选池
- `paper_0047`: 期刊 IF=4.8，低于第一批高质量门槛 6.0

## 对 `paper_0078` 和 `paper_0221` 的建议

### `paper_0078`

- 题目：A Plate-Type Anodic Alumina Supported Nickel Catalyst for Methane Steam Reforming
- 期刊：JOURNAL OF CHEMICAL ENGINEERING OF JAPAN
- IF：未可靠补全
- 当前标签：low_priority
- 建议：不建议继续作为第一批优先复核对象

原因：

- 期刊 IF 未能可靠补全，暂列人工核查或备选池

### `paper_0221`

- 题目：Support effect in Ni-based catalysts for methane steam reforming: Role of MxOy-Al2O3 (M = Ni, Mg, Co) supports for enhanced catalyst stability
- 期刊：Fuel Processing Technology
- IF：7.7
- 当前标签：top_priority
- 建议：仍建议保留在第一批优先复核池中

原因：

- 虽然相关，但在高 IF 优先逻辑下未进入第一批池

## 结论

这轮高 IF 优先重排后，第一批正式抽取不再由“当前可抓到的页面质量”主导，而改为由“SRM 相关性 + 可提取性 + 高质量期刊”共同决定。这样做的好处是：

- 第一批抽取池的文献质量更稳定
- 后续人工复核时间更值得投入
- 可以避免把低 IF 或来源证据不足的文章过早推入正式抽取

同时需要明确提醒：

- 期刊 IF 只是当前文献筛选硬指标，不是后续机器学习特征
- 若将其错误地带入模型，会构成明显的数据泄漏风险
