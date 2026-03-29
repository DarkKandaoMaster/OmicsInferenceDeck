import pandas as pd
import numpy as np
import snf
from sklearn.manifold import spectral_embedding
from .base import BaseAlgorithm

class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        # 1. 对齐样本：由于不同组学的样本必须严格一一对应，我们先取交集
        df_concat = pd.concat(data.values(), axis=1, join='inner')
        sample_names = df_concat.index.tolist()
        
        # 将对齐后的数据分别提取出来，转换为 SNF 需要的矩阵列表
        aligned_matrices = []
        for df in data.values():
            aligned_df = df.loc[sample_names]
            aligned_matrices.append(aligned_df.values)
            
        # 2. 提取参数
        n_clusters = self.params.get('n_clusters', 3)
        # SNF 的 K 值代表构建 KNN 图时的邻居数，前端如果没有传，默认给 20
        k_neighbors = self.params.get('n_neighbors', 20) 
        
        # 3. 运行 SNF 核心逻辑
        # 构建各个组学的亲和度网络
        affinity_networks = snf.make_affinity(aligned_matrices, metric='euclidean', K=k_neighbors, mu=0.5)
        # 融合网络
        fused_network = snf.snf(affinity_networks, K=k_neighbors)
        # 基于融合网络进行谱聚类
        labels = snf.clustering.spectral_clustering(fused_network, n_clusters=n_clusters)
        
        # 4. 生成用于降维和评估的特征矩阵
        # 因为 SNF 生成的是一个 N x N 的相似度矩阵，为了配合后端的 PCA/t-SNE 降维，
        # 我们使用谱嵌入（Spectral Embedding）将其转换为低维特征矩阵
        n_components = min(10, len(sample_names) - 1)
        embeddings = spectral_embedding(fused_network, n_components=n_components)
        
        return labels, embeddings, sample_names