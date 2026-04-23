\# AGENTS.md



This repository is for machine-learning-assisted SRM catalyst screening.



Rules:

\- Do not modify raw source files manually or overwrite them.

\- Always inspect data schema before coding.

\- Treat literature data under different temperatures, steam-to-carbon ratios, pressures, and GHSV as potentially non-comparable unless explicitly normalized.

\- Warn about likely data leakage.

\- Prefer reproducible Python scripts in src/ rather than one-off notebook-only work.

\- Save cleaned datasets to data/processed/.

\- Save figures to outputs/figures/ and tables to outputs/tables/.

\- For every ML step, explain assumptions, missing data risks, and validation strategy.

\- Never invent experimental values.

