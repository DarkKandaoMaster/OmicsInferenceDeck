const isLoading = ref(false)
const errorMessage = ref('')

export function useUIState() {
  function clearError() {
    errorMessage.value = ''
  }

  function setError(msg: string) {
    errorMessage.value = msg
  }

  return { isLoading, errorMessage, clearError, setError }
}
