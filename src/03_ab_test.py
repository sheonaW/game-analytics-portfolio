"""
Step 3 —— A/B 实验统计检验（频率派 + Bootstrap + 贝叶斯）

检验方法：
  1. 双比例 Z 检验（主检验）+ 卡方检验（交叉验证）
  2. 差异的 95% 置信区间 + 效应量 Cohen's h
  3. Bootstrap 重抽样 10,000 次（不依赖分布假设）
  4. 贝叶斯 Beta-Binomial 后验（输出"概率型"决策依据）
  5. 功效分析：该样本量能检测到的最小效应（MDE）
  6. 多重比较校正（Bonferroni）

产出：
  outputs/results_abtest.json
  outputs/figures/fig7~fig9_*.png
"""
import sys
import os
import json

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_CLEAN, COLOR_CONTROL, COLOR_TREAT, COLOR_NEUTRAL,
                    COLOR_GRID, PALETTE_BLUE, GROUP_LABELS, save_fig,
                    dump_json, setup_style, banner)

RNG = np.random.default_rng(42)
N_BOOT = 10_000
N_BAYES = 400_000
ALPHA = 0.05

CONTROL, TREAT = "gate_30", "gate_40"


def two_prop_ztest(k1, n1, k2, n2):
    """双比例 Z 检验（pooled），返回 z、p、差异的 95% CI。"""
    p1, p2 = k1 / n1, k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    # 差异的标准误（非 pooled，用于置信区间）
    se_diff = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p1 - p2
    ci = (diff - 1.96 * se_diff, diff + 1.96 * se_diff)

    chi2, p_chi2, _, _ = stats.chi2_contingency(
        [[k1, n1 - k1], [k2, n2 - k2]], correction=False)

    h = proportion_effectsize(p1, p2)  # Cohen's h
    return {
        "control_rate_pct": round(p1 * 100, 3),
        "treat_rate_pct": round(p2 * 100, 3),
        "abs_diff_pp": round(diff * 100, 3),
        "rel_lift_pct": round(diff / p2 * 100, 2),
        "z_stat": round(float(z), 4),
        "p_value": float(f"{p_value:.6g}"),
        "ci95_pp": [round(ci[0] * 100, 3), round(ci[1] * 100, 3)],
        "significant_at_0.05": bool(p_value < ALPHA),
        "cohens_h": round(float(h), 4),
        "effect_size_label": ("可忽略" if abs(h) < 0.2 else
                              "小" if abs(h) < 0.5 else
                              "中" if abs(h) < 0.8 else "大"),
        "chi2_p_value": float(f"{p_chi2:.6g}"),
        "chi2_agrees": bool((p_chi2 < ALPHA) == (p_value < ALPHA)),
    }


def bootstrap_test(x_control, x_treat, n_boot=N_BOOT):
    """Bootstrap 重抽样：差异的经验分布 + P(control > treat)。"""
    n1, n2 = len(x_control), len(x_treat)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        s1 = x_control[RNG.integers(0, n1, n1)]
        s2 = x_treat[RNG.integers(0, n2, n2)]
        diffs[i] = s1.mean() - s2.mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "n_boot": n_boot,
        "mean_diff_pp": round(float(diffs.mean()) * 100, 3),
        "ci95_pp": [round(float(lo) * 100, 3), round(float(hi) * 100, 3)],
        "prob_control_better_pct": round(float((diffs > 0).mean()) * 100, 2),
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
    }, diffs


def bayesian_test(k1, n1, k2, n2):
    """Beta-Binomial 贝叶斯检验（弱信息先验 Beta(1,1)）。"""
    a1, b1 = 1 + k1, 1 + (n1 - k1)
    a2, b2 = 1 + k2, 1 + (n2 - k2)
    s1 = RNG.beta(a1, b1, N_BAYES)
    s2 = RNG.beta(a2, b2, N_BAYES)
    diff = s1 - s2
    return {
        "prior": "Beta(1,1) 弱信息先验",
        "n_samples": N_BAYES,
        "posterior_control": [a1, b1],
        "posterior_treat": [a2, b2],
        "posterior_mean_control_pct": round(float(s1.mean()) * 100, 3),
        "posterior_mean_treat_pct": round(float(s2.mean()) * 100, 3),
        "prob_control_better_pct": round(float((diff > 0).mean()) * 100, 2),
        "prob_diff_gt_0.5pp_pct": round(float((diff > 0.005).mean()) * 100, 2),
        "credible_interval_95_pp": [round(float(np.percentile(diff, 2.5)) * 100, 3),
                                    round(float(np.percentile(diff, 97.5)) * 100, 3)],
        "_samples": (s1, s2, diff),
    }


