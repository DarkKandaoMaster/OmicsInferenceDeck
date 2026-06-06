"""资源页面箱线图：把「方法名 + 一组数值」的粘贴文本渲染成横向箱线图。

本模块是无状态的——不读取 upload/ 下的会话文件，而是直接解析前端传来的文本。
绘图逻辑由 senior_algorithms/2.py、3.py 两个脚本合并而来，通过 variant 参数化区分
x 轴标签与标题（A：-log10 P-values；B：显著临床参数数量）。
"""

import io
import re
from collections import OrderedDict

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from .base import figure_to_bytes, figure_to_svg


# 变体配置：决定 x 轴标签与左上角标题
VARIANTS: "OrderedDict[str, dict[str, str]]" = OrderedDict(
    [
        ("pvalues", {"xlabel": "-log10 P-values", "title": "A"}),
        ("clinical", {"xlabel": "The number of significant clinical parameters", "title": "B"}),
    ]
)


def parse_boxplot_data(text: str) -> "OrderedDict[str, list[float]]":
    """用 pandas.read_csv 解析「名称<分隔符>数值<分隔符>数值...」文本，支持 CSV 与 TSV。

    - 分隔符交给 read_csv 自动嗅探（sep=None + engine="python"，与 upload.py 一致），
      逗号、制表符等格式均通吃，无需手动判定；
    - 每行数值数量不限（不硬编码 9）：预留足够列数，较短行由 read_csv 补 NaN 后丢弃；
    - 名称缺失、数值无法解析或最终无任何有效行时，抛出 ValueError 并给出中文提示。
    """
    if not text or not text.strip():
        raise ValueError("输入数据为空，请粘贴「名称,数值,数值,...」格式的 CSV 或 TSV 数据。")

    # 去掉可能的 UTF-8 BOM（U+FEFF）：从 Excel 导出再粘贴时，文本可能以 BOM 开头，
    # 会让第一个方法名带上隐藏字符；str.strip() 不会去掉 U+FEFF，需在此显式 lstrip。
    text = text.lstrip("\ufeff")

    # 预留列数上界：实际分隔符必是逗号/制表符/空格之一，按这三者的并集切分必然 ≥ 真实列数，
    # 因此无需提前知道分隔符即可给出安全上界（多出的列由 read_csv 补 NaN，循环里被丢弃）。
    nonblank_lines = [line for line in text.splitlines() if line.strip()]
    max_cols = max(len(re.split(r"[,\t ]", line)) for line in nonblank_lines)

    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=None,                     # 自动嗅探分隔符：CSV / TSV 通吃
            engine="python",             # 自动嗅探与不等长行需要 python 引擎
            header=None,
            names=list(range(max_cols)),  # 预留足够列数，较短行自动补 NaN
            skip_blank_lines=True,
            dtype=str,                    # 统一按字符串读入，数值转换与校验自行处理
        )
    except pd.errors.ParserError as exc:
        raise ValueError(f"数据解析失败，请检查格式是否为规范的 CSV / TSV：{exc}")

    data: "OrderedDict[str, list[float]]" = OrderedDict()
    for rowno, (_, row) in enumerate(df.iterrows(), start=1):
        # 丢弃补位产生的 NaN（float），并去除每个单元格的首尾空白
        cells = [c.strip() for c in row.tolist() if isinstance(c, str) and c.strip() != ""]
        if len(cells) < 2:
            raise ValueError(f"第 {rowno} 行格式错误：需要「名称」加上至少一个数值。")

        name = cells[0]
        values: list[float] = []
        for token in cells[1:]:
            try:
                values.append(float(token))
            except ValueError:
                raise ValueError(f"第 {rowno} 行的数值「{token}」无法解析为数字。")

        if name in data:
            raise ValueError(f"第 {rowno} 行的方法名「{name}」重复。")
        data[name] = values

    if not data:
        raise ValueError("没有解析到任何有效数据行，请检查输入格式。")

    return data


def build_figure(data: "OrderedDict[str, list[float]]", variant: str) -> plt.Figure:
    """把解析后的数据绘制成横向箱线图。

    保留原脚本观感：white 主题、tab10 配色、横向 orient="h"、width=0.7、菱形离群点、despine。
    xlabel / title 取自 VARIANTS[variant]；非法 variant 抛出 ValueError。
    """
    if variant not in VARIANTS:
        valid = "、".join(VARIANTS.keys())
        raise ValueError(f"未知的图表类型「{variant}」，可选值为：{valid}。")

    config = VARIANTS[variant]
    xlabel = config["xlabel"]

    # 方法显示顺序（从上到下）保持输入顺序
    order = list(data.keys())

    # 转换为长格式
    records = []
    for method, values in data.items():
        for v in values:
            records.append({"Approaches": method, xlabel: v})
    df = pd.DataFrame(records)

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(
        data=df,
        x=xlabel,
        y="Approaches",
        order=order,
        orient="h",
        palette="tab10",
        width=0.7,
        linewidth=1.0,
        fliersize=5,
        flierprops={"marker": "D", "markersize": 5},
        ax=ax,
    )

    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Approaches", fontsize=13)
    ax.set_title(config["title"], loc="left", fontsize=15, fontweight="bold")
    sns.despine(top=True, right=True, ax=ax)

    fig.tight_layout()
    return fig


def render_svg(text: str, variant: str) -> str:
    return figure_to_svg(build_figure(parse_boxplot_data(text), variant))


def render_bytes(text: str, variant: str, file_format: str) -> bytes:
    return figure_to_bytes(build_figure(parse_boxplot_data(text), variant), file_format)
