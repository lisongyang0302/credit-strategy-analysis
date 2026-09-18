-- ============================================================
-- Project 02b · Lending Club 真实数据 · 三大核心报表（MySQL 8.0）
-- Vintage 账龄分析 / 月度 KPI 监控 / 定价有效性检验
-- 均基于 risk_project02.lc_loan_master（38,577 笔真实放款）
-- ============================================================

-- 报表一：Vintage 账龄矩阵
-- 口径：按放款月分列，账龄月 = 距放款月的月数；坏账 = 贷款已核销(Charged Off)
-- 且核销时点(近似用 last_pymnt_date) 早于该账龄。仅统计"已到账龄"的放款月（分母=仍在观察的贷款）
DROP TABLE IF EXISTS rpt_vintage_lc;
CREATE TABLE rpt_vintage_lc AS
WITH base AS (
    SELECT
        DATE_FORMAT(issue_date, '%Y-%m') AS issue_month,
        loan_amnt,
        target,
        last_pymnt_date,
        TIMESTAMPDIFF(MONTH, issue_date, COALESCE(last_pymnt_date, STR_TO_DATE('2011-12-31', '%Y-%m-%d'))) AS default_mob
    FROM risk_project02.lc_loan_master
),
grid AS (
    SELECT m AS mob FROM (SELECT 6 AS m UNION SELECT 12 UNION SELECT 18 UNION SELECT 24 UNION SELECT 30 UNION SELECT 36 UNION SELECT 42 UNION SELECT 48 UNION SELECT 54) t
)
SELECT
    b.issue_month,
    g.mob AS 账龄月,
    COUNT(*) AS 在贷笔数,
    SUM(CASE WHEN b.target = 1 AND b.default_mob <= g.mob THEN 1 ELSE 0 END) AS 已核销笔数,
    ROUND(SUM(CASE WHEN b.target = 1 AND b.default_mob <= g.mob THEN 1 ELSE 0 END)
          / COUNT(*) * 100, 2) AS 累计坏账率
FROM base b
JOIN grid g ON TIMESTAMPDIFF(MONTH, STR_TO_DATE(CONCAT(b.issue_month, '-01'), '%Y-%m-%d'),
                            STR_TO_DATE('2011-12-31', '%Y-%m-%d')) >= g.mob
GROUP BY b.issue_month, g.mob
ORDER BY b.issue_month, g.mob;

-- 报表二：月度 KPI（放款量/均价/利率/期限结构）
DROP TABLE IF EXISTS rpt_monthly_kpi_lc;
CREATE TABLE rpt_monthly_kpi_lc AS
SELECT
    DATE_FORMAT(issue_date, '%Y-%m') AS 放款月,
    COUNT(*) AS 放款笔数,
    ROUND(SUM(loan_amnt) / 10000, 1) AS 放款金额_万,
    ROUND(AVG(loan_amnt), 0) AS 平均金额,
    ROUND(AVG(int_rate), 2) AS 平均利率,
    ROUND(AVG(dti), 2) AS 平均DTI,
    ROUND(SUM(CASE WHEN term_months = 60 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS 六十期占比,
    ROUND(AVG(target) * 100, 2) AS 最终坏账率
FROM risk_project02.lc_loan_master
GROUP BY DATE_FORMAT(issue_date, '%Y-%m')
ORDER BY 放款月;

-- 报表三：定价有效性检验（grade 风险阶梯 + 实际坏账率）
-- 验证 LC 官方定价是否有效：利率阶梯应与实际坏账率阶梯同向
DROP TABLE IF EXISTS rpt_grade_pricing_lc;
CREATE TABLE rpt_grade_pricing_lc AS
SELECT
    grade,
    COUNT(*) AS 笔数,
    ROUND(AVG(int_rate), 2) AS 平均定价利率,
    ROUND(AVG(target) * 100, 2) AS 实际坏账率,
    ROUND(AVG(loan_amnt), 0) AS 平均金额,
    ROUND(AVG(dti), 2) AS 平均DTI
FROM risk_project02.lc_loan_master
GROUP BY grade
ORDER BY grade;

-- 报表四：用途(Purpose)坏账分布（策略归因用）
DROP TABLE IF EXISTS rpt_purpose_bad_lc;
CREATE TABLE rpt_purpose_bad_lc AS
SELECT
    purpose AS 贷款用途,
    COUNT(*) AS 笔数,
    ROUND(SUM(loan_amnt) / 10000, 1) AS 金额_万,
    ROUND(AVG(target) * 100, 2) AS 坏账率,
    ROUND(AVG(int_rate), 2) AS 平均利率
FROM risk_project02.lc_loan_master
GROUP BY purpose
ORDER BY 坏账率 DESC;
