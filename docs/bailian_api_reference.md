# 百炼（通义千问）API 参考文档

本文介绍通义千问 API 的输入输出参数。

模型介绍、选型建议和使用方法，请参考文本生成。
您可以通过 OpenAI 兼容或 DashScope 的方式调用通义千问 API。

## OpenAI 兼容模式

### 基础配置

**公有云金融云**
- 使用SDK调用时需配置的base_url：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 使用HTTP方式调用时需配置的endpoint：`POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`

您需要已获取API Key并配置API Key到环境变量。如果通过OpenAI SDK进行调用，还需要安装SDK。

### 请求体

#### 基础示例

```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你是谁？"},
    ],
    # Qwen3模型通过enable_thinking参数控制思考过程（开源版默认True，商业版默认False）
    # 使用Qwen3开源版模型时，若未启用流式输出，请将下行取消注释，否则会报错
    # extra_body={"enable_thinking": False},
)
print(completion.model_dump_json())
```

### 参数说明

#### 必选参数

##### model (string)
模型名称。

支持的模型：
- 通义千问大语言模型（商业版、开源版、Qwen-Long）
- 通义千问VL
- 通义千问Omni
- 数学模型
- 代码模型

> 注意：通义千问Audio暂不支持OpenAI兼容模式，仅支持DashScope方式。

##### messages (array)
由历史对话组成的消息列表。

**消息类型：**

1. **System Message** (可选)
   - 模型的目标或角色
   - 如果设置系统消息，请放在messages列表的第一位
   - QwQ 模型不建议设置 System Message
   - QVQ 模型设置System Message不会生效

2. **User Message** (必选)
   - 用户发送给模型的消息
   - content: string 或 array
     - 纯文本输入：string类型
     - 多模态输入：array类型

   **多模态输入属性：**
   - `type`: 内容类型
     - `"text"`: 文本输入
     - `"image_url"`: 图片输入
     - `"input_audio"`: 音频输入（仅Qwen-Omni）
     - `"video"`: 图片列表形式的视频
     - `"video_url"`: 视频文件

3. **Assistant Message** (可选)
   - 模型对用户消息的回复
   - `partial` (boolean): 是否开启Partial Mode（前缀续写）

4. **Tool Message** (可选)
   - 工具的输出信息
   - `tool_call_id`: 对应的工具调用ID

#### 可选参数

##### stream (boolean) 
默认值：false
- false：模型生成完所有内容后一次性返回结果
- true：边生成边输出

> 注意：Qwen3商业版（思考模式）、Qwen3开源版、QwQ、QVQ只支持流式输出

##### stream_options (object)
当启用流式输出时，可通过设置`{"include_usage": true}`在最后一行显示Token数。

##### modalities (array)
默认值：["text"]
输出数据的模态，仅支持 Qwen-Omni 模型：
- `["text","audio"]`：输出文本与音频
- `["text"]`：仅输出文本

##### audio (object)
输出音频配置（仅Qwen-Omni）：
- `voice`: 音色（Cherry/Serena/Ethan/Chelsie）
- `format`: 格式（当前仅支持"wav"）

##### temperature (float)
采样温度，控制生成文本的多样性。
- 取值范围：[0, 2)
- 越高生成越多样，越低生成越确定

##### top_p (float)
核采样的概率阈值。
- 取值范围：(0, 1.0]
- 建议只设置temperature或top_p其中一个

##### top_k (integer)
生成过程中采样候选集的大小。
- 取值需要大于或等于0
- 通过Python SDK调用时，请将top_k放入extra_body对象中

##### presence_penalty (float)
控制内容重复度。
- 取值范围：[-2.0, 2.0]
- 正数减少重复，负数增加重复

##### response_format (object)
默认值：{"type": "text"}
返回内容格式：
- `{"type": "text"}`：普通文本
- `{"type": "json_object"}`：JSON格式输出

##### max_tokens (integer)
本次请求返回的最大Token数。
- 默认值和最大值都是模型的最大输出长度
- 对于QwQ、QVQ与思考模式的Qwen3，只限制回复内容长度

##### n (integer)
默认值：1
生成响应的个数，取值范围1-4。

##### enable_thinking (boolean)
是否开启思考模式（适用于Qwen3）：
- Qwen3商业版默认False
- Qwen3开源版默认True
- 通过Python SDK调用时，使用extra_body配置

