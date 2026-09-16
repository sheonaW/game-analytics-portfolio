"""
Step 2 —— 留存分析、转化漏斗与分层归因

产出：
  outputs/results_retention.json
  outputs/figures/fig3~fig6_*.png
"""
import sys
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_CLEAN, COLOR_CONTROL, COLOR_TREAT, COLOR_NEUTRAL,
                    COLOR_GRID, PALETTE_BLUE, GROUP_LABELS, save_fig,
                    dump_json, setup_style, banner)

GROUPS = ["gate_30", "gate_40"]
COLORS = [COLOR_CONTROL, COLOR_TREAT]
ROUND_LABELS = ["0 轮", "1-5 轮", "6-20 轮", "21-50 轮", "51-100 轮", "100 轮以上"]


def wilson_ci(k, n, z=1.96):
    """Wilson 区间：小比例指标的置信区间更可靠。"""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (max(0.0, center - half), min(1.0, center + half))


def retention_summary(df):
    """核心留存指标：D1 / D7 / 深度指标 + 置信区间。"""
    res = {}
    for g in GROUPS:
        sub = df[df["version"] == g]
        n = len(sub)
        k1, k7 = int(sub["retained_1"].sum()), int(sub["retained_7"].sum())
        lo1, hi1 = wilson_ci(k1, n)
        lo7, hi7 = wilson_ci(k7, n)
        # 流失衰减：D1 留存玩家中，到 D7 仍留存的比例
        stay = sub.loc[sub["retained_1"] == 1, "retained_7"].mean()
        res[g] = {
            "users": n,
            "d1_users": k1, "d1_rate": round(k1 / n * 100, 3),
            "d1_ci": [round(lo1 * 100, 3), round(hi1 * 100, 3)],
            "d7_users": k7, "d7_rate": round(k7 / n * 100, 3),
            "d7_ci": [round(lo7 * 100, 3), round(hi7 * 100, 3)],
            "d1_to_d7_survival_pct": round(stay * 100, 2),
            "avg_gamerounds": round(sub["sum_gamerounds"].mean(), 2),
            "median_gamerounds": float(sub["sum_gamerounds"].median()),
            "p90_gamerounds": float(sub["sum_gamerounds"].quantile(0.90)),
            "played_rate_pct": round(sub["played_any"].mean() * 100, 3),
        }
    # 组间差异
    a, b = res["gate_30"], res["gate_40"]
    res["difference"] = {
        "d1_abs_pp": round(a["d1_rate"] - b["d1_rate"], 3),
        "d1_rel_pct": round((a["d1_rate"] - b["d1_rate"]) / b["d1_rate"] * 100, 2),
        "d7_abs_pp": round(a["d7_rate"] - b["d7_rate"], 3),
        "d7_rel_pct": round((a["d7_rate"] - b["d7_rate"]) / b["d7_rate"] * 100, 2),
        "d1_d7_survival_pp": round(a["d1_to_d7_survival_pct"] - b["d1_to_d7_survival_pct"], 2),
        "avg_gamerounds_pct": round(
            (a["avg_gamerounds"] - b["avg_gamerounds"]) / b["avg_gamerounds"] * 100, 2),
    }
    # 业务影响推算：每 100 万新玩家
    res["impact_per_million"] = {
        "d7_users_gate_30": int(round(a["d7_rate"] / 100 * 1_000_000)),
        "d7_users_gate_40": int(round(b["d7_rate"] / 100 * 1_000_000)),
        "d7_users_lost": int(round((a["d7_rate"] - b["d7_rate"]) / 100 * 1_000_000)),
        "d1_users_lost": int(round((a["d1_rate"] - b["d1_rate"]) / 100 * 1_000_000)),
    }
    return res


def funnel(df):
    """核心漏斗：安装 → 有效体验(≥1轮) → 次留 → 7日留存。"""
    out = {}
    for g in GROUPS:
        sub = df[df["version"] == g]
        n = len(sub)
        played = int(sub["played_any"].sum())
        d1 = int(sub["retained_1"].sum())
        d7 = int(sub["retained_7"].sum())
        out[g] = {
            "install": {"users": n, "pct": 100.0},
            "played": {"users": played, "pct": round(played / n * 100, 2)},
            "d1_retained": {"users": d1, "pct": round(d1 / n * 100, 2)},
            "d7_retained": {"users": d7, "pct": round(d7 / n * 100, 2)},
        }
    return out


