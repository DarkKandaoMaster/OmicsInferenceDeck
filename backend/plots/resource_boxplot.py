"""资源页面箱线图：把「方法名 + 一组数值」的粘贴文本渲染成横向箱线图。

本模块是无状态的——不读取 upload/ 下的会话文件，而是直接解析前端传来的文本。
绘图逻辑由 senior_algorithms/2.py、3.py 两个脚本合并而来，通过 variant 参数化区分
x 轴标签与标题（A：-log10 P-values；B：显著临床参数数量）。
"""

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
    """解析「名称,数值,数值,...」格式的多行文本。

    - 空行（含纯空白行）跳过；
    - 每行第一个字段为方法名，其余字段为数值，数量不限（不硬编码 9）；
    - 名称缺失、数值无法解析或最终无任何有效行时，抛出 ValueError 并给出中文提示。
    """
    if not text or not text.strip():
        raise ValueError("输入数据为空，请粘贴「名称,数值,数值,...」格式的数据。")

    data: "OrderedDict[str, list[float]]" = OrderedDict()
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        # 优先按逗号切分；若整行没有逗号，则退化为按空白切分，更宽容
        parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
        parts = [p for p in parts if p != ""]
        if len(parts) < 2:
            raise ValueError(f"第 {lineno} 行格式错误：需要「名称」加上至少一个数值。")

        name = parts[0]
        values: list[float] = []
        for token in parts[1:]:
            try:
                values.append(float(token))
            except ValueError:
                raise ValueError(f"第 {lineno} 行的数值「{token}」无法解析为数字。")

        if name in data:
            raise ValueError(f"第 {lineno} 行的方法名「{name}」重复。")
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
