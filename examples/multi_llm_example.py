"""
AutoForge 多LLM提供商示例
演示如何使用不同的LLM提供商（OpenAI、DeepSeek、百炼）
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv  # 新增
from loguru import logger

# 自动加载同级目录下的.env文件
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge import AutoForgeAgent
from autoforge.llm import OpenAIClient, DeepSeekClient, BaiLianClient

# 屏蔽httpx等三方库日志
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# 在大模型请求前后打印结构体
# 以OpenAI为例，其他同理

def demo_openai():
    """演示使用OpenAI"""
    print("\n=== 使用OpenAI ===")
    try:
        client = OpenAIClient(
            model="gpt-4.1"
        )
        prompt = "你好，请简单介绍一下机器学习"
        logger.info(f"[OpenAI请求] prompt: {prompt}")
        response = client.generate(prompt)
        logger.info(f"[OpenAI响应] response: {response}")
        print(f"OpenAI回复: {response[:100]}...")
        return client
    except Exception as e:
        logger.error(f"OpenAI示例失败: {e}")
        return None


def demo_deepseek():
    """演示使用DeepSeek"""
    print("\n=== 使用DeepSeek ===")
    try:
        client = DeepSeekClient(
            model="deepseek-reasoner"
        )
        prompt = "你好，请简单介绍一下深度学习"
        logger.info(f"[DeepSeek请求] prompt: {prompt}")
        response = client.generate(prompt)
        logger.info(f"[DeepSeek响应] response: {response}")
        print(f"DeepSeek回复: {response[:100]}...")
        client.set_model("deepseek-reasoner")
        messages = [{"role": "user", "content": "9.11和9.8，哪个更大？请详细解释"}]
        logger.info(f"[DeepSeek Reasoner请求] messages: {messages}")
        response = client.generate_with_messages(messages)
        logger.info(f"[DeepSeek Reasoner响应] response: {response}")
        print(f"DeepSeek Reasoner回复: {response[:100]}...")
        return client
    except Exception as e:
        logger.error(f"DeepSeek示例失败: {e}")
        return None


def demo_bailian():
    """演示使用百炼"""
    print("\n=== 使用阿里云百炼 ===")
    try:
        client = BaiLianClient(
            model="qwen3-235b-a22b"
        )
        prompt = "你好，请简单介绍一下通义千问"
        logger.info(f"[百炼请求] prompt: {prompt}")
        response = client.generate(prompt, enable_thinking=False)
        logger.info(f"[百炼响应] response: {response}")
        print(f"百炼回复: {response[:100]}...")
        return client
    except Exception as e:
        logger.error(f"百炼示例失败: {e}")
        return None


def demo_autoforge_with_different_llms():
    """演示使用不同的LLM运行AutoForge"""
    print("\n=== 使用不同LLM运行AutoForge ===")
    
    # 测试需求
    requirement = """
    我需要一个图像分类模型，用于识别常见的办公用品。
    具体要求：
    1. 能够识别至少10种常见办公用品（如笔、纸、订书机等）
    2. 准确率要求>90%
    3. 推理速度<100ms
    4. 部署环境：普通CPU服务器
    """
    
    # 获取可用的LLM客户端
    available_clients = []
    
    # 尝试OpenAI
    openai_client = demo_openai()
    if openai_client:
        available_clients.append(("OpenAI", openai_client))
    
    # 尝试DeepSeek
    deepseek_client = demo_deepseek()
    if deepseek_client:
        available_clients.append(("DeepSeek", deepseek_client))
    
    # 尝试百炼
    bailian_client = demo_bailian()
    if bailian_client:
        available_clients.append(("百炼", bailian_client))
    
    # 使用可用的客户端运行AutoForge
    for name, client in available_clients:
        print(f"\n使用 {name} 运行AutoForge...")
        
        try:
            # 创建Agent
            agent = AutoForgeAgent(
                llm_client=client,
                output_dir=f"outputs/demo_{name.lower()}"
            )
            
            # 分析需求
            result = agent.analyze_requirements(manual_description=requirement)
            
            print(f"{name}分析需求成功!")
            print(f"结果保存在: {result['output_file']}")
            
        except Exception as e:
            print(f"使用{name}运行AutoForge失败: {e}")


def demo_single_model(model_name: str):
    """演示使用单个指定的模型"""
    model_map = {
        "1": ("OpenAI", demo_openai),
        "2": ("DeepSeek", demo_deepseek),
        "3": ("百炼", demo_bailian)
    }
    
    if model_name in model_map:
        name, demo_func = model_map[model_name]
        print(f"\n仅测试 {name} 模型")
        client = demo_func()
        return name, client
    else:
        print("无效的选择")
        return None, None


def demo_autoforge_with_single_llm(model_choice: str):
    """使用单个指定的LLM运行AutoForge"""
    name, client = demo_single_model(model_choice)
    
    if not client:
        return
    
    print(f"\n=== 使用 {name} 运行AutoForge ===")
    
    # 测试需求
    requirement = """
    我需要一个图像分类模型，用于识别常见的办公用品。
    具体要求：
    1. 能够识别至少10种常见办公用品（如笔、纸、订书机等）
    2. 准确率要求>90%
    3. 推理速度<100ms
    4. 部署环境：普通CPU服务器
    """
    
    try:
        # 创建Agent
        agent = AutoForgeAgent(
            llm_client=client,
            output_dir=f"outputs/demo_{name.lower()}"
        )
        
        # 分析需求
        result = agent.analyze_requirements(manual_description=requirement)
        
        print(f"\n{name}分析需求成功!")
        print(f"结果保存在: {result['output_file']}")
        
    except Exception as e:
        print(f"使用{name}运行AutoForge失败: {e}")


def main():
    """主函数"""
    print("🚀 AutoForge 多LLM提供商示例\n")
    
    # 检查环境变量（已自动从.env加载）
    api_keys = {
        "OpenAI": os.getenv("OPENAI_API_KEY"),
        "DeepSeek": os.getenv("DEEPSEEK_API_KEY"),
        "百炼": os.getenv("DASHSCOPE_API_KEY")
    }
    
    print("API密钥状态:")
    for name, key in api_keys.items():
        status = "✓ 已设置" if key else "✗ 未设置"
        print(f"- {name}: {status}")
    
    # 运行示例
    print("\n请选择要运行的示例:")
    print("1. 测试所有LLM")
    print("2. 使用所有可用LLM运行AutoForge")
    print("3. 选择特定LLM测试")
    print("4. 使用特定LLM运行AutoForge")
    
    choice = input("\n请输入选择(1-4): ").strip()
    
    if choice == "1":
        demo_openai()
        demo_deepseek()
        demo_bailian()
    elif choice == "2":
        demo_autoforge_with_different_llms()
    elif choice == "3":
        print("\n选择要测试的模型:")
        print("1. OpenAI")
        print("2. DeepSeek")
        print("3. 百炼")
        model_choice = input("请输入选择(1-3): ").strip()
        demo_single_model(model_choice)
    elif choice == "4":
        print("\n选择要使用的模型运行AutoForge:")
        print("1. OpenAI")
        print("2. DeepSeek")
        print("3. 百炼")
        model_choice = input("请输入选择(1-3): ").strip()
        demo_autoforge_with_single_llm(model_choice)
    else:
        print("无效的选择")


if __name__ == "__main__":
    main() 