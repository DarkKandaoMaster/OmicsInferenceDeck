// 运行分析的累积式日志：运行前为空（面板隐藏），点“运行分析”后逐行追加。
// 每个步骤一行随状态演变（进行中 → 成功/失败），同一次运行内已展示的行不清除。

import { useRunControl } from '~/composables/core/useRunControl'

export type LogLevel = 'progress' | 'success' | 'error' | 'warning' | 'terminated'

export interface LogEntry {
  id: number
  level: LogLevel
  text: string
}

const logEntries = ref<LogEntry[]>([])
let nextId = 0

/** 从“正在 xxx…”这样的进行中文案里提取核心短语，用于拼接成功/失败文案。 */
function basePhrase(label: string) {
  return label.replace(/^正在/, '').replace(/[。.…\s]+$/, '')
}

/** 提取后端/异常里的可读报错信息。 */
function extractError(error: any) {
  return error?.response?.data?.detail || error?.message || String(error)
}

export function useAnalysisLog() {
  /** 清空日志（每次重新点击运行分析时调用）。 */
  function resetLog() {
    logEntries.value = []
  }

  /** 追加一条独立行（用于警告/一次性提示），返回该 entry（响应式代理）。 */
  function appendLog(text: string, level: LogLevel = 'progress'): LogEntry {
    logEntries.value.push({ id: nextId++, level, text })
    return logEntries.value[logEntries.value.length - 1]!
  }

  /** 追加一条进行中行，返回 entry 供后续就地改写（实现“一行演变”）。 */
  function startStep(text: string): LogEntry {
    return appendLog(text, 'progress')
  }

  /** 就地把某行改为完成（默认成功）。不传 text 则保留原文案。 */
  function finishStep(entry: LogEntry, text?: string, level: LogLevel = 'success') {
    if (text !== undefined) entry.text = text
    entry.level = level
  }

  /** 就地把某行改为失败。 */
  function failStep(entry: LogEntry, text: string) {
    entry.text = text
    entry.level = 'error'
  }

  /** 停止运行时调用：把所有“进行中”的行就地标记为“已停止”，其余行保留。 */
  function markRunningAsTerminated() {
    logEntries.value.forEach((entry) => {
      if (entry.level === 'progress') {
        entry.level = 'terminated'
        entry.text = `⏹ 已停止：${basePhrase(entry.text)}`
      }
    })
  }

  /**
   * async 包装器：startStep → await fn → 成功改本行为“✅ …完成”，
   * 失败改本行为“❌ …失败: 原因”后继续抛出。用于会抛异常的步骤。
   */
  async function logStep<T>(label: string, fn: () => Promise<T>): Promise<T> {
    const { runToken } = useRunControl()
    const token = runToken.value
    const entry = startStep(label)
    const base = basePhrase(label)
    try {
      const result = await fn()
      // 令牌已过期（运行被停止）：跳过成功标记，保留 markRunningAsTerminated 写的“已停止”，直接返回结果（调用方会自行丢弃）。
      if (token !== runToken.value) return result
      finishStep(entry, `✅ ${base}完成`)
      return result
    } catch (error: any) {
      // 停止导致的异常：不写失败标记、吞掉异常，避免上层 setError/alert 误报。
      if (token !== runToken.value) return undefined as T
      failStep(entry, `❌ ${base}失败: ${extractError(error)}`)
      throw error
    }
  }

  return {
    logEntries,
    resetLog,
    appendLog,
    startStep,
    finishStep,
    failStep,
    markRunningAsTerminated,
    logStep,
    extractError,
  }
}
