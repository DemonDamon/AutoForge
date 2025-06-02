import os
import sys
import time
import threading
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# =============================================
# 全局配置参数
# =============================================

# 目录配置
OUTPUT_DIR = "outputs/video_title_normalization"  # 输出目录
LOG_FILE = "autoforge_demo.log"                   # 日志文件名
DIR_MAX_FILES_DISPLAY = 10                        # 目录列表最大显示文件数

# 模型选择配置 - 指定要使用的模型
SELECTED_MODEL = "deepseek-reasoner"  # 可选: "deepseek-reasoner", "qwen-plus"

# 模型配置映射 - 从环境变量中读取
MODEL_CONFIGS = {
    "deepseek-reasoner": {
        "provider": "DeepSeek",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model_name": "deepseek-reasoner",
        "client_class": "DeepSeekClient"
    },
    "qwen-plus": {
        "provider": "阿里云百炼",
        "api_key": os.getenv("BAILIAN_API_KEY", ""),
        "model_name": "qwen-plus", 
        "client_class": "BaiLianClient"
    }
}

# 获取当前选择的模型配置
if SELECTED_MODEL not in MODEL_CONFIGS:
    raise ValueError(f"不支持的模型: {SELECTED_MODEL}. 支持的模型: {list(MODEL_CONFIGS.keys())}")

CURRENT_MODEL_CONFIG = MODEL_CONFIGS[SELECTED_MODEL]

# 验证API密钥是否存在
if not CURRENT_MODEL_CONFIG["api_key"]:
    raise ValueError(f"未找到模型 {SELECTED_MODEL} 的API密钥，请检查.env文件中的配置")

# API配置 - 使用选择的模型配置
API_KEY = CURRENT_MODEL_CONFIG["api_key"]
MODEL_NAME = CURRENT_MODEL_CONFIG["model_name"]
PROVIDER_NAME = CURRENT_MODEL_CONFIG["provider"]
CLIENT_CLASS = CURRENT_MODEL_CONFIG["client_class"]

# 爬虫配置
MODEL_CRAWL_COUNT = 30  # 每种任务类型爬取的模型数量
TEXT2TEXT_MODEL_DETAIL_COUNT = 30  # 获取详细信息的text2text模型数量
TEXT_GEN_MODEL_DETAIL_COUNT = 10   # 获取详细信息的text-generation模型数量
DISPLAY_MODEL_COUNT = 30           # 在LLM提示中显示的模型数量
PRINT_MODEL_COUNT = 10             # 在控制台打印的模型数量

# LLM参数配置
TEXT2TEXT_SAMPLE_COUNT = 30        # 传递给LLM的text2text模型样本数量
TEXT_GEN_SAMPLE_COUNT = 15         # 传递给LLM的text-generation模型样本数量
REQUEST_TIMEOUT = 300              # 请求超时时间(秒)，5分钟

# 监控配置
MONITOR_INTERVAL = 10              # 监控日志输出间隔(秒)
MAX_MONITOR_COUNT = 30             # 最大监控次数

