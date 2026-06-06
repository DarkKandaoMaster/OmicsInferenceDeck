"""工具页面热力图：把「算法 × 癌症类型」的二维评分矩阵渲染成热力图。

本模块是无状态的——不读取 upload/ 下的会话文件，而是直接解析前端传来的文本。
绘图逻辑由 senior_algorithms/1.py 迁移而来：YlGnBu 颜色条、单元格两位小数标注、
红框圈出每列最大值。与箱线图不同，热力图无 variant 参数，只有一种图。

输入格式：带「表头行（列名）+ 索引列（行名）」的二维矩阵，支持 CSV / TSV：

示例输入：
,Average,BLCA,BRCA,KIRC
Hclust,6.36,5.79,6.69,6.60
K-means,6.68,6.09,6.37,7.59
MOSD,6.62,6.60,6.34,6.93
NEMO,6.74,6.45,6.64,7.12
PIntMF,6.67,6.69,6.07,7.26
SNF,6.75,6.28,6.87,7.10
Spectral,7.05,6.94,6.58,7.64
"""

import io

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from .base import figure_to_bytes, figure_to_svg


def parse_heatmap_data(text: str) -> pd.DataFrame:
    """用 pandas.read_csv 解析「带表头行 + 索引列」的二维评分矩阵，支持 CSV 与 TSV。

    - 分隔符交给 read_csv 自动嗅探（sep=None + engine="python"），逗号、制表符通吃；
    - 第一行作列名（header=0）、第一列作行名（index_col=0）；
    - 每格用 pd.to_numeric(errors="coerce") 转数值，遇到无法解析的格子抛出带行/列名的中文报错；
    - 空输入、无数据行、列名/行名重复时抛中文 ValueError。
    """
    if not text or not text.strip():
        raise ValueError("输入数据为空，请粘贴带「表头行 + 索引列」的二维评分矩阵（CSV 或 TSV）。")

    # 去掉可能的 UTF-8 BOM（U+FEFF）：从 Excel 导出再粘贴时，文本可能以 BOM 开头，
    # 会让第一个列名/行名带上隐藏字符；str.strip() 不会去掉 U+FEFF，需在此显式 lstrip。
    text = text.lstrip("\ufeff")

    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=None,            # 自动嗅探分隔符：CSV / TSV 通吃
            engine="python",     # 自动嗅探需要 python 引擎
            header=0,            # 第一行作列名
            index_col=0,         # 第一列作行名
            skip_blank_lines=True,
            dtype=str,           # 统一按字符串读入，数值转换与校验自行处理
        )
    except pd.errors.ParserError as exc:
        raise ValueError(f"数据解析失败，请检查格式是否为规范的 CSV / TSV：{exc}")

    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError("没有解析到任何数据，请确认输入包含表头行、索引列以及至少一行一列数据。")

    # 列名 / 行名重复校验（重复会导致取最大值、绘图结果不可预期）
    dup_cols = df.columns[df.columns.duplicated()].tolist()
    if dup_cols:
        raise ValueError(f"列名重复：{ '、'.join(map(str, dup_cols)) }。请确保表头行的每个列名唯一。")
    dup_rows = df.index[df.index.duplicated()].tolist()
    if dup_rows:
        raise ValueError(f"行名重复：{ '、'.join(map(str, dup_rows)) }。请确保索引列的每个行名唯一。")

    # 逐格转数值，定位无法解析的单元格并给出行/列名提示
    numeric = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    bad_mask = numeric.isna() & df.notna()
    if bad_mask.to_numpy().any():
        row_pos, col_pos = bad_mask.to_numpy().nonzero()
        r, c = int(row_pos[0]), int(col_pos[0])
        bad_value = df.iat[r, c]
        raise ValueError(
            f"第「{df.index[r]}」行、第「{df.columns[c]}」列的数值「{bad_value}」无法解析为数字。"
        )

    return numeric


def build_figure(df: pd.DataFrame) -> plt.Figure:
    """把评分矩阵绘制成热力图，完整复刻 senior_algorithms/1.py 的观感。

    - white 主题、YlGnBu 颜色条、单元格两位小数标注、白色网格线；
    - vmin/vmax 从数据动态推算（留少量 padding），以支持任意矩阵；
    - 红框高亮每列最大值所在单元格。
    """
    sns.set_theme(style="white", font="DejaVu Sans")

    # 图尺寸按矩阵形状略作自适应，并保留 1.py 的下限
    n_rows, n_cols = df.shape
    width = max(8.2, 1.3 * n_cols + 2.0)
    height = max(5.2, 0.6 * n_rows + 2.0)
    fig, ax = plt.subplots(figsize=(width, height), dpi=300)

    # 动态色阶范围：在数据 min/max 基础上留一点 padding
    vmin = float(df.min().min())
    vmax = float(df.max().max())
    if vmin == vmax:
        # 全部相等时给一个对称区间，避免颜色条退化
        vmin, vmax = vmin - 0.5, vmax + 0.5
    else:
        pad = (vmax - vmin) * 0.1
        vmin, vmax = vmin - pad, vmax + pad

    cmap = sns.color_palette("YlGnBu", as_cmap=True)
    sns.heatmap(
        df,
        annot=True,
        fmt=".2f",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "3D-AWA score"},
        annot_kws={"fontsize": 10},
        ax=ax,
    )

    ax.set_xlabel("Cancer type / Average", fontsize=11, labelpad=8)
    ax.set_ylabel("Algorithm", fontsize=11, labelpad=8)
    ax.tick_params(axis="x", labelrotation=0, labelsize=10)
    ax.tick_params(axis="y", labelrotation=0, labelsize=10)

    # 红框高亮每列最大值所在单元格
    index_list = list(df.index)
    for col_idx, col in enumerate(df.columns):
        row_label = df[col].idxmax()
        y = index_list.index(row_label)
        rect = plt.Rectangle((col_idx, y), 1, 1, fill=False, edgecolor="#d62728", linewidth=1.8)
        ax.add_patch(rect)

    fig.tight_layout()
    return fig


def render_svg(text: str) -> str:
    return figure_to_svg(build_figure(parse_heatmap_data(text)))


def render_bytes(text: str, file_format: str) -> bytes:
    return figure_to_bytes(build_figure(parse_heatmap_data(text)), file_format)
