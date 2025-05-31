"""
OpenAI客户端实现
"""

import os
import logging
from typing import Optional, Dict, Any, List

from .base import BaseLLMClient

logger = logging.getLogger(__name__)

# 延迟导入，避免依赖问题
try:
    import openai
except ImportError:
    openai = None


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = "gpt-4",
                 organization: Optional[str] = None):
        """
        初始化OpenAI客户端
        
        Args:
            api_key: API密钥，默认从环境变量OPENAI_API_KEY读取
            base_url: API基础URL，用于自定义端点
            model: 使用的模型名称
            organization: 组织ID
        """
        if openai is None:
            raise ImportError("请安装openai包: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请提供OpenAI API密钥")
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            organization=organization
        )
        self.model = model
        
        logger.info(f"OpenAI客户端已初始化，使用模型: {self.model}")
    
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
                             **kwargs) -> str:
        """
        使用消息格式生成响应
        
        Args:
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise
    
    def set_model(self, model: str):
        """设置使用的模型"""
        self.model = model
        logger.info(f"模型已切换为: {self.model}") 