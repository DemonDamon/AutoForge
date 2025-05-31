"""
结果分析器
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .base import BaseAnalyzer
from ..prompts import PromptManager

logger = logging.getLogger(__name__)


class ResultAnalyzer(BaseAnalyzer):
    """结果分析器 - 分析实验结果并给出最终建议"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True,
                 prompt_manager: Optional[PromptManager] = None):
        """
        初始化结果分析器
        
        Args:
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
            prompt_manager: 提示词管理器
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        self.prompt_manager = prompt_manager or PromptManager()
    
    def analyze(self, 
                experiment_reports: List[Dict[str, Any]],
                hardware_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        分析实验结果
        
        Args:
            experiment_reports: 实验报告列表
            hardware_info: 硬件环境信息
            
        Returns:
            分析结果和建议
        """
        logger.info("开始分析实验结果...")
        
        # 准备硬件信息
        if hardware_info is None:
            hardware_info = {
                "gpu": "Unknown",
                "cpu": "Unknown",
                "memory": "Unknown",
                "os": "Unknown"
            }
        
        # 1. 将实验报告转换为JSON字符串
        reports_json = json.dumps(experiment_reports, indent=2, ensure_ascii=False)
        hardware_json = json.dumps(hardware_info, indent=2, ensure_ascii=False)
        
        # 2. 调用LLM分析结果
        prompt = self.prompt_manager.get_prompt(
            "EXPERIMENT_ANALYSIS",
            experiment_reports=reports_json,
            hardware_info=hardware_json
        )
        
        analysis_result = self.call_llm(prompt, temperature=0.3)
        
        # 3. 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"final_analysis_{timestamp}.md"
        
        if self.save_intermediate:
            self.save_result(
                analysis_result,
                result_filename,
                "result_analysis"
            )
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "analysis_result": analysis_result,
            "output_file": str(self.output_dir / "result_analysis" / result_filename)
        } 