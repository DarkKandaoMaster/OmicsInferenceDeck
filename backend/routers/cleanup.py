"""清理某个用户 session 产生的临时文件。

本文件提供 /api/cleanup 接口，前端在页面关闭或刷新时可以调用它。它会删除对应
session_id 目录下由 upload.py、run.py、metrics.py、plots.py 等接口生成的中间文件，
避免服务器长期保留不再使用的数据。
"""

import os
import shutil
from fastapi import APIRouter, Form

# 创建路由器实例 #如果不写这串代码，在main.py里就无法使用app.include_router(router)注册路由，该文件中也无法使用@router.post() 等装饰器来定义 API 端点
router=APIRouter()

@router.post("/api/cleanup")
async def cleanup_session(session_id: str = Form(...)):
    """处理前端页面关闭、刷新时发来的清理请求"""
    session_path = os.path.join("upload", session_id)
    if os.path.exists(session_path):
        try:
            shutil.rmtree(session_path)  # 递归删除该 session_id 下的所有文件和文件夹
            print(f"\n[后端日志] 垃圾清理成功: 会话 {session_id} 的临时文件夹已删除")
        except Exception as e:
            print(f"\n[后端日志] 垃圾清理失败: 无法删除会话 {session_id} - {str(e)}")
    return {"status": "success", "message": "Session cleaned up"}