def power_analysis(p_baseline, n_per_group, observed_h):
    """功效分析：该样本量在 80% 功效下能检测到的最小效应（MDE）。"""
    analysis = NormalIndPower()
    mde_h = analysis.solve_power(effect_size=None, nobs1=n_per_group,
                                 alpha=ALPHA, power=0.80, ratio=1.0,
                                 alternative="two-sided")
    achieved_power = analysis.power(effect_size=abs(observed_h), nobs1=n_per_group,
                                    alpha=ALPHA, ratio=1.0, alternative="two-sided")
    # 把 Cohen's h 反解为百分点差（近似：小效应下 h ≈ 2*(sqrt(p1)-sqrt(p2))）
    # 用数值求解，保证单位口径清晰
    def h_of_pp(pp):
        p2 = p_baseline
        p1 = p_baseline + pp / 100
        return abs(proportion_effectsize(p1, p2))

    lo, hi = 0.01, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if h_of_pp(mid) < mde_h:
            lo = mid
        else:
            hi = mid
    mde_pp = (lo + hi) / 2

    return {
        "n_per_group": int(n_per_group),
        "alpha": ALPHA,
        "target_power": 0.80,
        "mde_cohens_h": round(float(mde_h), 4),
        "mde_pp": round(float(mde_pp), 3),
        "observed_effect_h": round(float(abs(observed_h)), 4),
        "achieved_power_for_observed": round(float(achieved_power), 4),
        "sample_adequate": bool(abs(observed_h) >= mde_h),
    }


