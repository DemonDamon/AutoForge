"""
HuggingFace任务类型管理器
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TaskManager:
    """任务类型管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化任务管理器
        
        Args:
            config_path: 配置文件路径，默认使用内置配置
        """
        if config_path is None:
            # 使用默认配置文件
            config_path = Path(__file__).parent.parent / "data" / "hf_tasks.yaml"
        
        self.config_path = Path(config_path)
        self.tasks = {}
        self.sort_options = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 解析任务类型
        for category, tasks in config.items():
            if category == 'sort_options':
                # 解析排序选项
                self.sort_options = {opt['value']: opt for opt in tasks}
            else:
                # 解析任务类型
                for task in tasks:
                    task['category'] = category
                    self.tasks[task['tag']] = task
        
        logger.info(f"加载了 {len(self.tasks)} 个任务类型，{len(self.sort_options)} 个排序选项")
    
    def get_task_by_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """
        根据标签获取任务信息
        
        Args:
            tag: 任务标签
            
        Returns:
            任务信息字典
        """
        return self.tasks.get(tag)
    
    def get_tasks_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        获取某个类别下的所有任务
        
        Args:
            category: 任务类别
            
        Returns:
            任务列表
        """
        return [task for task in self.tasks.values() if task['category'] == category]
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务"""
        return self.tasks.copy()
    
    def get_all_categories(self) -> List[str]:
        """获取所有任务类别"""
        categories = set()
        for task in self.tasks.values():
            categories.add(task['category'])
        return sorted(list(categories))
    
    def get_sort_options(self) -> Dict[str, Dict[str, Any]]:
        """获取所有排序选项"""
        return self.sort_options.copy()
    
    def search_tasks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索任务
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的任务列表
        """
        keyword = keyword.lower()
        results = []
        
        for task in self.tasks.values():
            if (keyword in task['name'].lower() or 
                keyword in task['tag'].lower() or 
                keyword in task.get('description', '').lower()):
                results.append(task)
        
        return results
    
    def format_task_list(self) -> str:
        """格式化输出所有任务类型"""
        output = []
        
        for category in self.get_all_categories():
            output.append(f"\n## {category.replace('_', ' ').title()}")
            tasks = self.get_tasks_by_category(category)
            
            for task in tasks:
                output.append(f"  - {task['name']} ({task['tag']})")
                if task.get('description'):
                    output.append(f"    {task['description']}")
        
        output.append(f"\n## 排序选项")
        for opt in self.sort_options.values():
            output.append(f"  - {opt['name']} ({opt['value']})")
            if opt.get('description'):
                output.append(f"    {opt['description']}")
        
        return "\n".join(output) 