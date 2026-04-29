from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple, List, Any
import pandas as pd
import numpy as np

class BaseAlgorithm(ABC):
    def __init__(self, **kwargs):
        """
        接收从前端传来的所有参数（K值、迭代次数等）
        """
        self.params = kwargs

    @abstractmethod
    def fit_predict(self, data: Dict[str, pd.DataFrame]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        执行聚类算法的核心逻辑。
        
        输入:
            data: 包含所有模态数据的字典，键为文件名，值为对应的 DataFrame。
            
        输出:
            返回一个包含三个元素的元组: (labels, embeddings, sample_names)
            - labels: 一维的聚类标签 numpy 数组 (形状: N,)
            - embeddings: 融合/处理后的二维特征矩阵，用于指标计算和降维散点图 (形状: N, Features)
            - sample_names: 样本名称列表，长度必须与 labels 相同，确保后端能将标签对应到具体的病人
        """
        pass

    def _script_in_algorithm_dir(self, module_file: str, suffix: str = ".R") -> Path:
        module_path = Path(module_file)
        script_path = module_path.with_suffix("") / f"{module_path.stem}{suffix}"
        return script_path.resolve()
