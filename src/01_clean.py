"""
Step 1 —— 数据加载、质量检查与清洗

产出：
  data/cookie_cats_clean.csv   清洗后数据（新增衍生字段）
  outputs/results_quality.json 数据质量与分组均衡性结果
  outputs/figures/fig1_*.png   数据质量可视化
"""
import sys
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_RAW, DATA_CLEAN, GROUP_COLORS, GROUP_LABELS,
                    COLOR_CONTROL, COLOR_TREAT, PALETTE_BLUE, save_fig,
                    dump_json, setup_style, banner)

ROUND_BINS = [-1, 0, 5, 20, 50, 100, np.inf]
ROUND_LABELS = ["0 轮", "1-5 轮", "6-20 轮", "21-50 轮", "51-100 轮", "100 轮以上"]


def load_raw():
    df = pd.read_csv(DATA_RAW)
    return df


def quality_check(df):
    """数据质量检查：重复、缺失、异常、分组均衡。"""
    rep = {}

    rep["raw_rows"] = int(len(df))
    rep["columns"] = list(df.columns)
    rep["duplicated_userids"] = int(df["userid"].duplicated().sum())
    rep["missing"] = {c: int(df[c].isna().sum()) for c in df.columns}
    rep["total_missing"] = int(df.isna().sum().sum())

    g = df.groupby("version").size().to_dict()
    rep["group_counts"] = {k: int(v) for k, v in g.items()}
    rep["group_share"] = {k: round(v / len(df) * 100, 2) for k, v in g.items()}
    # 分组均衡性：两组人数占比偏离 50% 的程度
    rep["max_group_imbalance_pp"] = round(max(abs(v / len(df) * 100 - 50) for v in g.values()), 2)

    # 游玩轮次异常值（IQR 法）
    q1, q3 = df["sum_gamerounds"].quantile([0.25, 0.75])
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    rep["rounds_q1"] = float(q1)
    rep["rounds_q3"] = float(q3)
    rep["rounds_iqr_upper_fence"] = float(upper)
    rep["outlier_users"] = int((df["sum_gamerounds"] > upper).sum())
    rep["outlier_share_pct"] = round((df["sum_gamerounds"] > upper).mean() * 100, 3)
    rep["max_gamerounds"] = int(df["sum_gamerounds"].max())
    rep["max_gamerounds_userid"] = int(df.loc[df["sum_gamerounds"].idxmax(), "userid"])

    # 0 轮用户
    rep["zero_round_users"] = int((df["sum_gamerounds"] == 0).sum())
    rep["zero_round_share_pct"] = round((df["sum_gamerounds"] == 0).mean() * 100, 2)
    rep["zero_round_d7_retention_pct"] = round(
        df.loc[df["sum_gamerounds"] == 0, "retention_7"].mean() * 100, 3)

    # 描述统计
    desc = df["sum_gamerounds"].describe(percentiles=[0.5, 0.75, 0.9, 0.95, 0.99])
    rep["rounds_describe"] = {k: round(float(v), 2) for k, v in desc.items()}

    return rep


def enrich(df):
    """清洗与衍生字段：去重、布尔转数值、分桶、异常标记。"""
    df = df.drop_duplicates(subset=["userid"]).copy()

    df["retention_1"] = df["retention_1"].astype(bool)
    df["retention_7"] = df["retention_7"].astype(bool)
    df["retained_1"] = df["retention_1"].astype(int)
    df["retained_7"] = df["retention_7"].astype(int)

    q1, q3 = df["sum_gamerounds"].quantile([0.25, 0.75])
    fence = q3 + 1.5 * (q3 - q1)
    df["is_outlier"] = df["sum_gamerounds"] > fence
    df["played_any"] = df["sum_gamerounds"] >= 1
    df["log_rounds"] = np.log1p(df["sum_gamerounds"])
    df["rounds_bucket"] = pd.cut(df["sum_gamerounds"], bins=ROUND_BINS,
                                 labels=ROUND_LABELS, right=True)
    df["is_control"] = (df["version"] == "gate_30").astype(int)
    return df


