"""工具页面箱线图：把「方法名 + 一组数值」的粘贴文本渲染成横向箱线图。

本模块是无状态的——不读取 upload/ 下的会话文件，而是直接解析前端传来的文本。
绘图逻辑由 senior_algorithms/2.py、3.py 两个脚本合并而来，通过 variant 参数化区分

示例输入：
各方法在九个癌症数据集上的-log10 P-values分布：
Subtype-DCC,1.11,2.33,8.79,1.69,3.75,5.94,1.48,5.46,2.77
Subtype-GAN,1.28,1.45,7.77,2.83,1.65,0.1,0.39,7.4,2.62
NEMO,1.21,2.8,5.72,2.63,3.04,5.01,1.8,5.96,2.38
SNF,0.93,1.31,8.19,2.23,3.24,5.27,0.72,5,2.77
PINS,1.42,1.61,4.44,2.46,3.41,2.32,1.26,5.04,3.63
NMF,0.4,0.24,5.63,0.42,1.49,3.54,0.1,5.1,1.39
MCCA,1.73,1.03,7.91,0.49,2.15,0.89,0.18,3.75,1.1
iCluster,0.53,0.21,2.95,0.23,0.54,0.98,0.06,2.13,1.36
Spectral,0.08,1.67,5.46,0.6,2.39,1.77,0.19,0.81,1.82
K-Means,0.12,0.66,4.77,1.01,2.38,1.56,0.01,7.03,1.67
LRAcluster,0.27,0.63,6.83,0.19,2.03,2.05,0.14,4.58,2.52

各方法在九个癌症数据集上的显著临床参数数量分布：
Subtype-DCC,5,6,6,4,1,4,2,1,0
Subtype-GAN,6,4,6,3,1,2,2,1,0
NEMO,6,5,5,4,1,4,2,1,0
SNF,5,6,6,4,3,4,2,1,0
PINS,2,3,6,4,4,1,2,1,0
NMF,4,1,5,1,0,3,1,1,0
MCCA,3,3,5,3,4,3,1,1,1
iCluster,4,3,4,3,0,1,1,1,1
Spectral,4,3,6,1,0,2,2,1,0
K-Means,5,3,6,1,0,1,3,1,0
LRAcluster,5,1,6,1,1,1,1,1,0


测试输入：

① CSV(逗号分隔,名称无空格)—— 预期:✅ 正常
Subtype-DCC,1.11,2.33,8.79,1.69,3.75,5.94,1.48,5.46,2.77
Subtype-GAN,1.28,1.45,7.77,2.83,1.65,0.1,0.39,7.4,2.62
NEMO,1.21,2.8,5.72,2.63,3.04,5.01,1.8,5.96,2.38
SNF,0.93,1.31,8.19,2.23,3.24,5.27,0.72,5,2.77
PINS,1.42,1.61,4.44,2.46,3.41,2.32,1.26,5.04,3.63

② TSV(制表符分隔)—— 预期:✅ 正常（下面每个字段之间是一个 Tab,复制时请确认没被编辑器转成空格）
Subtype-DCC	1.11	2.33	8.79	1.69	3.75	5.94	1.48	5.46	2.77
Subtype-GAN	1.28	1.45	7.77	2.83	1.65	0.1	0.39	7.4	2.62
NEMO	1.21	2.8	5.72	2.63	3.04	5.01	1.8	5.96	2.38
SNF	0.93	1.31	8.19	2.23	3.24	5.27	0.72	5	2.77

③ 名称含空格 + 逗号分隔(把连字符换成空格)—— 预期:✅ 正常
Subtype DCC,1.11,2.33,8.79,1.69,3.75,5.94,1.48,5.46,2.77
Subtype GAN,1.28,1.45,7.77,2.83,1.65,0.1,0.39,7.4,2.62
K Means,0.12,0.66,4.77,1.01,2.38,1.56,0.01,7.03,1.67

④ 逗号后带多余空格(测试 strip 清理)—— 预期:✅ 正常
Subtype-DCC, 1.11 , 2.33 ,  8.79, 1.69, 3.75
  NEMO ,1.21, 2.8 ,5.72, 2.63 , 3.04
SNF , 0.93, 1.31, 8.19 ,2.23, 3.24

⑤ 空格分隔 + 名称无空格 —— 预期:✅ 正常
Subtype-DCC 1.11 2.33 8.79 1.69 3.75 5.94 1.48 5.46 2.77
NEMO 1.21 2.8 5.72 2.63 3.04 5.01 1.8 5.96 2.38
SNF 0.93 1.31 8.19 2.23 3.24 5.27 0.72 5 2.77
K-Means 0.12 0.66 4.77 1.01 2.38 1.56 0.01 7.03 1.67

⑥ 空格分隔 + 名称含空格 —— 预期:❌ 报错(名称被拆,float 失败)
Subtype DCC 1.11 2.33 8.79 1.69 3.75 5.94 1.48 5.46 2.77
Subtype GAN 1.28 1.45 7.77 2.83 1.65 0.1 0.39 7.4 2.62
K Means 0.12 0.66 4.77 1.01 2.38 1.56 0.01 7.03 1.67
"""

import io
import re
from collections import OrderedDict

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from .base import figure_to_bytes, figure_to_svg


VARIANTS: "OrderedDict[str, dict[str, str]]" = OrderedDict(
    [
        ("pvalues", {"xlabel": "-log10 P-values"}),
        ("clinical", {"xlabel": "The number of significant clinical parameters"}),
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


def build_figure(
    data: "OrderedDict[str, list[float]]",
    variant: str,
    xlabel: "str | None" = None,
    ylabel: "str | None" = None,
) -> plt.Figure:
    """把解析后的数据绘制成横向箱线图。

    保留原脚本观感：white 主题、tab10 配色、横向 orient="h"、width=0.7、菱形离群点、despine。

    显示标签与 DataFrame 列名解耦：列名固定为内部常量 "value"，避免用户留空 xlabel
    时列名变成空串。xlabel / ylabel 语义：None=回退该变体默认，空串=该轴不显示文字。
    """
    if variant not in VARIANTS:
        valid = "、".join(VARIANTS.keys())
        raise ValueError(f"未知的图表类型「{variant}」，可选值为：{valid}。")

    config = VARIANTS[variant]
    x_label = config["xlabel"] if xlabel is None else xlabel
    y_label = "Approaches" if ylabel is None else ylabel

    # 方法显示顺序（从上到下）保持输入顺序
    order = list(data.keys())

    # 转换为长格式：列名用固定内部常量，与显示标签解耦
    records = []
    for method, values in data.items():
        for v in values:
            records.append({"Approaches": method, "value": v})
    df = pd.DataFrame(records)

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(
        data=df,
        x="value",
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

    ax.set_xlabel(x_label, fontsize=13)
    ax.set_ylabel(y_label, fontsize=13)
    sns.despine(top=True, right=True, ax=ax)

    fig.tight_layout()
    return fig


def render_svg(
    text: str,
    variant: str,
    xlabel: "str | None" = None,
    ylabel: "str | None" = None,
) -> str:
    return figure_to_svg(build_figure(parse_boxplot_data(text), variant, xlabel, ylabel))


def render_bytes(
    text: str,
    variant: str,
    file_format: str,
    xlabel: "str | None" = None,
    ylabel: "str | None" = None,
) -> bytes:
    return figure_to_bytes(
        build_figure(parse_boxplot_data(text), variant, xlabel, ylabel), file_format
    )