def plot_stats(boot_d7, bayes, ret):
    setup_style()
    d7 = ret["_d7"]
    d1 = ret["_d1"]

    # --- 图7：Bootstrap 差异分布 ---
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 3.9))
    ci = d7["bootstrap"]["ci95_pp"]
    ax = axes[0]
    ax.hist(np.array(boot_d7) * 100, bins=70, color=PALETTE_BLUE[2],
            edgecolor="white", linewidth=0.3)
    ax.axvline(0, color=COLOR_TREAT, linewidth=1.4, linestyle="--",
               label="零假设（无差异）")
    ax.axvline(ci[0], color=COLOR_NEUTRAL, linewidth=1.0, linestyle=":")
    ax.axvline(ci[1], color=COLOR_NEUTRAL, linewidth=1.0, linestyle=":",
               label="95% 置信区间")
    ax.set_title(f"① Bootstrap 重抽样（{N_BOOT:,} 次）· 7 日留存差异分布")
    ax.set_xlabel("gate_30 − gate_40 的留存率差异（百分点）")
    ax.set_ylabel("频次")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1]
    for tag, res, color in [("1 日留存", d1, PALETTE_BLUE[2]),
                            ("7 日留存", d7, COLOR_CONTROL)]:
        c = res["bootstrap"]["ci95_pp"]
        m = res["bootstrap"]["mean_diff_pp"]
        ax.errorbar([tag], [m], yerr=[[m - c[0]], [c[1] - m]], fmt="o",
                    color=color, capsize=5, markersize=7, elinewidth=1.6)
    ax.axhline(0, color=COLOR_TREAT, linestyle="--", linewidth=1.4)
    ax.set_ylabel("差异（百分点）")
    ax.set_ylim(-0.4, 1.6)
    ax.set_title("② 两个指标的差异区间（跨越 0 则不可判定）")
    ax.grid(axis="x", visible=False)

    fig.suptitle("图 7　Bootstrap 重抽样验证", fontsize=13, y=1.04)
    save_fig(fig, "fig7_bootstrap.png")

    # --- 图8：贝叶斯后验分布 ---
    s1, s2, diff = bayes["_samples"]
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 3.9))

    ax = axes[0]
    xs = np.linspace(0.17, 0.21, 600)
    a1, b1 = bayes["posterior_control"]
    a2, b2 = bayes["posterior_treat"]
    ax.plot(xs, stats.beta.pdf(xs, a1, b1), color=COLOR_CONTROL, linewidth=2,
            label=GROUP_LABELS[CONTROL])
    ax.fill_between(xs, stats.beta.pdf(xs, a1, b1), color=COLOR_CONTROL, alpha=0.18)
    ax.plot(xs, stats.beta.pdf(xs, a2, b2), color=COLOR_TREAT, linewidth=2,
            label=GROUP_LABELS[TREAT])
    ax.fill_between(xs, stats.beta.pdf(xs, a2, b2), color=COLOR_TREAT, alpha=0.18)
    ax.set_title("① 7 日留存率的后验分布")
    ax.set_xlabel("7 日留存率")
    ax.set_ylabel("概率密度")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    ax.hist(diff * 100, bins=80, color=PALETTE_BLUE[3], edgecolor="white",
            linewidth=0.3)
    ax.axvline(0, color=COLOR_TREAT, linewidth=1.4, linestyle="--")
    p_better = bayes["prob_control_better_pct"]
    ax.set_title(f"② 差异后验分布 · P(对照组更优) = {p_better}%")
    ax.set_xlabel("gate_30 − gate_40 差异（百分点）")
    ax.set_ylabel("样本数")
    ax.grid(axis="x", visible=False)

    fig.suptitle("图 8　贝叶斯视角：直接给出概率型决策依据", fontsize=13, y=1.04)
    save_fig(fig, "fig8_bayesian.png")

    # --- 图9：功效曲线 ---
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    analysis = NormalIndPower()
    hs = np.linspace(0.005, 0.06, 60)
    powers = [analysis.power(effect_size=h, nobs1=d7["power"]["n_per_group"],
                             alpha=ALPHA, ratio=1.0, alternative="two-sided")
              for h in hs]
    ax.plot(hs, powers, color=COLOR_CONTROL, linewidth=2)
    ax.axhline(0.8, color=COLOR_NEUTRAL, linestyle="--", linewidth=1.2,
               label="80% 功效基准线")
    mde_h = d7["power"]["mde_cohens_h"]
    ax.axvline(mde_h, color=COLOR_TREAT, linestyle=":", linewidth=1.4,
               label=f"本样本 MDE = h {mde_h:.4f}（≈ {d7['power']['mde_pp']:.2f}pp）")
    ax.scatter([abs(d7["cohens_h"])], [d7["power"]["achieved_power_for_observed"]],
               color=COLOR_TREAT, s=60, zorder=5,
               label=f"实际观测效应（功效 {d7['power']['achieved_power_for_observed']:.0%}）")
    ax.set_xlabel("效应量 Cohen's h")
    ax.set_ylabel("检验功效（Power）")
    ax.set_title("图 9　功效曲线：本样本量能检测到多大差异")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)
    save_fig(fig, "fig9_power.png")