# 任务描述
TASK_DESCRIPTION = """
视频标题规范化 Text-to-Text 生成任务：

1. 任务定义：
   这是一个典型的文本到文本(text-to-text)生成任务，需要将包含噪声的原始视频标题转换为规范化的标准形式。
   系统需要接收一个输入文本（原始视频标题），然后生成一个输出文本（规范化后的标题）。

2. 输入与输出：
   - 输入：原始视频标题文本，可能包含噪声、非标准格式或冗余信息
   - 输出：规范化后的标题文本，只保留核心内容信息

3. 转换规则：
   - 移除非核心信息：年份标记、季数标记、平台标记、格式标记等
   - 修正文本错误：错别字、非标准缩写、特殊字符替代等
   - 标准化格式：保持一致的命名规则和格式约定
   - 保留语义核心：确保标题的主要含义和重要信息被保留

4. 具体示例（输入→输出对）：
   | 输入文本                                    | 输出文本           |
   |-------------------------------------------|------------------|
   | X-侠客行. 2001. 全40集. 国语中字侠客行       | 侠客行            |
   | 人鱼x姐                                    | 人鱼小姐           |
   | 搞x一j人                                   | 搞笑一家人         |
   | 路西法 第一季 Lucifer Season                | 路西法            |
   | W 我叫MT 1-7季                             | 我叫MT            |
   | 《特su案件z案组》 1-2季                      | 特殊案件专案组      |
   | 精灵宝可梦[09]沧海的王子玛娜 精灵宝可梦         | 精灵宝可梦         |
   | S 神犬小七                                  | 神犬小七           |
   | 龙年d案                                     | 龙年档案          |
   | 全！金S外壳                                  | 全金属外壳          |
   | 《s林民宿》                                  | 森林民宿           |
   | 读心神探GOTV国语                             | 读心神探           |
   | 《哲仁w后》                                  | 《哲仁王后》        |
   | 1988《肥猫流浪记》郑则仕                      | 肥猫流浪记          |
   | 屠MZ神【2022】                              | 屠魔战神           |
   | A-爱情是什么（2018）                         | 爱情是什么          |
   | 罗斯玛丽的yiner                             | 罗斯玛丽的婴儿       |
   | 社内x亲                                     | 社内相亲           |
   | [你是我的RY][2021]                          | 你是我的荣耀        |
   | 【许冠英电影】抢钱夫妻                         | 抢钱夫妻           |
   | 《过一次了》                                 | 《结过一次了》       |
   | 敦KE克                                     | 敦刻尔克            |

5. 数据规模与性能要求：
   - 训练数据：预计需要5,000-10,000对高质量的标题对
   - 推理规模：系统需要处理约10万条视频标题
   - 准确率要求：规范化准确率 >90%
   - 延迟要求：平均处理时间 <100ms/条

6. 技术挑战：
   - 噪声模式识别：识别各种不同类型的噪声和格式问题
   - 上下文理解：理解视频标题的语义内容，正确保留核心信息
   - 一致性保证：确保相似输入产生一致的输出结果
   - 中文特殊处理：处理中文特有的语言特性和表达方式
   - 稀有实体识别：正确识别和保留影视作品中的人名、剧名等专有名词

7. 模型选择考虑因素：
   - 序列到序列(seq2seq)生成能力：适用于text-to-text转换任务
   - 中文语言理解能力：良好的中文语义理解性能
   - 文本纠错能力：能够识别并修正各种文本错误
   - 推理速度：满足低延迟需求
   - 部署效率：资源消耗合理，适合大规模处理
"""

# 设置控制台编码，尝试解决中文和特殊字符问题
if sys.platform == 'win32':
    # Windows平台特殊处理
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # 设置控制台代码页为UTF-8
    except Exception:
        pass  # 如果失败，忽略错误

# 使用loguru替代标准logging
from loguru import logger

# 移除默认处理器
logger.remove()
# 添加控制台处理器
logger.add(sys.stdout, level="INFO", 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>")
# 添加文件处理器
logger.add(LOG_FILE, level="DEBUG", encoding="utf-8",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}")

# 过滤掉httpx和httpcore的日志
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# 设置请求超时处理（跨平台兼容）
class TimeoutError(Exception):
    pass

class TimeoutManager:
    def __init__(self, seconds, error_message="操作超时"):
        self.seconds = seconds
        self.error_message = error_message
        self.timer = None
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cancel()
        
    def timeout_handler(self):
        """超时处理函数"""
        # 直接在当前线程内引发超时异常
        # 这不会中断主线程，但会设置一个标志，供我们检查
        self.timeout_occurred = True
        
    def start(self):
        """启动超时计时器"""
        self.timeout_occurred = False
        self.timer = threading.Timer(self.seconds, self.timeout_handler)
        self.timer.daemon = True
        self.timer.start()
        
    def cancel(self):
        """取消超时计时器"""
        if self.timer:
            self.timer.cancel()
            
    def check_timeout(self):
        """检查是否发生超时"""
        if self.timeout_occurred:
            raise TimeoutError(self.error_message)

# 打印格式化文本
def print_formatted_text(text, title="文本内容"):
    """格式化打印文本内容"""
    separator = "=" * 80
    print(f"\n{separator}")
    print(f"【{title}】")
    print(f"{separator}")
    print(text)
    print(f"{separator}\n")

# 添加项目根目录到Python路径
root_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, root_dir)
logger.info(f"项目根目录已添加到Python路径: {root_dir}")

try:
    logger.info("开始导入AutoForge模块...")
    from autoforge import AutoForgeAgent
    from autoforge.llm import DeepSeekClient, BaiLianClient
    logger.info("AutoForge模块导入成功")
