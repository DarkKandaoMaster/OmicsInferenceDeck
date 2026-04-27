from sklearn.metrics import silhouette_score
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
def visualize_tsne(data, labels, title, save_path_base):
    """
    使用t-SNE进行可视化并保存结果
    """
    # 创建图形和轴
    plt.figure(figsize=(12, 10))
    
    # 设置全局字体参数
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['font.size'] = 16
    
    # 使用perplexity参数来优化聚类效果
    tsne = TSNE(
        n_components=2,
        perplexity=50, 
        learning_rate='auto',
        n_iter=1000,
        early_exaggeration=50,
        init='random',
        random_state=3407,
        method='exact'
    )
    data_tsne = tsne.fit_transform(data)
    
    # 使用更鲜明的颜色方案
    palette = sns.color_palette("husl", len(np.unique(labels)))
    
    # 创建散点图
    for label in np.unique(labels):
        idx = labels == label
        plt.scatter(data_tsne[idx, 0], data_tsne[idx, 1], 
                   label=f'Cluster {label}', 
                   color=palette[label], 
                   s=50,
                   alpha=0.7)
    
    # 设置坐标轴标签
    plt.xlabel('t-SNE dimension 1', fontproperties={'family': 'Times New Roman', 'weight': 'bold', 'size': 16})
    plt.ylabel('t-SNE dimension 2', fontproperties={'family': 'Times New Roman', 'weight': 'bold', 'size': 16})
    
    # 设置刻度标签
    plt.xticks(fontname='Times New Roman', fontsize=16, fontweight='bold')
    plt.yticks(fontname='Times New Roman', fontsize=16, fontweight='bold')
    
    # 添加图例（放在图内）
    legend = plt.legend(title='Clusters',
                       loc='upper right',
                       frameon=True,
                       framealpha=0.9,
                       edgecolor='black',
                       facecolor='white',
                       bbox_to_anchor=(1, 1))
    
    # 设置图例标题和标签的字体
    plt.setp(legend.get_title(), fontproperties={'family': 'Times New Roman', 'weight': 'bold', 'size': 16})
    for text in legend.get_texts():
        text.set_fontproperties({'family': 'Times New Roman', 'weight': 'bold', 'size': 16})
    
    # 设置标题
    plt.title(title, fontdict={'family': 'Times New Roman', 'weight': 'bold', 'size': 16})
    
    # 调整布局
    plt.tight_layout()
    
    # 确保保存目录存在
    os.makedirs(os.path.dirname(save_path_base), exist_ok=True)
    
    # 保存PNG和PDF格式
    for ext in ['png', 'pdf']:
        save_path = f"{save_path_base}.{ext}"
        plt.savefig(save_path, bbox_inches='tight', dpi=600, format=ext)
    
    plt.close()