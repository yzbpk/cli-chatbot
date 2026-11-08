"""智能式AI对话机器人。

分层结构：

- ``core``         配置与跨层共享定义
- ``models``       Pydantic 数据模型（请求 / 响应 / 消息）
- ``services``     大模型调用等业务服务
- ``repositories`` 数据访问层（会话存储）
- ``api``          FastAPI 接口层
- ``cli``          命令行入口
"""

__version__ = "0.4.0"
