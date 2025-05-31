"""
数据集设计器
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseAnalyzer
from ..prompts import PromptManager

logger = logging.getLogger(__name__)


class DatasetDesigner(BaseAnalyzer):
    """数据集设计器 - 设计数据集构建方案"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True,
                 prompt_manager: Optional[PromptManager] = None):
        """
        初始化数据集设计器
        
        Args:
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
            prompt_manager: 提示词管理器
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        self.prompt_manager = prompt_manager or PromptManager()
    
    def analyze(self, 
                requirement_analysis: str,
                selected_models: str) -> Dict[str, Any]:
        """
        设计数据集构建方案
        
        Args:
            requirement_analysis: 需求分析结果
            selected_models: 选定的模型方案
            
        Returns:
            数据集设计方案
        """
        logger.info("开始设计数据集构建方案...")
        
        # 1. 调用LLM设计数据集方案
        prompt = self.prompt_manager.get_prompt(
            "DATASET_CONSTRUCTION",
            requirement_analysis=requirement_analysis,
            selected_models=selected_models
        )
        
        design_result = self.call_llm(prompt, temperature=0.3)
        
        # 2. 保存设计结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"dataset_design_{timestamp}.md"
        
        if self.save_intermediate:
            self.save_result(
                design_result,
                result_filename,
                "dataset_design"
            )
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "design_result": design_result,
            "output_file": str(self.output_dir / "dataset_design" / result_filename)
        } 