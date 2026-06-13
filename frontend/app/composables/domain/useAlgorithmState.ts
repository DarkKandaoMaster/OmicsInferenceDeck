const algorithms = ['K-means', 'Hclust', 'Spectral Clustering', 'PIntMF', /* 'Subtype-GAN', 后端未实现，暂时注释掉 */ 'NEMO', 'SNF', 'MOSD', 'Parea']
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

// 各内置算法的可自定义参数（普通模式），默认值与后端 wrapper 保持一致
const kmeansNInit = ref(10)
const kmeansTol = ref(0.0001)
const kmeansInit = ref('k-means++')
const spectralAssignLabels = ref('kmeans')
const spectralNInit = ref(10)
const hclustMethod = ref('ward.D2')
const hclustDistance = ref('euclidean')
const snfAlpha = ref(0.5)
const snfIterations = ref(20)
const pintmfLatentDim = ref(kValue.value)   // 默认随 K
const pintmfMaxIter = ref(5)
const pintmfMaxFeatures = ref(500)
const nemoNNeighbors = ref(0)               // 0 = 自动
const pareaStructure = ref('2')

// latent_dim 默认跟随 K 变化（用户手动改动后仍会被下一次 K 变更覆盖，符合“默认=K”语义）
watch(kValue, (v) => { pintmfLatentDim.value = v })
const inputReduction = ref('t-SNE')
const predReduction = ref('t-SNE')
const isInputReductionLoading = ref(false)
const isPredReductionLoading = ref(false)

const isTestMode = ref(false)
const testNClusters = ref('2,3,4,5')
const testMaxIter = ref('100,200,300')
const testNNeighbors = ref('5,10,15')
const testLatentDim = ref('2,3,4,5')   // PIntMF 第二维扫描范围

const psResult = ref<any>(null)
const isPsLoading = ref(false)
const psParam1 = ref('n_clusters')
const psParam2 = ref('max_iter')

// 展示快照：运行开始时冻结癌症亚型，结果区的富集图下载/簇刷新读这份快照，
// 运行后在上传区改亚型不会让下载/刷新用上与屏幕上不一致的 dataset（selectedCancerSubtype 仍 live）。
const displayedCancerSubtype = ref<CancerSubtype>(selectedCancerSubtype.value)

export function useAlgorithmState() {
  function applyCancerSubtypeClusterCount(subtype: CancerSubtype | '') {
    if(subtype){
      selectedCancerSubtype.value = subtype
      kValue.value = cancerSubtypeClusterMap[subtype]
    }
  }

  function captureAlgorithmDisplaySnapshot() {
    displayedCancerSubtype.value = selectedCancerSubtype.value
  }

  return {
    algorithms, selectedAlgorithm,
    cancerSubtypeClusterMap, cancerSubtypeOptions, selectedCancerSubtype, applyCancerSubtypeClusterCount,
    displayedCancerSubtype, captureAlgorithmDisplaySnapshot,
    kValue, maxIter, nNeighbors, randomSeed,
    kmeansNInit, kmeansTol, kmeansInit,
    spectralAssignLabels, spectralNInit,
    hclustMethod, hclustDistance,
    snfAlpha, snfIterations,
    pintmfLatentDim, pintmfMaxIter, pintmfMaxFeatures,
    nemoNNeighbors, pareaStructure,
    inputReduction, predReduction, isInputReductionLoading, isPredReductionLoading,
    isTestMode, testNClusters, testMaxIter, testNNeighbors, testLatentDim,
    psResult, isPsLoading, psParam1, psParam2,
  }
}
