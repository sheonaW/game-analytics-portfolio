"""
Step 4 —— 用户留存预测建模与运营资源投放效率分析

建模目标：在安装早期识别"高价值留存用户"，并反向输出"流失风险名单"。

⚠️ 为什么不用"流失"作为正类？
   本数据中有 81.4% 的玩家在 D7 流失，流失是多数类。若以流失为正类，
   只要把所有用户都预测为流失，准确率就高达 81%，模型价值被掩盖，
   Lift 指标也会失真。因此这里以"7 日留存"为正类建模，同一个模型的
   得分反向排序即为流失风险排序 —— 一次建模，两个运营出口。

模型设计（体现"特征可得性"的严谨性）：
  Model A · 安装时点模型 —— 仅有实验分组信息，验证"单靠分组无法预测留存"
  Model B · 早期行为模型 —— 加入行为特征，作为可落地的用户分层模型

⚠️ 诚实声明：本数据集只提供 14 天累计游玩轮次与 D1/D7 留存标记，
   Model B 的"游玩深度"特征严格来说属于同期信息而非 D1 截面信息。
   此处用于完整演示建模与评估流程；生产环境应替换为 D1 截面行为特征。

产出：
  outputs/results_churn.json
  outputs/figures/fig10~fig12_*.png
"""
import sys
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (roc_auc_score, average_precision_score, roc_curve,
                             accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_CLEAN, COLOR_CONTROL, COLOR_TREAT, COLOR_NEUTRAL,
                    PALETTE_BLUE, save_fig, dump_json, setup_style, banner)

FEATURE_CN = {
    "version_gate_40": "实验分组（gate_40=1）",
    "retained_1": "是否次日留存",
    "played_any": "是否曾游玩（≥1轮）",
    "log_rounds": "游玩深度 log(轮次+1)",
    "rounds_gt_20": "是否游玩>20轮",
    "rounds_gt_50": "是否游玩>50轮",
    "bucket_ord": "游玩深度等级(0-5)",
}
RNG_SEED = 42


def build_features(df):
    d = df.copy()
    d["version_gate_40"] = (d["version"] == "gate_40").astype(int)
    d["played_any"] = d["played_any"].astype(int)
    d["rounds_gt_20"] = (d["sum_gamerounds"] > 20).astype(int)
    d["rounds_gt_50"] = (d["sum_gamerounds"] > 50).astype(int)
    bucket_map = {"0 轮": 0, "1-5 轮": 1, "6-20 轮": 2, "21-50 轮": 3,
                  "51-100 轮": 4, "100 轮以上": 5}
    d["bucket_ord"] = d["rounds_bucket"].map(bucket_map).astype(int)
    d["y"] = d["retained_7"].astype(int)      # 1 = 7 日留存（高价值）
    return d


def evaluate(model, X_tr, y_tr, X_te, y_te, name):
    model.fit(X_tr, y_tr)
    prob = model.predict_proba(X_te)[:, 1]
    pred = (prob >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_te, pred).ravel()
    cv = cross_val_score(model, X_tr, y_tr,
                         cv=StratifiedKFold(5, shuffle=True, random_state=RNG_SEED),
                         scoring="roc_auc")
    return {
        "model": name,
        "auc": round(roc_auc_score(y_te, prob), 4),
        "pr_auc": round(average_precision_score(y_te, prob), 4),
        "accuracy": round(accuracy_score(y_te, pred), 4),
        "precision": round(precision_score(y_te, pred, zero_division=0), 4),
        "recall": round(recall_score(y_te, pred, zero_division=0), 4),
        "f1": round(f1_score(y_te, pred, zero_division=0), 4),
        "cv_auc_mean": round(cv.mean(), 4),
        "cv_auc_std": round(cv.std(), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp),
                             "fn": int(fn), "tp": int(tp)},
        "_prob": prob,
    }


def decile_lift(y_true, score, direction="desc"):
    """十分位提升分析。

    direction='desc'：按得分降序圈选（得分 = P(留存)，圈高价值用户）
    direction='asc' ：按得分升序圈选（圈流失风险用户）
    """
    d = pd.DataFrame({"y": y_true, "s": score})
    rank = d["s"].rank(method="first", ascending=(direction == "asc"))
    d["decile"] = pd.qcut(rank, 10, labels=False) + 1
    base = d["y"].mean()
    rows = []
    for k in range(1, 11):
        sub = d[d["decile"] <= k]
        rows.append({
            "top_pct": k * 10,
            "users": int(len(sub)),
            "captured_pct": round(sub["y"].sum() / d["y"].sum() * 100, 2),
            "lift": round(sub["y"].mean() / base, 2),
            "precision_pct": round(sub["y"].mean() * 100, 2),
        })
    return rows