def plot_quality(df, rep):
    setup_style()

    # --- 图1：分组均衡性 + 关键指标对比 ---
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.5))
    groups = ["gate_30", "gate_40"]
    colors = [COLOR_CONTROL, COLOR_TREAT]

    ax = axes[0]
    counts = [rep["group_counts"][g] for g in groups]
    bars = ax.bar([GROUP_LABELS[g] for g in groups], counts, color=colors, width=0.55)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c, f"{c:,}", ha="center",
                va="bottom", fontsize=9)
    ax.set_title("① 实验分组均衡性（人数）")
    ax.set_ylabel("玩家数")
    ax.set_ylim(0, max(counts) * 1.15)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    play_rates = [(df.loc[df.version == g, "played_any"].mean() * 100) for g in groups]
    bars = ax.bar([GROUP_LABELS[g] for g in groups], play_rates, color=colors, width=0.55)
    for b, c in zip(bars, play_rates):
        ax.text(b.get_x() + b.get_width() / 2, c, f"{c:.2f}%", ha="center",
                va="bottom", fontsize=9)
    ax.set_title("② 有效体验率（至少游玩 1 轮）")
    ax.set_ylabel("占比 %")
    ax.set_ylim(0, max(play_rates) * 1.2)
    ax.grid(axis="x", visible=False)

    ax = axes[2]
    zero_rates = [(df.loc[df.version == g, "sum_gamerounds"].eq(0).mean() * 100) for g in groups]
    bars = ax.bar([GROUP_LABELS[g] for g in groups], zero_rates, color=PALETTE_BLUE[2:4][::-1], width=0.55)
    for b, c in zip(bars, zero_rates):
        ax.text(b.get_x() + b.get_width() / 2, c, f"{c:.2f}%", ha="center",
                va="bottom", fontsize=9)
    ax.set_title("③ 零体验用户占比（安装未游玩）")
    ax.set_ylabel("占比 %")
    ax.set_ylim(0, max(zero_rates) * 1.25)
    ax.grid(axis="x", visible=False)

    fig.suptitle("图 1　数据质量与实验分组体检", fontsize=13, y=1.05)
    save_fig(fig, "fig1_data_quality.png")

    # --- 图2：游玩轮次分布（对数刻度） ---
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 3.8))

    ax = axes[0]
    positive = df.loc[df["sum_gamerounds"] > 0, "sum_gamerounds"]
    bins = np.logspace(0, np.log10(positive.max()), 50)
    ax.hist(positive, bins=bins, color=PALETTE_BLUE[3], edgecolor="white", linewidth=0.4)
    ax.set_xscale("log")
    ax.set_title("① 游玩轮次分布（对数刻度，右偏长尾）")
    ax.set_xlabel("14 天内游玩轮次（log）")
    ax.set_ylabel("玩家数")

    ax = axes[1]
    order = ROUND_LABELS
    width = 0.38
    xs = np.arange(len(order))
    for i, g in enumerate(groups):
        sub = df[df["version"] == g]
        shares = [(sub["rounds_bucket"] == o).mean() * 100 for o in order]
        ax.bar(xs + (i - 0.5) * width, shares, width=width,
               color=colors[i], label=GROUP_LABELS[g])
    ax.set_xticks(xs)
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set_title("② 玩家游玩深度分层结构（两组口径一致）")
    ax.set_ylabel("玩家占比 %")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)

    fig.suptitle("图 2　玩家活跃度结构画像", fontsize=13, y=1.03)
    save_fig(fig, "fig2_rounds_distribution.png")


def main():
    banner("STEP 1　数据加载 · 质量检查 · 清洗")
    df = load_raw()
    print(f"  原始数据: {len(df):,} 行 × {df.shape[1]} 列")

    rep = quality_check(df)
    print(f"  重复 userid        : {rep['duplicated_userids']}")
    print(f"  缺失值合计         : {rep['total_missing']}")
    print(f"  分组人数           : {rep['group_counts']}")
    print(f"  分组最大不均衡     : {rep['max_group_imbalance_pp']} pp")
    print(f"  游玩轮次异常值     : {rep['outlier_users']:,} 人 "
          f"({rep['outlier_share_pct']}%)，最大 {rep['max_gamerounds']:,} 轮")
    print(f"  零体验用户         : {rep['zero_round_users']:,} 人 "
          f"({rep['zero_round_share_pct']}%)，其 7 日留存 "
          f"{rep['zero_round_d7_retention_pct']}%")

    dfc = enrich(df)
    dfc.to_csv(DATA_CLEAN, index=False, encoding="utf-8-sig")
    print(f"  清洗后数据已保存   : data/cookie_cats_clean.csv ({len(dfc):,} 行)")

    rep["clean_rows"] = int(len(dfc))
    rep["derived_columns"] = ["retained_1", "retained_7", "is_outlier",
                              "played_any", "log_rounds", "rounds_bucket",
                              "is_control"]
    dump_json(rep, "results_quality.json")

    plot_quality(dfc, rep)
    print("  STEP 1 完成")
    return rep


if __name__ == "__main__":
    main()
