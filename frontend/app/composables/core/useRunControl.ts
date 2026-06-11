// 运行令牌（run token）：用一个递增计数器标识“当前这一轮运行”。
// 每次开始运行 ++token；点停止时再 ++token 让正在进行的运行作废。
// 所有“await 之后才写状态 / 发下一个请求”的地方先用 isStale(token) 判断令牌是否过期，
// 过期则直接 return 丢弃结果。无其它 composable 依赖，避免循环引用。

const runToken = ref(0)

export function useRunControl() {
  /** 开始新一轮运行，返回本次令牌。 */
  function startRun() { return ++runToken.value }
  /** 停止：使当前运行作废（令牌前移，旧令牌随即 stale）。 */
  function invalidate() { runToken.value++ }
  /** 令牌是否已过期（不再是当前运行）。 */
  function isStale(token: number) { return token !== runToken.value }

  return { runToken, startRun, invalidate, isStale }
}
