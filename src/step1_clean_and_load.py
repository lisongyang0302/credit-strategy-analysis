# -*- coding: utf-8 -*-
"""step1 数据清洗与入库：Lending Club 真实贷款数据 → MySQL risk_project02

目标定义（工业口径）：
- Fully Paid  → 好客户（0）
- Charged Off → 坏客户（1，核销）
- Current     → 观察期未完整，剔除（真实业务不会把未到期贷款当样本）
派生：credit_history_months（信用历史长度）、issue_month（放款月，Vintage 维度）
"""
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "loan.csv"
MYSQL = dict(host="127.0.0.1", port=3307, user="root",
             password=os.environ.get("MYSQL_PWD", ""), charset="utf8mb4")
engine = create_engine(
    f"mysql+pymysql://{MYSQL['user']}:{MYSQL['password']}@{MYSQL['host']}:{MYSQL['port']}/?charset=utf8mb4")


def parse_mon_yy(s):
    return pd.to_datetime(s, format="%b-%y", errors="coerce")


def main():
    df = pd.read_csv(DATA, low_memory=False)
    print(f"原始 {len(df):,} 行 × {df.shape[1]} 列")

    # ---- 目标定义（工业口径）----
    keep_status = {"Fully Paid": 0, "Charged Off": 1}
    df = df[df["loan_status"].isin(keep_status)].copy()
    df["target"] = df["loan_status"].map(keep_status)
    print(f"剔除 Current 后 {len(df):,} 行（Fully Paid {int((df.target==0).sum()):,} / Charged Off {int((df.target==1).sum()):,}）")

    # ---- 时间字段解析 ----
    df["issue_date"] = parse_mon_yy(df["issue_d"])
    df["issue_month"] = df["issue_date"].dt.strftime("%Y-%m")
    df["credit_history_months"] = (
        (df["issue_date"] - parse_mon_yy(df["earliest_cr_line"])).dt.days / 30.4).round(1)

    # ---- 清洗 ----
    df["revol_util_num"] = (df["revol_util"].astype(str).str.rstrip("%")
                            .replace("nan", np.nan)).astype(float)
    df["emp_length_num"] = (df["emp_length"].astype(str)
                            .str.extract(r"(\d+)")[0].astype(float))
    df.loc[df["emp_length"].astype(str).str.contains("10\\+"), "emp_length_num"] = 10
    df["int_rate_num"] = df["int_rate"].astype(str).str.rstrip("%").astype(float)

    # 收入极端值：99.5 分位截尾（真实数据长尾）
    cap = df["annual_inc"].quantile(0.995)
    df["annual_inc"] = df["annual_inc"].clip(upper=cap)
    print(f"收入 99.5 分位截尾至 {cap:,.0f}")

    # ---- 核心宽表 ----
    master = df[[
        "target", "loan_amnt", "term", "int_rate_num", "installment", "grade",
        "sub_grade", "emp_length_num", "home_ownership", "annual_inc",
        "purpose", "dti", "delinq_2yrs", "credit_history_months", "revol_util_num",
        "total_pymnt", "issue_date", "issue_month", "last_pymnt_d",
    ]].copy()
    master.columns = [
        "target", "loan_amnt", "term_months", "int_rate", "monthly_installment", "grade",
        "sub_grade", "emp_length_years", "home_ownership", "annual_inc",
        "purpose", "dti", "delinq_2yrs", "credit_history_months", "revol_util",
        "total_pymnt", "issue_date", "issue_month", "last_pymnt_date",
    ]
    master["last_pymnt_date"] = parse_mon_yy(master["last_pymnt_date"])
    master["id"] = range(1, len(master) + 1)

    with engine.begin() as conn:
        conn.execute(df.__class__.__mro__[0] and __import__("sqlalchemy").text("DROP DATABASE IF EXISTS risk_project02"))
        conn.execute(__import__("sqlalchemy").text("CREATE DATABASE risk_project02 CHARACTER SET utf8mb4"))
    master.to_sql("lc_loan_master", engine, schema="risk_project02",
                  if_exists="replace", index=False, chunksize=5000)
    print(f"入库 risk_project02.lc_loan_master：{len(master):,} 行")
    print(f"坏账率 {master['target'].mean():.2%} | 放款月 {master['issue_month'].nunique()} 个月跨度")


if __name__ == "__main__":
    main()