except Exception as e:
    logger.error(f"导入AutoForge模块失败: {e}")
    raise

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
logger.info(f"输出目录已创建: {OUTPUT_DIR}")

# 记录使用的模型信息
active_model_info = {
    "provider": PROVIDER_NAME,
    "model_name": MODEL_NAME,
    "api_key_prefix": API_KEY[:8] + "***" if API_KEY else "未设置"
}

logger.info(f"初始化{PROVIDER_NAME}客户端...")
try:
    # 根据选择的模型动态创建客户端
    if CLIENT_CLASS == "DeepSeekClient":
        active_client = DeepSeekClient(
            api_key=API_KEY,
            model=MODEL_NAME
        )
        logger.info(f"{PROVIDER_NAME}客户端初始化成功")
        
        # 测试客户端连接
        logger.info(f"测试{PROVIDER_NAME}客户端连接...")
        test_result = active_client.validate_connection()
        logger.info(f"{PROVIDER_NAME}连接测试结果: {'成功' if test_result else '失败'}")
        
    elif CLIENT_CLASS == "BaiLianClient":
        active_client = BaiLianClient(
            api_key=API_KEY,
            model=MODEL_NAME
        )
        logger.info(f"{PROVIDER_NAME}客户端初始化成功")
        
    else:
        raise ValueError(f"不支持的客户端类型: {CLIENT_CLASS}")
        
except Exception as e:
    logger.error(f"初始化{PROVIDER_NAME}客户端失败: {e}")
    raise

# 创建AutoForge Agent
logger.info("创建AutoForge Agent...")
try:
    agent = AutoForgeAgent(llm_client=active_client, output_dir=OUTPUT_DIR)
    logger.info(f"AutoForge Agent创建成功，使用模型: {active_model_info['provider']} {active_model_info['model_name']}")
except Exception as e:
    logger.error(f"创建AutoForge Agent失败: {e}")
    raise

# 监控LLM请求情况
def monitor_llm_response(operation_name):
    """监控LLM响应情况，定期输出等待状态"""
    start_time = time.time()
    i = 1
    while True:
        elapsed = time.time() - start_time
        logger.info(f"{operation_name} - 仍在等待响应... (已等待 {elapsed:.1f} 秒)")
        time.sleep(MONITOR_INTERVAL)  # 使用全局变量
        i += 1
        if i > MAX_MONITOR_COUNT:  # 使用全局变量
            break

# 分析需求
logger.info("开始需求分析...")
start_time = time.time()
try:
    # 创建监控线程
    monitor_thread = threading.Thread(target=monitor_llm_response, args=("需求分析",))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 需求描述
    req_description = TASK_DESCRIPTION
    
    # 打印格式化的请求内容
    logger.info(f"发送需求分析请求，内容长度: {len(req_description)} 字符")
    print_formatted_text(req_description, "需求分析请求内容")
    
    # 使用超时管理器
    with TimeoutManager(REQUEST_TIMEOUT) as timeout_mgr:
        # 执行需求分析
        requirement_result = agent.analyze_requirements(
            manual_description=req_description
        )
        # 检查是否超时
        timeout_mgr.check_timeout()
    
    end_time = time.time()
    logger.info(f"需求分析完成，耗时: {end_time - start_time:.2f}秒")
    logger.info(f"需求分析结果保存在: {requirement_result['output_file']}")
    
    # 显示结果摘要
    try:
        if os.path.exists(requirement_result['output_file']):
            with open(requirement_result['output_file'], 'r', encoding='utf-8') as f:
                content = f.read()
                summary = content[:500] + "..." if len(content) > 500 else content
                logger.info(f"需求分析结果摘要 (使用模型: {active_model_info['provider']} {active_model_info['model_name']}):")
                print_formatted_text(summary, f"需求分析结果摘要 (由 {active_model_info['provider']} {active_model_info['model_name']} 生成)")
    except Exception as e:
        logger.error(f"读取结果文件失败: {e}")
    
except TimeoutError as e:
    logger.error(f"需求分析超时: {e}")
    print(f"需求分析请求已超时（{REQUEST_TIMEOUT}秒），请检查网络连接或API状态")
    sys.exit(1)
except Exception as e:
    logger.error(f"需求分析失败: {e}")
    raise

