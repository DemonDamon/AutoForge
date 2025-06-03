"""
阿里云百炼（通义千问）客户端实现
支持OpenAI兼容模式调用通义千问系列模型
"""

import os
from loguru import logger
from typing import Optional, Dict, Any, List, Union, Iterator

from .base import BaseLLMClient

# 屏蔽httpx日志
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# 延迟导入，避免依赖问题
try:
    import openai
except ImportError:
    openai = None


class BaiLianClient(BaseLLMClient):
    """阿里云百炼（通义千问）API客户端"""
    
    # 需要思考模式的模型
    THINKING_MODELS = ["qwen3", "qwq", "qvq"]
    
    # 只支持流式输出的模型
    STREAM_ONLY_MODELS = ["qwq", "qvq"]
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "qwen-plus",
                 organization: Optional[str] = None):
        """
        初始化百炼客户端
        
        Args:
            api_key: API密钥，默认从环境变量DASHSCOPE_API_KEY读取
            base_url: API基础URL，默认为百炼的兼容模式API地址
            model: 使用的模型名称
            organization: 组织ID
        """
        if openai is None:
            raise ImportError("请安装openai包: pip install openai")
        
        # 支持多个环境变量名
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
        if not self.api_key:
            raise ValueError("请提供百炼 API密钥（通过DASHSCOPE_API_KEY环境变量或api_key参数）")
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            organization=organization
        )
        self.model = model
        
        logger.info(f"百炼客户端已初始化，使用模型: {self.model}")
    
    def _is_thinking_model(self, model: Optional[str] = None) -> bool:
        """检查是否是思考模式模型"""
        model = model or self.model
        return any(thinking_model in model.lower() for thinking_model in self.THINKING_MODELS)
    
    def _is_stream_only_model(self, model: Optional[str] = None) -> bool:
        """检查是否是只支持流式输出的模型"""
        model = model or self.model
        return any(stream_model in model.lower() for stream_model in self.STREAM_ONLY_MODELS)
    
    def generate(self, 
                prompt: str,
                temperature: float = 0.7,
                max_tokens: int = 4000,
                **kwargs) -> str:
        """
        生成响应
        
        Args:
            prompt: 提示词
            temperature: 生成温度
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_with_messages(messages, temperature, max_tokens, **kwargs)
    
    def generate_with_messages(self,
                             messages: List[Dict[str, str]],
                             temperature: float = 0.7,
                             max_tokens: int = 4000,
                             stream: bool = False,
                             **kwargs) -> Union[str, Iterator[str]]:
        """
        使用消息格式生成响应
        
        Args:
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大token数
            stream: 是否流式输出
            **kwargs: 其他参数，支持：
                - top_p: 核采样概率阈值
                - top_k: 采样候选集大小（需通过extra_body传递）
                - presence_penalty: 控制重复度
                - n: 生成响应个数
                - seed: 随机种子
                - stop: 停止条件
                - response_format: 输出格式
                - enable_thinking: 是否开启思考模式（Qwen3）
                - thinking_budget: 思考过程最大长度
                - tools: 工具列表
                - tool_choice: 工具选择策略
                - parallel_tool_calls: 是否并行调用工具
                - enable_search: 是否启用联网搜索
                - search_options: 搜索选项
                - stream_options: 流式选项
            
        Returns:
            生成的文本或流式迭代器
        """
        try:
            # 提取需要放入extra_body的参数
            extra_body = kwargs.pop("extra_body", {})
            
            # 处理思考模式相关参数
            model = kwargs.get("model", self.model)
            if self._is_thinking_model(model):
                # Qwen3开源版默认开启思考模式，商业版默认关闭
                # 非流式调用时必须显式设置enable_thinking
                if not stream and "enable_thinking" not in extra_body:
                    # 对于非流式调用，默认关闭思考模式以避免错误
                    extra_body["enable_thinking"] = False
                    logger.info(f"模型 {model} 非流式调用，自动设置 enable_thinking=False")
            
            # 处理只支持流式的模型
            if self._is_stream_only_model(model) and not stream:
                logger.warning(f"模型 {model} 只支持流式输出，自动切换为流式模式")
                stream = True
            
            # 处理top_k参数（需要通过extra_body传递）
            if "top_k" in kwargs:
                extra_body["top_k"] = kwargs.pop("top_k")
            
            # 处理thinking_budget参数
            if "thinking_budget" in kwargs:
                extra_body["thinking_budget"] = kwargs.pop("thinking_budget")
            
            # 处理enable_thinking参数
            if "enable_thinking" in kwargs:
                extra_body["enable_thinking"] = kwargs.pop("enable_thinking")
            
            # 处理enable_search参数
            if "enable_search" in kwargs:
                extra_body["enable_search"] = kwargs.pop("enable_search")
            
            # 处理search_options参数
            if "search_options" in kwargs:
                extra_body["search_options"] = kwargs.pop("search_options")
            
            # 构建请求参数
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            
            # 添加可选参数
            optional_params = [
                "top_p", "presence_penalty", "n", "seed", "stop",
                "response_format", "tools", "tool_choice", 
                "parallel_tool_calls", "stream_options"
            ]
            
            for param in optional_params:
                if param in kwargs:
                    request_params[param] = kwargs[param]
            
            # 添加extra_body（如果有内容）
            if extra_body:
                request_params["extra_body"] = extra_body
            
            # 日志记录请求
            logger.info(f"[百炼请求] model={model}, messages={messages}")
            if extra_body:
                logger.info(f"[百炼请求extra_body] {extra_body}")
            
            # 调用API
            if stream:
                # 流式输出
                stream_response = self.client.chat.completions.create(**request_params)
                return self._handle_stream_response(stream_response)
            else:
                # 非流式输出
                response = self.client.chat.completions.create(**request_params)
                
                # 提取内容
                content = response.choices[0].message.content
                
                # 日志记录响应
                logger.info(f"[百炼响应] {content}")
                
                # 记录token使用情况
                if hasattr(response, 'usage'):
                    logger.debug(f"Token使用: {response.usage}")
                
                return content
            
        except Exception as e:
            logger.error(f"百炼 API调用失败: {e}")
            raise
    
    def _handle_stream_response(self, stream_response) -> Iterator[str]:
        """处理流式响应"""
        try:
            full_content = ""
            for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield content
            
            # 日志记录完整响应
            logger.info(f"[百炼流式响应完成] 总长度: {len(full_content)} 字符")
            
        except Exception as e:
            logger.error(f"处理流式响应失败: {e}")
            raise
    
    def generate_with_tools(self,
                          messages: List[Dict[str, str]],
                          tools: List[Dict[str, Any]],
                          tool_choice: Union[str, Dict[str, Any]] = "auto",
                          **kwargs) -> Dict[str, Any]:
        """
        使用工具调用生成响应
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            tool_choice: 工具选择策略
            **kwargs: 其他生成参数
            
        Returns:
            包含工具调用信息的响应
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )
            
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": []
            }
            
            # 提取工具调用信息
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"工具调用失败: {e}")
            raise
    
    def generate_json(self,
                     prompt: str,
                     schema: Optional[Dict[str, Any]] = None,
                     **kwargs) -> Dict[str, Any]:
        """
        生成JSON格式的响应
        
        Args:
            prompt: 提示词（应包含JSON格式要求）
            schema: JSON Schema（可选）
            **kwargs: 其他生成参数
            
        Returns:
            解析后的JSON对象
        """
        import json
        
        # 设置响应格式为JSON
        kwargs["response_format"] = {"type": "json_object"}
        
        # 如果提供了schema，将其加入提示词
        if schema:
            prompt += f"\n\n请严格按照以下JSON Schema格式输出：\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
        
        response = self.generate(prompt, **kwargs)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response}")
            raise
    
    def set_model(self, model: str):
        """设置使用的模型"""
        self.model = model
        logger.info(f"模型已切换为: {self.model}")
    
    def list_models(self) -> List[str]:
        """列出支持的模型"""
        return [
            # 通用模型
            "qwen-max", "qwen-max-latest",
            "qwen-plus", "qwen-plus-latest", 
            "qwen-turbo", "qwen-turbo-latest",
            
            # Qwen3系列
            "qwen3-72b", "qwen3-14b", "qwen3-7b",
            "qwen3-235b-a22b",  # 大型Qwen3模型
            
            # 长文本模型
            "qwen-long",
            
            # 推理模型
            "qwq-32b-preview", "qvq-72b-preview",
            
            # 数学模型
            "qwen-math-plus", "qwen-math-turbo",
            
            # 代码模型
            "qwen-coder-plus", "qwen-coder-turbo",
            
            # 多模态模型
            "qwen-vl-plus", "qwen-vl-max",
            "qwen-audio-turbo", "qwen-audio-chat",
            
            # 专用模型
            "qwen-ocr", "farui-plus"
        ] 