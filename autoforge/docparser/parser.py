"""
多模态文档解析器主类
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from .converters import (
    BaseConverter,
    PDFConverter,
    WordConverter,
    ExcelConverter,
    ImageConverter,
    MarkdownConverter
)

logger = logging.getLogger(__name__)


class MultiModalDocParser:
    """多模态文档解析器"""
    
    def __init__(self, 
                 use_multimodal: bool = True,
                 multimodal_api_key: Optional[str] = None,
                 max_workers: int = 4):
        """
        初始化解析器
        
        Args:
            use_multimodal: 是否使用多模态模型（用于图片分析）
            multimodal_api_key: 多模态模型API密钥
            max_workers: 并行处理的最大线程数
        """
        self.use_multimodal = use_multimodal
        self.multimodal_api_key = multimodal_api_key
        self.max_workers = max_workers
        
        # 初始化转换器
        self.converters: List[BaseConverter] = []
        self._init_converters()
    
    def _init_converters(self):
        """初始化所有可用的转换器"""
        # PDF转换器
        try:
            self.converters.append(PDFConverter())
            logger.info("PDF转换器已加载")
        except ImportError as e:
            logger.warning(f"PDF转换器未能加载: {e}")
        
        # Word转换器
        try:
            self.converters.append(WordConverter())
            logger.info("Word转换器已加载")
        except ImportError as e:
            logger.warning(f"Word转换器未能加载: {e}")
        
        # Excel转换器
        try:
            self.converters.append(ExcelConverter())
            logger.info("Excel转换器已加载")
        except ImportError as e:
            logger.warning(f"Excel转换器未能加载: {e}")
        
        # 图片转换器
        try:
            self.converters.append(ImageConverter(
                use_multimodal=self.use_multimodal,
                multimodal_api_key=self.multimodal_api_key
            ))
            logger.info("图片转换器已加载")
        except ImportError as e:
            logger.warning(f"图片转换器未能加载: {e}")
        
        # Markdown转换器（始终可用）
        self.converters.append(MarkdownConverter())
        logger.info("Markdown转换器已加载")
    
    def parse_file(self, file_path: Union[str, Path]) -> Dict[str, str]:
        """
        解析单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含解析结果的字典
        """
        file_path = str(file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 查找合适的转换器
        converter = None
        for conv in self.converters:
            if conv.can_convert(file_path):
                converter = conv
                break
        
        if converter is None:
            logger.warning(f"没有找到适合的转换器: {file_path}")
            return {
                "file_path": file_path,
                "status": "unsupported",
                "content": "",
                "error": "不支持的文件格式"
            }
        
        try:
            content = converter.convert(file_path)
            return {
                "file_path": file_path,
                "status": "success",
                "content": content,
                "converter": converter.__class__.__name__
            }
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return {
                "file_path": file_path,
                "status": "error",
                "content": "",
                "error": str(e)
            }
    
    def parse_directory(self, 
                       directory_path: Union[str, Path],
                       recursive: bool = True,
                       file_extensions: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        解析目录下的所有文件
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归搜索子目录
            file_extensions: 要处理的文件扩展名列表（None表示处理所有支持的格式）
            
        Returns:
            解析结果列表
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        # 收集所有文件
        files_to_process = []
        
        if recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._should_process_file(file_path, file_extensions):
                        files_to_process.append(file_path)
        else:
            for file_path in directory_path.iterdir():
                if file_path.is_file() and self._should_process_file(str(file_path), file_extensions):
                    files_to_process.append(str(file_path))
        
        # 并行处理文件
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.parse_file, file_path): file_path 
                             for file_path in files_to_process}
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"成功解析: {file_path}")
                except Exception as e:
                    logger.error(f"处理文件时出错 {file_path}: {e}")
                    results.append({
                        "file_path": file_path,
                        "status": "error",
                        "content": "",
                        "error": str(e)
                    })
        
        return results
    
    def _should_process_file(self, file_path: str, file_extensions: Optional[List[str]]) -> bool:
        """检查是否应该处理该文件"""
        if file_extensions:
            # 检查文件扩展名是否在指定列表中
            return any(file_path.lower().endswith(ext.lower()) for ext in file_extensions)
        else:
            # 检查是否有转换器能处理该文件
            return any(conv.can_convert(file_path) for conv in self.converters)
    
    def merge_results(self, results: List[Dict[str, str]], output_path: Optional[str] = None) -> str:
        """
        合并所有解析结果为一个Markdown文档
        
        Args:
            results: 解析结果列表
            output_path: 输出文件路径（可选）
            
        Returns:
            合并后的Markdown内容
        """
        merged_content = ["# 多模态文档解析结果\n"]
        
        # 统计信息
        total_files = len(results)
        success_files = sum(1 for r in results if r["status"] == "success")
        error_files = sum(1 for r in results if r["status"] == "error")
        unsupported_files = sum(1 for r in results if r["status"] == "unsupported")
        
        merged_content.append(f"## 解析统计\n")
        merged_content.append(f"- 总文件数: {total_files}")
        merged_content.append(f"- 成功解析: {success_files}")
        merged_content.append(f"- 解析失败: {error_files}")
        merged_content.append(f"- 不支持格式: {unsupported_files}\n")
        
        # 成功解析的文件
        if success_files > 0:
            merged_content.append("## 成功解析的文档\n")
            for result in results:
                if result["status"] == "success":
                    merged_content.append(f"### 文件: {result['file_path']}")
                    merged_content.append(f"*转换器: {result.get('converter', 'Unknown')}*\n")
                    merged_content.append(result["content"])
                    merged_content.append("\n---\n")
        
        # 失败的文件
        if error_files > 0:
            merged_content.append("## 解析失败的文档\n")
            for result in results:
                if result["status"] == "error":
                    merged_content.append(f"- {result['file_path']}: {result.get('error', 'Unknown error')}")
        
        # 不支持的文件
        if unsupported_files > 0:
            merged_content.append("\n## 不支持的文档格式\n")
            for result in results:
                if result["status"] == "unsupported":
                    merged_content.append(f"- {result['file_path']}")
        
        final_content = "\n".join(merged_content)
        
        # 保存到文件
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            logger.info(f"合并结果已保存到: {output_path}")
        
        return final_content 