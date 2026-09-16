"""
共用配置：路径、绘图样式、结果读写。
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(ROOT, "data", "cookie_cats.csv")
DATA_CLEAN = os.path.join(ROOT, "data", "cookie_cats_clean.csv")
OUT_DIR = os.path.join(ROOT, "outputs")
FIG_DIR = os.path.join(OUT_DIR, "figures")
SQL_DIR = os.path.join(ROOT, "sql")

for _d in (OUT_DIR, FIG_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------
# 配色（与报告主题一致）
# ---------------------------------------------------------------
COLOR_CONTROL = "#2E75B6"   # 对照组 gate_30 —— 蓝
COLOR_TREAT = "#D85A30"     # 实验组 gate_40 —— 橙红
COLOR_NEUTRAL = "#8A8F98"
COLOR_GRID = "#DCE1E8"
COLOR_TEXT = "#2B2F36"
PALETTE_BLUE = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5", "#0C447C"]

GROUP_COLORS = {"gate_30": COLOR_CONTROL, "gate_40": COLOR_TREAT}
GROUP_LABELS = {"gate_30": "gate_30（对照组）", "gate_40": "gate_40（实验组）"}


def setup_style():
    """统一绘图样式，并解决中文字体。"""
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": COLOR_GRID,
        "axes.labelcolor": COLOR_TEXT,
        "axes.titlecolor": COLOR_TEXT,
        "text.color": COLOR_TEXT,
        "xtick.color": COLOR_TEXT,
        "ytick.color": COLOR_TEXT,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.grid": True,
        "grid.color": COLOR_GRID,
        "grid.linewidth": 0.6,
        "grid.alpha": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": False,
    })


def save_fig(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"      figure -> {name}")
    return path


def dump_json(obj, name):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    print(f"      result -> {name}")
    return path


def load_json(name):
    with open(os.path.join(OUT_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def banner(text):
    print("\n" + "=" * 68)
    print(text)
    print("=" * 68)
