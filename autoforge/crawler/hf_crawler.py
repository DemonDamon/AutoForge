"""
HuggingFace模型爬虫
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import yaml

from .task_manager import TaskManager
from .parsers import HFModelListParser, HFModelCardParser

logger = logging.getLogger(__name__)


class HuggingFaceCrawler:
    """HuggingFace模型爬虫"""
    
    def __init__(self, 
                 base_url: str = "https://hf-mirror.com",
                 output_dir: str = "outputs/hf_models",
                 max_workers: int = 4,
                 delay: float = 1.0):
        """
        初始化爬虫
        
        Args:
            base_url: HuggingFace镜像站基础URL
            output_dir: 输出目录
            max_workers: 并发爬取线程数
            delay: 请求间隔（秒）
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.delay = delay
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务管理器
        self.task_manager = TaskManager()
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 会话对象
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def crawl_models_by_task(self, 
                            task_tag: str, 
                            sort: str = "trending",
                            top_k: int = 10) -> List[Dict[str, Any]]:
        """
        根据任务类型爬取模型列表
        
        Args:
            task_tag: 任务标签，如 'audio-text-to-text'
            sort: 排序方式，如 'trending', 'downloads', 'likes'
            top_k: 爬取前K个模型
            
        Returns:
            模型信息列表
        """
        # 验证任务标签
        task_info = self.task_manager.get_task_by_tag(task_tag)
        if not task_info:
            raise ValueError(f"未知的任务标签: {task_tag}")
        
        logger.info(f"开始爬取任务 '{task_info['name']}' 的模型列表...")
        
        # 构建URL
        url = f"{self.base_url}/models"
        params = {
            'pipeline_tag': task_tag,
            'sort': sort
        }
        
        try:
            # 发送请求
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # 使用解析器解析页面
            models = HFModelListParser.parse_model_list(response.text, top_k)
            
            # 补充完整URL
            for model in models:
                if 'url' in model and not model['url'].startswith('http'):
                    model['url'] = urljoin(self.base_url, model['url'])
            
            # 保存模型列表
            self._save_model_list(task_tag, sort, models)
            
            logger.info(f"成功爬取 {len(models)} 个模型")
            
            return models
            
        except Exception as e:
            logger.error(f"爬取模型列表失败: {e}")
            raise
    
    def crawl_model_card(self, model_id: str) -> Dict[str, Any]:
        """
        爬取单个模型的ModelCard
        
        Args:
            model_id: 模型ID，格式为 'username/model-name'
            
        Returns:
            模型详细信息
        """
        logger.info(f"开始爬取模型 '{model_id}' 的ModelCard...")
        
        # 构建URL
        url = f"{self.base_url}/{model_id}"
        
        try:
            # 添加延迟
            time.sleep(self.delay)
            
            # 发送请求
            response = self.session.get(url)
            response.raise_for_status()
            
            # 使用解析器解析页面
            model_info = HFModelCardParser.parse_model_card(response.text, model_id)
            model_info['url'] = url
            model_info['crawled_at'] = datetime.now().isoformat()
            
            # 保存ModelCard
            self._save_model_card(model_id, model_info)
            
            logger.info(f"成功爬取模型 '{model_id}' 的信息")
            
            return model_info
            
        except Exception as e:
            logger.error(f"爬取ModelCard失败: {e}")
            raise
    
    def crawl_models_batch(self, 
                          task_tag: str,
                          sort: str = "trending",
                          top_k: int = 10,
                          fetch_details: bool = True) -> List[Dict[str, Any]]:
        """
        批量爬取模型（包括列表和详细信息）
        
        Args:
            task_tag: 任务标签
            sort: 排序方式
            top_k: 爬取数量
            fetch_details: 是否爬取详细信息
            
        Returns:
            完整的模型信息列表
        """
        # 首先爬取模型列表
        models = self.crawl_models_by_task(task_tag, sort, top_k)
        
        if not fetch_details:
            return models
        
        # 并发爬取模型详情
        logger.info(f"开始批量爬取 {len(models)} 个模型的详细信息...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_model = {
                executor.submit(self.crawl_model_card, model['model_id']): model
                for model in models if 'model_id' in model
            }
            
            detailed_models = []
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    detail = future.result()
                    # 合并列表信息和详细信息
                    model.update(detail)
                    detailed_models.append(model)
                except Exception as e:
                    logger.error(f"爬取模型 '{model.get('model_id')}' 详情失败: {e}")
                    detailed_models.append(model)
        
        # 保存完整的批量爬取结果
        self._save_batch_result(task_tag, sort, detailed_models)
        
        return detailed_models
    
    def _save_model_list(self, task_tag: str, sort: str, models: List[Dict[str, Any]]):
        """保存模型列表"""
        # 创建任务目录
        task_dir = self.output_dir / task_tag
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为JSON
        filename = f"models_{sort}_top{len(models)}.json"
        filepath = task_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'task': task_tag,
                'sort': sort,
                'count': len(models),
                'crawled_at': datetime.now().isoformat(),
                'models': models
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"模型列表已保存到: {filepath}")
    
    def _save_model_card(self, model_id: str, model_info: Dict[str, Any]):
        """保存ModelCard"""
        # 创建模型目录
        model_dir = self.output_dir / "model_cards" / model_id.replace('/', '_')
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存元信息为JSON
        meta_file = model_dir / "metadata.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        
        # 保存ModelCard为Markdown
        if 'model_card' in model_info:
            card_file = model_dir / "README.md"
            with open(card_file, 'w', encoding='utf-8') as f:
                f.write(f"# {model_id}\n\n")
                f.write(f"Source: {model_info.get('url', 'N/A')}\n\n")
                f.write(f"Crawled at: {model_info.get('crawled_at', 'N/A')}\n\n")
                f.write("---\n\n")
                f.write(model_info['model_card'])
        
        logger.info(f"ModelCard已保存到: {model_dir}")
    
    def _save_batch_result(self, task_tag: str, sort: str, models: List[Dict[str, Any]]):
        """保存批量爬取结果"""
        # 创建任务目录
        task_dir = self.output_dir / task_tag
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存完整结果
        filename = f"models_{sort}_top{len(models)}_detailed.json"
        filepath = task_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'task': task_tag,
                'sort': sort,
                'count': len(models),
                'crawled_at': datetime.now().isoformat(),
                'models': models
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"批量爬取结果已保存到: {filepath}")
    
    def search_models(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        搜索模型
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            
        Returns:
            模型列表
        """
        url = f"{self.base_url}/models"
        params = {'search': query}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            models = HFModelListParser.parse_model_list(response.text, top_k)
            
            # 补充完整URL
            for model in models:
                if 'url' in model and not model['url'].startswith('http'):
                    model['url'] = urljoin(self.base_url, model['url'])
            
            return models
            
        except Exception as e:
            logger.error(f"搜索模型失败: {e}")
            raise
    
    def get_available_tasks(self) -> str:
        """获取所有可用的任务类型"""
        return self.task_manager.format_task_list()
    
    def list_crawled_models(self) -> Dict[str, List[str]]:
        """列出已爬取的模型"""
        crawled = {}
        
        # 扫描输出目录
        for task_dir in self.output_dir.iterdir():
            if task_dir.is_dir() and task_dir.name != "model_cards":
                crawled[task_dir.name] = []
                
                # 列出该任务下的所有JSON文件
                for json_file in task_dir.glob("*.json"):
                    crawled[task_dir.name].append(json_file.name)
        
        return crawled 