# 模型搜索（针对text2text-generation和text-generation任务爬取相关模型）
logger.info("开始模型搜索...")
start_time = time.time()
try:
    # 创建监控线程
    monitor_thread = threading.Thread(target=monitor_llm_response, args=("模型搜索",))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 爬取额外的模型信息用于分析
    from autoforge.crawler.hf_crawler import HuggingFaceCrawler
    
    # 创建爬虫实例
    crawler = HuggingFaceCrawler(output_dir=f"{OUTPUT_DIR}/hf_models")
    logger.info("初始化HuggingFace爬虫...")
    
    # 爬取text2text-generation任务的模型(正确任务类型)
    logger.info("爬取text2text-generation任务的模型...")
    try:
        text2text_models = crawler.crawl_models_by_task(
            task_tag="text2text-generation", 
            sort="trending",
            top_k=MODEL_CRAWL_COUNT
        )
        logger.info(f"成功爬取 {len(text2text_models)} 个text2text-generation模型")
    except Exception as e:
        logger.error(f"爬取text2text-generation模型失败: {e}")
        text2text_models = []
    
    # 爬取text-generation任务的模型(作为补充)
    logger.info("爬取text-generation任务的模型...")
    try:
        text_gen_models = crawler.crawl_models_by_task(
            task_tag="text-generation", 
            sort="trending",
            top_k=MODEL_CRAWL_COUNT
        )
        logger.info(f"成功爬取 {len(text_gen_models)} 个text-generation模型")
    except Exception as e:
        logger.error(f"爬取text-generation模型失败: {e}")
        text_gen_models = []
    
    # 爬取模型卡片信息获取更多细节(比如模型大小)
    if text2text_models:
        logger.info("获取text2text模型详细信息...")
        for i, model in enumerate(text2text_models[:TEXT2TEXT_MODEL_DETAIL_COUNT]):  # 获取全部30个模型的详细信息
            try:
                model_id = model.get('model_id')
                if model_id:
                    logger.info(f"获取模型 {model_id} 的详细信息...")
                    model_info = crawler.crawl_model_card(model_id)
                    logger.info(f"获取模型 {model_id} 详细信息成功")
            except Exception as e:
                logger.error(f"获取模型详细信息失败: {e}")
    
    # 同样获取一些text-generation模型的详细信息
    if text_gen_models:
        logger.info("获取text-generation模型详细信息...")
        for i, model in enumerate(text_gen_models[:TEXT_GEN_MODEL_DETAIL_COUNT]):  # 获取前10个详细信息
            try:
                model_id = model.get('model_id')
                if model_id:
                    logger.info(f"获取模型 {model_id} 的详细信息...")
                    model_info = crawler.crawl_model_card(model_id)
                    logger.info(f"获取模型 {model_id} 详细信息成功")
            except Exception as e:
                logger.error(f"获取模型详细信息失败: {e}")
    
    # 使用超时管理器
    with TimeoutManager(REQUEST_TIMEOUT) as timeout_mgr:
        # 构建任务特定的增强信息（业务层逻辑）
        def build_video_title_task_info():
            """构建视频标题规范化任务的特定信息"""
            task_info_section = ""
            model_selection_guide = ""
            custom_notes = ""
            
            # 构建任务类型信息
            if text2text_models or text_gen_models:
                task_info_section += "\n## 任务类型信息\n\n"
                
                # 添加text2text-generation信息
                if text2text_models:
                    task_info_section += f"### Text-to-Text生成 (text2text-generation)\n"
                    task_info_section += "这是一个序列到序列(seq2seq)生成任务，模型接收输入文本并生成输出文本。\n"
                    task_info_section += "适用于需要保持语义但改变格式或内容的任务，如文本规范化、摘要、翻译等。\n"
                    task_info_section += f"已爬取到 {len(text2text_models)} 个相关模型。\n\n"
                
                # 添加text-generation信息
                if text_gen_models:
                    task_info_section += f"### 文本生成 (text-generation)\n"
                    task_info_section += "这是一个自回归文本生成任务，模型接收提示文本并继续生成后续内容。\n"
                    task_info_section += "可以通过适当的prompt工程应用于text2text任务，但不如专门的text2text模型直接。\n"
                    task_info_section += f"已爬取到 {len(text_gen_models)} 个相关模型。\n\n"
                
                task_info_section += "**说明**：对于视频标题规范化任务，text2text-generation模型更加适合，因为它们专门设计用于输入-输出文本转换。\n\n"
            
            # 构建模型选择指导
            if text2text_models:
                model_selection_guide += "\n### 模型选择指导\n"
                model_selection_guide += "- 以上是专门的text2text-generation模型，特别适合视频标题规范化任务\n"
                model_selection_guide += "- 这些模型已经针对输入->输出的文本转换任务进行了优化\n"
                model_selection_guide += "- 使用这些模型可能比通用text-generation模型更高效、更准确\n\n"
            
            # 构建自定义注意事项
            custom_notes += "\n## 注意事项\n\n"
            custom_notes += "1. 模型大小评估应准确。例如，DeepSeek-R1是一个大型模型，不是8GB，其实际大小通常在数十GB甚至更大。\n"
            custom_notes += "2. 请确保推荐的模型与任务类型匹配，特别是对于text-to-text/seq2seq类型的任务，需要专门的模型支持。\n"
            custom_notes += "3. 请评估模型的中文能力，确保能处理中文视频标题中的各种噪声和不规范写法。\n"
            custom_notes += "4. **特别提示**：视频标题规范化是一个典型的text2text-generation任务，请重点考虑专门的序列到序列模型。\n"
            
            return task_info_section, model_selection_guide, custom_notes
        
        # 构建通用的additional_info
        task_info_section, model_selection_guide, custom_notes = build_video_title_task_info()
        
        # 合并所有爬取的模型
        all_crawled_models = []
        if text2text_models:
            all_crawled_models.extend(text2text_models[:TEXT2TEXT_SAMPLE_COUNT])
        if text_gen_models:
            all_crawled_models.extend(text_gen_models[:TEXT_GEN_SAMPLE_COUNT])
        
        # 确定模型来源描述
        model_source_desc = "Text-to-Text生成任务" if text2text_models else "文本生成任务"
        
        # 设置任务信息（如果有text2text模型，优先使用text2text任务）
        task_info = None
        if text2text_models:
            # 获取text2text-generation任务信息
            from autoforge.crawler.task_manager import TaskManager
            task_manager = TaskManager()
            all_tasks = task_manager.get_all_tasks()
            if "text2text-generation" in all_tasks:
                task_info = all_tasks["text2text-generation"]
        
        # 构建符合新接口的additional_info
        additional_info = {
            "crawled_models": all_crawled_models,
            "task_info": task_info,
            "model_source_description": model_source_desc,
            "custom_task_info": task_info_section,
            "model_selection_guide": model_selection_guide,
            "custom_notes": custom_notes,
            "display_model_count": DISPLAY_MODEL_COUNT
        }
        
        # 执行模型搜索
        model_result = agent.search_models(additional_info=additional_info)
        # 检查是否超时
        timeout_mgr.check_timeout()
    
    end_time = time.time()
    logger.info(f"模型搜索完成，耗时: {end_time - start_time:.2f}秒")
    logger.info(f"模型搜索结果保存在: {model_result['output_file']}")
    
    # 打印找到的模型数量
    crawled_models = []
    if text2text_models:
        crawled_models.extend(text2text_models)
    if text_gen_models:
        crawled_models.extend(text_gen_models)
    
    if 'crawled_models' in model_result:
        model_result['crawled_models'] = crawled_models
    else:
        model_result['crawled_models'] = crawled_models
    
    if crawled_models:
        logger.info(f"总共爬取到 {len(crawled_models)} 个相关模型")
        # 打印前10个模型信息
        for i, model in enumerate(crawled_models[:PRINT_MODEL_COUNT]):
            logger.info(f"模型 {i+1}: {model.get('model_id', 'Unknown')} (来源: {'text2text-generation' if i < len(text2text_models) else 'text-generation'})")
        
        # 格式化打印爬取的模型信息
        crawled_models_info = json.dumps(crawled_models[:PRINT_MODEL_COUNT], ensure_ascii=False, indent=2)
        print_formatted_text(crawled_models_info, f"爬取的前{PRINT_MODEL_COUNT}个模型信息")
    
    # 显示结果摘要
    try:
        if os.path.exists(model_result['output_file']):
            with open(model_result['output_file'], 'r', encoding='utf-8') as f:
                content = f.read()
                summary = content[:500] + "..." if len(content) > 500 else content
                print_formatted_text(summary, f"模型搜索结果摘要 (由 {active_model_info['provider']} {active_model_info['model_name']} 生成)")
    except Exception as e:
        logger.error(f"读取模型搜索结果文件失败: {e}")
        