def plot_models(results, feat_imp, lift_hi, lift_risk, y_te):
    setup_style()

    # --- 图10：ROC 曲线对比 ---
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.2))
    ax = axes[0]
    colors = [PALETTE_BLUE[2], PALETTE_BLUE[3], COLOR_CONTROL, COLOR_TREAT]
    for r, c in zip(results, colors):
        fpr, tpr, _ = roc_curve(y_te, r["_prob"])
        ax.plot(fpr, tpr, linewidth=1.8, color=c,
                label=f'{r["model"]}（AUC {r["auc"]:.3f}）')
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.0, color=COLOR_NEUTRAL,
            label="随机猜测（AUC 0.500）")
    ax.set_xlabel("假正率 FPR")
    ax.set_ylabel("真正率 TPR")
    ax.set_title("① ROC 曲线对比")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")

    ax = axes[1]
    names = [r["model"] for r in results]
    aucs = [r["auc"] for r in results]
    bars = ax.barh(names, aucs, color=colors, height=0.5)
    for b, v in zip(bars, aucs):
        ax.text(v + 0.005, b.get_y() + b.get_height() / 2, f"{v:.3f}",
                va="center", fontsize=9)
    ax.axvline(0.5, color=COLOR_NEUTRAL, linestyle="--", linewidth=1.0)
    ax.set_xlim(0.45, 0.98)
    ax.set_xlabel("测试集 AUC")
    ax.set_title("② 模型区分能力（0.5 = 无预测力）")
    ax.grid(axis="y", visible=False)

    fig.suptitle("图 10　留存预测模型评估", fontsize=13, y=1.03)
    save_fig(fig, "fig10_roc.png")

    # --- 图11：特征重要性 ---
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    items = sorted(feat_imp.items(), key=lambda kv: kv[1])
    names = [FEATURE_CN.get(k, k) for k, _ in items]
    vals = [v for _, v in items]
    bars = ax.barh(names, vals, color=PALETTE_BLUE[3], height=0.55)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.015, b.get_y() + b.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("重要性（随机森林不纯度重要性）")
    ax.set_title("图 11　留存驱动因素排序")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.grid(axis="y", visible=False)
    save_fig(fig, "fig11_feature_importance.png")

    # --- 图12：双向提升曲线 ---
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 3.9))
    xs = [r["top_pct"] for r in lift_hi]

    ax = axes[0]
    ax.plot(xs, [r["captured_pct"] for r in lift_hi], marker="o",
            color=COLOR_CONTROL, linewidth=2, label="高价值用户（按留存概率降序）")
    ax.plot(xs, [r["captured_pct"] for r in lift_risk], marker="s",
            color=COLOR_TREAT, linewidth=2, label="流失用户（按流失概率降序）")
    ax.plot(xs, xs, linestyle="--", color=COLOR_NEUTRAL, linewidth=1.0,
            label="随机圈选基准")
    ax.set_xlabel("按得分排序圈选的前 N% 用户")
    ax.set_ylabel("捕获目标人群占比 %")
    ax.set_title("① 提升曲线：定向运营的覆盖效率")
    ax.legend(frameon=False, fontsize=8)
    ax.set_ylim(0, 105)

    ax = axes[1]
    ax.plot(xs, [r["lift"] for r in lift_hi], marker="o", color=COLOR_CONTROL,
            linewidth=2, label="高价值用户识别 Lift")
    ax.plot(xs, [r["lift"] for r in lift_risk], marker="s", color=COLOR_TREAT,
            linewidth=2, label="流失用户识别 Lift")
    ax.axhline(1.0, color=COLOR_NEUTRAL, linestyle="--", linewidth=1.2,
               label="无提升基准（lift = 1.0）")
    ax.set_xlabel("圈选比例 %")
    ax.set_ylabel("Lift（目标人群浓度倍数）")
    ax.set_title("② 圈选比例与人群浓度")
    ax.legend(frameon=False, fontsize=8)

    fig.suptitle("图 12　运营资源投放效率分析", fontsize=13, y=1.03)
    save_fig(fig, "fig12_lift.png")