def stratified(df):
    """分层下钻：按游玩深度看留存差异（归因定位）。"""
    rows = []
    for bucket in ROUND_LABELS:
        for g in GROUPS:
            sub = df[(df["rounds_bucket"] == bucket) & (df["version"] == g)]
            if len(sub) == 0:
                continue
            rows.append({
                "rounds_bucket": bucket,
                "version": g,
                "users": int(len(sub)),
                "share_pct": round(len(sub) / len(df[df["version"] == g]) * 100, 2),
                "d1_rate": round(sub["retained_1"].mean() * 100, 2),
                "d7_rate": round(sub["retained_7"].mean() * 100, 2),
            })
    tab = pd.DataFrame(rows)
    # 每个分桶的组间差异
    diff = []
    for bucket in ROUND_LABELS:
        s = tab[tab["rounds_bucket"] == bucket]
        if len(s) < 2:
            continue
        a = s[s["version"] == "gate_30"].iloc[0]
        b = s[s["version"] == "gate_40"].iloc[0]
        diff.append({
            "rounds_bucket": bucket,
            "users_total": int(a["users"] + b["users"]),
            "d7_diff_pp": round(a["d7_rate"] - b["d7_rate"], 2),
            "d7_gate_30": float(a["d7_rate"]),
            "d7_gate_40": float(b["d7_rate"]),
        })
    return tab.to_dict("records"), diff


