/** 格式化 P-value 显示 */
export function formatPValue(p: number): string {
  if (p < 0.0001) return p.toExponential(4)
  return p.toFixed(4)
}

/** 格式化数值，保留指定小数位 */
export function toFixed(value: number, digits = 3): string {
  return value.toFixed(digits)
}

/** 截断过长文本 */
export function truncateText(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text
  return text.substring(0, maxLen) + '...'
}
