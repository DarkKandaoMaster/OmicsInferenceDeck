const algorithms = ['K-means', 'Spectral Clustering', 'PIntMF', 'Subtype-GAN', 'NEMO', 'SNF', 'MOSD']
const selectedAlgorithm = ref<string[]>([])

const kValue = ref(3)
const maxIter = ref(300)
const nNeighbors = ref(10)
const randomSeed = ref(42)
const currentReduction = ref('PCA')

const isTestMode = ref(false)
const testNClusters = ref('2,3,4,5')
const testMaxIter = ref('100,200,300')
const testNNeighbors = ref('5,10,15')

const psResult = ref<any>(null)
const isPsLoading = ref(false)
const psParam1 = ref('n_clusters')
const psParam2 = ref('max_iter')

export function useAlgorithmState() {
  return {
    algorithms, selectedAlgorithm,
    kValue, maxIter, nNeighbors, randomSeed, currentReduction,
    isTestMode, testNClusters, testMaxIter, testNNeighbors,
    psResult, isPsLoading, psParam1, psParam2,
  }
}