def plot_retention(res, tab):
    setup_style()

    # --- 图3：D1 / D7 留存对比（含置信区间）---
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0))
    for ax, metric, title, star in zip(
            axes, ["d1", "d7"],
            ["① 1 日留存率（短期粘性）", "② 7 日留存率（北极星指标）"],
            ["", " ★显著"]):
        rates = [res[g][f"{metric}_rate"] for g in GROUPS]
        errs = []
        for g in GROUPS:
            lo, hi = res[g][f"{metric}_ci"]
            center = res[g][f"{metric}_rate"]
            errs.append([center - lo, hi - center])
        errs = np.array(errs).T
        bars = ax.bar([GROUP_LABELS[g] for g in GROUPS], rates, color=COLORS, width=0.5)
        ax.errorbar([GROUP_LABELS[g] for g in GROUPS], rates, yerr=errs,
                    fmt="none", ecolor="#404040", elinewidth=1.0, capsize=4)
        for bar, r, g in zip(bars, rates, GROUPS):
            ax.text(bar.get_x() + bar.get_width() / 2, r + 1.0, f"{r:.2f}%",
                    ha="center", va="bottom", fontsize=10, fontweight="bold")
        ax.set_title(title + star)
        ax.set_ylabel("留存率 %")
        ax.set_ylim(0, max(rates) * 1.35)
        ax.grid(axis="x", visible=False)

    diff = res["difference"]
    fig.suptitle(
        f"图 3　留存率组间对比（误差线为 95% Wilson 置信区间）　"
        f"D1 差异 {diff['d1_abs_pp']:+.2f}pp / D7 差异 {diff['d7_abs_pp']:+.2f}pp",
        fontsize=12, y=1.04)
    save_fig(fig, "fig3_retention_comparison.png")

    # --- 图4：转化漏斗 ---
    fun = res["_funnel"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    stages = ["install", "played", "d1_retained", "d7_retained"]
    stage_names = ["安装\n100%", "有效体验\n(≥1轮)", "次日留存", "7日留存"]
    y = np.arange(len(stages))[::-1]
    for i, g in enumerate(GROUPS):
        vals = [fun[g][s]["pct"] for s in stages]
        ax.barh(y + (0.18 if i == 0 else -0.18), vals, height=0.32,
                color=COLORS[i], label=GROUP_LABELS[g])
        for yy, v in zip(y + (0.18 if i == 0 else -0.18), vals):
            ax.text(v + 1.0, yy, f"{v:.2f}%", va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(stage_names)
    ax.set_xlabel("相对安装量的转化率 %")
    ax.set_xlim(0, 118)
    ax.set_title("图 4　玩家核心转化漏斗（两组对比）")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "fig4_funnel.png")

    # --- 图5：分层留存 ---
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.0))
    dfp = pd.DataFrame(tab)
    xs = np.arange(len(ROUND_LABELS))
    width = 0.38

    ax = axes[0]
    for i, g in enumerate(GROUPS):
        s = dfp[dfp["version"] == g].set_index("rounds_bucket").reindex(ROUND_LABELS)
        ax.bar(xs + (i - 0.5) * width, s["d7_rate"], width=width,
               color=COLORS[i], label=GROUP_LABELS[g])
    ax.set_xticks(xs)
    ax.set_xticklabels(ROUND_LABELS, rotation=20, ha="right")
    ax.set_title("① 各游玩深度下的 7 日留存率")
    ax.set_ylabel("7 日留存率 %")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    for i, g in enumerate(GROUPS):
        s = dfp[dfp["version"] == g].set_index("rounds_bucket").reindex(ROUND_LABELS)
        ax.bar(xs + (i - 0.5) * width, s["share_pct"], width=width,
               color=PALETTE_BLUE[2:4][::-1][i], label=GROUP_LABELS[g])
    ax.set_xticks(xs)
    ax.set_xticklabels(ROUND_LABELS, rotation=20, ha="right")
    ax.set_title("② 各深度玩家规模占比（两组结构一致）")
    ax.set_ylabel("占本组玩家比例 %")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)

    fig.suptitle("图 5　分层下钻：游玩深度与留存的关系", fontsize=13, y=1.03)
    save_fig(fig, "fig5_stratified.png")

    # --- 图6：留存衰减路径 ---
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for i, g in enumerate(GROUPS):
        r = res[g]
        ax.plot([0, 1, 7], [100, r["d1_rate"], r["d7_rate"]], marker="o",
                markersize=6, linewidth=2, color=COLORS[i], label=GROUP_LABELS[g])
        ax.annotate(f'{r["d1_rate"]:.2f}%', (1, r["d1_rate"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=9,
                    color=COLORS[i])
        ax.annotate(f'{r["d7_rate"]:.2f}%', (7, r["d7_rate"]),
                    textcoords="offset points", xytext=(-10, -16), fontsize=9,
                    color=COLORS[i])
    ax.set_xticks([0, 1, 7])
    ax.set_xticklabels(["D0 安装", "D1 次日", "D7 第7日"])
    ax.set_ylabel("留存率 %")
    ax.set_ylim(0, 105)
    ax.set_title("图 6　留存衰减曲线（安装为 100%）")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    save_fig(fig, "fig6_retention_decay.png")


def main():
    banner("STEP 2　留存分析 · 转化漏斗 · 分层归因")
    df = pd.read_csv(DATA_CLEAN)

    res = retention_summary(df)
    d = res["difference"]
    print(f"  D1 留存    : gate_30 {res['gate_30']['d1_rate']}%  vs  "
          f"gate_40 {res['gate_40']['d1_rate']}%   →  {d['d1_abs_pp']:+.2f} pp")
    print(f"  D7 留存    : gate_30 {res['gate_30']['d7_rate']}%  vs  "
          f"gate_40 {res['gate_40']['d7_rate']}%   →  {d['d7_abs_pp']:+.2f} pp "
          f"({d['d7_rel_pct']:+.2f}%)")
    print(f"  D1→D7 存活 : gate_30 {res['gate_30']['d1_to_d7_survival_pct']}%  vs  "
          f"gate_40 {res['gate_40']['d1_to_d7_survival_pct']}%")
    print(f"  人均轮次   : {res['gate_30']['avg_gamerounds']} vs "
          f"{res['gate_40']['avg_gamerounds']} ({d['avg_gamerounds_pct']:+.2f}%)")

    fun = funnel(df)
    res["_funnel"] = fun
    print(f"  漏斗(安装→有效体验) : {fun['gate_30']['played']['pct']}% vs "
          f"{fun['gate_40']['played']['pct']}%")

    tab, diff = stratified(df)
    res["_stratified"] = tab
    res["_stratified_diff"] = diff
    print("  分桶 7 日留存差异 (gate_30 − gate_40):")
    for r in diff:
        print(f"    {r['rounds_bucket']:<12s} n={r['users_total']:>6,}  "
              f"{r['d7_diff_pp']:+.2f} pp")

    print(f"  业务影响推算（每百万新玩家）：D7 留存用户损失 "
          f"{res['impact_per_million']['d7_users_lost']:,} 人")

    plot_retention(res, tab)
    dump_json(res, "results_retention.json")
    print("  STEP 2 完成")
    return res


if __name__ == "__main__":
    main()