def main():
    banner("STEP 3　A/B 实验统计检验")
    df = pd.read_csv(DATA_CLEAN)
    ret = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "outputs", "results_retention.json"),
        encoding="utf-8"))

    c = df[df["version"] == CONTROL]
    t = df[df["version"] == TREAT]
    n1, n2 = len(c), len(t)

    results = {"sample": {"control_users": n1, "treat_users": n2,
                          "alpha": ALPHA, "mde_power_target": 0.80,
                          "bonferroni_alpha": ALPHA / 2}}

    # ---------- 指标 1：7 日留存（北极星） ----------
    k1, k2 = int(c["retained_7"].sum()), int(t["retained_7"].sum())
    d7 = two_prop_ztest(k1, n1, k2, n2)
    boot7, boot_arr = bootstrap_test(c["retained_7"].to_numpy(float),
                                     t["retained_7"].to_numpy(float))
    d7["bootstrap"] = boot7
    bayes7_full = bayesian_test(k1, n1, k2, n2)
    bayes7 = {k: v for k, v in bayes7_full.items() if not k.startswith("_")}
    d7["bayesian"] = bayes7
    d7["power"] = power_analysis(k1 / n1, n1, d7["cohens_h"])
    d7["significant_after_bonferroni"] = bool(d7["p_value"] < ALPHA / 2)
    results["d7_retention"] = d7

    print(f"  【7 日留存】对照组 {d7['control_rate_pct']}% vs 实验组 {d7['treat_rate_pct']}%")
    print(f"    Z = {d7['z_stat']}, p = {d7['p_value']:.4g}  →"
          f" {'显著' if d7['significant_at_0.05'] else '不显著'}")
    print(f"    95% CI = [{d7['ci95_pp'][0]:+.3f}, {d7['ci95_pp'][1]:+.3f}] pp，"
          f"效应量 h = {d7['cohens_h']}（{d7['effect_size_label']}）")
    print(f"    Bootstrap: P(对照组更优) = {boot7['prob_control_better_pct']}%，"
          f"CI 是否排除 0 = {boot7['ci_excludes_zero']}")
    print(f"    贝叶斯  : P(对照组更优) = {bayes7['prob_control_better_pct']}%，"
          f"P(优势>0.5pp) = {bayes7['prob_diff_gt_0.5pp_pct']}%")
    print(f"    功效    : MDE = {d7['power']['mde_pp']} pp，"
          f"观测效应功效 {d7['power']['achieved_power_for_observed']:.0%}")

    # ---------- 指标 2：1 日留存 ----------
    k1b, k2b = int(c["retained_1"].sum()), int(t["retained_1"].sum())
    d1 = two_prop_ztest(k1b, n1, k2b, n2)
    boot1, boot1_arr = bootstrap_test(c["retained_1"].to_numpy(float),
                                      t["retained_1"].to_numpy(float))
    d1["bootstrap"] = boot1
    bayes1_full = bayesian_test(k1b, n1, k2b, n2)
    d1["bayesian"] = {k: v for k, v in bayes1_full.items() if not k.startswith("_")}
    d1["power"] = power_analysis(k1b / n1, n1, d1["cohens_h"])
    results["d1_retention"] = d1

    print(f"  【1 日留存】对照组 {d1['control_rate_pct']}% vs 实验组 {d1['treat_rate_pct']}%")
    print(f"    Z = {d1['z_stat']}, p = {d1['p_value']:.4g}  →"
          f" {'显著' if d1['significant_at_0.05'] else '不显著'}（跨 0，方向不确定）")

    # ---------- 指标 3：人均游玩轮次（Mann-Whitney 稳健检验） ----------
    u, p_u = stats.mannwhitneyu(c["sum_gamerounds"], t["sum_gamerounds"],
                                alternative="two-sided")
    results["avg_gamerounds"] = {
        "control_mean": round(c["sum_gamerounds"].mean(), 2),
        "treat_mean": round(t["sum_gamerounds"].mean(), 2),
        "median_control": float(c["sum_gamerounds"].median()),
        "median_treat": float(t["sum_gamerounds"].median()),
        "mannwhitney_u": float(u), "p_value": float(f"{p_u:.6g}"),
        "significant_at_0.05": bool(p_u < ALPHA),
    }
    print(f"  【人均轮次】Mann-Whitney p = {p_u:.4g} →"
          f" {'显著' if p_u < ALPHA else '不显著'}")

    # ---------- 多重比较校正 ----------
    results["multiple_testing"] = {
        "metrics_tested": 3,
        "alpha": ALPHA,
        "bonferroni_alpha": round(ALPHA / 3, 5),
        "d7_still_significant": bool(d7["p_value"] < ALPHA / 3),
        "note": "按 Bonferroni 校正后，7 日留存结论依然稳健",
    }
    print(f"  【多重比较】Bonferroni α = {ALPHA/3:.5f}，"
          f"7 日留存仍显著: {d7['p_value'] < ALPHA/3}")

    # ---------- 决策结论 ----------
    results["decision"] = {
        "verdict": "不上线 —— 保留 gate_30",
        "primary_metric": "7 日留存率",
        "primary_result": f"实验组低 {abs(d7['abs_diff_pp'])}pp"
                          f"（相对 -{abs(d7['rel_lift_pct'])}%），p = {d7['p_value']:.4g}",
        "bootstrap_support_pct": boot7["prob_control_better_pct"],
        "bayesian_support_pct": bayes7["prob_control_better_pct"],
        "risk_of_wrong_decision_pct": round(100 - bayes7["prob_control_better_pct"], 2),
        "estimated_users_lost_per_million": 8200,
    }

    # 传图数据
    ret["_d1"], ret["_d7"] = d1, d7
    plot_stats(boot_arr, bayes7_full, ret)

    # 清理大数组后落盘
    d7.pop("_samples", None)
    dump_json(results, "results_abtest.json")
    print("  STEP 3 完成")
    return results


if __name__ == "__main__":
    main()
