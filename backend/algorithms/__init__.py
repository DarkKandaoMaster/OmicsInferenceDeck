import importlib

ALGORITHM_MAP={ #建立前端算法名称到后端文件名的映射关系。比如前端传来"K-means"，我们就把它映射成"kmeans"，然后调用kmeans.py这个文件
    "K-means": "kmeans",
    "Spectral Clustering": "spectral",
    "SNF": "snf",
    "NEMO": "nemo"
    #DarkKandaoMaster：如果发现算法代码完全错了，并且之后一段时间不打算添加这个算法，那么最好把改动都恢复回去。这样用户使用这个算法的时候才能提示“暂时不支持的算法”而不是报错，也方便我们之后添加这个算法，不然algorithms文件夹里的文件一多，很麻烦的。我先帮你恢复回去了哈。
    #以后也这样吧，如果我需要修改algorithms文件夹里的内容，那就在修改处以“DarkKandaoMaster：”开头写个注释，说明一下情况；如果你需要修改algorithms文件夹外的内容，同理。
    #或者我们也可以在微信里交流几句，然后就不写注释了。总之这个algorithms文件夹就完全靠你管了。
}

def load_algorithm(algorithm_name:str): #根据传入的字符串（算法名称），动态导入对应的算法模块，返回该算法模块里面的Algorithm类
    if algorithm_name not in ALGORITHM_MAP:
        raise ValueError(f"暂时不支持的算法：{algorithm_name}")
    try:
        module=importlib.import_module(   f".{ALGORITHM_MAP[algorithm_name]}"   ,package=__name__) #使用相对导入。拼接出相对导入的字符串。package=__name__表示从当前目录开始
        return module.Algorithm
    except Exception as e:
        raise RuntimeError(f"加载算法模块 {algorithm_name} 失败：{str(e)}")