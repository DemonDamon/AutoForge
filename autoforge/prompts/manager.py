"""
提示词管理器
"""

import re
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

from .templates import PromptTemplates

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器"""
    
    def __init__(self, custom_prompts_dir: Optional[str] = None):
        """
        初始化提示词管理器
        
        Args:
            custom_prompts_dir: 自定义提示词目录路径
        """
        self.templates = PromptTemplates()
        self.custom_prompts = {}
        
        if custom_prompts_dir:
            self.load_custom_prompts(custom_prompts_dir)
    
    def load_custom_prompts(self, prompts_dir: str):
        """加载自定义提示词"""
        prompts_path = Path(prompts_dir)
        
        if not prompts_path.exists():
            logger.warning(f"自定义提示词目录不存在: {prompts_dir}")
            return
        
        # 加载JSON格式的提示词
        json_files = prompts_path.glob("*.json")
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)
                    self.custom_prompts.update(prompts_data)
                logger.info(f"加载自定义提示词: {json_file}")
            except Exception as e:
                logger.error(f"加载提示词文件失败 {json_file}: {e}")
        
        # 加载文本格式的提示词
        txt_files = prompts_path.glob("*.txt")
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    prompt_name = txt_file.stem
                    self.custom_prompts[prompt_name] = f.read()
                logger.info(f"加载自定义提示词: {txt_file}")
            except Exception as e:
                logger.error(f"加载提示词文件失败 {txt_file}: {e}")
    
    def get_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        获取并格式化提示词
        
        Args:
            prompt_name: 提示词名称
            **kwargs: 要替换的变量
            
        Returns:
            格式化后的提示词
        """
        # 优先使用自定义提示词
        if prompt_name in self.custom_prompts:
            template = self.custom_prompts[prompt_name]
        # 否则使用内置提示词
        elif hasattr(self.templates, prompt_name):
            template = getattr(self.templates, prompt_name)
        else:
            raise ValueError(f"未找到提示词: {prompt_name}")
        
        # 格式化提示词
        return self.format_prompt(template, **kwargs)
    
    def format_prompt(self, template: str, **kwargs) -> str:
        """
        格式化提示词模板
        
        Args:
            template: 提示词模板
            **kwargs: 要替换的变量
            
        Returns:
            格式化后的提示词
        """
        # 使用安全的字符串格式化
        try:
            # 首先尝试使用format方法
            formatted = template.format(**kwargs)
        except KeyError as e:
            # 如果有缺失的变量，记录警告并返回部分格式化的结果
            logger.warning(f"提示词格式化时缺少变量: {e}")
            # 使用正则表达式进行部分替换
            formatted = template
            for key, value in kwargs.items():
                pattern = r'\{' + key + r'\}'
                formatted = re.sub(pattern, str(value), formatted)
        
        return formatted
    
    def save_custom_prompt(self, name: str, content: str, prompts_dir: str):
        """
        保存自定义提示词
        
        Args:
            name: 提示词名称
            content: 提示词内容
            prompts_dir: 保存目录
        """
        prompts_path = Path(prompts_dir)
        prompts_path.mkdir(parents=True, exist_ok=True)
        
        # 保存为文本文件
        file_path = prompts_path / f"{name}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新内存中的提示词
        self.custom_prompts[name] = content
        logger.info(f"保存自定义提示词: {file_path}")
    
    def list_prompts(self) -> Dict[str, str]:
        """
        列出所有可用的提示词
        
        Returns:
            提示词名称和描述的字典
        """
        prompts = {}
        
        # 内置提示词
        for attr_name in dir(self.templates):
            if not attr_name.startswith('_') and isinstance(getattr(self.templates, attr_name), str):
                # 提取提示词的第一行作为描述
                prompt_content = getattr(self.templates, attr_name)
                first_line = prompt_content.split('\n')[0]
                prompts[attr_name] = f"[内置] {first_line[:50]}..."
        
        # 自定义提示词
        for name, content in self.custom_prompts.items():
            first_line = content.split('\n')[0]
            prompts[name] = f"[自定义] {first_line[:50]}..."
        
        return prompts
    
    def validate_prompt(self, prompt_name: str, required_vars: list) -> bool:
        """
        验证提示词是否包含所需的变量
        
        Args:
            prompt_name: 提示词名称
            required_vars: 必需的变量列表
            
        Returns:
            是否验证通过
        """
        try:
            template = self.get_prompt(prompt_name)
            
            # 查找模板中的所有变量
            pattern = r'\{(\w+)\}'
            found_vars = re.findall(pattern, template)
            
            # 检查是否包含所有必需的变量
            missing_vars = set(required_vars) - set(found_vars)
            
            if missing_vars:
                logger.warning(f"提示词 {prompt_name} 缺少变量: {missing_vars}")
                return False
            
            return True
            
        except ValueError:
            logger.error(f"提示词 {prompt_name} 不存在")
            return False 