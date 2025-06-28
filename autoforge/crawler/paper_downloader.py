"""
论文下载器模块
支持从arxiv、PDF链接等多种来源下载论文
"""

import os
import re
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, unquote
import random

logger = logging.getLogger(__name__)


class PaperDownloader:
    """论文下载器"""
    
    def __init__(self, 
                 output_dir: str = "outputs/papers",
                 max_retries: int = 3,
                 delay: float = 1.0,
                 timeout: int = 60):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录
            max_retries: 最大重试次数
            delay: 请求间隔（秒）
            timeout: 请求超时时间（秒）
        """
        self.output_dir = Path(output_dir)
        self.max_retries = max_retries
        self.delay = delay
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
        }
        
        # 随机用户代理
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        # 会话对象
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def download_paper(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        下载论文
        
        Args:
            url: 论文URL
            filename: 保存的文件名（可选），如果不提供将自动生成
            
        Returns:
            论文保存路径，下载失败返回None
        """
        # 根据URL类型选择下载方法
        if 'arxiv.org' in url:
            return self.download_from_arxiv(url, filename)
        else:
            return self.download_from_url(url, filename)
    
    def download_from_url(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        从URL下载论文
        
        Args:
            url: 论文URL
            filename: 保存的文件名（可选）
            
        Returns:
            论文保存路径，下载失败返回None
        """
        logger.info(f"开始从URL下载论文: {url}")
        
        # 如果未提供文件名，从URL生成
        if not filename:
            filename = self._generate_filename_from_url(url)
        
        # 确保文件名有.pdf后缀
        if not filename.lower().endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # 构建保存路径
        save_path = self.output_dir / filename
        
        # 如果文件已存在，直接返回路径
        if save_path.exists():
            logger.info(f"论文已存在，跳过下载: {save_path}")
            return str(save_path)
        
        # 下载文件
        for attempt in range(self.max_retries + 1):
            try:
                # 随机使用不同的用户代理
                self.session.headers.update({
                    'User-Agent': random.choice(self.user_agents)
                })
                
                # 添加随机延迟
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
                    timeout=self.timeout,
                    stream=True  # 流式下载大文件
                )
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' not in content_type and 'octet-stream' not in content_type:
                    logger.warning(f"下载的内容可能不是PDF，Content-Type: {content_type}")
                
                # 保存文件
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"论文下载成功: {save_path}")
                return str(save_path)
                
            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError) as e:
                logger.warning(f"请求超时或连接错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"下载失败，已达最大重试次数: {url}")
                    return None
            
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if e.response.status_code == 404:
                    # 404错误不重试
                    logger.error(f"论文不存在 (404): {url}")
                    return None
                if attempt == self.max_retries:
                    logger.error(f"下载失败，已达最大重试次数: {url}")
                    return None
            
            except Exception as e:
                logger.warning(f"未知错误 (尝试 {attempt+1}/{self.max_retries+1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"下载失败，已达最大重试次数: {url}")
                    return None
        
        return None
    
    def download_from_arxiv(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        从arXiv下载论文
        
        Args:
            url: arXiv URL或论文ID
            filename: 保存的文件名（可选）
            
        Returns:
            论文保存路径，下载失败返回None
        """
        logger.info(f"开始从arXiv下载论文: {url}")
        
        # 提取arxiv ID
        arxiv_id = self._extract_arxiv_id(url)
        if not arxiv_id:
            logger.error(f"无法提取arXiv ID: {url}")
            return None
        
        # 如果未提供文件名，使用arxiv ID
        if not filename:
            filename = f"arxiv_{arxiv_id.replace('.', '_').replace('/', '_')}.pdf"
        
        # 确保文件名有.pdf后缀
        if not filename.lower().endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # 构建保存路径
        save_path = self.output_dir / filename
        
        # 如果文件已存在，直接返回路径
        if save_path.exists():
            logger.info(f"论文已存在，跳过下载: {save_path}")
            return str(save_path)
        
        # 构建下载URL
        download_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # 下载文件
        return self.download_from_url(download_url, filename)
    
    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """提取arXiv ID"""
        # 处理完整URL
        if url.startswith(('http://', 'https://')):
            # 尝试不同的URL模式
            patterns = [
                r'arxiv\.org/abs/([0-9v\.]+)',
                r'arxiv\.org/pdf/([0-9v\.]+)',
                r'arxiv\.org/ps/([0-9v\.]+)',
                r'arxiv\.org/e-print/([0-9v\.]+)',
                r'arxiv\.org/format/([0-9v\.]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        # 处理纯ID格式（如1234.5678）
        elif re.match(r'^[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?$', url):
            return url
        
        # 处理旧版ID格式（如quant-ph/9901123）
        elif re.match(r'^[a-z\-]+/[0-9]{7}(v[0-9]+)?$', url):
            return url
        
        return None
    
    def _generate_filename_from_url(self, url: str) -> str:
        """从URL生成文件名"""
        # 解析URL
        parsed_url = urlparse(url)
        
        # 尝试从路径中提取文件名
        path = parsed_url.path
        filename = os.path.basename(path)
        
        # 如果文件名为空或太短，使用URL的哈希值
        if not filename or len(filename) < 5:
            # 使用URL的最后部分
            parts = [p for p in path.split('/') if p]
            if parts:
                filename = parts[-1]
            else:
                # 使用域名+时间戳
                filename = f"{parsed_url.netloc.replace('.', '_')}_{int(time.time())}"
        
        # 解码URL编码的字符
        filename = unquote(filename)
        
        # 移除非法字符
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # 确保文件名不超过255个字符
        if len(filename) > 250:
            name, ext = os.path.splitext(filename)
            filename = name[:250-len(ext)] + ext
        
        return filename
    
    def download_papers_batch(self, urls: List[str]) -> Dict[str, Optional[str]]:
        """
        批量下载论文
        
        Args:
            urls: 论文URL列表
            
        Returns:
            字典，键为URL，值为保存路径
        """
        logger.info(f"开始批量下载 {len(urls)} 篇论文...")
        
        results = {}
        for url in urls:
            try:
                save_path = self.download_paper(url)
                results[url] = save_path
            except Exception as e:
                logger.error(f"下载论文失败: {url}, 错误: {e}")
                results[url] = None
        
        success_count = sum(1 for path in results.values() if path)
        logger.info(f"批量下载完成，成功: {success_count}/{len(urls)}")
        
        return results 