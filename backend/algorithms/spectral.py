import pandas as pd
import numpy as np
from sklearn.cluster import SpectralClustering
from .base import BaseAlgorithm

class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        # 同样使用早期融合
        df_concat = pd.concat(data.values(), axis=1, join='inner')
        
        n_clusters = self.params.get('n_clusters', 3)
        n_neighbors = self.params.get('n_neighbors', 10)
        random_state = self.params.get('random_state', 42)
        
        model = SpectralClustering(
            n_clusters=n_clusters,
            n_neighbors=n_neighbors,
            random_state=random_state,
            affinity='nearest_neighbors'
        )
        labels = model.fit_predict(df_concat)
        
        return labels, df_concat.values, df_concat.index.tolist()