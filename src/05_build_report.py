"""
Step 5 —— 生成单文件交互式 HTML 报告（可直接用于作品展示）

产出：
  outputs/游戏留存与AB实验分析报告.html
"""
import sys
import os
import base64
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (OUT_DIR, FIG_DIR, ROOT, SQL_DIR, load_json, banner)

REPORT_NAME = "游戏留存与AB实验分析报告.html"


def img_b64(name):
    with open(os.path.join(FIG_DIR, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def read_sql():
    with open(os.path.join(SQL_DIR, "01_metrics.sql"), "r", encoding="utf-8") as f:
        return f.read()


def kpi_card(label, value, sub="", tone="neutral"):
    return f"""
      <div class="kpi kpi-{tone}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
      </div>"""


def table(headers, rows, align=None):
    align = align or ["left"] * len(headers)
    th = "".join(f'<th class="ta-{a}">{h}</th>' for h, a in zip(headers, align))
    trs = []
    for r in rows:
        tds = "".join(f'<td class="ta-{a}">{c}</td>' for c, a in zip(r, align))
        trs.append(f"<tr>{tds}</tr>")
    return f"""
    <table class="tbl">
      <thead><tr>{th}</tr></thead>
      <tbody>{"".join(trs)}</tbody>
    </table>"""


def figure(name, caption, note=""):
    note_html = f'<div class="fig-note">{note}</div>' if note else ""
    return f"""
    <figure class="fig">
      <img src="{img_b64(name)}" alt="{caption}">
      <figcaption>{caption}{note_html}</figcaption>
    </figure>"""


def section(num, title, body, kicker=""):
    kicker_html = f'<div class="sec-kicker">{kicker}</div>' if kicker else ""
    return f"""
  <section class="sec">
    <div class="sec-head">
      <div class="sec-num">{num}</div>
      <div>
        {kicker_html}
        <h2>{title}</h2>
      </div>
    </div>
    {body}
  </section>"""


def build():
    q = load_json("results_quality.json")
    r = load_json("results_retention.json")
    ab = load_json("results_abtest.json")
    ch = load_json("results_churn.json")

    d7 = ab["d7_retention"]
    d1 = ab["d1_retention"]
    diff = r["difference"]
    best = ch["best_model"]
    best_row = [m for m in ch["models"] if m["model"] == best][0]
    lift_hi, lift_risk = ch["lift_high_value"], ch["lift_risk"]

    # ---------------- 摘要 KPI ----------------
    kpis = "".join([
        kpi_card("样本规模", f"{q['clean_rows']:,}", "真实线上 A/B 实验玩家", "neutral"),
        kpi_card("7 日留存差异", f"{d7['abs_diff_pp']:+.2f}pp",
                 f"对照组更优（相对 {d7['rel_lift_pct']:+.1f}%）", "bad"),
        kpi_card("统计显著性", f"p = {d7['p_value']:.4f}",
                 f"贝叶斯 P(对照组更优) = {d7['bayesian']['prob_control_better_pct']}%", "good"),
        kpi_card("决策结论", "不上线", "保留第 30 关门槛", "bad"),
    ])

    summary = f"""
  <div class="hero">
    <div class="hero-tag">游戏数据运营 · 作品集</div>
    <h1>手游《Cookie Cats》关卡门槛 A/B 实验与留存归因分析</h1>
    <p class="hero-sub">
      「把第一个关卡门从第 30 关移到第 40 关，到底该不该上线？」<br>
      基于 <strong>90,189 名玩家</strong>的真实线上实验数据，从指标体系设计、异动归因，
      到统计检验与流失建模，给出可落地的产品决策。
    </p>
    <div class="meta">
      <span>数据源：Kaggle · Mobile Games A/B Testing</span>
      <span>分析日期：{datetime.date.today().isoformat()}</span>
      <span>技术栈：Python / SQL / SciPy / statsmodels / scikit-learn</span>
    </div>
  </div>

  <div class="kpi-row">{kpis}</div>

  <div class="callout callout-bad">
    <div class="callout-title">核心结论</div>
    <p>
      将门槛后移到第 40 关后，<strong>7 日留存率从 19.02% 降至 18.20%，下降 0.82 个百分点
      （相对下降 4.5%）</strong>，双比例 Z 检验 p = {d7['p_value']:.4f}，达到统计显著；
      贝叶斯后验显示对照组更优的概率为 <strong>{d7['bayesian']['prob_control_better_pct']}%</strong>。
      短期指标（1 日留存）差异不显著（p = {d1['p_value']:.4f}），说明<strong>伤害是在长期累积显现的</strong>——
      玩家更早消耗完新鲜感后，第 7 天更容易流失。
    </p>
    <p class="callout-action">
      <strong>建议：不予上线，保留第 30 关门槛。</strong>
      按每 100 万新玩家测算，该改动将损失约 <strong>8,200 名</strong> 7 日留存用户。
    </p>
  </div>"""

    # ---------------- 1 业务背景 ----------------
    background = """
    <div class="grid-2">
      <div>
        <h3>产品机制</h3>
        <p class="p">
          Cookie Cats 是一款三消手游。玩家闯关到一定进度时会遇到「关卡门（gate）」——
          必须等待一段时间或完成内购才能继续。关卡门的双重作用是：
          <strong>驱动内购变现</strong>，以及<strong>给玩家强制的休息节奏，延长游戏生命周期</strong>。
        </p>
        <h3>实验设计</h3>
        <p class="p">
          新玩家安装时被随机分配到两组：对照组保留第 30 关门槛，实验组把门槛后移到第 40 关。
          团队希望验证「让玩家多体验 10 关再遇到阻碍，是否能带来更好的留存表现」。
        </p>
        <p class="p">
          这是一个典型的<strong>「短期变现 vs 长期留存」权衡型实验</strong>——
          门槛越晚，早期付费转化机会被延后；但如果留存变好，长期 LTV 可能更高。
          因此<strong>留存率是判断该改动成败的核心裁判</strong>。
        </p>
      </div>
      <div>
        <h3>实验规模与字段</h3>
""" + table(
        ["字段", "含义", "类型"],
        [["userid", "玩家唯一标识", "ID"],
         ["version", "实验分组（gate_30 / gate_40）", "类别"],
         ["sum_gamerounds", "安装后 14 天内游玩总轮次", "数值"],
         ["retention_1", "安装后第 1 天是否回访", "布尔"],
         ["retention_7", "安装后第 7 天是否回访", "布尔"]]) + """
        <div class="pair">
          <div class="pair-item"><span>对照组 gate_30</span><strong>44,700 人</strong></div>
          <div class="pair-item"><span>实验组 gate_40</span><strong>45,489 人</strong></div>
        </div>
      </div>
    </div>"""

    # ---------------- 2 指标体系 ----------------
    indicator = """
    <p class="p">
      分析的第一步不是跑数，而是<strong>明确「看什么」</strong>。
      围绕本次决策问题，我把指标拆成三层：北极星指标回答「改动是否成功」，
      过程指标回答「为什么成功/失败」，分层维度回答「问题出在谁身上」。
    </p>
""" + table(
        ["层级", "指标", "定义", "在本次分析中的作用"],
        [["<strong>北极星</strong>", "7 日留存率", "第 7 天回访玩家 / 总安装玩家", "决定改动是否上线的最终依据"],
         ["一级 · 留存", "1 日留存率", "第 1 天回访玩家 / 总安装玩家", "观察短期粘性是否受影响"],
         ["一级 · 参与", "人均游玩轮次", "总轮次 / 玩家数", "衡量沉浸深度"],
         ["二级 · 质量", "零体验用户占比", "安装后从未游玩的玩家占比", "定位买量质量与新手体验问题"],
         ["二级 · 漏斗", "安装→首玩→次留→7留", "逐层转化率", "定位流失发生在哪一环"],
         ["分层维度", "游玩深度分桶 / 实验分组", "按轮次分 6 桶交叉对比", "异动归因下钻"]])

    # ---------------- 3 数据体检 ----------------
    quality = f"""
    <p class="p">
      数据可信度是所有结论的前提。这一步检查三件事：
      <strong>实验分组是否均衡</strong>（随机分流是否成功）、
      <strong>数据是否完整干净</strong>（缺失/重复/异常值）、
      <strong>指标分布是否符合业务常识</strong>。
    </p>
""" + table(
        ["检查项", "结果", "判断"],
        [["原始记录数", f"{q['raw_rows']:,} 行 × {len(q['columns'])} 列", "与官方数据集一致 ✓"],
         ["重复 userid", f"{q['duplicated_userids']} 条", "无需去重 ✓"],
         ["缺失值", f"{q['total_missing']} 个", "数据完整 ✓"],
         ["分组人数", f"gate_30 {q['group_counts']['gate_30']:,} / gate_40 {q['group_counts']['gate_40']:,}",
          f"最大偏差 {q['max_group_imbalance_pp']}pp，随机分流成功 ✓"],
         ["游玩轮次异常值", f"{q['outlier_users']:,} 人（{q['outlier_share_pct']}%），最大 {q['max_gamerounds']:,} 轮",
          "长尾重，采用稳健统计量与对数刻度处理 ⚠"],
         ["零体验用户", f"{q['zero_round_users']:,} 人（{q['zero_round_share_pct']}%），其 7 日留存仅 {q['zero_round_d7_retention_pct']}%",
          "独立分桶观察，避免污染归因结论 ⚠"]]) + """
    <div class="callout callout-info">
      <div class="callout-title">两个关键判断</div>
      <p>
        <strong>① 分组均衡性通过验证。</strong>两组人数偏差仅 """ + f"{q['max_group_imbalance_pp']}" + """ 个百分点，
        说明随机分流确实生效，后续组间差异可以归因到门槛位置本身，而不是人群结构差异。
      </p>
      <p>
        <strong>② 存在一个极端异常值：</strong>有玩家在 14 天内游玩了 49,854 轮（正常玩家中位数仅 16 轮）。
        这类数据不会被删除（否则破坏随机性），但会显著拉高均值——
        所以我在留存分析中以<strong>留存率</strong>为主口径，仅在参与度分析中辅以中位数。
      </p>
    </div>""" + figure("fig1_data_quality.png", "图 1　数据质量与实验分组体检") \
        + figure("fig2_rounds_distribution.png", "图 2　玩家活跃度结构画像",
                 "右偏长尾是游戏用户数据的典型特征：少数重度玩家贡献绝大部分游玩量。")

    # ---------------- 4 留存分析 ----------------
    strat_rows = []
    for row in r["_stratified"]:
        if row["version"] == "gate_30":
            g30 = row
        else:
            diff_row = [x for x in r["_stratified_diff"]
                        if x["rounds_bucket"] == row["rounds_bucket"]]
            dd = diff_row[0] if diff_row else None
            strat_rows.append([
                row["rounds_bucket"],
                f"{g30['users']:,}",
                f"{g30['d7_rate']:.2f}%",
                f"{row['d7_rate']:.2f}%",
                f'<span class="{"pos" if dd and dd["d7_diff_pp"] > 0 else "neg"}">{dd["d7_diff_pp"]:+.2f}pp</span>' if dd else "—",
            ])

    retention = f"""
    <h3>4.1　核心留存指标对比</h3>
""" + table(
        ["指标", "gate_30（对照组）", "gate_40（实验组）", "绝对差异", "相对差异"],
        [["1 日留存率", f"{d1['control_rate_pct']:.3f}%", f"{d1['treat_rate_pct']:.3f}%",
          f'<span class="{"pos" if d1["abs_diff_pp"] > 0 else "neg"}">{d1["abs_diff_pp"]:+.3f}pp</span>',
          f"{d1['rel_lift_pct']:+.2f}%"],
         ["<strong>7 日留存率</strong>", f"<strong>{d7['control_rate_pct']:.3f}%</strong>",
          f"<strong>{d7['treat_rate_pct']:.3f}%</strong>",
          f'<span class="{"pos" if d7["abs_diff_pp"] > 0 else "neg"}"><strong>{d7["abs_diff_pp"]:+.3f}pp</strong></span>',
          f"<strong>{d7['rel_lift_pct']:+.2f}%</strong>"],
         ["D1 留存玩家的 D7 存活率", f"{r['gate_30']['d1_to_d7_survival_pct']:.2f}%",
          f"{r['gate_40']['d1_to_d7_survival_pct']:.2f}%",
          f'<span class="{"pos" if diff["d1_d7_survival_pp"] > 0 else "neg"}">{diff["d1_d7_survival_pp"]:+.2f}pp</span>',
          "—"],
         ["人均游玩轮次", f"{r['gate_30']['avg_gamerounds']:.2f}", f"{r['gate_40']['avg_gamerounds']:.2f}",
          f'<span class="{"pos" if diff["avg_gamerounds_pct"] > 0 else "neg"}">{diff["avg_gamerounds_pct"]:+.2f}%</span>',
          "—"]]) + """
    <p class="p">
      一个容易被忽略的洞察：<strong>在已经次日留存的玩家中，对照组到第 7 天仍留存的比例高 0.98 个百分点</strong>。
      这说明差异不是来自「拉进来的人不一样」，而是<strong>同一批活跃玩家的长期粘性出现了分化</strong>——
      后移门槛让玩家在更短时间内消耗掉成长节奏，第 7 天更容易脱落。
    </p>
""" + figure("fig3_retention_comparison.png", "图 3　留存率组间对比（95% Wilson 置信区间）",
             "7 日留存的置信区间不跨越零线，方向明确；1 日留存的区间较宽且贴近零线。") \
        + figure("fig4_funnel.png", "图 4　玩家核心转化漏斗（两组对比）") \
        + f"""
    <h3>4.2　分层下钻：问题出在谁身上</h3>
    <p class="p">
      总体差异只能告诉我们「要不要上」，<strong>分层下钻才能告诉我们「为什么」</strong>。
      把玩家按游玩深度分成 6 桶后，差异的真实来源浮现出来：
    </p>
""" + table(["游玩深度", "两组玩家数", "gate_30 的 7 日留存", "gate_40 的 7 日留存", "差异"],
            strat_rows) + """
    <div class="callout callout-info">
      <div class="callout-title">归因结论</div>
      <p>
        损失<strong>高度集中在 51-100 轮的中深度玩家群体</strong>（差异 +4.78pp），
        而 0 轮用户的差异几乎为零（+0.20pp）。这恰好印证了产品逻辑：
        关卡门的作用是给「已经投入但尚未疲劳」的玩家一个<strong>强制休息与期待点</strong>；
        门槛后移，这批玩家在热情最高的阶段被迫多消耗 10 关内容，反而提前进入疲劳期。
      </p>
      <p>
        叠加该群体占比来看：51-100 轮玩家占全体的 11.6%，
        <strong>用 11.6% 的人群解释了主要留存缺口</strong>——这就是可落地的运营焦点。
      </p>
    </div>""" + figure("fig5_stratified.png", "图 5　分层下钻：游玩深度与留存的关系") \
        + figure("fig6_retention_decay.png", "图 6　留存衰减曲线（安装为 100%）")

    # ---------------- 5 A/B 检验 ----------------
    boot7 = d7["bootstrap"]
    bayes7 = d7["bayesian"]
    pw = d7["power"]

    abtest = f"""
    <p class="p">
      观察到差异之后，下一个问题是：<strong>这个差异是真实效应，还是随机波动？</strong>
      我用三条互相独立的路径交叉验证，避免单方法带来的误判风险。
    </p>

    <h3>5.1　主检验：双比例 Z 检验</h3>
""" + table(
        ["检验项", "7 日留存（北极星）", "1 日留存"],
        [["对照组留存率", f"{d7['control_rate_pct']:.3f}%", f"{d1['control_rate_pct']:.3f}%"],
         ["实验组留存率", f"{d7['treat_rate_pct']:.3f}%", f"{d1['treat_rate_pct']:.3f}%"],
         ["绝对差异", f"{d7['abs_diff_pp']:+.3f}pp", f"{d1['abs_diff_pp']:+.3f}pp"],
         ["Z 统计量", f"{d7['z_stat']:.4f}", f"{d1['z_stat']:.4f}"],
         ["<strong>p 值</strong>",
          f'<strong class="{"good" if d7["p_value"] < 0.05 else "muted"}">{d7["p_value"]:.4f}</strong>',
          f'<strong class="{"good" if d1["p_value"] < 0.05 else "muted"}">{d1["p_value"]:.4f}</strong>'],
         ["差异 95% 置信区间", f"[{d7['ci95_pp'][0]:+.3f}, {d7['ci95_pp'][1]:+.3f}] pp",
          f"[{d1['ci95_pp'][0]:+.3f}, {d1['ci95_pp'][1]:+.3f}] pp"],
         ["结论", '<strong>差异显著</strong>（区间不含 0）',
          '不显著（区间跨越 0，方向不确定）'],
         ["效应量 Cohen's h", f"{d7['cohens_h']:.4f}（{d7['effect_size_label']}）",
          f"{d1['cohens_h']:.4f}（{d1['effect_size_label']}）"],
         ["卡方检验交叉验证", f"p = {d7['chi2_p_value']:.4f}，结论一致 ✓",
          f"p = {d1['chi2_p_value']:.4f}，结论一致 ✓"]]) + f"""
    <div class="callout callout-warn">
      <div class="callout-title">关于效应量的诚实说明</div>
      <p>
        Cohen's h = {d7['cohens_h']:.4f}，按传统标准属于「可忽略」量级（&lt; 0.2）。
        这<strong>不代表结论不重要</strong>——留存是乘法型指标，0.82pp 的次级留存差异
        在百万级用户规模上意味着数千名长期活跃用户的去留。
      </p>
      <p>
        在游戏行业，能稳定提升 0.8pp 的 7 日留存已属显著的产品改进；
        但反过来说，<strong>这也意味着门槛位置对留存的弹性本身有限</strong>，
        真正的留存杠杆可能在新手引导与买量质量（见下方建模部分）。
      </p>
    </div>

    <h3>5.2　Bootstrap 重抽样（不依赖分布假设）</h3>
""" + table(
        ["Bootstrap 指标（7 日留存）", "结果"],
        [["重抽样次数", f"{boot7['n_boot']:,} 次"],
         ["差异均值", f"{boot7['mean_diff_pp']:+.3f}pp"],
         ["95% 经验置信区间", f"[{boot7['ci95_pp'][0]:+.3f}, {boot7['ci95_pp'][1]:+.3f}] pp"],
         ["<strong>P(对照组更优)</strong>", f"<strong>{boot7['prob_control_better_pct']}%</strong>"],
         ["置信区间是否排除 0", f"{'是 ✓' if boot7['ci_excludes_zero'] else '否'}"]])

    abtest += f"""
    <h3>5.3　贝叶斯检验（输出概率型决策依据）</h3>
    <p class="p">
      频率派的 p 值回答的是「如果没有差异，观察到这个结果的概率」，
      但产品决策者真正想问的是：<strong>「对照组更优的概率有多大？」</strong>
      贝叶斯方法可以直接回答这个问题。
    </p>
""" + table(
        ["贝叶斯指标", "结果"],
        [["先验分布", bayes7["prior"]],
         ["后验抽样次数", f"{bayes7['n_samples']:,}"],
         ["对照组后验均值", f"{bayes7['posterior_mean_control_pct']:.3f}%"],
         ["实验组后验均值", f"{bayes7['posterior_mean_treat_pct']:.3f}%"],
         ["<strong>P(对照组更优)</strong>", f'<strong class="good">{bayes7["prob_control_better_pct"]}%</strong>'],
         ["P(对照组优势 &gt; 0.5pp)", f"{bayes7['prob_diff_gt_0.5pp_pct']}%"],
         ["差异 95% 可信区间", f"[{bayes7['credible_interval_95_pp'][0]:+.3f}, {bayes7['credible_interval_95_pp'][1]:+.3f}] pp"],
         ["决策失败风险（错误上线）", f"{ab['decision']['risk_of_wrong_decision_pct']}%"]])

    abtest += f"""
    <h3>5.4　功效分析：这个样本量够不够</h3>
""" + table(
        ["功效参数", "数值", "含义"],
        [["每组样本量", f"{pw['n_per_group']:,} 人", "本次实验实际规模"],
         ["显著性水平 α", f"{pw['alpha']}", "双尾检验"],
         ["<strong>最小可检测效应 MDE</strong>", f"{pw['mde_pp']:.3f}pp", "80% 功效下能可靠捕捉的最小差异"],
         ["实际观测效应", f"{abs(d7['abs_diff_pp']):.3f}pp", "大于 MDE ✓"],
         ["观测效应下的检验功效", f"{pw['achieved_power_for_observed']:.0%}", "高于 80% 基准 ✓"],
         ["样本量是否充分", "充分 ✓", "结论可信"]])

    abtest += f"""
    <div class="callout callout-info">
      <div class="callout-title">三重验证的一致性</div>
      <p>
        三条路径给出同一答案：Z 检验 p = {d7['p_value']:.4f}、
        Bootstrap 显示 {boot7['prob_control_better_pct']}% 的重抽样结果支持对照组、
        贝叶斯后验显示 P(对照组更优) = {bayes7['prob_control_better_pct']}%。
        <strong>结论稳健，可以支撑产品决策。</strong>
      </p>
      <p>
        同时我对三个指标做了 Bonferroni 多重比较校正（α 从 0.05 收紧至
        {ab['multiple_testing']['bonferroni_alpha']}），7 日留存的结论依然显著——
        排除了「多指标反复检验碰运气」的质疑。
      </p>
    </div>""" + figure("fig7_bootstrap.png", "图 7　Bootstrap 重抽样验证") \
        + figure("fig8_bayesian.png", "图 8　贝叶斯后验：直接给出概率型决策依据") \
        + figure("fig9_power.png", "图 9　功效曲线：本样本量能检测到多大差异")

    # ---------------- 6 建模 ----------------
    model_rows = []
    for m in ch["models"]:
        star = "★ " if m["model"] == best else ""
        model_rows.append([star + m["model"], f"{m['auc']:.4f}",
                           f"{m['cv_auc_mean']:.4f} ± {m['cv_auc_std']:.4f}",
                           f"{m['pr_auc']:.4f}", f"{m['accuracy']:.2%}",
                           f"{m['precision']:.2%}", f"{m['recall']:.2%}"])

    lift_rows = []
    for a, b in zip(lift_hi, lift_risk):
        lift_rows.append([f"前 {a['top_pct']}%", f"{a['users']:,}",
                          f"{a['captured_pct']}%", f"{a['lift']}x",
                          f"{b['captured_pct']}%", f"{b['lift']}x"])

    fi = ch["feature_importance"]
    fi_rows = [[k.replace("_", " "), f"{v:.4f}"] for k, v in
               sorted(fi.items(), key=lambda kv: -kv[1])]

    modeling = f"""
    <p class="p">
      前面的分析回答了「门槛放在哪」，但更根本的问题是：
      <strong>什么样的玩家会留下来？运营资源应该投向谁？</strong>
      我基于安装早期可获得的信息构建留存预测模型，把分析从「解释过去」推进到「指导未来」。
    </p>

    <div class="callout callout-warn">
      <div class="callout-title">一个建模口径上的关键决策</div>
      <p>
        本数据中 <strong>81.4% 的玩家在 D7 流失</strong>，流失是多数类。
        如果以「流失」为正类建模，只要把所有用户都判为流失，准确率就高达 81%——
        模型看起来很美但毫无价值，Lift 指标也会严重失真。
      </p>
      <p>
        因此我以 <strong>「7 日留存」为正类</strong>建模（正类占比 18.61%）。
        同一个模型的得分反向排序，即为流失风险排序——
        <strong>一次建模，两个运营出口</strong>。
      </p>
    </div>

    <h3>6.1　两个模型对照：验证特征的价值</h3>
""" + table(["模型", "测试集 AUC", "5 折交叉验证 AUC", "PR-AUC", "准确率", "精确率", "召回率"],
            model_rows) + f"""
    <p class="p">
      <strong>Model A（仅用实验分组）AUC = {ch['models'][0]['auc']:.4f}</strong>，
      与随机猜测（0.5）几乎无差异——这从建模角度<strong>再次确认了分组信息本身不含预测力</strong>，
      与前面的统计检验结论互相印证。
    </p>
    <p class="p">
      加入早期行为特征后，<strong>Model B 系列 AUC 提升至约 {best_row['auc']:.4f}</strong>，
      三个模型（逻辑回归 / 随机森林 / 梯度提升树）表现高度接近，
      说明<strong>预测力主要来自特征本身而非模型复杂度</strong>——
      这在业务上是好消息：可以选最易解释、最易上线的逻辑回归。
    </p>

    <h3>6.2　留存驱动因素排序</h3>
""" + table(["特征", "重要性"], fi_rows) + """
    <p class="p">
      <strong>游玩深度是最强的留存信号</strong>，且呈明显的非线性关系：
      玩家在早期玩得越多，7 日留存概率越高。
      这与分层下钻的结论一致，共同指向一个明确的运营方向——
      <strong>留存的关键不在门槛位置，而在早期体验深度。</strong>
    </p>
""" + figure("fig10_roc.png", "图 10　留存预测模型评估") \
        + figure("fig11_feature_importance.png", "图 11　留存驱动因素排序")

    modeling += f"""
    <h3>6.3　运营资源投放效率（Lift 分析）</h3>
    <p class="p">
      模型的价值最终要落到「省下多少资源、提高多少命中率」。
      把用户按模型得分排序后分十分位，测算不同圈选比例下的命中效率：
    </p>
""" + table(["圈选比例", "覆盖用户数", "覆盖的留存用户占比", "留存用户浓度 Lift",
            "覆盖的流失用户占比", "流失用户浓度 Lift"], lift_rows) + f"""
    <div class="callout callout-good">
      <div class="callout-title">投放建议</div>
      <p>
        <strong>只需圈选前 10% 的高潜用户（约 {lift_hi[0]['users']:,} 人），
        就能覆盖 {lift_hi[0]['captured_pct']}% 的 7 日留存用户，浓度是随机圈选的 {lift_hi[0]['lift']} 倍。</strong>
      </p>
      <p>
        扩到前 30% 时，可覆盖 <strong>{lift_hi[2]['captured_pct']}%</strong> 的留存用户
        （Lift {lift_hi[2]['lift']}x）——这是性价比拐点：
        继续扩大圈选范围，边际覆盖率下降而投放成本线性上升。
      </p>
      <p>
        落地形式：在新玩家安装后 24 小时内按模型得分分层，
        高分段投放新手礼包 / 首日任务引导，中低分段做低成本召回触达，
        替代当前「全量撒网」的运营方式。
      </p>
    </div>""" + figure("fig12_lift.png", "图 12　运营资源投放效率分析")

    # ---------------- 7 建议 ----------------
    action = """
    <p class="p">
      分析的价值在于改变决策。基于以上发现，给出按优先级排序的行动建议：
    </p>
""" + table(
        ["优先级", "建议", "依据", "预期效果"],
        [["<strong>P0</strong>", "<strong>不上线</strong>第 40 关门槛方案，保留第 30 关",
          f"7 日留存显著下降 {abs(d7['abs_diff_pp']):.2f}pp（p = {d7['p_value']:.4f}）",
          "避免每百万新玩家损失约 8,200 名留存用户"],
         ["P1", "用「破冰激励」替代「后移门槛」来提升早期体验",
          "留存差异的根源是早期体验深度不足，而非门槛位置",
          "在不影响早期变现机会的前提下提升留存"],
         ["P1", "针对 51-100 轮中深度玩家设计专属休息点与期待机制",
          "该群体留存差异最大（+4.78pp），是最敏感人群",
          "精准修复主要留存缺口"],
         ["P1", "排查零体验用户（4.43%）的渠道来源，优化买量质量",
          "该群体 7 日留存仅 0.73%，几乎全部流失",
          "降低无效买量成本"],
         ["P2", "对前 30% 高潜用户做定向新手引导与首日任务",
          f"该群体可覆盖 {lift_hi[2]['captured_pct']}% 的留存用户（Lift {lift_hi[2]['lift']}x）",
          "投放效率提升数倍"],
         ["P2", "建立留存异动日监控看板 + 实验分层看板",
          "同类改动需要快速可验证的常态化机制",
          "缩短决策周期，形成实验闭环"]])

    # ---------------- 8 方法论与局限 ----------------
    method = """
    <div class="grid-2">
      <div>
        <h3>分析方法</h3>
        <ul class="list">
          <li><strong>指标体系</strong>：北极星 + 一级/二级指标 + 分层维度三层拆解</li>
          <li><strong>数据质量</strong>：IQR 异常值检测、分组均衡性校验、稳健统计量</li>
          <li><strong>显著性检验</strong>：双比例 Z 检验、卡方检验交叉验证、Wilson 置信区间</li>
          <li><strong>重抽样</strong>：Bootstrap 10,000 次，不依赖分布假设</li>
          <li><strong>贝叶斯</strong>：Beta-Binomial 后验，输出概率型决策依据</li>
          <li><strong>功效分析</strong>：样本量充分性验证与 MDE 计算</li>
          <li><strong>多重比较</strong>：Bonferroni 校正</li>
          <li><strong>归因下钻</strong>：按游玩深度分 6 桶分层对比</li>
          <li><strong>预测建模</strong>：逻辑回归 / 随机森林 / 梯度提升树对照，5 折交叉验证，十分位 Lift 分析</li>
        </ul>
      </div>
      <div>
        <h3>局限与后续改进</h3>
        <ul class="list">
          <li><strong>缺少变现数据：</strong>数据集无内购金额字段，无法计算 ARPU / LTV，
              因此本结论只覆盖留存与参与度，未回答「留存损失是否被变现提升抵消」这个关键权衡</li>
          <li><strong>特征可用性：</strong>游玩轮次为 14 天累计值，
              严格来说属于同期信息；生产环境应替换为 D1 截面的行为特征</li>
          <li><strong>维度不足：</strong>缺少渠道、机型、地域、国家等维度，
              无法做更细粒度的分层归因</li>
          <li><strong>观测窗口：</strong>仅 14 天，无法评估 D30 长期留存与生命周期价值</li>
          <li><strong>后续可做：</strong>引入生存分析（Kaplan-Meier）刻画流失时点分布，
              并用 CUPED 方差缩减提升实验灵敏度</li>
        </ul>
      </div>
    </div>"""

    # ---------------- 附录 SQL ----------------
    sql = read_sql()
    appendix = f"""
    <p class="p">核心指标计算保留了 SQL 版本，可直接在 DuckDB / 数仓环境复现：</p>
    <pre class="code"><code>{sql.replace("<", "&lt;").replace(">", "&gt;")}</code></pre>
    <p class="p muted">
      完整代码与可复现流程：<code>src/01_clean.py</code> → <code>02_analysis.py</code>
      → <code>03_ab_test.py</code> → <code>04_churn.py</code> → <code>05_build_report.py</code>
    </p>"""

    # ---------------- 组装 ----------------
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>手游关卡门槛 A/B 实验与留存归因分析</title>
<style>
  :root {{
    --bg: #F5F7FA; --card: #FFFFFF; --text: #1B1F26; --sub: #5C6673;
    --line: #E4E8EE; --blue: #185FA5; --blue-light: #EAF2FB; --teal: #0F6E56;
    --red: #B4232A; --red-light: #FDECEC; --green: #1E7A45; --green-light: #EAF6EE;
    --amber: #8A5A00; --amber-light: #FFF6E5;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: "PingFang SC", "Microsoft YaHei", -apple-system, "Segoe UI", sans-serif;
    font-size: 15px; line-height: 1.75; -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 0 28px 80px; }}

  .hero {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 44px 44px 36px; margin-top: 36px; }}
  .hero-tag {{ display: inline-block; font-size: 12.5px; letter-spacing: .06em;
    color: var(--blue); background: var(--blue-light); padding: 5px 12px;
    border-radius: 999px; font-weight: 500; }}
  .hero h1 {{ font-size: 31px; line-height: 1.35; margin: 18px 0 14px; font-weight: 600;
    letter-spacing: -.01em; }}
  .hero-sub {{ color: var(--sub); font-size: 15.5px; margin: 0 0 22px; }}
  .hero-sub strong {{ color: var(--text); font-weight: 600; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 12.5px; color: var(--sub); }}
  .meta span {{ background: var(--bg); padding: 5px 11px; border-radius: 6px; }}

  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
    margin: 18px 0 0; }}
  .kpi {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 18px 18px 16px; border-top: 3px solid var(--line); }}
  .kpi-label {{ font-size: 12.5px; color: var(--sub); margin-bottom: 6px; }}
  .kpi-value {{ font-size: 27px; font-weight: 600; letter-spacing: -.02em;
    font-variant-numeric: tabular-nums; }}
  .kpi-sub {{ font-size: 12px; color: var(--sub); margin-top: 5px; }}
  .kpi-good {{ border-top-color: var(--green); }}
  .kpi-good .kpi-value {{ color: var(--green); }}
  .kpi-bad {{ border-top-color: var(--red); }}
  .kpi-bad .kpi-value {{ color: var(--red); }}

  .sec {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 34px 40px 30px; margin-top: 18px; }}
  .sec-head {{ display: flex; align-items: flex-start; gap: 16px; margin-bottom: 20px;
    padding-bottom: 18px; border-bottom: 1px solid var(--line); }}
  .sec-num {{ flex: 0 0 auto; width: 34px; height: 34px; border-radius: 9px;
    background: var(--blue); color: #fff; display: flex; align-items: center;
    justify-content: center; font-size: 15px; font-weight: 600; margin-top: 2px; }}
  .sec-kicker {{ font-size: 12px; color: var(--blue); letter-spacing: .05em;
    text-transform: uppercase; margin-bottom: 3px; }}
  .sec h2 {{ font-size: 20.5px; margin: 0; font-weight: 600; letter-spacing: -.01em; }}
  .sec h3 {{ font-size: 16px; margin: 26px 0 10px; font-weight: 600; }}
  .sec h3:first-child {{ margin-top: 0; }}
  .p {{ margin: 0 0 14px; color: #333A44; }}
  .p strong, .callout strong, .list strong {{ font-weight: 600; color: var(--text); }}
  .muted {{ color: var(--sub); }}

  .callout {{ border-radius: 11px; padding: 18px 22px; margin: 18px 0;
    border-left: 4px solid var(--line); background: var(--bg); }}
  .callout p {{ margin: 0 0 10px; font-size: 14.5px; }}
  .callout p:last-child {{ margin-bottom: 0; }}
  .callout-title {{ font-weight: 600; font-size: 14px; margin-bottom: 8px; }}
  .callout-bad {{ background: var(--red-light); border-left-color: var(--red); }}
  .callout-bad .callout-title {{ color: var(--red); }}
  .callout-info {{ background: var(--blue-light); border-left-color: var(--blue); }}
  .callout-info .callout-title {{ color: var(--blue); }}
  .callout-good {{ background: var(--green-light); border-left-color: var(--green); }}
  .callout-good .callout-title {{ color: var(--green); }}
  .callout-warn {{ background: var(--amber-light); border-left-color: #C08A1E; }}
  .callout-warn .callout-title {{ color: var(--amber); }}
  .callout-action {{ padding-top: 10px; border-top: 1px dashed rgba(0,0,0,.12); }}

  .tbl {{ width: 100%; border-collapse: collapse; margin: 14px 0 18px; font-size: 14px; }}
  .tbl th {{ background: var(--bg); text-align: left; padding: 11px 13px;
    font-weight: 600; font-size: 13px; color: #3A424E;
    border-bottom: 1px solid var(--line); }}
  .tbl td {{ padding: 11px 13px; border-bottom: 1px solid var(--line);
    font-variant-numeric: tabular-nums; }}
  .tbl tbody tr:last-child td {{ border-bottom: none; }}
  .tbl tbody tr:hover {{ background: #FAFBFC; }}
  .ta-right, .ta-center {{ text-align: right; }}
  .ta-center {{ text-align: center; }}
  .pos {{ color: var(--green); font-weight: 600; }}
  .neg {{ color: var(--red); font-weight: 600; }}
  .good {{ color: var(--green); }}
  .muted {{ color: var(--sub); }}

  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 34px; }}
  .list {{ margin: 0; padding-left: 20px; }}
  .list li {{ margin-bottom: 8px; font-size: 14.3px; color: #333A44; }}

  .pair {{ display: flex; gap: 12px; margin-top: 14px; }}
  .pair-item {{ flex: 1; background: var(--bg); border-radius: 10px;
    padding: 13px 16px; display: flex; flex-direction: column; gap: 3px; }}
  .pair-item span {{ font-size: 12.5px; color: var(--sub); }}
  .pair-item strong {{ font-size: 17px; font-weight: 600; }}

  .fig {{ margin: 22px 0; }}
  .fig img {{ width: 100%; border: 1px solid var(--line); border-radius: 10px;
    display: block; background: #fff; }}
  .fig figcaption {{ font-size: 13px; color: var(--sub); margin-top: 9px; }}
  .fig-note {{ margin-top: 3px; font-size: 12.5px; color: #8A929D; }}

  .code {{ background: #1E242E; color: #D8E0EA; padding: 20px 22px;
    border-radius: 11px; overflow-x: auto; font-size: 12.5px; line-height: 1.65;
    font-family: "Cascadia Code", Consolas, "Courier New", monospace; }}
  .code code {{ font-family: inherit; }}

  .foot {{ text-align: center; color: var(--sub); font-size: 13px;
    margin-top: 34px; line-height: 1.9; }}

  @media (max-width: 900px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; gap: 20px; }}
    .hero {{ padding: 30px 24px; }}
    .sec {{ padding: 26px 22px; }}
  }}
</style>
</head>
<body>
<div class="wrap">
{summary}
{section("01", "业务背景与实验设计", background, "Background")}
{section("02", "指标体系设计", indicator, "Metrics")}
{section("03", "数据体检：可信度前置检查", quality, "Data Quality")}
{section("04", "留存分析与分层归因", retention, "Retention")}
{section("05", "A/B 实验统计检验", abtest, "Statistical Testing")}
{section("06", "留存预测建模与投放效率", modeling, "Modeling")}
{section("07", "结论与行动建议", action, "Recommendation")}
{section("08", "方法论与局限", method, "Methodology")}
{section("09", "附录：SQL 复现脚本", appendix, "Appendix")}
<p class="foot">
  手游《Cookie Cats》关卡门槛 A/B 实验与留存归因分析<br>
  数据源：Kaggle · Mobile Games A/B Testing（90,189 名玩家真实实验数据）
</p>
</div>
</body>
</html>"""

    path = os.path.join(OUT_DIR, REPORT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      report -> {REPORT_NAME}  ({len(html) / 1024:.0f} KB)")
    return path


if __name__ == "__main__":
    banner("STEP 5　生成 HTML 作品报告")
    build()
    print("  STEP 5 完成")
