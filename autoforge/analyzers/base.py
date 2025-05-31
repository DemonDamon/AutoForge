"""
分析器基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """分析器基类"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True):
        """
        初始化分析器
        
        Args:
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
        """
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.save_intermediate = save_intermediate
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """执行分析"""
        pass
    
    def save_result(self, content: str, filename: str, subdir: Optional[str] = None):
        """
        保存分析结果
        
        Args:
            content: 要保存的内容
            filename: 文件名
            subdir: 子目录名（可选）
        """
        if not self.save_intermediate:
            return
        
        # 确定保存路径
        if subdir:
            save_dir = self.output_dir / subdir
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.output_dir
        
        file_path = save_dir / filename
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"保存分析结果: {file_path}")
    
    def call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        调用大语言模型
        
        Args:
            prompt: 提示词
            temperature: 生成温度
            max_tokens: 最大token数
            
        Returns:
            模型响应
        """
        if self.llm_client is None:
            raise ValueError("未配置LLM客户端")
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            raise 