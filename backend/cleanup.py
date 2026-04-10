# =============================================================================
# 后台定时清理任务
# =============================================================================

"""
后台定时清理任务模块

该模块负责定期清理 upload 文件夹下超过指定时间未修改的会话文件夹，
防止服务器磁盘空间被临时文件占满。
"""

import os
import shutil
import time
import asyncio
from contextlib import asynccontextmanager
from typing import List

# 清理间隔时间（秒）
CLEANUP_INTERVAL = 6 * 60 * 60  # 6小时

# 上传文件存放目录
UPLOAD_DIR = "upload"


async def cleanup_expired_folders():
    """
    每隔6小时自动运行一次，清理超过6小时未修改的会话文件夹
    
    该函数使用 asyncio.sleep 实现异步休眠，在休眠期间 CPU 会去处理其他用户的 API 请求，
    完全没有任何性能损耗。
    """
    
    while True:
        # 挂起当前任务 6 小时（不阻塞服务器处理其他请求），它会让这个 while True 循环每执行一次就休眠 6 小时。由于是 await 异步休眠，在这 6 小时内 CPU 会去全速处理其他用户的 API 请求，完全没有任何性能损耗。
        await asyncio.sleep(CLEANUP_INTERVAL)
        
        if not os.path.exists(UPLOAD_DIR):
            continue
            
        print(f"\n[后台任务] 开始清理 {UPLOAD_DIR} 下的过期文件夹...")
        current_time = time.time()
        
        # 遍历 upload 文件夹下的所有内容
        for folder_name in os.listdir(UPLOAD_DIR):
            folder_path = os.path.join(UPLOAD_DIR, folder_name)
            
            # 确保它是一个文件夹
            if os.path.isdir(folder_path):
                # 获取文件夹的最后修改时间（Linux/Windows通用，getmtime 最稳妥）
                folder_mtime = os.path.getmtime(folder_path)
                
                # 判断：当前时间 - 文件夹最后修改时间 > 6 小时
                if current_time - folder_mtime > CLEANUP_INTERVAL:
                    try:
                        shutil.rmtree(folder_path)
                        print(f"[后台任务] 成功删除过期文件夹: {folder_name}")
                    except Exception as e:
                        print(f"[后台任务] 删除过期文件夹 {folder_name} 失败: {str(e)}")

# 定义 FastAPI 的生命周期管理器
@asynccontextmanager #这是目前 FastAPI 官方推荐的处理“服务器启动/关闭事件”的标准做法，用于替代旧版本会报警告的 @app.on_event("startup") 装饰器。
async def lifespan(app):
    """
    FastAPI 生命周期管理器
    
    这是目前 FastAPI 官方推荐的处理"服务器启动/关闭事件"的标准做法，
    用于替代旧版本会报警告的 @app.on_event("startup") 装饰器。
    
    Parameters
    ----------
    app : FastAPI
        FastAPI 应用实例
    """
    # 【启动服务器时】创建并启动后台清理任务
    task = asyncio.create_task(cleanup_expired_folders())
    yield  # 交出控制权，让 FastAPI 正常启动并处理请求
    # 【关闭服务器时】取消清理任务，优雅退出
    task.cancel()



def cleanup_temp_files(file_paths: List[str]) -> None: #-> None 是 Python 类型注解（Type Hint） 语法的一部分，用于声明函数的返回类型。像注释一样给开发者看的。表示函数 cleanup_temp_files() 不返回任何值。
    """
    清理临时文件列表中的所有文件
    
    遍历传入的文件路径列表，删除所有存在的文件。
    用于在请求处理完成后或出错时清理临时文件。
    
    Parameters
    ----------
    file_paths : List[str]
        需要删除的文件路径列表
    """
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)
