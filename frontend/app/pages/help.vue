<script setup lang="ts">
useHead({ title: 'Help - OmicsInferenceDeck' })

const sections = [
  {
    id: 'background',
    eyebrow: 'Background',
    title: '研究背景与痛点',
    paragraphs: [
      '癌症是一类高度复杂的疾病。即使是同一种癌症，不同患者之间也可能存在明显的分子差异和治疗响应差异。因此，研究者需要结合基因组、转录组、表观组等多组学数据，对患者进行更精细的亚型识别，从而支持预后评估、标志物发现和个体化治疗。',
      '近年来，多组学癌症亚型识别算法发展迅速。但在实际研究中，模型训练完成并获得聚类标签并不意味着研究流程结束。聚类结果是否可信，还需要进一步回答三个问题：分群结构是否合理、是否与生存结局和临床特征相关、是否具有明确的生物学解释。而这正是当前研究流程中的痛点。',
      '在算法训练后的评估阶段，研究者往往需要依赖大量分散的 Python、R 脚本和绘图模板。不同脚本之间的数据格式、样本交集和统计口径并不统一，导致结果难以横向比较，也难以复现。大量时间被消耗在整理文件、转换格式和重复绘图上，而不是聚焦于真正的科学问题。',
    ],
  },
  {
    id: 'platform',
    eyebrow: 'Platform',
    title: '平台定位与系统架构',
    paragraphs: [
      '基于这一背景，我们研发了 OmicsInferenceDeck 平台。它面向算法训练后的评估、验证和成果呈现，提供一套统一、透明、可复核的工作流。平台将指标计算、生存分析、临床关联分析、差异表达分析、GO/KEGG 富集分析、参数敏感性分析，以及论文级图表导出，整合到同一条流程中。',
      '在系统架构上，平台采用前后端分离设计。前端基于 Nuxt 和 Vue 构建交互式工作台，后端基于 FastAPI，结合 Python 与 R 完成统计分析和可视化任务。同时，系统通过 session_id 管理每一次分析任务，保证整个流程可追踪、可复现。',
    ],
  },
  {
    id: 'custom-mode',
    eyebrow: 'Analysis · Mode 1',
    title: '自定义算法评估模式',
    paragraphs: [
      '接下来，我们看一下平台的具体使用方法。进入 Analysis 页面后，用户可以选择两种分析入口：自定义算法评估模式和内置基线算法模式。',
      '自定义算法评估模式适合已经在平台外完成模型训练的用户。用户只需要上传多组学矩阵、临床随访数据、mRNA 表达矩阵，以及外部算法输出的聚类结果。平台会自动校验样本名、特征名、缺失值、关键临床字段和样本交集，随后围绕聚类结构、临床预后和生物学机制三个层面生成证据，解释分型结果。',
    ],
  },
  {
    id: 'baseline-mode',
    eyebrow: 'Analysis · Mode 2',
    title: '内置基线算法模式',
    paragraphs: [
      '内置基线算法模式主要用于论文中的横向对照实验。用户上传同样的数据后，可以直接选择 K-means、Hclust、SpectralClustering、SNF、NEMO、PIntMF、MOSD 等方法，并配置聚类簇数、随机种子、邻居数、迭代次数等参数。',
      '平台会调用对应的后端模块，生成与自定义算法评估模式格式一致的聚类标签和融合表征，以此实现自研算法和基线算法在相同数据、相同指标和相同图表规范下进行比较。',
    ],
  },
  {
    id: 'sensitivity',
    eyebrow: 'Sensitivity',
    title: '参数敏感性分析',
    paragraphs: [
      '平台还支持参数敏感性分析。对于内置算法，用户可以设置参数搜索范围，平台批量运行后通过 Log-rank 检验评估不同参数组合的预后区分能力，并生成二维曲线或三维曲面；对于平台外完成的参数扫描，也可以上传 MATLAB 的 .mat 结果文件，直接生成敏感性图表。',
    ],
  },
  {
    id: 'results',
    eyebrow: 'Results & Tools',
    title: '结果查看与图表工具',
    paragraphs: [
      '分析完成后，用户可以在结果页面集中查看和调整各类图表，并将散点图、生存曲线、火山图、热图、富集图和参数敏感性曲线导出为 PNG、SVG 或 PDF。',
      '除此之外，Tools 页面还提供图表拼接、箱线图和热图三个轻量化工具，既能整理平台主流程导出的结果，也能接收外部实验数据，帮助用户快速形成论文组图和答辩材料。',
    ],
  },
  {
    id: 'summary',
    eyebrow: 'Summary',
    title: '总结',
    paragraphs: [
      '总的来说，OmicsInferenceDeck 将原本分散、繁琐、难以复现的脚本操作，转化为统一、可追踪、可比较的服务化工作流。它帮助研究者更高效地把算法输出，转化为结构合理、临床相关、机制可解释，并且适合展示和发表的科研证据。',
    ],
  },
]
</script>

<template>
  <div class="mx-auto max-w-4xl px-6 py-12 lg:py-16">
    <header class="mb-12">
      <p class="text-sm font-bold uppercase tracking-wider text-indigo-600">Help</p>
      <h1 class="mt-4 text-3xl font-extrabold text-slate-900 md:text-4xl">
        OmicsInferenceDeck 使用帮助
      </h1>
      <p class="mt-5 text-lg leading-8 text-slate-600">
        本页面介绍平台的研究背景、系统架构以及完整的使用流程，帮助您快速上手分析工作。
      </p>
      <a
        href="/samples/samples.7z"
        download
        class="mt-6 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-indigo-500"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        下载示例输入数据
      </a>
    </header>

    <div class="space-y-12">
      <section v-for="section in sections" :id="section.id" :key="section.id">
        <p class="text-xs font-bold uppercase tracking-wider text-indigo-600">{{ section.eyebrow }}</p>
        <h2 class="mt-2 text-2xl font-bold text-slate-900">{{ section.title }}</h2>
        <div class="mt-4 space-y-4">
          <p
            v-for="(paragraph, index) in section.paragraphs"
            :key="index"
            class="leading-8 text-slate-600"
          >
            {{ paragraph }}
          </p>
        </div>
      </section>
    </div>
  </div>
</template>
