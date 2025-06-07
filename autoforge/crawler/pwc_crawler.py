"""
Papers with Code 爬虫模块
用于爬取 Papers with Code 网站上的论文信息和相关代码仓库
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

from bs4 import BeautifulSoup
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PapersWithCodeCrawler:
    """Papers with Code 爬虫"""
    
    def __init__(self, 
                 base_url: str = "https://paperswithcode.com",
                 output_dir: str = "outputs/pwc_papers",
                 max_workers: int = 4,
                 delay: float = 1.0,
                 max_retries: int = 3,
                 timeout: int = 60):
        """
        初始化爬虫
        
        Args:
            base_url: Papers with Code 网站基础URL
            output_dir: 输出目录
            max_workers: 并发爬取线程数
            delay: 请求间隔（秒）
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Referer': base_url,
        }
        
        # 随机用户代理
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        # 设置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        # 会话对象
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(self.headers)
    
    def _get_with_retry(self, url, params=None, **kwargs):
        """发送GET请求，带重试机制"""
        for attempt in range(self.max_retries + 1):
            try:
                # 随机使用不同的用户代理
                self.session.headers.update({
                    'User-Agent': random.choice(self.user_agents)
                })
                
                # 添加随机延迟，避免被识别为爬虫
                if attempt > 0:
                    jitter = random.uniform(0.5, 2.0)
                    sleep_time = self.delay * (2 ** attempt) * jitter
                    logger.info(f"第 {attempt} 次重试，等待 {sleep_time:.2f} 秒...")
                    time.sleep(sleep_time)
                else:
                    time.sleep(self.delay)
                
                # 发送请求
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
            
            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError) as e:
                logger.warning(f"请求超时或连接错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if attempt == self.max_retries:
                    raise
            
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if e.response.status_code == 404:
                    # 404错误不重试
                    raise
                if attempt == self.max_retries:
                    raise
            
            except Exception as e:
                logger.warning(f"未知错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if attempt == self.max_retries:
                    raise
    
    def crawl_trending_papers(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        爬取热门论文列表
        
        Args:
            top_k: 爬取前K篇论文
            
        Returns:
            论文信息列表
        """
        logger.info(f"开始爬取 Papers with Code 热门论文...")
        
        url = f"{self.base_url}/"
        
        try:
            response = self._get_with_retry(url)
            
            # 确保正确编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找热门论文部分 - 根据最新的页面结构进行查找
            papers = []
            
            # 尝试多种可能的卡片选择器
            paper_items = (
                soup.find_all('div', class_='row paper-card') or
                soup.find_all('div', class_='paper-card') or
                soup.select('.paper-card') or
                soup.select('.paper-card-container') or
                soup.select('.infinite-item')
            )
            
            logger.info(f"找到 {len(paper_items)} 个论文卡片")
            
            # 只处理前 top_k 个结果
            paper_items = paper_items[:top_k]
            
            for item in paper_items:
                paper_info = self._parse_paper_item(item)
                if paper_info:
                    papers.append(paper_info)
            
            # 保存论文列表
            self._save_paper_list("trending", papers)
            
            logger.info(f"成功爬取 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            logger.error(f"爬取热门论文失败: {e}")
            raise
    
    def crawl_papers_by_area(self, area: str, sort: str = "trending", top_k: int = 10) -> List[Dict[str, Any]]:
        """
        根据研究领域爬取论文
        
        Args:
            area: 研究领域，如 'computer-vision', 'natural-language-processing'
            sort: 排序方式，'trending' 或 'newest'
            top_k: 爬取数量
            
        Returns:
            论文信息列表
        """
        logger.info(f"开始爬取领域 '{area}' 的论文...")
        
        # 构建URL
        url = f"{self.base_url}/area/{area}"
        params = None
        if sort == "newest":
            params = {"order": "newest"}
        
        try:
            response = self._get_with_retry(url, params=params)
            
            # 确保正确编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            papers = []
            
            # 尝试多种可能的卡片选择器
            paper_items = (
                soup.find_all('div', class_='row paper-card') or
                soup.find_all('div', class_='paper-card') or
                soup.select('.paper-card') or
                soup.select('.paper-card-container') or
                soup.select('.infinite-item')
            )
            
            logger.info(f"找到 {len(paper_items)} 个论文卡片")
            
            # 只处理前 top_k 个结果
            paper_items = paper_items[:top_k]
            
            for item in paper_items:
                paper_info = self._parse_paper_item(item)
                if paper_info:
                    paper_info['area'] = area
                    papers.append(paper_info)
            
            # 保存论文列表
            self._save_paper_list(f"{area}_{sort}", papers)
            
            logger.info(f"成功爬取 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            logger.error(f"爬取领域论文失败: {e}")
            raise
    
    def crawl_paper_details(self, paper_url: str) -> Dict[str, Any]:
        """
        爬取单篇论文的详细信息
        
        Args:
            paper_url: 论文页面URL
            
        Returns:
            论文详细信息
        """
        logger.info(f"开始爬取论文详情: {paper_url}")
        
        try:
            if not paper_url.startswith('http'):
                paper_url = urljoin(self.base_url, paper_url)
            
            response = self._get_with_retry(paper_url)
            
            # 确保正确编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取论文信息
            paper_details = {
                'url': paper_url,
                'crawled_at': datetime.now().isoformat()
            }
            
            # 标题
            title_elem = soup.find('h1')
            if title_elem:
                paper_details['title'] = title_elem.text.strip()
            
            # 作者
            authors_elem = soup.find('div', class_='authors')
            if authors_elem:
                paper_details['authors'] = [a.text.strip() for a in authors_elem.find_all('a')]
            
            # 摘要
            abstract_elem = soup.find('div', class_='paper-abstract')
            if abstract_elem:
                paper_details['abstract'] = abstract_elem.text.strip()
            
            # 标签
            tags = []
            tag_elems = soup.find_all('a', class_='badge badge-secondary')
            for tag in tag_elems:
                tags.append(tag.text.strip())
            paper_details['tags'] = tags
            
            # GitHub仓库链接
            github_repos = self._extract_github_repos(soup)
            paper_details['github_repos'] = github_repos
            
            # 代码实现列表
            implementations = self._extract_implementations(soup)
            paper_details['implementations'] = implementations
            
            # 论文链接（arxiv等）
            paper_links = self._extract_paper_links(soup)
            paper_details['paper_links'] = paper_links
            
            return paper_details
            
        except Exception as e:
            logger.error(f"爬取论文详情失败: {e}")
            raise
    
    def crawl_papers_batch(self, 
                          papers: List[Dict[str, Any]], 
                          fetch_details: bool = True) -> List[Dict[str, Any]]:
        """
        批量爬取论文详情
        
        Args:
            papers: 论文列表（需包含url字段）
            fetch_details: 是否爬取详细信息
            
        Returns:
            包含详细信息的论文列表
        """
        if not fetch_details:
            return papers
        
        logger.info(f"开始批量爬取 {len(papers)} 篇论文的详细信息...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_paper = {
                executor.submit(self.crawl_paper_details, paper['url']): paper
                for paper in papers if 'url' in paper
            }
            
            detailed_papers = []
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    details = future.result()
                    # 合并基本信息和详细信息
                    paper.update(details)
                    detailed_papers.append(paper)
                except Exception as e:
                    logger.error(f"爬取论文详情失败: {e}")
                    detailed_papers.append(paper)
        
        return detailed_papers
    
    def search_papers(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        搜索论文
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            
        Returns:
            论文列表
        """
        logger.info(f"搜索论文: {query}")
        
        # 构建搜索URL
        # 例如: https://paperswithcode.com/search?q_meta=&q_type=&q=2
        url = f"{self.base_url}/search"
        params = {'q': query, 'q_meta': '', 'q_type': ''}
        
        try:
            response = self._get_with_retry(url, params=params)
            
            # 确保正确编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            papers = []
            
            # 尝试多种可能的卡片选择器
            paper_items = (
                soup.find_all('div', class_='row paper-card') or 
                soup.find_all('div', class_='paper-card') or
                soup.select('.paper-card') or
                soup.select('.paper-card-container') or
                soup.select('.infinite-item')
            )
            
            logger.info(f"搜索 '{query}' 找到 {len(paper_items)} 个论文卡片")
            
            # 只处理前 top_k 个结果
            paper_items = paper_items[:top_k]
            
            for item in paper_items:
                paper_info = self._parse_paper_item(item)
                if paper_info:
                    papers.append(paper_info)
            
            # 保存搜索结果
            self._save_paper_list(f"search_{query}", papers)
            
            return papers
            
        except Exception as e:
            logger.error(f"搜索论文失败: {e}")
            raise
    
    def _parse_paper_item(self, item) -> Optional[Dict[str, Any]]:
        """解析论文列表项"""
        try:
            paper_info = {}
            
            # 记录原始HTML便于调试
            # paper_info['_debug_html'] = str(item)
            
            # 提取标题和链接（尝试多种可能的选择器）
            title_elem = (
                item.find('h1') or 
                item.find('h2') or 
                item.find('h3') or
                item.find('a', class_='paper-card-title') or
                item.select_one('.paper-card-title') or
                item.select_one('.item-title') or
                item.select_one('h1 a') or
                item.select_one('h2 a') or
                item.select_one('h3 a')
            )
            
            if title_elem:
                # 直接从标题元素获取文本
                if hasattr(title_elem, 'text'):
                    paper_info['title'] = title_elem.text.strip()
                
                # 获取链接
                if title_elem.name == 'a':
                    link_elem = title_elem
                else:
                    link_elem = title_elem.find('a')
                
                if link_elem and link_elem.has_attr('href'):
                    paper_info['url'] = urljoin(self.base_url, link_elem.get('href', ''))
            
            # 如果没有找到标题或链接，返回None
            if 'title' not in paper_info or 'url' not in paper_info:
                return None
            
            # 作者（尝试多种可能的选择器）
            authors_elem = (
                item.find('div', class_='authors') or
                item.find('div', class_='author-section') or
                item.select_one('.authors') or
                item.select_one('.author-section')
            )
            
            if authors_elem:
                paper_info['authors'] = authors_elem.text.strip()
            
            # 星标数（尝试多种可能的选择器）
            stars_elem = (
                item.find('span', class_='stars-accumulated') or
                item.find('span', class_='badge badge-stars') or
                item.select_one('.stars-accumulated') or
                item.select_one('.stars')
            )
            
            if stars_elem:
                paper_info['stars'] = stars_elem.text.strip()
            
            # 任务标签
            tasks = []
            tasks_elem = (
                item.find('div', class_='task') or
                item.find('div', class_='tasks') or
                item.select_one('.task') or
                item.select_one('.tasks')
            )
            
            if tasks_elem:
                task_links = tasks_elem.find_all('a')
                for task in task_links:
                    tasks.append(task.text.strip())
                
                if tasks:
                    paper_info['tasks'] = tasks
            
            # 代码实现数量
            impl_count_pattern = re.compile(r'(\d+)\s+implementations?', re.I)
            
            # 方法1：从文本中查找
            for span in item.find_all('span'):
                match = impl_count_pattern.search(span.text)
                if match:
                    paper_info['implementation_count'] = int(match.group(1))
                    break
            
            # 方法2：如果没找到，尝试其他元素
            if 'implementation_count' not in paper_info:
                for div in item.find_all('div'):
                    match = impl_count_pattern.search(div.text)
                    if match:
                        paper_info['implementation_count'] = int(match.group(1))
                        break
            
            # 添加日期（如果有）
            date_elem = (
                item.find('div', class_='date') or
                item.find('span', class_='date') or
                item.select_one('.date')
            )
            
            if date_elem:
                paper_info['date'] = date_elem.text.strip()
            
            return paper_info if paper_info else None
            
        except Exception as e:
            logger.error(f"解析论文项失败: {e}")
            return None
    
    def _extract_github_repos(self, soup) -> List[Dict[str, str]]:
        """提取GitHub仓库链接"""
        repos = []
        
        # 查找所有GitHub链接
        github_links = soup.find_all('a', href=re.compile(r'github\.com/[\w-]+/[\w-]+'))
        
        for link in github_links:
            repo_url = link.get('href', '')
            if repo_url:
                # 提取仓库信息
                match = re.search(r'github\.com/([\w-]+)/([\w-]+)', repo_url)
                if match:
                    owner, repo_name = match.groups()
                    
                    repo_info = {
                        'url': repo_url,
                        'owner': owner,
                        'repo_name': repo_name,
                        'full_name': f"{owner}/{repo_name}"
                    }
                    
                    # 获取星标数等信息（如果页面上有）
                    parent = link.parent
                    if parent:
                        stars_elem = parent.find('span', class_='stars')
                        if stars_elem:
                            repo_info['stars'] = stars_elem.text.strip()
                    
                    repos.append(repo_info)
        
        # 去重
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo['full_name'] not in seen:
                seen.add(repo['full_name'])
                unique_repos.append(repo)
        
        return unique_repos
    
    def _extract_implementations(self, soup) -> List[Dict[str, Any]]:
        """提取代码实现列表"""
        implementations = []
        
        # 查找实现部分（尝试多种可能的选择器）
        impl_section = (
            soup.find('div', id='implementations') or 
            soup.find('div', class_='implementations') or
            soup.select_one('#implementations') or
            soup.select_one('.implementations')
        )
        
        if not impl_section:
            return implementations
        
        # 尝试多种可能的实现项选择器
        impl_items = (
            impl_section.find_all('div', class_='row') or
            impl_section.find_all('div', class_='implementation-card') or
            impl_section.select('.implementation-card') or
            impl_section.select('.row')
        )
        
        for item in impl_items:
            impl_info = {}
            
            # 框架信息
            framework_elem = (
                item.find('span', class_='framework-badge') or
                item.select_one('.framework-badge') or
                item.select_one('.framework')
            )
            
            if framework_elem:
                impl_info['framework'] = framework_elem.text.strip()
            
            # GitHub链接
            github_link = item.find('a', href=re.compile(r'github\.com'))
            if github_link:
                impl_info['github_url'] = github_link.get('href', '')
                impl_info['title'] = github_link.text.strip()
            
            # 星标数
            stars_elem = (
                item.find('span', class_='stars') or
                item.select_one('.stars')
            )
            
            if stars_elem:
                impl_info['stars'] = stars_elem.text.strip()
            
            if impl_info:
                implementations.append(impl_info)
        
        return implementations
    
    def _extract_paper_links(self, soup) -> Dict[str, str]:
        """提取论文链接（arxiv等）"""
        links = {}
        
        # ArXiv链接
        arxiv_link = soup.find('a', href=re.compile(r'arxiv\.org'))
        if arxiv_link:
            links['arxiv'] = arxiv_link.get('href', '')
        
        # PDF链接
        pdf_link = soup.find('a', text=re.compile(r'PDF', re.I))
        if pdf_link:
            links['pdf'] = pdf_link.get('href', '')
        
        # 其他论文链接（尝试多种可能的选择器）
        paper_section = (
            soup.find('div', class_='paper-links') or
            soup.find('div', class_='paper-resources') or
            soup.select_one('.paper-links') or
            soup.select_one('.paper-resources')
        )
        
        if paper_section:
            for link in paper_section.find_all('a'):
                text = link.text.strip().lower()
                href = link.get('href', '')
                if href and text:
                    links[text] = href
        
        return links
    
    def _save_paper_list(self, category: str, papers: List[Dict[str, Any]]):
        """保存论文列表"""
        # 创建分类目录
        category_dir = self.output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"papers_{timestamp}.json"
        filepath = category_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'category': category,
                'count': len(papers),
                'crawled_at': datetime.now().isoformat(),
                'papers': papers
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"论文列表已保存到: {filepath}")
    
    def get_research_areas(self) -> List[str]:
        """获取所有研究领域"""
        return [
            'computer-vision',
            'natural-language-processing',
            'reinforcement-learning',
            'machine-learning',
            'audio',
            'robotics',
            'graphs',
            'time-series',
            'adversarial',
            'knowledge-base',
            'medical',
            'speech',
            'reasoning',
            'music',
            'playing-games'
        ] 