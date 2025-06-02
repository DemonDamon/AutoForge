"""
AutoForge核心Agent
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json

from .analyzers import (
    RequirementAnalyzer,
    ModelSearcher,
    DatasetDesigner,
    ExperimentDesigner,
    ResultAnalyzer
)
from .prompts import PromptManager
from .docparser import MultiModalDocParser
from .llm import BaseLLMClient, OpenAIClient, DeepSeekClient, BaiLianClient

logger = logging.getLogger(__name__)


class AutoForgeAgent:
    """AutoForge智能体 - 自动化模型优化的核心控制器"""
    
    def __init__(self,
                 llm_client=None,
                 llm_config: Optional[Dict[str, Any]] = None,
                 output_dir: str = "outputs",
                 custom_prompts_dir: Optional[str] = None):
        """
        初始化AutoForge Agent
        
        Args:
            llm_client: 大语言模型客户端（如果提供，则优先使用）
            llm_config: LLM配置（如果未提供llm_client，则使用此配置创建客户端）
            output_dir: 输出目录
            custom_prompts_dir: 自定义提示词目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建LLM客户端
        if llm_client is None and llm_config is not None:
            self.llm_client = self._create_llm_client(llm_config)
        else:
            self.llm_client = llm_client
        
        # 初始化提示词管理器
        self.prompt_manager = PromptManager(custom_prompts_dir)
        
        # 初始化各个分析器
        self.requirement_analyzer = RequirementAnalyzer(
            llm_client=self.llm_client,
            output_dir=output_dir,
            prompt_manager=self.prompt_manager
        )
        
        self.model_searcher = ModelSearcher(
            llm_client=self.llm_client,
            output_dir=output_dir,
            prompt_manager=self.prompt_manager
        )
        
        self.dataset_designer = DatasetDesigner(
            llm_client=self.llm_client,
            output_dir=output_dir,
            prompt_manager=self.prompt_manager
        )
        
        self.experiment_designer = ExperimentDesigner(
            llm_client=self.llm_client,
            output_dir=output_dir,
            prompt_manager=self.prompt_manager
        )
        
        self.result_analyzer = ResultAnalyzer(
            llm_client=self.llm_client,
            output_dir=output_dir,
            prompt_manager=self.prompt_manager
        )
        
        # 工作流状态
        self.workflow_state = {
            "requirement_analysis": None,
            "model_search": None,
            "dataset_design": None,
            "experiment_design": None,
            "final_analysis": None
        }
    
    def _create_llm_client(self, config: Dict[str, Any]) -> BaseLLMClient:
        """
        根据配置创建LLM客户端
        
        Args:
            config: LLM配置
            
        Returns:
            LLM客户端
        """
        provider = config.get("provider", "openai").lower()
        
        # 提取常用配置
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        model = config.get("model")
        organization = config.get("organization")
        
        if provider == "openai":
            return OpenAIClient(
                api_key=api_key,
                base_url=base_url,
                model=model,
                organization=organization
            )
        elif provider == "deepseek":
            return DeepSeekClient(
                api_key=api_key,
                base_url=base_url or "https://api.deepseek.com",
                model=model or "deepseek-chat",
                organization=organization
            )
        elif provider == "bailian":
            return BaiLianClient(
                api_key=api_key,
                base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                model=model or "qwen-plus",
                organization=organization
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
    
    def analyze_requirements(self,
                           document_path: Optional[str] = None,
                           document_content: Optional[str] = None,
                           manual_description: Optional[str] = None) -> Dict[str, Any]:
        """
        步骤1: 分析需求
        
        Args:
            document_path: 文档路径
            document_content: 文档内容
            manual_description: 手动描述
            
        Returns:
            需求分析结果
        """
        logger.info("=== 步骤1: 需求分析 ===")
        
        result = self.requirement_analyzer.analyze(
            document_path=document_path,
            document_content=document_content,
            manual_description=manual_description
        )
        
        self.workflow_state["requirement_analysis"] = result
        return result
    
    def search_models(self, requirement_analysis: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        步骤2: 搜索模型
        
        Args:
            requirement_analysis: 需求分析结果（可选，默认使用上一步结果）
            additional_info: 额外的信息，如手动爬取的模型数据
            
        Returns:
            模型搜索结果
        """
        logger.info("=== 步骤2: 模型搜索 ===")
        
        if requirement_analysis is None:
            if self.workflow_state["requirement_analysis"] is None:
                raise ValueError("请先执行需求分析")
            requirement_analysis = self.workflow_state["requirement_analysis"]["analysis"]
        
        result = self.model_searcher.analyze(
            requirement_analysis=requirement_analysis,
            additional_info=additional_info
        )
        
        self.workflow_state["model_search"] = result
        return result
    
    def design_dataset(self,
                      requirement_analysis: Optional[str] = None,
                      selected_models: Optional[str] = None) -> Dict[str, Any]:
        """
        步骤3.1: 设计数据集
        
        Args:
            requirement_analysis: 需求分析结果
            selected_models: 选定的模型方案
            
        Returns:
            数据集设计方案
        """
        logger.info("=== 步骤3.1: 数据集设计 ===")
        
        if requirement_analysis is None:
            if self.workflow_state["requirement_analysis"] is None:
                raise ValueError("请先执行需求分析")
            requirement_analysis = self.workflow_state["requirement_analysis"]["analysis"]
        
        if selected_models is None:
            if self.workflow_state["model_search"] is None:
                raise ValueError("请先执行模型搜索")
            selected_models = self.workflow_state["model_search"]["search_result"]
        
        result = self.dataset_designer.analyze(requirement_analysis, selected_models)
        
        self.workflow_state["dataset_design"] = result
        return result
    
    def design_experiments(self,
                         model_solution: Optional[str] = None,
                         dataset_info: Optional[str] = None) -> Dict[str, Any]:
        """
        步骤3.2: 设计实验
        
        Args:
            model_solution: 模型方案
            dataset_info: 数据集信息
            
        Returns:
            实验设计方案
        """
        logger.info("=== 步骤3.2: 实验设计 ===")
        
        if model_solution is None:
            if self.workflow_state["model_search"] is None:
                raise ValueError("请先执行模型搜索")
            model_solution = self.workflow_state["model_search"]["search_result"]
        
        if dataset_info is None:
            if self.workflow_state["dataset_design"] is None:
                raise ValueError("请先执行数据集设计")
            dataset_info = self.workflow_state["dataset_design"]["design_result"]
        
        result = self.experiment_designer.analyze(model_solution, dataset_info)
        
        self.workflow_state["experiment_design"] = result
        return result
    
    def analyze_results(self,
                       experiment_reports: List[Dict[str, Any]],
                       hardware_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        步骤3.3: 分析实验结果
        
        Args:
            experiment_reports: 实验报告列表
            hardware_info: 硬件信息
            
        Returns:
            最终分析结果
        """
        logger.info("=== 步骤3.3: 结果分析 ===")
        
        result = self.result_analyzer.analyze(experiment_reports, hardware_info)
        
        self.workflow_state["final_analysis"] = result
        return result
    
    def run_full_pipeline(self,
                         document_path: Optional[str] = None,
                         document_content: Optional[str] = None,
                         manual_description: Optional[str] = None,
                         skip_experiment_execution: bool = True) -> Dict[str, Any]:
        """
        运行完整的分析流程
        
        Args:
            document_path: 文档路径
            document_content: 文档内容
            manual_description: 手动描述
            skip_experiment_execution: 是否跳过实验执行（仅生成方案）
            
        Returns:
            完整的分析结果
        """
        logger.info("开始运行AutoForge完整流程...")
        
        # 1. 需求分析
        self.analyze_requirements(document_path, document_content, manual_description)
        
        # 2. 模型搜索
        self.search_models()
        
        # 3.1 数据集设计
        self.design_dataset()
        
        # 3.2 实验设计
        self.design_experiments()
        
        # 生成最终报告
        final_report = self.generate_final_report(skip_experiment_execution)
        
        return {
            "status": "success",
            "workflow_state": self.workflow_state,
            "final_report": final_report
        }
    
    def generate_final_report(self, skip_experiment_execution: bool = True) -> str:
        """生成最终报告"""
        report_parts = []
        
        report_parts.append("# AutoForge 分析报告\n")
        report_parts.append("## 1. 需求分析")
        if self.workflow_state["requirement_analysis"]:
            report_parts.append(f"- 输出文件: {self.workflow_state['requirement_analysis']['output_file']}")
        
        report_parts.append("\n## 2. 模型搜索")
        if self.workflow_state["model_search"]:
            report_parts.append(f"- 输出文件: {self.workflow_state['model_search']['output_file']}")
        
        report_parts.append("\n## 3. 数据集设计")
        if self.workflow_state["dataset_design"]:
            report_parts.append(f"- 输出文件: {self.workflow_state['dataset_design']['output_file']}")
        
        report_parts.append("\n## 4. 实验设计")
        if self.workflow_state["experiment_design"]:
            report_parts.append(f"- 输出文件: {self.workflow_state['experiment_design']['output_file']}")
        
        if skip_experiment_execution:
            report_parts.append("\n## 5. 后续步骤")
            report_parts.append("- 根据数据集设计方案构建数据集")
            report_parts.append("- 根据实验设计方案执行网格化实验")
            report_parts.append("- 收集实验报告并使用analyze_results方法进行最终分析")
        
        report = "\n".join(report_parts)
        
        # 保存报告
        report_path = self.output_dir / "autoforge_final_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"最终报告已保存至: {report_path}")
        return report
    
    def save_workflow_state(self, filename: str = "workflow_state.json"):
        """保存工作流状态"""
        state_path = self.output_dir / filename
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(self.workflow_state, f, indent=2, ensure_ascii=False)
        logger.info(f"工作流状态已保存至: {state_path}")
    
    def load_workflow_state(self, filename: str = "workflow_state.json"):
        """加载工作流状态"""
        state_path = self.output_dir / filename
        if state_path.exists():
            with open(state_path, 'r', encoding='utf-8') as f:
                self.workflow_state = json.load(f)
            logger.info(f"工作流状态已从 {state_path} 加载")
        else:
            logger.warning(f"工作流状态文件不存在: {state_path}") 