"""
LLM客户端基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def generate_with_messages(self,
                             messages: List[Dict[str, str]],
                             temperature: float = 0.7,
                             max_tokens: int = 4000,
                             **kwargs) -> str:
        """
        使用消息格式生成响应
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 生成温度
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        pass
    
    def validate_connection(self) -> bool:
        """
        验证连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            response = self.generate("Hello, please respond with 'OK'.", temperature=0)
            return "OK" in response or "ok" in response.lower()
        except Exception as e:
            logger.error(f"连接验证失败: {e}")
            return False 