import { v4 as uuidv4 } from 'uuid'
import { cleanupSession } from '~/utils/api'

const sessionId = ref(uuidv4())

export function useSession() {
  const doCleanup = () => {
    if (!sessionId.value) return
    cleanupSession(sessionId.value)
  }

  const registerUnloadHook = () => {
    onMounted(() => window.addEventListener('beforeunload', doCleanup))
    onUnmounted(() => {
      window.removeEventListener('beforeunload', doCleanup)
      doCleanup()
    })
  }

  return { sessionId, doCleanup, registerUnloadHook }
}
