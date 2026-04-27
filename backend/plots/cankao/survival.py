import os
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from matplotlib import pyplot as plt

def plot(sub_name, neg_log_p, pred_Y):
    # 设置全局字体
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'font.weight': 'bold',
        'font.size': 16,
        'axes.labelweight': 'bold',
        'axes.titleweight': 'bold',
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'legend.fontsize': 16,
        'legend.title_fontsize': 16
    })

    path_clinic = f'T:\\Files\\projs\\subtype\\datasets\\clinic\\{sub_name}.clinic'
    clinical = pd.read_csv(path_clinic, sep=',')
    clinical['days'] = pd.to_numeric(clinical['days'], errors='coerce')
    clinical['days'] = clinical['days'].fillna(clinical['days'].median())
    clinical['status'] = clinical['status'].fillna(0)
    
    merged_data = pd.DataFrame({
        "pred_Y": pred_Y,
        "days": clinical["days"],
        "status": clinical["status"]
    }) 
    
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'survival')
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    p_val_avg = 10**(-neg_log_p)
    pred_Y = pred_Y.astype(int)
    
    # 创建颜色映射
    unique_labels = np.unique(pred_Y)
    cluster_colors = {}
    colors = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00"]
    for i, label in enumerate(unique_labels):
        cluster_colors[label] = colors[i % len(colors)]
    
    plt.figure(figsize=(9, 6))
    kmf = KaplanMeierFitter()
    
    # 绘制生存曲线
    for label in set(pred_Y):
        mask = (merged_data['pred_Y'] == label)
        kmf.fit(merged_data[mask]['days'], 
               event_observed=merged_data[mask]['status'], 
               label=f'Cluster {label}')
        kmf.plot(ci_show=False, color=cluster_colors[label], linewidth=2.5)
        
        # 添加删失标记
        censored = merged_data[mask][merged_data[mask]["status"] == 0]
        if not censored.empty:
            plt.scatter(
                censored["days"],
                kmf.survival_function_at_times(censored["days"]).values,
                marker="+",
                s=80,
                color=cluster_colors[label],
                linewidths=2,
                zorder=3
            )
    
    # 添加P值（放在左下角）
    plt.text(0.05, 0.05, f'P-value: {format(p_val_avg, ".2e")}',
            horizontalalignment='left',
            verticalalignment='bottom',
            transform=plt.gca().transAxes,
            bbox=dict(facecolor='white', edgecolor='#D6D6D6', 
                     boxstyle='round,pad=0.5', alpha=0.9))
    
    # 设置坐标轴标签
    plt.xlabel('Time (days)')
    plt.ylabel('Survival Probability')
    
    # 添加图例（放在图内）
    legend = plt.legend(title='Clusters',
                       loc='upper right',
                       frameon=True,
                       framealpha=0.9,
                       edgecolor='black',
                       facecolor='white',
                       bbox_to_anchor=(1, 1))
    plt.setp(legend.get_title(), fontweight='bold')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存PNG和PDF格式
    for ext in ['png', 'pdf']:
        save_path = os.path.join(save_dir, f'{sub_name}_survival.{ext}')
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
    
    plt.close()