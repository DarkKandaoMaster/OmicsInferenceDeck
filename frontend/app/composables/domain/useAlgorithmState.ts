const algorithms = ['K-means', 'Hclust', 'Spectral Clustering', 'PIntMF', 'Subtype-GAN', 'NEMO', 'SNF', 'MOSD', 'Parea']
const selectedAlgorithm = ref<string[]>([])

const cancerSubtypeClusterMap = {
  BRCA: 5,
  BLCA: 5,
  KIRC: 4,
  GBM: 3,
  LUAD: 3,
  PAAD: 2,
  SKCM: 4,
  STAD: 3,
  UCEC: 4,
  UVM: 4,
} as const
type CancerSubtype = keyof typeof cancerSubtypeClusterMap
const cancerSubtypeOptions = Object.entries(cancerSubtypeClusterMap).map(([type, clusters]) => ({
  type: type as CancerSubtype,
  clusters,
}))
const selectedCancerSubtype = ref<CancerSubtype>('BRCA')
const kValue = ref(5)
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
  function applyCancerSubtypeClusterCount(subtype: CancerSubtype | '') {
    if(subtype){
      selectedCancerSubtype.value = subtype
      kValue.value = cancerSubtypeClusterMap[subtype]
    }
  }

  return {
    algorithms, selectedAlgorithm,
    cancerSubtypeClusterMap, cancerSubtypeOptions, selectedCancerSubtype, applyCancerSubtypeClusterCount,
    kValue, maxIter, nNeighbors, randomSeed, currentReduction,
    isTestMode, testNClusters, testMaxIter, testNNeighbors,
    psResult, isPsLoading, psParam1, psParam2,
  }
}
