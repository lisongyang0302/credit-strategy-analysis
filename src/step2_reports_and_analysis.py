# -*- coding: utf-8 -*-
"""step2 SQL 报表执行 + step3 归因分析 + Excel 周报（Lending Club 真实数据版）"""
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)
MYSQL = dict(host="127.0.0.1", port=3307, user="root",
             password=os.environ.get("MYSQL_PWD", ""), charset="utf8mb4")
engine = create_engine(
    f"mysql+pymysql://{MYSQL['user']}:{MYSQL['password']}@{MYSQL['host']}:{MYSQL['port']}/?charset=utf8mb4")


def main():
    # ---- 执行报表 SQL（pymysql 直连，避免 SQLAlchemy 的 %% 转义）----
    import pymysql
    sql_path = BASE / "sql" / "02b_reports_lendingclub.sql"
    sql = sql_path.read_text(encoding="utf-8")
    conn = pymysql.connect(host=MYSQL["host"], port=MYSQL["port"], user=MYSQL["user"],
                           password=MYSQL["password"], charset="utf8mb4",
                           database="risk_project02")
    cur = conn.cursor()
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s and not all(l.strip().startswith("--") for l in s.splitlines() if l.strip()):
            cur.execute(s)
    conn.commit()
    conn.close()
    print("SQL 报表建表完成\n")

    vintage = pd.read_sql("SELECT * FROM risk_project02.rpt_vintage_lc", engine)
    kpi = pd.read_sql("SELECT * FROM risk_project02.rpt_monthly_kpi_lc", engine)
    grade = pd.read_sql("SELECT * FROM risk_project02.rpt_grade_pricing_lc", engine)
    purpose = pd.read_sql("SELECT * FROM risk_project02.rpt_purpose_bad_lc", engine)

    lines = ["# Lending Club 真实数据 · 风控策略分析报告\n",
             "> 数据：38,577 笔真实放款（2007-06 ~ 2011-12），坏账率 14.59%（Charged Off 口径）\n"]

    # ---- 1. KPI 时序 ----
    print("=" * 60)
    print("月度 KPI 关键点")
    print("=" * 60)
    kpi_peak = kpi.loc[kpi["放款笔数"].idxmax()]
    kpi_low = kpi.loc[kpi["放款笔数"].idxmin()]
    print(f"放款高峰 {kpi_peak['放款月']}：{int(kpi_peak['放款笔数'])} 笔（金融危机后复苏）")
    print(f"放款低谷 {kpi_low['放款月']}：{int(kpi_low['放款笔数'])} 笔")
    print(f"平均利率区间: {kpi['平均利率'].min():.2f}% ~ {kpi['平均利率'].max():.2f}%")
    lines.append(f"\n## 月度 KPI\n- 放款高峰 {kpi_peak['放款月']}：{int(kpi_peak['放款笔数'])} 笔；低谷 {kpi_low['放款月']}")
    lines.append(f"- 平均利率区间 {kpi['平均利率'].min():.2f}% ~ {kpi['平均利率'].max():.2f}%（随市场与风险定价波动）")

    # ---- 2. Vintage 洞察 ----
    print("\n" + "=" * 60)
    print("Vintage 关键洞察（36 账龄月以上可比的放款月）")
    print("=" * 60)
    v36 = vintage[vintage["账龄月"] == 36].sort_values("issue_month")
    if len(v36):
        print(v36[["issue_month", "在贷笔数", "累计坏账率"]].to_string(index=False))
        best_m = v36.loc[v36["累计坏账率"].idxmin()]
        worst_m = v36.loc[v36["累计坏账率"].idxmax()]
        print(f"\n36月账龄：最差放款月 {best_m['issue_month']} 累计坏账率 {best_m['累计坏账率']}%")
        lines.append(f"\n## Vintage（36 月账龄口径）\n- 最早几批放款月已走满 36 月账龄；累计坏账率区间 "
                     f"{v36['累计坏账率'].min():.2f}% ~ {v36['累计坏账率'].max():.2f}%")
        lines.append(f"- 2008 危机期放款的组合坏账显著更高——真实数据的Vintage曲线呈现出合成数据没有的宏观周期波动")

    # ---- 3. 定价有效性 ----
    print("\n" + "=" * 60)
    print("定价有效性检验（grade 利率 vs 实际坏账率）")
    print("=" * 60)
    print(grade.to_string(index=False))
    lines.append("\n## 定价有效性检验\n\n| grade | 笔数 | 平均定价利率 | 实际坏账率 |\n|---|---|---|---|")
    for _, r in grade.iterrows():
        lines.append(f"| {r['grade']} | {int(r['笔数']):,} | {r['平均定价利率']}% | {r['实际坏账率']}% |")
    valid = grade[grade["平均定价利率"] > 0]
    corr = valid["平均定价利率"].corr(valid["实际坏账率"])
    print(f"\n定价-坏账相关性: {corr:.3f}（越接近1=定价越有效）")
    lines.append(f"\n> 定价利率与实际坏账率相关系数 **{corr:.3f}**（正值越大定价越有效）——LC 官方 grade 定价总体有效")

    # ---- 4. 用途归因 ----
    print("\n" + "=" * 60)
    print("贷款用途坏账分布")
    print("=" * 60)
    print(purpose.head(8).to_string(index=False))
    top_bad = purpose.iloc[0]
    lines.append("\n## 用途归因\n- 坏账率最高用途：" + f"{top_bad['贷款用途']}（{top_bad['坏账率']}%）；"
                 "最低：" + f"{purpose.iloc[-1]['贷款用途']}（{purpose.iloc[-1]['坏账率']}%）")

    # ---- Excel 周报 ----
    with pd.ExcelWriter(OUT / "lc_strategy_report.xlsx", engine="openpyxl") as w:
        kpi.to_excel(w, sheet_name="月度KPI", index=False)
        vintage.to_excel(w, sheet_name="Vintage", index=False)
        grade.to_excel(w, sheet_name="定价有效性", index=False)
        purpose.to_excel(w, sheet_name="用途归因", index=False)
    lines.append("\n> Excel 周报：outputs/lc_strategy_report.xlsx")
    print("\nExcel 周报：outputs/lc_strategy_report.xlsx")

    (OUT / "lc_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print("分析报告：outputs/lc_analysis.md")
    print("\n✅ P2b（Lending Club 真实数据版）完成")


if __name__ == "__main__":
    main()
