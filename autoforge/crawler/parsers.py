"""
HuggingFace页面解析器
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HFModelListParser:
    """HuggingFace模型列表页面解析器"""
    
    @staticmethod
    def parse_model_list(html_content: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        解析模型列表页面
        
        Args:
            html_content: HTML内容
            top_k: 提取前K个模型
            
        Returns:
            模型信息列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        models = []
        
        # 方法1: 查找article标签（通常包含模型卡片）
        articles = soup.find_all('article', limit=top_k)
        
        if articles:
            for article in articles:
                model_info = HFModelListParser._parse_article_card(article)
                if model_info and model_info.get('model_id'):
                    models.append(model_info)
        
        # 方法2: 如果article不存在，尝试其他结构
        if not models:
            # 查找包含模型链接的div
            model_divs = soup.find_all('div', class_=re.compile(r'model|card'), limit=top_k*2)
            
            for div in model_divs:
                model_info = HFModelListParser._parse_div_card(div)
                if model_info and model_info.get('model_id'):
                    models.append(model_info)
                    if len(models) >= top_k:
                        break
        
        # 方法3: 查找直接的链接列表
        if not models:
            links = soup.find_all('a', href=re.compile(r'^/[\w-]+/[\w.-]+$'), limit=top_k*2)
            
            for link in links:
                model_info = HFModelListParser._parse_link(link)
                if model_info and model_info.get('model_id'):
                    models.append(model_info)
                    if len(models) >= top_k:
                        break
        
        logger.info(f"解析出 {len(models)} 个模型")
        return models[:top_k]
    
    @staticmethod
    def _parse_article_card(article) -> Dict[str, Any]:
        """解析article形式的模型卡片"""
        model_info = {}
        
        try:
            # 查找模型链接
            link = article.find('a', href=re.compile(r'^/[\w-]+/[\w.-]+$'))
            if link:
                model_id = link['href'].strip('/')
                model_info['model_id'] = model_id
                model_info['name'] = link.text.strip() or model_id
                model_info['url'] = link['href']
            
            # 查找统计信息
            # 下载量
            download_elem = article.find(text=re.compile(r'\d+\.?\d*[kKmM]?'))
            if download_elem and any(word in str(download_elem.parent) for word in ['download', 'Download', '下载']):
                model_info['downloads'] = download_elem.strip()
            
            # 点赞数
            like_elem = article.find(text=re.compile(r'♥|❤|like|Like'))
            if like_elem:
                like_text = like_elem.parent.text
                match = re.search(r'(\d+\.?\d*[kKmM]?)', like_text)
                if match:
                    model_info['likes'] = match.group(1)
            
            # 更新时间
            time_elem = article.find(['time', 'span'], text=re.compile(r'ago|前|days?|hours?|minutes?'))
            if time_elem:
                model_info['updated'] = time_elem.text.strip()
            
            # 任务标签
            tags = []
            tag_elems = article.find_all(['span', 'div'], class_=re.compile(r'tag|label|badge'))
            for tag in tag_elems:
                tag_text = tag.text.strip()
                if tag_text and len(tag_text) < 50:  # 避免过长的文本
                    tags.append(tag_text)
            if tags:
                model_info['tags'] = tags
            
        except Exception as e:
            logger.debug(f"解析article卡片失败: {e}")
        
        return model_info
    
    @staticmethod
    def _parse_div_card(div) -> Dict[str, Any]:
        """解析div形式的模型卡片"""
        model_info = {}
        
        try:
            # 查找模型链接
            link = div.find('a', href=re.compile(r'^/[\w-]+/[\w.-]+$'))
            if link:
                model_id = link['href'].strip('/')
                model_info['model_id'] = model_id
                
                # 尝试从链接文本或其他地方获取名称
                model_info['name'] = link.text.strip() or model_id
                model_info['url'] = link['href']
                
                # 在div中查找其他信息
                text_content = div.get_text(' ', strip=True)
                
                # 提取数字信息（可能是下载量或点赞数）
                numbers = re.findall(r'(\d+\.?\d*[kKmM]?)', text_content)
                if numbers:
                    if 'download' in text_content.lower():
                        model_info['downloads'] = numbers[0]
                    elif 'like' in text_content.lower() or '♥' in text_content:
                        model_info['likes'] = numbers[0]
            
        except Exception as e:
            logger.debug(f"解析div卡片失败: {e}")
        
        return model_info
    
    @staticmethod
    def _parse_link(link) -> Dict[str, Any]:
        """从单个链接解析模型信息"""
        model_info = {}
        
        try:
            href = link.get('href', '')
            if re.match(r'^/[\w-]+/[\w.-]+$', href):
                model_id = href.strip('/')
                model_info['model_id'] = model_id
                model_info['name'] = link.text.strip() or model_id
                model_info['url'] = href
                
                # 尝试从父元素获取更多信息
                parent = link.parent
                if parent:
                    parent_text = parent.get_text(' ', strip=True)
                    
                    # 提取数字信息
                    numbers = re.findall(r'(\d+\.?\d*[kKmM]?)', parent_text)
                    if numbers:
                        model_info['stats'] = numbers
        
        except Exception as e:
            logger.debug(f"解析链接失败: {e}")
        
        return model_info


class HFModelCardParser:
    """HuggingFace ModelCard页面解析器"""
    
    @staticmethod
    def parse_model_card(html_content: str, model_id: str) -> Dict[str, Any]:
        """
        解析ModelCard页面
        
        Args:
            html_content: HTML内容
            model_id: 模型ID
            
        Returns:
            模型详细信息
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        model_info = {
            'model_id': model_id
        }
        
        # 提取ModelCard内容
        model_card_content = HFModelCardParser._extract_model_card(soup)
        if model_card_content:
            model_info['model_card'] = model_card_content
        
        # 提取元数据
        metadata = HFModelCardParser._extract_metadata(soup)
        if metadata:
            model_info['metadata'] = metadata
        
        # 提取文件列表
        files = HFModelCardParser._extract_files(soup)
        if files:
            model_info['files'] = files
        
        # 提取统计信息
        stats = HFModelCardParser._extract_stats(soup)
        if stats:
            model_info['stats'] = stats
        
        return model_info
    
    @staticmethod
    def _extract_model_card(soup) -> Optional[str]:
        """提取ModelCard内容"""
        # 方法1: 查找markdown内容区域
        card_elem = soup.find(['div', 'section'], class_=re.compile(r'model-card|readme|markdown'))
        if card_elem:
            return card_elem.get_text('\n', strip=True)
        
        # 方法2: 查找包含README内容的元素
        readme_elem = soup.find(text=re.compile(r'Model Card|README', re.I))
        if readme_elem:
            parent = readme_elem.find_parent(['div', 'section'])
            if parent:
                return parent.get_text('\n', strip=True)
        
        # 方法3: 查找主要内容区域
        main_content = soup.find(['main', 'div'], class_=re.compile(r'content|main'))
        if main_content:
            # 移除导航、侧边栏等
            for elem in main_content.find_all(['nav', 'aside', 'header', 'footer']):
                elem.decompose()
            return main_content.get_text('\n', strip=True)
        
        return None
    
    @staticmethod
    def _extract_metadata(soup) -> Dict[str, Any]:
        """提取模型元数据"""
        metadata = {}
        
        # 查找包含元数据的区域
        meta_sections = soup.find_all(['div', 'section'], class_=re.compile(r'meta|info|detail'))
        
        for section in meta_sections:
            # 提取键值对
            items = section.find_all(['div', 'span', 'li'])
            for item in items:
                text = item.get_text(' ', strip=True)
                # 尝试解析 "key: value" 格式
                if ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace(' ', '_')
                        value = parts[1].strip()
                        if key and value:
                            metadata[key] = value
        
        # 特定元数据提取
        # License
        license_elem = soup.find(text=re.compile(r'License|许可', re.I))
        if license_elem:
            license_text = license_elem.find_parent().get_text(strip=True)
            match = re.search(r'(MIT|Apache|GPL|BSD|CC[\w-]+)', license_text, re.I)
            if match:
                metadata['license'] = match.group(1)
        
        # Language
        lang_elem = soup.find(text=re.compile(r'Language|语言', re.I))
        if lang_elem:
            lang_text = lang_elem.find_parent().get_text(strip=True)
            metadata['language'] = lang_text
        
        return metadata
    
    @staticmethod
    def _extract_files(soup) -> List[Dict[str, str]]:
        """提取模型文件列表"""
        files = []
        
        # 查找文件列表区域
        files_section = soup.find(['div', 'section'], class_=re.compile(r'files?|models?'))
        
        if files_section:
            # 查找文件链接
            file_links = files_section.find_all('a', href=re.compile(r'\.(bin|pt|pth|h5|onnx|safetensors|json|txt)'))
            
            for link in file_links:
                file_info = {
                    'name': link.text.strip(),
                    'url': link['href']
                }
                
                # 尝试获取文件大小
                size_elem = link.find_next(text=re.compile(r'\d+\.?\d*\s*(B|KB|MB|GB)'))
                if size_elem:
                    file_info['size'] = size_elem.strip()
                
                files.append(file_info)
        
        return files
    
    @staticmethod
    def _extract_stats(soup) -> Dict[str, Any]:
        """提取统计信息"""
        stats = {}
        
        # 下载量
        download_elem = soup.find(text=re.compile(r'download|下载', re.I))
        if download_elem:
            parent = download_elem.find_parent()
            if parent:
                match = re.search(r'(\d+\.?\d*[kKmM]?)', parent.get_text())
                if match:
                    stats['downloads'] = match.group(1)
        
        # 点赞数
        like_elem = soup.find(text=re.compile(r'like|赞|♥|❤', re.I))
        if like_elem:
            parent = like_elem.find_parent()
            if parent:
                match = re.search(r'(\d+\.?\d*[kKmM]?)', parent.get_text())
                if match:
                    stats['likes'] = match.group(1)
        
        return stats 