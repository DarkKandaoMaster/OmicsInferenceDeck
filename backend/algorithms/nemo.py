import pandas as pd
import numpy as np
import subprocess
import os
import tempfile
from .base import BaseAlgorithm

class Algorithm(BaseAlgorithm):
    def fit_predict(self, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        # 1. 样本对齐
        df_concat = pd.concat(data.values(), axis=1, join='inner')
        sample_names = df_concat.index.tolist()
        
        n_clusters = self.params.get('n_clusters', 3)
        
        # 2. 使用临时文件夹，确保高并发时不同用户的临时文件不会冲突
        with tempfile.TemporaryDirectory() as temp_dir:
            # 将对齐后的数据按特征导出给 R 脚本读取
            for name, df in data.items():
                aligned_df = df.loc[sample_names]
                # 清理文件名中的特殊字符，防止 R 读取报错
                safe_name = "".join([c for c in name if c.isalnum()]) or "omics"
                aligned_df.to_csv(os.path.join(temp_dir, f"{safe_name}.csv"))
                
            labels_path = os.path.join(temp_dir, "labels.csv")
            embed_path = os.path.join(temp_dir, "embeddings.csv")
            
            # R 脚本所在路径（就在当前 nemo.py 所在的同级目录下）
            r_script_path = os.path.join(os.path.dirname(__file__), "nemo.R")
            # __file__ 代表当前运行的脚本（即 nemo.py）的完整路径。
            # os.path.dirname(__file__) 会提取出 nemo.py 所在的目录路径（也就是 algorithms 文件夹）。
            # os.path.join(..., "nemo.R") 会把这个目录和 "nemo.R" 拼起来。
            
            # 3. 组装命令并通过 subprocess 调用 Rscript
            cmd = [
                "Rscript", r_script_path,
                temp_dir,           # arg 1: 临时目录（存放输入CSV）
                str(n_clusters),    # arg 2: K值
                labels_path,        # arg 3: 标签输出路径
                embed_path          # arg 4: 特征矩阵输出路径
            ]
            
            try:
                # capture_output=True 可以截获 R 脚本的 print 报错信息
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"NEMO 算法运行失败, R 报错信息:\n{e.stderr}")
                
            # 4. 读取 R 脚本算出来的结果
            labels_df = pd.read_csv(labels_path, index_col=0)
            embed_df = pd.read_csv(embed_path, index_col=0)
            
            # 确保样本顺序与最初提取的 sample_names 完全一致
            labels_df = labels_df.loc[sample_names]
            embed_df = embed_df.loc[sample_names]
            
            labels = labels_df['Cluster'].values
            embeddings = embed_df.values
            
        return labels, embeddings, sample_names