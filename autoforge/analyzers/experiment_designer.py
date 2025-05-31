"""
实验设计器
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseAnalyzer
from ..prompts import PromptManager

logger = logging.getLogger(__name__)


class ExperimentDesigner(BaseAnalyzer):
    """实验设计器 - 设计网格化实验方案"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True,
                 prompt_manager: Optional[PromptManager] = None):
        """
        初始化实验设计器
        
        Args:
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
            prompt_manager: 提示词管理器
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        self.prompt_manager = prompt_manager or PromptManager()
    
    def analyze(self, 
                model_solution: str,
                dataset_info: str) -> Dict[str, Any]:
        """
        设计网格化实验方案
        
        Args:
            model_solution: 模型方案
            dataset_info: 数据集信息
            
        Returns:
            实验设计方案
        """
        logger.info("开始设计网格化实验方案...")
        
        # 1. 调用LLM设计实验方案
        prompt = self.prompt_manager.get_prompt(
            "GRID_EXPERIMENT_DESIGN",
            model_solution=model_solution,
            dataset_info=dataset_info
        )
        
        design_result = self.call_llm(prompt, temperature=0.3)
        
        # 2. 保存设计结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"experiment_design_{timestamp}.md"
        
        if self.save_intermediate:
            self.save_result(
                design_result,
                result_filename,
                "experiment_design"
            )
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "design_result": design_result,
            "output_file": str(self.output_dir / "experiment_design" / result_filename)
        } 