##### thinking_budget (integer)
思考过程的最大长度，仅在enable_thinking为true时生效。

##### seed (integer)
设置seed使生成更确定。
取值范围：0到2^31-1

##### stop (string 或 array)
停止生成的条件，可传入敏感词控制输出。

##### tools (array)
可供模型调用的工具数组。

##### tool_choice (string 或 object)
默认值："auto"
控制工具调用策略：
- `"auto"`：模型自动选择
- `"none"`：不调用工具
- 对象格式：指定特定工具

##### parallel_tool_calls (boolean)
默认值：false
是否开启并行工具调用。

##### translation_options (object)
翻译参数（仅翻译模型）：
- `source_lang`: 源语言
- `target_lang`: 目标语言
- `terms`: 术语数组
- `tm_list`: 翻译记忆数组
- `domains`: 领域提示

##### enable_search (boolean)
是否使用互联网搜索结果参考。

##### search_options (object)
联网搜索策略配置。

##### X-DashScope-DataInspection (string)
内容安全检测配置。

### 响应格式

#### 非流式输出

```json
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "我是阿里云开发的一款超大规模语言模型，我叫通义千问。"
            },
            "finish_reason": "stop",
            "index": 0,
            "logprobs": null
        }
    ],
    "object": "chat.completion",
    "usage": {
        "prompt_tokens": 3019,
        "completion_tokens": 104,
        "total_tokens": 3123,
        "prompt_tokens_details": {
            "cached_tokens": 2048
        }
    },
    "created": 1735120033,
    "system_fingerprint": null,
    "model": "qwen-plus",
    "id": "chatcmpl-6ada9ed2-7f33-9de2-8bb0-78bd4035025a"
}
```

#### 流式输出

每个chunk格式：
```json
{
    "id": "chatcmpl-xxx",
    "choices": [{
        "delta": {
            "content": "内容片段",
            "role": "assistant"
        },
        "finish_reason": null,
        "index": 0
    }],
    "created": 1735113344,
    "model": "qwen-plus",
    "object": "chat.completion.chunk"
}
```

## DashScope 原生模式

### 基础配置

**公有云金融云**
- 通义千问大语言模型：`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- 通义千问VL/Audio模型：`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`

### 请求体示例

```python
import os
import dashscope

messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': '你是谁？'}
]
response = dashscope.Generation.call(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen-plus",
    messages=messages,
    result_format='message'
)
print(response)
```

### 参数说明

DashScope模式的参数与OpenAI兼容模式类似，主要区别：

1. HTTP调用时，`messages`需要放入`input`对象中
2. 大部分参数需要放入`parameters`对象中
3. 某些参数名称不同：
   - Java SDK：`topP`、`topK`、`maxTokens`等
   - `result_format`默认值可能不同

### 响应格式

```json
{
    "status_code": 200,
    "request_id": "902fee3b-f7f0-9a8c-96a1-6b4ea25af114",
    "code": "",
    "message": "",
    "output": {
        "text": null,
        "finish_reason": null,
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "我是阿里云开发的一款超大规模语言模型，我叫通义千问。"
            }
        }]
    },
    "usage": {
        "input_tokens": 22,
        "output_tokens": 17,
        "total_tokens": 39
    }
}
```

## 支持的模型

### 文本模型
- qwen-max系列
- qwen-plus系列
- qwen-turbo系列
- qwen-long系列
- Qwen3系列（商业版/开源版）
- QwQ（深度推理）

### 多模态模型
- qwen-vl系列（视觉理解）
- QVQ（视觉推理）
- qwen-audio系列（音频理解）
- qwen-omni系列（全模态）

### 专用模型
- qwen-math系列（数学）
- qwen-coder系列（代码）
- 翻译模型
- OCR模型

## 注意事项

1. **思考模式**：Qwen3开源版默认开启，商业版默认关闭。非流式调用时必须设置`enable_thinking: false`
2. **流式输出**：QwQ、QVQ只支持流式输出
3. **Token限制**：不同模型有不同的输入输出Token限制
4. **参数兼容性**：某些参数仅适用于特定模型
5. **API密钥**：环境变量名为`DASHSCOPE_API_KEY`（不是`BAILIAN_API_KEY`） 