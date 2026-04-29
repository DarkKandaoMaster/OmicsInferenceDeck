import importlib

ALGORITHM_MAP={ #建立前端算法名称到后端文件名的映射关系。比如前端传来"K-means"，我们就把它映射成"kmeans"，然后调用kmeans.py这个文件
    "K-means": "kmeans",
    "Spectral Clustering": "spectral",
    "PIntMF": "pintmf",
    "SNF": "snf",
    "MOSD": "mosd",
    "Parea": "parea",
    "Hclust": "hclust"
}

def load_algorithm(algorithm_name:str): #根据传入的字符串（算法名称），动态导入对应的算法模块，返回该算法模块里面的Algorithm类
    if algorithm_name not in ALGORITHM_MAP:
        raise ValueError(f"暂时不支持的算法：{algorithm_name}")
    try:
        module=importlib.import_module(   f".{ALGORITHM_MAP[algorithm_name]}"   ,package=__name__) #使用相对导入。拼接出相对导入的字符串。package=__name__表示从当前目录开始
        return module.Algorithm
    except Exception as e:
        raise RuntimeError(f"加载算法模块 {algorithm_name} 失败：{str(e)}")
