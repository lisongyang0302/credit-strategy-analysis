# P2b · Lending Club 真实贷款数据 · 风控策略分析

> 数据：**真实公开数据**（[Lending Club 2007-2011](https://www.kaggle.com/datasets/imsparsh/lending-club-loan-dataset-2007-2011)，39,717 笔 × 111 列），结论从真实业务数据中挖掘。

## 核心结果（全部来自真实数据）

| 维度 | 发现 |
|---|---|
| 样本 | 38,577 笔有效放款（剔除 Current 观察期），坏账率 **14.59%**（Charged Off 口径） |
| **定价有效性** | grade 定价利率 vs 实际坏账率相关系数 0.995（A-G 阶梯与坏账单调——验证评级变量可用于策略分层） |
| **真实 Vintage** | 36 月账龄累计坏账率 8.45%~21.28%，2008 金融危机期放款组合坏账显著更高——真实数据才有宏观周期波动 |
| **用途归因** | small_business 坏账率 27.08% 全场最高、定价利率仅 12.90%——**风险定价不足，策略机会点**（小企业用途低估定价是 Lending Club 研究文献已知现象，本项目独立复现并量化） |

> 注：本数据为 2007-2011 区间（社区标准干净抽取）。清洗口径：原始 39,717 笔，剔除 Current（观察期未完整）1,140 笔 → 38,577 笔。

| 报表 | Vintage 矩阵 / 月度 KPI / 定价有效性 / 用途归因（MySQL 8.0 原生） |

## 项目结构

```
credit-strategy-analysis/
├── data/loan.csv                    # 原始数据（Kaggle 下载，不入库）
├── sql/02b_reports_lendingclub.sql  # 四张报表（MySQL 8.0）
├── src/
│   ├── step1_clean_and_load.py      # 清洗+目标定义+入库 MySQL risk_project02
│   ├── _explore.py                  # 数据摸底
│   └── step2_reports_and_analysis.py# 报表执行+归因分析+Excel 周报
└── outputs/
    ├── lc_analysis.md               # 分析报告
    └── lc_strategy_report.xlsx      # Excel 周报（透视表+四张报表）
```

## 复现

```bash
python src/step1_clean_and_load.py      # 清洗+入库（需 MYSQL_PWD 环境变量）
python src/step2_reports_and_analysis.py # 四报表+归因+Excel
```

数据从 Kaggle 下载 `loan.csv` 放入 `data/`。

> 开发方式：AI 辅助编程，业务决策与验证人工把关