def main():
    banner("STEP 4　留存预测建模 · 用户画像 · 投放效率")
    df = pd.read_csv(DATA_CLEAN)
    d = build_features(df)

    y = d["y"].to_numpy()
    print(f"  样本: {len(d):,}　7 日留存率（正类）: {y.mean()*100:.2f}%　"
          f"7 日流失率: {(1-y.mean())*100:.2f}%")

    feat_a = ["version_gate_40"]
    feat_b = ["version_gate_40", "retained_1", "played_any",
              "log_rounds", "rounds_gt_20", "rounds_gt_50", "bucket_ord"]

    res = {"sample": {"rows": int(len(d)),
                      "positive_class": "7 日留存（retention_7 = True）",
                      "positive_rate_pct": round(y.mean() * 100, 2),
                      "features_model_a": [FEATURE_CN[f] for f in feat_a],
                      "features_model_b": [FEATURE_CN[f] for f in feat_b]},
           "models": []}

    results, y_targets = [], {}

    # ---- Model A：仅实验分组（基线，验证分组无预测力） ----
    Xa = d[feat_a].to_numpy()
    Xa_tr, Xa_te, ya_tr, ya_te = train_test_split(
        Xa, y, test_size=0.25, random_state=RNG_SEED, stratify=y)
    mA = evaluate(LogisticRegression(max_iter=1000, random_state=RNG_SEED),
                  Xa_tr, ya_tr, Xa_te, ya_te, "Model A · 仅实验分组")
    print(f"  Model A AUC = {mA['auc']}　（≈0.5 → 分组信息无预测力，符合预期）")
    results.append(mA)
    y_targets[mA["model"]] = ya_te

    # ---- Model B：早期行为模型 ----
    Xb = d[feat_b].to_numpy()
    Xb_tr, Xb_te, yb_tr, yb_te = train_test_split(
        Xb, y, test_size=0.25, random_state=RNG_SEED, stratify=y)

    mB1 = evaluate(Pipeline([("sc", StandardScaler()),
                            ("lr", LogisticRegression(max_iter=2000,
                                                      random_state=RNG_SEED))]),
                   Xb_tr, yb_tr, Xb_te, yb_te, "Model B1 · 逻辑回归")
    mB2 = evaluate(RandomForestClassifier(n_estimators=300, max_depth=8,
                                          min_samples_leaf=50, n_jobs=-1,
                                          random_state=RNG_SEED),
                   Xb_tr, yb_tr, Xb_te, yb_te, "Model B2 · 随机森林")
    mB3 = evaluate(GradientBoostingClassifier(n_estimators=250, learning_rate=0.08,
                                              max_depth=3, random_state=RNG_SEED),
                   Xb_tr, yb_tr, Xb_te, yb_te, "Model B3 · 梯度提升树")

    for m in (mB1, mB2, mB3):
        results.append(m)
        y_targets[m["model"]] = yb_te
        print(f"  {m['model']:<22s} AUC {m['auc']:.4f}  CV-AUC "
              f"{m['cv_auc_mean']:.4f}±{m['cv_auc_std']:.4f}  "
              f"PR-AUC {m['pr_auc']:.4f}")

    # 特征重要性
    rf = RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=50,
                                n_jobs=-1, random_state=RNG_SEED).fit(Xb_tr, yb_tr)
    lr = Pipeline([("sc", StandardScaler()),
                   ("lr", LogisticRegression(max_iter=2000,
                                             random_state=RNG_SEED))]).fit(Xb_tr, yb_tr)
    imp = dict(zip(feat_b, rf.feature_importances_))
    feat_imp = {k: round(float(v), 4) for k, v in imp.items()}
    coefs = dict(zip(feat_b, lr.named_steps["lr"].coef_[0]))

    best = max(results, key=lambda r: r["auc"])
    y_best = y_targets[best["model"]]
    score = best["_prob"]
    lift_hi = decile_lift(y_best, score, direction="desc")   # 圈高价值用户
    lift_risk = decile_lift(1 - y_best, -score, direction="desc")  # 圈流失用户

    print(f"  最佳模型: {best['model']}（AUC {best['auc']}）")
    print(f"  高价值圈选: 前 10% 覆盖 {lift_hi[0]['captured_pct']}% 的留存用户"
          f"（Lift {lift_hi[0]['lift']}x）；前 30% 覆盖 {lift_hi[2]['captured_pct']}%")
    print(f"  流失风险圈选: 前 10% 覆盖 {lift_risk[0]['captured_pct']}% 的流失用户"
          f"（Lift {lift_risk[0]['lift']}x）；前 30% 覆盖 {lift_risk[2]['captured_pct']}%")

    res["models"] = [{k: v for k, v in r.items() if not k.startswith("_")}
                     for r in results]
    res["best_model"] = best["model"]
    res["feature_importance"] = feat_imp
    res["logistic_coefficients"] = {FEATURE_CN.get(k, k): round(float(v), 4)
                                    for k, v in coefs.items()}
    res["lift_high_value"] = lift_hi
    res["lift_risk"] = lift_risk
    res["business_reading"] = {
        "high_value_top10_capture_pct": lift_hi[0]["captured_pct"],
        "high_value_top10_lift": lift_hi[0]["lift"],
        "high_value_top30_capture_pct": lift_hi[2]["captured_pct"],
        "high_value_top30_lift": lift_hi[2]["lift"],
        "risk_top10_capture_pct": lift_risk[0]["captured_pct"],
        "risk_top30_capture_pct": lift_risk[2]["captured_pct"],
        "conclusion": "前 30% 高潜用户可覆盖约八成留存用户，"
                      "运营资源应集中投向该人群而非全量撒网",
    }

    plot_models(results, feat_imp, lift_hi, lift_risk, y_best)
    dump_json(res, "results_churn.json")
    print("  STEP 4 完成")
    return res


if __name__ == "__main__":
    main()
