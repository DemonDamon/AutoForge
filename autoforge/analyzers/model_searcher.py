"""
模型搜索器
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .base import BaseAnalyzer
from ..prompts import PromptManager
from ..crawler import HuggingFaceCrawler, TaskManager

logger = logging.getLogger(__name__)


class ModelSearcher(BaseAnalyzer):
    """模型搜索器 - 基于需求分析结果搜索HuggingFace模型"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True,
                 prompt_manager: Optional[PromptManager] = None,
                 use_crawler: bool = True,
                 crawler_config: Optional[Dict[str, Any]] = None):
        """
        初始化模型搜索器
        
        Args:
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
            prompt_manager: 提示词管理器
            use_crawler: 是否使用爬虫获取最新模型信息
            crawler_config: 爬虫配置
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        self.prompt_manager = prompt_manager or PromptManager()
        self.use_crawler = use_crawler
        
        # 初始化爬虫
        if self.use_crawler:
            crawler_config = crawler_config or {}
            self.crawler = HuggingFaceCrawler(
                base_url=crawler_config.get('base_url', 'https://hf-mirror.com'),
                output_dir=crawler_config.get('output_dir', str(self.output_dir / 'hf_models')),
                max_workers=crawler_config.get('max_workers', 4),
                delay=crawler_config.get('delay', 1.0)
            )
            self.task_manager = TaskManager()

    def analyze(self, requirement_analysis: str, 
                crawl_models: bool = True,
                top_k: int = 10,
                sort: str = "trending",
                additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行模型搜索和推荐
        
        Args:
            requirement_analysis: 需求分析结果
            crawl_models: 是否爬取最新模型信息
            top_k: 爬取模型数量
            sort: 排序方式
            additional_info: 额外的信息，包含业务层处理的模型数据和自定义提示
            
        Returns:
            模型推荐结果
        """
        logger.info("开始模型搜索...")
        
        # 检查additional_info中是否有top_k参数，有则覆盖默认值
        if additional_info and "top_k" in additional_info:
            top_k = additional_info["top_k"]
            logger.info(f"使用业务层提供的top_k值: {top_k}")
        
        # 1. 首先使用LLM分析需求，确定任务类型
        task_info = self._identify_task_from_requirements(requirement_analysis)
        
        # 2. 如果启用爬虫且找到了任务类型，爬取相关模型
        crawled_models = None
        if self.use_crawler and crawl_models and task_info and not additional_info:
            crawled_models = self._crawl_relevant_models(task_info, top_k, sort)
        
        # 3. 使用额外提供的模型信息(如果有)
        if additional_info and "crawled_models" in additional_info:
            crawled_models = additional_info.get("crawled_models", [])
            if crawled_models:
                logger.info(f"使用业务层提供的模型信息，包含 {len(crawled_models)} 个模型")
                
                # 如果业务层提供了任务信息，则使用业务层的任务信息
                if "task_info" in additional_info:
                    task_info = additional_info["task_info"]
                    logger.info(f"使用业务层提供的任务类型: {task_info.get('name', 'Unknown')}")
        
        # 4. 准备增强的提示词（包含爬取的模型信息）
        enhanced_prompt = self._prepare_enhanced_prompt(
            requirement_analysis, 
            task_info, 
            crawled_models,
            additional_info
        )
        
        # 5. 调用LLM进行模型搜索和推荐
        search_result = self.call_llm(enhanced_prompt, temperature=0.3)
        
        # 6. 保存搜索结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"model_search_{timestamp}.md"
        
        if self.save_intermediate:
            self.save_result(
                search_result,
                result_filename,
                "model_search"
            )
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "search_result": search_result,
            "task_info": task_info,
            "crawled_models": crawled_models,
            "output_file": str(self.output_dir / "model_search" / result_filename)
        }
    
    def _identify_task_from_requirements(self, requirement_analysis: str) -> Optional[Dict[str, Any]]:
        """从需求分析中识别任务类型"""
        if not self.use_crawler:
            return None
        
        # 使用简单的关键词匹配来识别任务类型
        # 也可以使用LLM来更准确地识别
        requirement_lower = requirement_analysis.lower()
        
        # 获取所有任务
        all_tasks = self.task_manager.get_all_tasks()
        
        # 匹配任务
        matched_tasks = []
        for task_tag, task_info in all_tasks.items():
            # 检查任务名称、标签或描述是否在需求中出现
            if (task_info['name'].lower() in requirement_lower or
                task_tag in requirement_lower or
                task_info.get('description', '').lower() in requirement_lower):
                matched_tasks.append(task_info)
        
        # 如果没有直接匹配，尝试更宽泛的匹配
        if not matched_tasks:
            # 关键词映射
            keyword_mapping = {
                '文本分类': ['text-classification'],
                '图像分类': ['image-classification'],
                '语音识别': ['automatic-speech-recognition'],
                '文本生成': ['text-generation'],
                '翻译': ['translation'],
                '问答': ['question-answering'],
                '目标检测': ['object-detection'],
                '图像分割': ['image-segmentation'],
            }
            
            for keyword, tags in keyword_mapping.items():
                if keyword in requirement_lower:
                    for tag in tags:
                        if tag in all_tasks:
                            matched_tasks.append(all_tasks[tag])
        
        # 返回第一个匹配的任务
        if matched_tasks:
            logger.info(f"识别到任务类型: {matched_tasks[0]['name']}")
            return matched_tasks[0]
        
        logger.warning("未能从需求中识别出具体的任务类型")
        return None
    
    def _crawl_relevant_models(self, task_info: Dict[str, Any], 
                              top_k: int, sort: str) -> Optional[List[Dict[str, Any]]]:
        """爬取相关任务的模型"""
        try:
            logger.info(f"开始爬取任务 '{task_info['name']}' 的相关模型...")
            
            # 爬取模型列表（不获取详细信息以加快速度）
            models = self.crawler.crawl_models_by_task(
                task_tag=task_info['tag'],
                sort=sort,
                top_k=top_k
            )
            
            logger.info(f"成功爬取 {len(models)} 个模型")
            return models
            
        except Exception as e:
            logger.error(f"爬取模型失败: {e}")
            return None
    
    def _prepare_enhanced_prompt(self, requirement_analysis: str,
                               task_info: Optional[Dict[str, Any]],
                               crawled_models: Optional[List[Dict[str, Any]]],
                               additional_info: Optional[Dict[str, Any]] = None) -> str:
        """准备增强的提示词"""
        # 基础提示词
        base_prompt = self.prompt_manager.get_prompt(
            "MODEL_SEARCH",
            requirement_analysis=requirement_analysis
        )
        
        # 如果有额外信息，直接添加到提示词中
        enhanced_prompt = base_prompt
        
        # 添加自定义的任务信息（由业务层提供）
        if additional_info and "custom_task_info" in additional_info:
            enhanced_prompt += "\n" + additional_info["custom_task_info"]
        
        # 如果有爬取的模型信息，添加到提示词中
        if crawled_models:
            models_info = "\n## 最新的HuggingFace模型信息\n\n"
            
            # 获取模型的任务类型说明
            task_name = "相关模型"
            if task_info:
                task_name = task_info.get('name', '相关模型')
            
            # 获取模型来源描述（由业务层提供）
            model_source_desc = "相关模型"
            if additional_info and "model_source_description" in additional_info:
                model_source_desc = additional_info["model_source_description"]
            
            models_info += f"以下是{model_source_desc}的最新热门模型：\n\n"
            
            # 获取要显示的模型数量
            max_models_to_show = 30  # 默认值
            if additional_info and "display_model_count" in additional_info:
                max_models_to_show = additional_info.get("display_model_count", 30)
            
            for i, model in enumerate(crawled_models[:max_models_to_show], 1):
                models_info += f"{i}. **{model.get('model_id', 'Unknown')}**\n"
                if model.get('name'):
                    models_info += f"   - 名称: {model['name']}\n"
                if model.get('downloads'):
                    models_info += f"   - 下载量: {model['downloads']}\n"
                if model.get('likes'):
                    models_info += f"   - 点赞数: {model['likes']}\n"
                if model.get('tags'):
                    models_info += f"   - 标签: {', '.join(model['tags'][:5])}\n"
                if model.get('url'):
                    models_info += f"   - 链接: {model['url']}\n"
                models_info += "\n"
            
            # 添加自定义的模型选择指导（由业务层提供）
            if additional_info and "model_selection_guide" in additional_info:
                models_info += "\n" + additional_info["model_selection_guide"]
            
            enhanced_prompt += "\n" + models_info
            enhanced_prompt += "\n请在推荐模型时，优先考虑上述最新的热门模型（如果它们符合需求）。\n"
        
        # 添加自定义的注意事项（由业务层提供）
        if additional_info and "custom_notes" in additional_info:
            enhanced_prompt += "\n" + additional_info["custom_notes"]
        else:
            # 默认注意事项
            enhanced_prompt += "\n## 注意事项\n\n"
            enhanced_prompt += "1. 请准确评估模型大小和资源需求。\n"
            enhanced_prompt += "2. 请确保推荐的模型与任务类型匹配。\n"
            enhanced_prompt += "3. 请考虑模型的语言支持能力。\n"
        
        return enhanced_prompt
    
    def get_available_tasks(self) -> str:
        """获取所有可用的任务类型"""
        if self.use_crawler:
            return self.crawler.get_available_tasks()
        return "爬虫未启用，无法获取任务列表"
    
    def search_models_by_keyword(self, keyword: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """通过关键词搜索模型"""
        if not self.use_crawler:
            logger.warning("爬虫未启用，无法搜索模型")
            return []
        
        try:
            return self.crawler.search_models(keyword, top_k)
        except Exception as e:
            logger.error(f"搜索模型失败: {e}")
            return []
