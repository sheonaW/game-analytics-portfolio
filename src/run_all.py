"""
一键跑通全流程：数据清洗 → 留存分析 → A/B 检验 → 建模 → HTML 报告
用法：python src/run_all.py
"""
import subprocess
import sys
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEPS = [
    ("01_clean.py", "数据加载 · 质量检查 · 清洗"),
    ("02_analysis.py", "留存分析 · 转化漏斗 · 分层归因"),
    ("03_ab_test.py", "A/B 实验统计检验"),
    ("04_churn.py", "留存预测建模 · 投放效率"),
    ("05_build_report.py", "生成 HTML 作品报告"),
]


def main():
    t0 = time.time()
    print("\n" + "#" * 68)
    print("#  手游关卡门槛 A/B 实验与留存归因分析 · 全流程执行")
    print("#" * 68)
    for fname, label in STEPS:
        path = os.path.join(HERE, fname)
        print(f"\n>>> {fname}　—　{label}")
        r = subprocess.run([sys.executable, path], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.stdout:
            print(r.stdout.rstrip())
        if r.returncode != 0:
            print("\n!! 执行失败，标准错误输出：")
            print(r.stderr)
            sys.exit(1)
    print(f"\n{'#' * 68}")
    print(f"#  全部完成，耗时 {time.time() - t0:.1f}s")
    print(f"#  报告：outputs/游戏留存与AB实验分析报告.html")
    print(f"{'#' * 68}\n")


if __name__ == "__main__":
    main()
