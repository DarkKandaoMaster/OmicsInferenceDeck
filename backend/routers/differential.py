# =============================================================================
# 接口：差异表达分析
# =============================================================================
import os
import joblib
import pandas as pd
import numpy as np
from scipy import stats
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 创建路由器实例
router=APIRouter()

class DifferentialAnalysisRequest(BaseModel): #定义数据校验模型
    # omics_filename: str #用户上传的使用UUID改名后的组学数据文件名
    session_id: str # 【修改】
    omics_type: str # 👈 【新增】让前端指定要使用哪个组学进行差异分析
    sample: list[str] #样本名称列表
    labels: list[int] #和样本名称列表一一对应的聚类标签列表

@router.post("/api/differential_analysis")
async def run_differential_analysis(request:DifferentialAnalysisRequest):
    # print(f"\n[后端日志] 收到差异分析请求，处理文件: {request.omics_filename}")

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的组学数据文件，得到df
    # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_info
    # 3.把df和cluster_info合并起来，得到merged_df
    # 4.计算差异倍数（Log2 Fold Change）。这是火山图的x轴数据
    # 5.计算T检验P值，然后把它处理成-Log10(P-value)。这是火山图的y轴数据
    # 6.保存用来绘制火山图的数据。然后就已经可以绘制火山图了
    # 7.筛选一下数据，每个簇挑10个基因名称（特征名称）。这是差异基因热图的y轴数据
    # 8.在merged_df中把刚才挑出来的基因名称、以及"Cluster"列筛选出来，然后计算Z-score。这个Z-score决定了差异基因热图对应位置的颜色
    # 9.整理一下我们刚才得到的数据，然后提取样本名称、样本对应的簇。这个样本名称就是差异基因热图的x轴数据。也就是说如果你输入了1031个样本，差异基因热图的x轴就会有1031列
    # 10.然后我们再整理一下刚才得到的数据，得到差异基因热图中所有点对应的坐标和Z-score。然后就已经可以绘制差异基因热图了
    # 11.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的组学数据文件
        # file_path=os.path.join("upload",request.omics_filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        file_path = os.path.join("upload", request.session_id, "omics_data.joblib")
        if not os.path.exists(file_path):
            raise FileNotFoundError("找不到组学数据文件")
        # df=pd.read_csv(file_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据
        data_dict = joblib.load(file_path)
        # 👈 【修改】不再拼接所有文件，而是提取指定的单一组学数据
        # 👈 【修改】支持提取指定的单一组学数据，或者拼接所有组学数据
        if request.omics_type == "All (Concatenated)":
            # 将 data_dict 中所有的 DataFrame 按列拼接（取样本的交集）
            df = pd.concat(list(data_dict.values()), axis=1, join='inner')
        else:
            if request.omics_type not in data_dict:
                raise ValueError(f"未找到指定的组学数据类型: {request.omics_type}")
            df = data_dict[request.omics_type]
            # 👇 【新增】根据前端传来的 omics_type，去掉对应的组学后缀名
            # 注意：使用 endswith 和切片，防止基因名中间刚好包含后缀字符被误删
            # 根据前端传来的omics_type，把组学后缀名去掉。但如果omics_type为All，那么不删
            suffix = f"_{request.omics_type}"
            df.columns=[     col[:-len(suffix)] if str(col).endswith(suffix) else col     for col in df.columns]
            # [ ... for col in df.columns ]
            # 这是 Python 的列表推导式。它的意思是：把 df.columns（原数据表的所有列名）里的每一个列名拿出来，记作 col，然后通过前面的规则处理它，最后把处理完的所有名字打包成一个新的列表。

        # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_info
        #创建一个DataFrame对象，同时传入一个字典。于是字典的key就会变成列名，value就会变成列的数据
        cluster_info=pd.DataFrame({
            "SampleID": request.sample, #样本名称列表
            "Cluster": request.labels #聚类标签列表
        })
        cluster_info.set_index("SampleID",inplace=True) #.set_index()可以将cluster_info的"SampleID"列设置为索引列；inplace=True表示直接在原对象上修改

        # 3.把df和cluster_info合并起来，得到merged_df
        merged_df=df.join(cluster_info,how="inner") #how='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if merged_df.empty:
            raise ValueError("样本名称无法匹配，请检查数据一致性。")

        genes=merged_df.columns[:-1] #获取所有特征名称，也就是获取除了最后一列之外的所有列名。因为最后一列是我们刚刚加进去的"Cluster"
        unique_clusters=sorted(merged_df["Cluster"].unique()) #获取簇编号。先获取merged_df中"Cluster"列的值，然后对它去除重复值，再对它排个序。结果类似于[0,1,2]
        volcano_data={} #存放每个簇的用来绘制火山图的数据
        top_genes_set=set() #存放后面筛选出来的基因名称（特征名称）。这是差异基因热图的y轴数据

        #遍历每一个簇，进行“一对多”比较，找出每个簇特有的特征【【【【【以后或许可以在这里加一个“一对一”比较
        for target_cluster in unique_clusters:
            group_a_df=merged_df[merged_df["Cluster"]==target_cluster][genes] #首先筛选出属于当前簇的样本，然后只保留所有特征列
            group_b_df=merged_df[merged_df["Cluster"]!=target_cluster][genes] #首先筛选出不属于当前簇的样本，然后只保留所有特征列
            if len(group_a_df)<2 or len(group_b_df)<2: #如果任意一组样本数量少于2，就没法做T检验
                print(f"[警告] Cluster {target_cluster} 样本数不足，跳过该簇")
                volcano_data[int(target_cluster)]=[] #给这个簇一个空列表，防止前端报错
                continue
            # 4.计算差异倍数（Log2 Fold Change）。这是火山图的x轴数据
            mean_a=group_a_df.mean(axis=0) #对a组每一列求平均值
            mean_b=group_b_df.mean(axis=0) #对b组每一列求平均值
            log_fc=mean_a-mean_b #pandas会自动按索引对齐相减 #这里我们先假设数据已经log2处理过，于是log2(A)-log2(B)=log2(A/B)，这样就能计算出差异倍数。下载下来的数据集一般都是已经Log2处理过的 #如果是原始count数据，这里应该用np.log2(mean_a/mean_b)【【【【【看看学长的代码有没有处理Log2

            # 5.计算T检验P值，然后把它处理成-Log10(P-value)。这是火山图的y轴数据
            t_stat,t_pvalue=stats.ttest_ind(group_a_df,group_b_df,axis=0,equal_var=False,nan_policy='omit') #比较a组和b组的每一列数据，得到T检验P值。equal_var=False表示不假设两组方差相等；nan_policy='omit'表示如果数据中有缺失值，那么自动忽略，防止报错
            #我们先把刚才计算出来的东西放进pd.DataFrame里，方便后续处理
            cluster_res_df=pd.DataFrame({ #还是和之前一样，字典的key就会变成列名，value就会变成列的数据
                "gene": genes,
                "logFC": log_fc.values, #.values可以把pandas.Series转换成numpy数组
                "t_pvalue": t_pvalue #把原始T检验P值也传给前端，于是前端会把t_pvalue<0.05的点涂成红色和蓝色，其他点涂成灰色
            })
            cluster_res_df["t_pvalue"]=cluster_res_df["t_pvalue"].fillna(1.0) #计算出的T检验P值可能含有NaN，所以我们来处理一下它，把NaN填为1.0（最大值，代表完全不显著）
            cluster_res_df["negLog10P"]=-np.log10(cluster_res_df["t_pvalue"]+1e-300) #然后我们把它-log10一下，就能得到-Log10(P-value)。加上1e-300是为了防止P值为0时算出负无穷，于是无法绘图

            # 6.保存用来绘制火山图的数据。此时就已经可以绘制火山图了
            volcano_data[int(target_cluster)]=cluster_res_df.to_dict(orient="records") #.to_dict(orient="records")可以把pd.DataFrame转换为字典列表，也就是[{"gene":"A","logFC":...},{"gene":"B"...}]

            # 7.筛选一下数据，每个簇挑10个基因名称（特征名称）。这是差异基因热图的y轴数据
            top_genes_set.update(   cluster_res_df[(cluster_res_df["t_pvalue"]<0.05)&(cluster_res_df["logFC"]>0)]   .sort_values(by="logFC",ascending=False).head(10)["gene"].tolist()   ) #首先筛选出cluster_res_df中t_pvalue<0.05且logFC>0的数据，然后把它们按"LogFC"列降序排序，取前10行，然后只保留"gene"列，然后转换成列表，最后.update()会自动把列表中的元素逐个加入集合，并自动去重

        # 8.在merged_df中把刚才挑出来的基因名称、以及"Cluster"列筛选出来，然后计算Z-score。这个Z-score决定了差异基因热图对应位置的颜色
        top_genes_list=list(top_genes_set) #首先我们把top_genes_set集合转换成列表
        if not top_genes_list: #如果列表为空，那么直接返回空热图数据
            print("[警告] 未检测到显著差异基因，返回空热图数据")
            return{
                "status": "success",
                "volcano_data": volcano_data,
                "heatmap_data": {"samples":[],"sample_labels":[],"genes":[],"values":[]}
            }
        heatmap_df=merged_df[top_genes_list+["Cluster"]].copy() #首先把两个列表top_genes_list、["Cluster"]拼接一下，然后在merged_df中把这些列筛选出来，最后.copy()一下
        #为什么这里要用.copy()？因为Pandas有一个很容易让人困惑的机制：视图（View）vs副本（Copy）。不知道的话自己去搜，反正你只要知道：
        # 修改数据时我们最好不要在原始数据上修改，而是创建一个副本，在副本上修改。基于这个原则：
        #  不修改具体单元格的值（比如筛选、排序、改列名、计算平均值）：可以不用.copy()。因为它们默认情况下会直接返回一个新DataFrame对象，不会修改原始数据
        #  要修改具体单元格的值：必须用.copy()。不然会修改原始数据，Pandas也会弹出著名的SettingWithCopyWarning警告
        heatmap_df[top_genes_list]=( heatmap_df[top_genes_list] - heatmap_df[top_genes_list].mean() ) / heatmap_df[top_genes_list].std() #首先在heatmap_df中把top_genes_list这些列筛选出来（因为不能让"Cluster"列也参与运算），然后计算Z-score：(值-平均值)/标准差，最后把它赋值回去。这是能减得起来的，因为Pandas有广播机制 #此时这些值都会被压缩到大致-2 ~ 2的区间内

        # 9.整理一下我们刚才得到的数据，然后提取样本名称、样本对应的簇。这个样本名称就是差异基因热图的x轴数据
        heatmap_df=heatmap_df.sort_values(by="Cluster") #把heatmap_df按"Cluster"列升序排序，这样就能把同一个簇的数据排在一起
        sorted_samples=heatmap_df.index.tolist() #提取样本名称（也就是行索引）
        sorted_labels=heatmap_df["Cluster"].tolist() #提取样本对应的簇

        # 10.然后我们再整理一下刚才得到的数据，得到差异基因热图中所有点对应的坐标和Z-score。然后就已经可以绘制差异基因热图了
        heatmap_values_df=heatmap_df.drop(columns=["Cluster"]) #删除"Cluster"列
        matrix_values=heatmap_values_df.fillna(0).values #把heatmap_values_df中的NaN填为0，然后把heatmap_values_df转换成numpy数组
        flat_values=matrix_values.ravel() #按行展平matrix_values，也就是把1,2,3\n4,5,6展平为1,2,3,4,5,6
        #现在我们就已经按行展平matrix_values了。但如果直接把flat_values返回给前端，前端是不知道flat_values中的某元素在matrix_values中是第几行第几列的。所以接下来我们把flat_values中的某元素在matrix_values中是第几行第几列也返回给前端
        #假设matrix_values有1031个样本、30个基因
        #请想象一个1031行、30列的矩阵，把它按行展平后，第一行第一列应为(0,0)，第一行最后一列应为(0,29)，第二行第一列应为(1,0)，第二行最后一列应为(1,29)，以此类推
        #也就是说我们要生成并返回的是[[0,0,某元素],[0,1,某元素],...,[0,29,某元素],[1,0,某元素],[1,1,某元素],...[1030,0,某元素],[1030,1,某元素],...,[1030,29,某元素]]。事实上，如果我们真的把这东西返回给前端，前端直接把它传给echarts就能绘制出热图了，而不需要对它做额外的处理
        #也就是说首先我们要生成[0,0,0,...,1,1,1,...,1030,1030,1030,...]和[0,1,2,...,29,0,1,2,...,29,...]
        n_rows,n_cols=matrix_values.shape #获取matrix_values的行数和列数。于是此时n_rows为1031，n_cols为30
        xs=np.repeat(np.arange(n_rows),n_cols) #np.arange(1031)会生成[0,1,2,...,1030]这个numpy数组，np.repeat会把每个元素重复30次，最终变成[0,0,0,...,1,1,1,...,1030,1030,1030,...]，长度是1031*30==295320 #给它命名为xs是因为在差异基因热图中该数组对应的是x轴
        ys=np.tile(np.arange(n_cols),n_rows) #np.arange(30)会生成[0,1,2,...,29]这个numpy数组，np.tile会把整个数组平铺1031次，最终变成[0,1,2,...,29,0,1,2,...,29,...]，长度是30*1031==295320
        heatmap_matrix=np.column_stack([xs,ys,flat_values]).tolist() #首先把xs、ys、flat_values放进列表里，同时传入np.column_stack，于是np.column_stack可以将这三个一维数组竖着拼成一个295320*3的矩阵，最后把它转换成列表，就能成功得到我们想要的返回给前端的东西了

        return{
            "status": "success",
            "volcano_data": volcano_data, #每个簇的用来绘制火山图的数据
            "heatmap_data": {
                "samples": sorted_samples, #提取出来的样本名称，也就是差异基因热图的x轴数据
                "sample_labels": sorted_labels, #提取出来的样本对应的簇，用于画差异基因热图的分组颜色条
                "genes": heatmap_values_df.columns.tolist(), #挑出来的基因名称，也就是差异基因热图的y轴数据
                "values": heatmap_matrix #差异基因热图中所有点对应的坐标和Z-score
            }
        }
    except Exception as e:
        print(f"[差异分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=str(e))
