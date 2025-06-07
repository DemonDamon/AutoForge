"""
GitHub 仓库分析器
用于克隆和分析 GitHub 代码仓库
"""

import os
import json
import time
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import tempfile
from datetime import datetime
import re

from tqdm import tqdm

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class GitHubRepoAnalyzer(BaseAnalyzer):
    """GitHub 仓库分析器"""
    
    def __init__(self, 
                 workspace_dir: str = "outputs/github_repos",
                 clone_timeout: int = 300,
                 keep_repos: bool = False,
                 llm_client=None,
                 output_dir: str = "outputs",
                 save_intermediate: bool = True):
        """
        初始化 GitHub 仓库分析器
        
        Args:
            workspace_dir: 工作目录，用于存放克隆的仓库
            clone_timeout: 克隆仓库的超时时间（秒）
            keep_repos: 是否保留克隆的仓库（True）或分析后删除（False）
            llm_client: 大语言模型客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
        """
        super().__init__(llm_client=llm_client, output_dir=output_dir, save_intermediate=save_intermediate)
        self.workspace_dir = Path(workspace_dir)
        self.clone_timeout = clone_timeout
        self.keep_repos = keep_repos
        
        # 创建工作目录
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 确认 git 命令可用
        self._check_git_availability()
    
    def analyze(self, repo_url: str, **kwargs) -> Dict[str, Any]:
        """
        分析GitHub仓库
        
        Args:
            repo_url: GitHub仓库URL
            **kwargs: 其他参数
            
        Returns:
            分析结果
        """
        # 实现 BaseAnalyzer 要求的抽象方法
        return self.analyze_repo_from_url(repo_url)
    
    def _check_git_availability(self):
        """检查 git 命令是否可用"""
        try:
            subprocess.run(
                ["git", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Git 命令不可用，请确保已安装 Git 并添加到系统路径")
            raise RuntimeError("Git 命令不可用")
    
    def clone_repo(self, repo_url: str, target_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        克隆 GitHub 仓库
        
        Args:
            repo_url: GitHub 仓库URL
            target_dir: 目标目录，默认为临时目录
            
        Returns:
            (成功标志, 目标目录路径)
        """
        # 提取仓库名称
        repo_name = self._extract_repo_name(repo_url)
        if not repo_name:
            logger.error(f"无效的仓库URL: {repo_url}")
            return False, ""
        
        # 确定目标目录
        if target_dir:
            repo_dir = Path(target_dir)
        else:
            repo_dir = self.workspace_dir / repo_name
        
        # 如果目录已存在，先删除
        if repo_dir.exists():
            logger.info(f"目标目录已存在，正在删除: {repo_dir}")
            shutil.rmtree(repo_dir, ignore_errors=True)
        
        # 创建目录
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始克隆仓库: {repo_url} -> {repo_dir}")
        
        try:
            # 执行克隆命令
            process = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(repo_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.clone_timeout,
                check=False  # 不自动抛出异常
            )
            
            if process.returncode != 0:
                error_msg = process.stderr.decode('utf-8', errors='ignore')
                logger.error(f"克隆仓库失败: {error_msg}")
                return False, str(repo_dir)
            
            logger.info(f"成功克隆仓库: {repo_url}")
            return True, str(repo_dir)
            
        except subprocess.TimeoutExpired:
            logger.error(f"克隆仓库超时: {repo_url}")
            return False, str(repo_dir)
        except Exception as e:
            logger.error(f"克隆仓库异常: {e}")
            return False, str(repo_dir)
    
    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        """
        分析仓库，收集基本信息
        
        Args:
            repo_path: 仓库本地路径
            
        Returns:
            包含仓库信息的字典
        """
        repo_dir = Path(repo_path)
        if not repo_dir.exists() or not (repo_dir / ".git").exists():
            logger.error(f"无效的仓库路径: {repo_path}")
            return {"status": "error", "message": "无效的仓库路径"}
        
        logger.info(f"开始分析仓库: {repo_path}")
        
        try:
            # 基本信息
            repo_info = {
                "status": "success",
                "repo_path": str(repo_dir),
                "analyzed_at": datetime.now().isoformat(),
                "file_stats": self._analyze_file_stats(repo_dir),
                "language_stats": self._analyze_languages(repo_dir),
                "git_info": self._get_git_info(repo_dir),
                "dependencies": self._analyze_dependencies(repo_dir),
                "structure": self._analyze_structure(repo_dir),
                "readme": self._extract_readme(repo_dir)
            }
            
            return repo_info
            
        except Exception as e:
            logger.error(f"分析仓库异常: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # 如果不保留仓库，则删除
            if not self.keep_repos and repo_dir.exists():
                logger.info(f"删除仓库目录: {repo_dir}")
                shutil.rmtree(repo_dir, ignore_errors=True)
    
    def analyze_repo_from_url(self, repo_url: str) -> Dict[str, Any]:
        """
        从URL克隆并分析仓库
        
        Args:
            repo_url: GitHub 仓库URL
            
        Returns:
            仓库分析信息
        """
        # 克隆仓库
        success, repo_path = self.clone_repo(repo_url)
        
        if not success:
            return {
                "status": "error",
                "message": f"克隆仓库失败: {repo_url}",
                "repo_url": repo_url
            }
        
        # 分析仓库
        analysis_result = self.analyze_repo(repo_path)
        analysis_result["repo_url"] = repo_url
        
        return analysis_result
    
    def batch_analyze_repos(self, repo_urls: List[str]) -> List[Dict[str, Any]]:
        """
        批量分析多个仓库
        
        Args:
            repo_urls: GitHub 仓库URL列表
            
        Returns:
            分析结果列表
        """
        logger.info(f"开始批量分析 {len(repo_urls)} 个仓库")
        
        results = []
        
        for repo_url in tqdm(repo_urls, desc="分析仓库"):
            try:
                result = self.analyze_repo_from_url(repo_url)
                results.append(result)
                
                # 保存阶段性结果
                self._save_analysis_results(results)
                
                # 避免频繁请求
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"分析仓库异常: {repo_url} - {e}")
                results.append({
                    "status": "error",
                    "message": str(e),
                    "repo_url": repo_url
                })
        
        return results
    
    def analyze_repos_from_pwc_results(self, pwc_results_file: str) -> Dict[str, Any]:
        """
        从 Papers with Code 爬取结果中分析仓库
        
        Args:
            pwc_results_file: PwC 爬取结果JSON文件路径
            
        Returns:
            分析摘要和详细结果
        """
        logger.info(f"从PwC结果文件分析仓库: {pwc_results_file}")
        
        try:
            # 读取PwC结果
            with open(pwc_results_file, 'r', encoding='utf-8') as f:
                pwc_data = json.load(f)
            
            papers = pwc_data.get('papers', [])
            if not papers:
                return {"status": "error", "message": "未找到论文数据"}
            
            # 收集所有GitHub仓库URL
            repo_urls = []
            paper_repo_map = {}  # 论文ID到仓库URL的映射
            
            for paper in papers:
                paper_id = paper.get('title', '')
                # 从论文详情中提取GitHub仓库
                github_repos = paper.get('github_repos', [])
                
                if github_repos:
                    for repo in github_repos:
                        repo_url = repo.get('url', '')
                        if repo_url and repo_url not in repo_urls:
                            repo_urls.append(repo_url)
                            if paper_id:
                                if paper_id not in paper_repo_map:
                                    paper_repo_map[paper_id] = []
                                paper_repo_map[paper_id].append(repo_url)
            
            if not repo_urls:
                return {"status": "warning", "message": "未找到GitHub仓库URL"}
            
            # 批量分析仓库
            analysis_results = self.batch_analyze_repos(repo_urls)
            
            # 构建结果摘要
            summary = {
                "total_papers": len(papers),
                "total_repos": len(repo_urls),
                "success_count": sum(1 for r in analysis_results if r.get("status") == "success"),
                "error_count": sum(1 for r in analysis_results if r.get("status") == "error"),
                "paper_repo_map": paper_repo_map,
                "analyzed_at": datetime.now().isoformat()
            }
            
            # 保存完整结果
            output_file = Path(pwc_results_file).parent / f"repo_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": summary,
                    "results": analysis_results
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"仓库分析结果已保存至: {output_file}")
            
            return {
                "status": "success",
                "summary": summary,
                "output_file": str(output_file)
            }
            
        except Exception as e:
            logger.error(f"分析PwC结果文件异常: {e}")
            return {"status": "error", "message": str(e)}
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """从URL中提取仓库名称"""
        # 匹配 github.com/owner/repo 格式
        match = re.search(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if match:
            owner, repo = match.groups()
            return f"{owner}_{repo}"
        return ""
    
    def _analyze_file_stats(self, repo_dir: Path) -> Dict[str, Any]:
        """分析文件统计信息"""
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "total_size_bytes": 0,
            "file_extensions": {},
            "largest_files": []
        }
        
        largest_files = []
        
        # 遍历所有文件
        for root, dirs, files in os.walk(repo_dir):
            # 排除 .git 目录
            if '.git' in dirs:
                dirs.remove('.git')
            
            stats["total_dirs"] += len(dirs)
            stats["total_files"] += len(files)
            
            for file in files:
                file_path = Path(root) / file
                file_size = file_path.stat().st_size
                stats["total_size_bytes"] += file_size
                
                # 统计文件扩展名
                ext = file_path.suffix.lower()
                if ext:
                    stats["file_extensions"][ext] = stats["file_extensions"].get(ext, 0) + 1
                
                # 记录最大文件
                rel_path = str(file_path.relative_to(repo_dir))
                largest_files.append((rel_path, file_size))
        
        # 排序并保留前10个最大文件
        largest_files.sort(key=lambda x: x[1], reverse=True)
        stats["largest_files"] = [{"path": p, "size_bytes": s} for p, s in largest_files[:10]]
        
        return stats
    
    def _analyze_languages(self, repo_dir: Path) -> Dict[str, Any]:
        """分析仓库语言占比"""
        # 语言到扩展名的映射
        language_map = {
            "Python": [".py", ".pyx", ".pyd", ".pyi"],
            "JavaScript": [".js", ".jsx", ".mjs"],
            "TypeScript": [".ts", ".tsx"],
            "Java": [".java", ".jar"],
            "C++": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "C": [".c", ".h"],
            "C#": [".cs"],
            "Go": [".go"],
            "Rust": [".rs"],
            "PHP": [".php"],
            "Ruby": [".rb"],
            "Swift": [".swift"],
            "Kotlin": [".kt", ".kts"],
            "Scala": [".scala"],
            "R": [".r", ".R"],
            "Shell": [".sh", ".bash"],
            "HTML": [".html", ".htm"],
            "CSS": [".css", ".scss", ".sass"],
            "Markdown": [".md", ".markdown"],
            "JSON": [".json"],
            "YAML": [".yml", ".yaml"],
            "XML": [".xml"],
        }
        
        # 初始化计数
        language_stats = {lang: {"files": 0, "size_bytes": 0} for lang in language_map}
        language_stats["Other"] = {"files": 0, "size_bytes": 0}
        
        # 遍历所有文件
        for root, dirs, files in os.walk(repo_dir):
            # 排除 .git 目录
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = Path(root) / file
                file_size = file_path.stat().st_size
                ext = file_path.suffix.lower()
                
                # 确定语言
                language = "Other"
                for lang, extensions in language_map.items():
                    if ext in extensions:
                        language = lang
                        break
                
                # 更新统计
                language_stats[language]["files"] += 1
                language_stats[language]["size_bytes"] += file_size
        
        # 计算百分比
        total_size = sum(stats["size_bytes"] for stats in language_stats.values())
        if total_size > 0:
            for lang in language_stats:
                percentage = (language_stats[lang]["size_bytes"] / total_size) * 100
                language_stats[lang]["percentage"] = round(percentage, 2)
        
        # 移除空语言
        return {lang: stats for lang, stats in language_stats.items() if stats["files"] > 0}
    
    def _get_git_info(self, repo_dir: Path) -> Dict[str, Any]:
        """获取Git仓库信息"""
        git_info = {}
        
        try:
            # 获取最后一次提交信息
            last_commit = subprocess.run(
                ["git", "log", "-1", "--format=%H|%an|%ae|%ad|%s"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            if last_commit.returncode == 0:
                commit_parts = last_commit.stdout.decode('utf-8', errors='ignore').strip().split('|')
                if len(commit_parts) >= 5:
                    git_info["last_commit"] = {
                        "hash": commit_parts[0],
                        "author": commit_parts[1],
                        "email": commit_parts[2],
                        "date": commit_parts[3],
                        "message": commit_parts[4]
                    }
            
            # 获取提交数量
            commit_count = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if commit_count.returncode == 0:
                git_info["commit_count"] = int(commit_count.stdout.decode('utf-8').strip())
            
            # 获取分支信息
            branches = subprocess.run(
                ["git", "branch", "-r"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if branches.returncode == 0:
                branch_list = [
                    b.strip().replace('origin/', '') 
                    for b in branches.stdout.decode('utf-8').split('\n') 
                    if b.strip()
                ]
                git_info["branches"] = branch_list
            
            # 获取远程仓库信息
            remotes = subprocess.run(
                ["git", "remote", "-v"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if remotes.returncode == 0:
                remote_info = {}
                for line in remotes.stdout.decode('utf-8').split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            name, url = parts[0], parts[1]
                            remote_info[name] = url
                git_info["remotes"] = remote_info
            
        except Exception as e:
            logger.error(f"获取Git信息异常: {e}")
            git_info["error"] = str(e)
        
        return git_info
    
    def _analyze_dependencies(self, repo_dir: Path) -> Dict[str, Any]:
        """分析项目依赖"""
        dependencies = {}
        
        # 检查 Python 依赖
        requirement_files = list(repo_dir.glob("*requirements*.txt")) + list(repo_dir.glob("setup.py"))
        if requirement_files:
            python_deps = []
            for req_file in requirement_files:
                with open(req_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 简单提取依赖名称
                    if req_file.name == "setup.py":
                        # 从 setup.py 中提取 install_requires
                        matches = re.findall(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
                        if matches:
                            deps = re.findall(r'[\'"](.+?)[\'"](,|\s|$)', matches[0])
                            python_deps.extend([d[0] for d in deps])
                    else:
                        # 从 requirements.txt 提取
                        for line in content.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # 去除版本信息
                                dep_name = line.split('=')[0].split('>')[0].split('<')[0].strip()
                                if dep_name:
                                    python_deps.append(dep_name)
            
            dependencies["python"] = sorted(list(set(python_deps)))
        
        # 检查 JavaScript/Node.js 依赖
        package_json = repo_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    js_deps = {}
                    
                    if "dependencies" in package_data:
                        js_deps["dependencies"] = list(package_data["dependencies"].keys())
                    
                    if "devDependencies" in package_data:
                        js_deps["devDependencies"] = list(package_data["devDependencies"].keys())
                    
                    dependencies["javascript"] = js_deps
            except:
                pass
        
        # 检查 Java/Maven 依赖
        pom_xml = repo_dir / "pom.xml"
        if pom_xml.exists():
            dependencies["java"] = {"maven": True}
        
        # 检查 Rust 依赖
        cargo_toml = repo_dir / "Cargo.toml"
        if cargo_toml.exists():
            dependencies["rust"] = {"cargo": True}
        
        # 返回依赖信息
        return dependencies
    
    def _analyze_structure(self, repo_dir: Path) -> Dict[str, Any]:
        """分析项目结构"""
        # 获取顶层目录和文件
        structure = {
            "top_level": [],
            "has_readme": False,
            "has_license": False,
            "has_test": False,
            "has_ci": False,
            "has_docker": False
        }
        
        # 检查顶层目录和文件
        for item in repo_dir.iterdir():
            if item.name == ".git":
                continue
                
            rel_path = str(item.relative_to(repo_dir))
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file"
            }
            
            structure["top_level"].append(item_info)
            
            # 检查特殊文件和目录
            lower_name = item.name.lower()
            if lower_name in ["readme.md", "readme.txt", "readme"]:
                structure["has_readme"] = True
            elif lower_name in ["license", "license.md", "license.txt"]:
                structure["has_license"] = True
            elif lower_name in ["test", "tests", "testing"]:
                structure["has_test"] = True
            elif lower_name in [".github", ".travis.yml", ".gitlab-ci.yml", "azure-pipelines.yml"]:
                structure["has_ci"] = True
            elif lower_name in ["dockerfile", "docker-compose.yml", ".dockerignore"]:
                structure["has_docker"] = True
        
        return structure
    
    def _extract_readme(self, repo_dir: Path) -> str:
        """提取README内容"""
        readme_candidates = [
            repo_dir / "README.md",
            repo_dir / "Readme.md",
            repo_dir / "README.txt",
            repo_dir / "README"
        ]
        
        for readme_file in readme_candidates:
            if readme_file.exists():
                try:
                    with open(readme_file, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except:
                    pass
        
        return ""
    
    def _save_analysis_results(self, results: List[Dict[str, Any]]):
        """保存分析结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.workspace_dir / f"repo_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析结果已保存至: {output_file}") 