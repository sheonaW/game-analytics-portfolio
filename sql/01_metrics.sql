-- ============================================================
-- 手游 A/B 实验核心指标体系 —— SQL 版（DuckDB 语法）
-- 数据源: data/cookie_cats.csv (90,189 行)
-- 运行  : duckdb < sql/01_metrics.sql
-- ============================================================

-- ------------------------------------------------------------
-- 1. 分组核心指标总览（北极星 + 一级指标）
-- ------------------------------------------------------------
SELECT
    version                                        AS experiment_group,
    COUNT(*)                                       AS users,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS user_share_pct,
    ROUND(AVG(CASE WHEN retention_1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS d1_retention_pct,
    ROUND(AVG(CASE WHEN retention_7 THEN 1.0 ELSE 0.0 END) * 100, 2) AS d7_retention_pct,
    ROUND(AVG(sum_gamerounds), 2)                  AS avg_gamerounds,
    MEDIAN(sum_gamerounds)                         AS median_gamerounds,
    ROUND(AVG(CASE WHEN sum_gamerounds = 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS zero_round_pct
FROM read_csv_auto('data/cookie_cats.csv')
GROUP BY version
ORDER BY version;


-- ------------------------------------------------------------
-- 2. 核心漏斗：安装 → 有效体验 → 次留 → 7日留存
--    （安装为基数 100%，逐层计算转化率）
-- ------------------------------------------------------------
WITH base AS (
    SELECT
        version,
        COUNT(*)                                                    AS installed,
        SUM(CASE WHEN sum_gamerounds >= 1 THEN 1 ELSE 0 END)         AS played,
        SUM(CASE WHEN retention_1 = TRUE THEN 1 ELSE 0 END)          AS d1_retained,
        SUM(CASE WHEN retention_7 = TRUE THEN 1 ELSE 0 END)          AS d7_retained
    FROM read_csv_auto('data/cookie_cats.csv')
    GROUP BY version
)
SELECT
    version                                     AS experiment_group,
    installed,
    played,
    ROUND(played * 100.0 / installed, 2)        AS step1_played_pct,
    d1_retained,
    ROUND(d1_retained * 100.0 / installed, 2)   AS step2_d1_pct,
    d7_retained,
    ROUND(d7_retained * 100.0 / installed, 2)   AS step3_d7_pct
FROM base
ORDER BY version;


-- ------------------------------------------------------------
-- 3. 分层下钻：按游戏轮次分桶看留存（归因定位）
-- ------------------------------------------------------------
SELECT
    version                                       AS experiment_group,
    CASE
        WHEN sum_gamerounds = 0              THEN '0 轮 (安装未游玩)'
        WHEN sum_gamerounds BETWEEN 1 AND 5  THEN '1-5 轮'
        WHEN sum_gamerounds BETWEEN 6 AND 20 THEN '6-20 轮'
        WHEN sum_gamerounds BETWEEN 21 AND 50 THEN '21-50 轮'
        WHEN sum_gamerounds BETWEEN 51 AND 100 THEN '51-100 轮'
        ELSE '100 轮以上'
    END                                           AS rounds_bucket,
    COUNT(*)                                      AS users,
    ROUND(AVG(CASE WHEN retention_1 THEN 1.0 ELSE 0.0 END) * 100, 2) AS d1_retention_pct,
    ROUND(AVG(CASE WHEN retention_7 THEN 1.0 ELSE 0.0 END) * 100, 2) AS d7_retention_pct
FROM read_csv_auto('data/cookie_cats.csv')
GROUP BY version, rounds_bucket
ORDER BY rounds_bucket, version;


-- ------------------------------------------------------------
-- 4. 数据质量：重复用户与异常游玩轮次
-- ------------------------------------------------------------
SELECT
    COUNT(*)                                          AS total_rows,
    COUNT(DISTINCT userid)                            AS unique_users,
    COUNT(*) - COUNT(DISTINCT userid)                 AS duplicated_userids,
    SUM(CASE WHEN sum_gamerounds IS NULL THEN 1 ELSE 0 END) AS null_rounds,
    MAX(sum_gamerounds)                               AS max_gamerounds
FROM read_csv_auto('data/cookie_cats.csv');
