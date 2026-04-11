# =============================================================================
# 接口：生存分析
# =============================================================================
import os
import joblib
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 创建路由器实例
router=APIRouter()

class SurvivalRequest(BaseModel): #定义数据校验模型
    # clinical_filename: str #用户上传的使用UUID改名后的临床数据文件名
    session_id: str # 【修改】
    sample: list[str] #样本名称列表
    labels: list[int] #和样本名称列表一一对应的聚类标签列表

@router.post("/api/survival_analysis")
async def run_survival_analysis(request:SurvivalRequest):
    # print(f"\n[后端日志] 收到生存分析请求，处理文件: {request.clinical_filename}")

    #接下来我们打算：
    # 1.读取"/api/upload"已经处理好的临床数据文件，得到clinical_df
    # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_df
    # 3.把clinical_df和cluster_df合并起来
    # 4.计算Log-Rank P-value
    # 5.计算绘制生存曲线所需数据
    # 6.返回结果

    try:
        # 1.读取"/api/upload"已经处理好的临床数据文件
        # clinical_path=os.path.join("upload",request.clinical_filename) #"/api/upload"已经处理好的组学数据文件的所在路径
        clinical_path=os.path.join("upload",request.session_id,"clinical_data.joblib")
        if not os.path.exists(clinical_path):
            raise FileNotFoundError("找不到临床数据文件")
        clinical_dict = joblib.load(clinical_path)
        clinical_df = list(clinical_dict.values())[0] # 取出唯一的一份临床数据
        # clinical_df=pd.read_csv(clinical_path,header=0,index_col=0,sep=',') #因为"/api/upload"已经处理好文件了，所以这里可以直接这么读取输入数据

        # 2.把前端传过来的样本名称列表、聚类标签列表整理成一个cluster_df
        #创建一个DataFrame对象，同时传入一个字典。于是字典的key就会变成列名，value就会变成列的数据
        cluster_df=pd.DataFrame({
            "SampleID": request.sample, #样本名称列表
            "Cluster": request.labels #聚类标签列表
        })
        cluster_df.set_index("SampleID",inplace=True) #.set_index()可以将cluster_df的"SampleID"列设置为索引列；inplace=True表示直接在原对象上修改

        # 3.把clinical_df和cluster_df合并起来
        merged_df=clinical_df.join(cluster_df,how="inner") #how='inner'表示取索引的交集，即“如果病人名称有对不上的，那么取病人名称的交集”
        if merged_df.empty:
            raise ValueError("临床数据与组学数据的样本名称没有交集，无法进行分析。请检查选择的数据格式是否正确，或者样本ID是否一致。")

        # 👇 【新增】计算因为没有对应临床数据而被丢弃的聚类样本数
        lost_samples = len(cluster_df) - len(merged_df)

        # 4.计算Log-Rank P-value
        #我们来解释一下，在统计学中，我们做检验通常是为了验证一个假设：你提供的分组标签对生存时间没有任何影响
        #于是下面这个函数multivariate_logrank_test就可以根据我们传进去的三个数据，计算出一个概率（P值），告诉你上述假设成立的可能性有多大。如果P值<0.05，说明原假设大概率是错的，分组标签是有意义的
        results=multivariate_logrank_test(
            merged_df["OS.time"], #生存时间（代表病人从诊断开始到死亡或最后一次随访的时间长度）
            merged_df["Cluster"], #分组标签（根据用户选择算法算出来的分组标签）
            merged_df["OS"] #生存状态（1代表死亡，或者说事件发生；0代表存活，或者说删失）
        )
        p_value=results.p_value #得到P值

        #于是我们就计算出来P值了。但它也不太直观，所以我们来另外计算一个生存曲线。如果聚类效果确实很好（样本确实分得很开），那么通常P值会很小、生存曲线也会分得很开，两者趋势是一致的
        #总的来说，三个聚类评估指标、散点图可以看数学上分得好不好，有没有把数据分开；P值、生存曲线可以看医学上有没意义，分出来的组能不能预测病人的死活
        # 5.计算绘制生存曲线所需数据
        kmf=KaplanMeierFitter() #用来计算绘制生存曲线所需数据
        plot_data=[] #用来存放绘制生存曲线所需数据
        for cluster_id in sorted(merged_df["Cluster"].unique()): #遍历所有簇，分别计算其生存曲线 #.unique()可以获取merged_df["Cluster"]中所有不重复的值，即获取所有簇；sorted()可以升序排序
            subset=merged_df[merged_df["Cluster"]==cluster_id] #筛选出merged_df中属于当前簇的样本
            kmf.fit(subset["OS.time"],subset["OS"],label=f"Cluster {cluster_id}") #使用传入的OS.time、OS数据计算生存概率；label用于标记这条曲线的名称
            #此时使用kmf.survival_function_就能返回一个DataFrame，索引代表时间轴、列代表生存概率、列名代表上一句代码中我们传入的label。当然，整个DataFrame只有一列数据
            #接下来我们来计算删失点的坐标
            censored_times=subset[subset["OS"]==0]   ["OS.time"].tolist() #筛选出subset中删失（OS==0）的样本，取OS.time那一列，把那一列转换为列表并返回
            censored_probs=kmf.survival_function_at_times(censored_times).values.tolist() #获取删失点对应的生存概率 #.survival_function_at_times()返回的是pandas.Series，需要用.values转换为numpy数组
            plot_data.append({
                "name": f"Cluster {cluster_id}", #这条曲线的名称
                "times": kmf.survival_function_.index.tolist(), #时间轴，作为生存曲线中的x轴坐标
                "probs": kmf.survival_function_[f"Cluster {cluster_id}"].tolist(), #生存概率，作为生存曲线中的y轴坐标
                "censored_times": censored_times, #删失点的OS.time，作为删失点的x轴坐标
                "censored_probs": censored_probs #删失点对应的生存概率，作为删失点的y轴坐标
            })

        return{
            "status": "success",
            "p_value": p_value, #P值
            "km_data": plot_data, #绘制生存曲线所需数据
            "n_samples": len(merged_df), #合并后的行数，即合并后的样本数量
            "lost_samples": lost_samples # 👇 【新增】返回丢弃数量
        }
    except Exception as e:
        print(f"[生存分析错误] {str(e)}")
        raise HTTPException(status_code=400,detail=str(e))