except TimeoutError as e:
    logger.error(f"模型搜索超时: {e}")
    print(f"模型搜索请求已超时（{REQUEST_TIMEOUT}秒），请检查网络连接或API状态")
except Exception as e:
    logger.error(f"模型搜索失败: {e}")
    raise

# 解释输出目录结构和文件用途
def explain_output_directory(dir_path):
    """生成输出目录结构的详细说明"""
    output_path = Path(dir_path)
    
    if not output_path.exists():
        return "输出目录尚未创建"
    
    explanation = f"\n{'='*80}\n"
    explanation += f"【{output_path}】目录结构及文件说明\n"
    explanation += f"{'='*80}\n\n"
    
    # 添加使用的模型信息
    explanation += f"【生成使用的模型信息】\n"
    explanation += f"- 提供商: {active_model_info['provider']}\n"
    explanation += f"- 模型名称: {active_model_info['model_name']}\n"
    explanation += f"- API密钥: {active_model_info['api_key_prefix']}\n\n"
    
    # 子目录说明
    subdirs = {
        "requirement_analysis": {
            "description": "需求分析结果目录",
            "files": {
                "requirement_analysis_*.md": "需求分析详细报告，包含任务理解、技术建议等",
                "raw_document_content.md": "原始需求文档内容"
            },
            "usage": "查看这些文件可以了解系统如何理解您的需求，以及提出的初步解决方案建议"
        },
        "model_search": {
            "description": "模型搜索结果目录",
            "files": {
                "model_search_*.md": "模型推荐报告，包含推荐模型列表及理由",
                "candidates.json": "候选模型信息的结构化数据"
            },
            "usage": "从这里可以了解系统推荐的适合视频标题规范化的模型，包括每个模型的优缺点分析"
        },
        "hf_models": {
            "description": "HuggingFace模型爬取结果目录",
            "files": {
                "*/models_*.json": "按任务分类的模型列表数据",
                "model_cards/": "爬取的模型卡片详细信息"
            },
            "usage": "包含从HuggingFace爬取的最新模型数据，可用于了解模型的详细参数和使用情况"
        }
    }
    
    for subdir_name, info in subdirs.items():
        subdir_path = output_path / subdir_name
        if subdir_path.exists():
            explanation += f"【{subdir_name}】- {info['description']}\n"
            
            # 列出实际文件
            explanation += "  实际文件列表:\n"
            files = list(subdir_path.glob("**/*"))[:DIR_MAX_FILES_DISPLAY]  # 限制显示前10个文件
            if files:
                for file in files:
                    if file.is_file():
                        relative_path = file.relative_to(output_path)
                        explanation += f"  - {relative_path}\n"
                if len(list(subdir_path.glob("**/*"))) > DIR_MAX_FILES_DISPLAY:
                    explanation += "  - ... (更多文件)\n"
            else:
                explanation += "  - (暂无文件)\n"
            
            # 文件说明
            explanation += "  文件说明:\n"
            for pattern, desc in info['files'].items():
                explanation += f"  - {pattern}: {desc}\n"
            
            # 使用方式
            explanation += "  使用方式:\n"
            explanation += f"  - {info['usage']}\n\n"
    
    # 总体使用建议
    explanation += "【使用建议】\n"
    explanation += "1. 首先查看需求分析报告，了解系统对任务的理解\n"
    explanation += "2. 然后查看模型搜索结果，选择最适合的模型\n"
    explanation += "3. 参考HuggingFace模型数据，了解模型的详细参数\n"
    explanation += "4. 根据报告建议，设计您的文本到文本转换实现方案\n\n"
    
    # 后续步骤
    explanation += "【后续步骤】\n"
    explanation += "1. 实现文本预处理流程，处理输入文本中的噪声\n"
    explanation += "2. 使用推荐模型构建seq2seq转换流程\n"
    explanation += "3. 设计评估方法，确保达到90%以上的准确率\n"
    explanation += "4. 优化推理速度，满足<100ms的延迟要求\n"
    
    return explanation

# 使用不包含Unicode表情符号的消息
logger.info("任务完成！")
print("\n✓ 需求分析完成，结果保存在: {}".format(requirement_result['output_file']))
print("✓ 模型搜索完成，结果保存在: {}".format(model_result['output_file']))
print(f"✓ 使用的模型: {active_model_info['provider']} {active_model_info['model_name']}")

# 输出目录结构说明
directory_explanation = explain_output_directory(OUTPUT_DIR)
print(directory_explanation)