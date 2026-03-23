import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from .base import BaseAlgorithm

class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        # K-means 属于早期融合，在算法内部直接将多个组学进行内连接合并
        df_concat = pd.concat(data.values(), axis=1, join='inner')
        
        # 提取参数，设置默认兜底值
        n_clusters = self.params.get('n_clusters', 3)
        random_state = self.params.get('random_state', 42)
        max_iter = self.params.get('max_iter', 300)
        
        # 初始化模型并训练
        model = KMeans(
            n_clusters=n_clusters, 
            random_state=random_state, 
            max_iter=max_iter
        )
        labels = model.fit_predict(df_concat)
        
        # 返回 聚类标签, 融合后的特征矩阵, 样本名称列表
        return labels, df_concat.values, df_concat.index.tolist()