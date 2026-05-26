<script setup lang="ts">
useHead({ title: 'OmicsInferenceDeck - 多组学癌症亚型分析平台' })

const capabilities = [
  {
    title: '数据接入',
    description: '支持多组学矩阵、临床信息与生存数据协同进入分析流程，减少前期整理成本。',
  },
  {
    title: '亚型推断',
    description: '围绕癌症分子分型任务组织算法参数、运行状态与结果解释，适合快速迭代实验。',
  },
  {
    title: '结果评估',
    description: '集中展示聚类、差异、富集、生存与评价指标，帮助判断亚型的统计和生物学意义。',
  },
]

const workflow = ['上传数据', '配置算法', '运行分析', '查看报告']

const metrics = [
  { value: '14', label: '可计算指标' },
  { value: '6', label: '可生成图表' },
  { value: '9', label: '已内置算法' },
]
</script>

<template>
  <div class="relative left-1/2 w-screen -translate-x-1/2 overflow-hidden bg-white">
    <section class="relative min-h-[calc(100vh-4rem)] bg-indigo-600 text-white">
      <div class="absolute inset-0 opacity-15">
        <svg class="h-full w-full" viewBox="0 0 1200 720" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 160C210 70 340 260 520 160C720 50 850 220 1200 120" fill="none" stroke="white" stroke-width="2" />
          <path d="M0 420C230 330 360 520 560 390C790 240 910 470 1200 330" fill="none" stroke="white" stroke-width="2" />
          <path d="M0 610C260 510 420 700 620 560C830 410 980 630 1200 520" fill="none" stroke="white" stroke-width="2" />
        </svg>
      </div>

      <div class="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-[1400px] items-center gap-12 px-6 py-16 lg:grid-cols-[1.02fr_0.98fr] lg:px-10">
        <div>
          <p class="mb-5 inline-flex rounded-full border border-white/25 bg-white/10 px-4 py-2 text-sm font-semibold text-indigo-50">
            OmicsInferenceDeck
          </p>

          <h1 class="max-w-4xl text-4xl font-extrabold leading-tight md:text-6xl">
            多组学癌症亚型识别算法评估平台
          </h1>

          <p class="mt-6 max-w-2xl text-lg leading-8 text-indigo-50 md:text-xl">
            你可以用你写的算法生成一个结果文件，然后根据平台的指示操作，平台便会为你计算指标、绘制图表；<br>
            你也可以上传你自己的输入数据集，选择平台内置经典算法，作为基线对照组计算指标、绘制图表。
          </p>

          <div class="mt-10 flex flex-col gap-4 sm:flex-row">
            <NuxtLink
              to="/analysis"
              class="inline-flex items-center justify-center rounded-full bg-white px-8 py-4 text-base font-bold text-indigo-700 no-underline shadow-lg shadow-indigo-950/20 transition hover:-translate-y-0.5 hover:bg-indigo-50"
            >
              开始分析
            </NuxtLink>
            <NuxtLink
              to="/help"
              class="inline-flex items-center justify-center rounded-full border border-white/35 px-8 py-4 text-base font-bold text-white no-underline transition hover:bg-white/10"
            >
              查看帮助
            </NuxtLink>
          </div>

          <div class="mt-12 grid max-w-xl grid-cols-3 gap-4">
            <div v-for="metric in metrics" :key="metric.label" class="border-l border-white/25 pl-4">
              <p class="text-3xl font-extrabold">{{ metric.value }}</p>
              <p class="mt-1 text-sm text-indigo-100">{{ metric.label }}</p>
            </div>
          </div>
        </div>

        <div class="relative">
          <div class="rounded-lg border border-white/20 bg-white/12 p-4 shadow-2xl shadow-indigo-950/30 backdrop-blur">
            <div class="rounded-lg bg-slate-950 p-4">
              <div class="flex items-center gap-2 border-b border-white/10 pb-4">
                <span class="h-3 w-3 rounded-full bg-rose-400" />
                <span class="h-3 w-3 rounded-full bg-amber-300" />
                <span class="h-3 w-3 rounded-full bg-emerald-400" />
                <span class="ml-3 text-sm font-medium text-slate-300">Subtype analysis workspace</span>
              </div>

              <div class="grid gap-4 pt-5 md:grid-cols-[0.9fr_1.1fr]">
                <div class="space-y-3">
                  <div class="rounded-lg bg-white/10 p-4">
                    <p class="text-xs font-semibold uppercase tracking-wider text-cyan-200">Input</p>
                    <div class="mt-4 space-y-3">
                      <div class="h-2 rounded-full bg-cyan-300/80" />
                      <div class="h-2 w-4/5 rounded-full bg-indigo-300/80" />
                      <div class="h-2 w-2/3 rounded-full bg-fuchsia-300/80" />
                    </div>
                  </div>
                  <div class="rounded-lg bg-white/10 p-4">
                    <p class="text-xs font-semibold uppercase tracking-wider text-emerald-200">Pipeline</p>
                    <div class="mt-4 grid grid-cols-2 gap-3">
                      <span v-for="item in workflow" :key="item" class="rounded-lg bg-white/10 px-3 py-2 text-center text-xs text-slate-100">
                        {{ item }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="rounded-lg bg-white p-4 text-slate-900">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-sm font-bold text-slate-800">分型结果概览</p>
                      <p class="mt-1 text-xs text-slate-500">Cluster distribution</p>
                    </div>
                    <span class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">Ready</span>
                  </div>

                  <div class="mt-6 grid grid-cols-7 items-end gap-2">
                    <span class="h-20 rounded-t bg-indigo-500" />
                    <span class="h-32 rounded-t bg-cyan-500" />
                    <span class="h-24 rounded-t bg-fuchsia-500" />
                    <span class="h-36 rounded-t bg-indigo-400" />
                    <span class="h-28 rounded-t bg-cyan-400" />
                    <span class="h-40 rounded-t bg-fuchsia-400" />
                    <span class="h-24 rounded-t bg-indigo-500" />
                  </div>

                  <div class="mt-6 rounded-lg bg-slate-100 p-4">
                    <div class="mb-3 flex items-center justify-between text-xs font-semibold text-slate-500">
                      <span>Survival</span>
                      <span>p = 0.018</span>
                    </div>
                    <svg viewBox="0 0 260 90" class="h-24 w-full">
                      <path d="M8 18H46V30H84V43H124V57H172V68H246" fill="none" stroke="#4f46e5" stroke-width="4" stroke-linecap="round" />
                      <path d="M8 32H52V44H96V52H140V63H190V76H246" fill="none" stroke="#06b6d4" stroke-width="4" stroke-linecap="round" />
                      <path d="M8 46H40V56H82V64H130V72H178V80H246" fill="none" stroke="#d946ef" stroke-width="4" stroke-linecap="round" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <svg class="block h-12 w-full fill-white" viewBox="0 0 1440 57" preserveAspectRatio="none" aria-hidden="true">
        <path d="M1440 57H0V0C720 57 1440 0 1440 0V57Z" />
      </svg>
    </section>

    <section class="bg-white px-6 py-16 lg:px-10 lg:py-24">
      <div class="mx-auto max-w-[1400px]">
        <div class="max-w-3xl">
          <p class="text-sm font-bold uppercase tracking-wider text-indigo-600">Platform Capability</p>
          <h2 class="mt-4 text-3xl font-extrabold text-slate-900 md:text-4xl">从数据到解释的完整分析闭环</h2>
          <p class="mt-5 text-lg leading-8 text-slate-600">
            围绕多组学癌症分型任务组织关键入口，降低从原始数据到亚型解释之间的操作断点。
          </p>
        </div>

        <div class="mt-12 grid gap-6 md:grid-cols-3">
          <article
            v-for="capability in capabilities"
            :key="capability.title"
            class="rounded-lg border border-slate-200 bg-slate-50 p-7 shadow-sm"
          >
            <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-600 text-lg font-extrabold text-white">
              {{ capability.title.slice(0, 1) }}
            </div>
            <h3 class="text-xl font-bold text-slate-900">{{ capability.title }}</h3>
            <p class="mt-4 leading-7 text-slate-600">{{ capability.description }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="bg-slate-950 px-6 py-16 text-white lg:px-10 lg:py-24">
      <div class="mx-auto grid max-w-[1400px] gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p class="text-sm font-bold uppercase tracking-wider text-cyan-300">Workflow</p>
          <h2 class="mt-4 text-3xl font-extrabold md:text-4xl">贴合桌面端研究场景的清晰流程</h2>
          <p class="mt-5 text-lg leading-8 text-slate-300">
            保留必要步骤和结果入口，让 Windows 10/11 环境下的本地分析过程保持稳定、直接、可复查。
          </p>
        </div>

        <div class="grid gap-4 sm:grid-cols-4">
          <div
            v-for="(item, index) in workflow"
            :key="item"
            class="rounded-lg border border-white/10 bg-white/10 p-5"
          >
            <p class="text-sm font-bold text-cyan-200">0{{ index + 1 }}</p>
            <p class="mt-5 text-lg font-bold">{{ item }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
