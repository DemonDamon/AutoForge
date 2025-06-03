# 百炼（通义千问）客户端使用指南

## 快速开始

### 1. 设置API密钥

在项目根目录或`examples`目录下创建`.env`文件：

```bash
# 正确的环境变量名
DASHSCOPE_API_KEY=sk-your-api-key-here
```

> 注意：官方环境变量名是`DASHSCOPE_API_KEY`，不是`BAILIAN_API_KEY`

### 2. 基础使用

```python
from autoforge.llm import BaiLianClient

# 初始化客户端
client = BaiLianClient(model="qwen-plus")

# 简单生成
response = client.generate("你好，请介绍一下你自己")
print(response)
```

### 3. 高级功能

#### 思考模式（Qwen3模型）

```python
# 对于Qwen3模型，非流式调用需要显式关闭思考模式
client = BaiLianClient(model="qwen3-235b-a22b")
response = client.generate(
    "解释量子计算的基本原理",
    enable_thinking=False  # 非流式调用必须设置
)
```

#### 流式输出

```python
# 流式生成
for chunk in client.generate_with_messages(
    messages=[{"role": "user", "content": "写一个故事"}],
    stream=True
):
    print(chunk, end="", flush=True)
```

#### JSON格式输出

```python
# 生成结构化JSON
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "skills": {"type": "array", "items": {"type": "string"}}
    }
}

result = client.generate_json(
    "生成一个程序员的信息",
    schema=schema
)
print(result)  # 返回解析后的字典
```

#### 工具调用

```python
# 定义工具
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "城市名"}
            },
            "required": ["location"]
        }
    }
}]

# 使用工具
result = client.generate_with_tools(
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=tools
)

if result["tool_calls"]:
    for tool_call in result["tool_calls"]:
        print(f"需要调用: {tool_call['function']['name']}")
        print(f"参数: {tool_call['function']['arguments']}")
```

#### 联网搜索

```python
# 启用联网搜索
response = client.generate(
    "2024年诺贝尔物理学奖获得者是谁？",
    enable_search=True,
    search_options={
        "forced_search": True  # 强制搜索
    }
)
```

## 支持的模型

### 文本生成模型
- `qwen-plus` / `qwen-plus-latest` - 高性能通用模型
- `qwen-turbo` / `qwen-turbo-latest` - 快速响应模型
- `qwen-max` / `qwen-max-latest` - 最强能力模型

### Qwen3系列（支持思考模式）
- `qwen3-72b` - 大型模型
- `qwen3-235b-a22b` - 超大型模型
- 注意：非流式调用需设置`enable_thinking=False`

### 推理模型（只支持流式）
- `qwq-32b-preview` - 深度推理模型
- `qvq-72b-preview` - 视觉推理模型

### 专用模型
- `qwen-math-plus/turbo` - 数学模型
- `qwen-coder-plus/turbo` - 代码模型
- `qwen-vl-plus/max` - 视觉理解模型
- `qwen-audio-turbo/chat` - 音频理解模型

## 常见问题

### 1. enable_thinking错误

**错误信息**: `parameter.enable_thinking must be set to false for non-streaming calls`

**解决方案**:
```python
# 方式1：使用流式输出
response = client.generate("问题", stream=True)

# 方式2：显式关闭思考模式
response = client.generate("问题", enable_thinking=False)
```

### 2. API密钥错误

确保使用正确的环境变量名：
- ✅ 正确：`DASHSCOPE_API_KEY`
- ❌ 错误：`BAILIAN_API_KEY`

### 3. 模型选择建议

- **通用场景**: `qwen-plus`
- **快速响应**: `qwen-turbo`
- **复杂任务**: `qwen-max`
- **深度推理**: `qwq-32b-preview`（仅流式）
- **代码生成**: `qwen-coder-plus`
- **数学问题**: `qwen-math-plus`

## 完整示例

```python
from autoforge.llm import BaiLianClient
from loguru import logger

# 初始化客户端
client = BaiLianClient(model="qwen-plus")

# 多轮对话
messages = [
    {"role": "system", "content": "你是一个有帮助的助手"},
    {"role": "user", "content": "介绍一下Python"}
]

# 带高级参数的生成
response = client.generate_with_messages(
    messages=messages,
    temperature=0.7,
    max_tokens=2000,
    top_p=0.9,
    presence_penalty=0.1,
    seed=42,  # 固定随机性
    response_format={"type": "text"}  # 或 "json_object"
)

logger.info(f"生成完成：{len(response)} 字符")
print(response)
``` 