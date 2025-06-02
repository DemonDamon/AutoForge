"""
AutoForge 多LLM提供商示例
演示如何使用不同的LLM提供商（OpenAI、DeepSeek、百炼）
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge import AutoForgeAgent
from autoforge.llm import OpenAIClient, DeepSeekClient, BaiLianClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def demo_openai():
    """演示使用OpenAI"""
    print("\n=== 使用OpenAI ===")
    
    try:
        # 初始化OpenAI客户端
        client = OpenAIClient(
            # api_key="your-api-key-here",  # 或从环境变量OPENAI_API_KEY读取
            model="gpt-4-turbo"
        )
        
        # 测试生成
        response = client.generate("你好，请简单介绍一下机器学习")
        print(f"OpenAI回复: {response[:100]}...")
        
        return client
    except Exception as e:
        print(f"OpenAI示例失败: {e}")
        return None


def demo_deepseek():
    """演示使用DeepSeek"""
    print("\n=== 使用DeepSeek ===")
    
    try:
        # 初始化DeepSeek客户端
        client = DeepSeekClient(
            # api_key="your-api-key-here",  # 或从环境变量DEEPSEEK_API_KEY读取
            model="deepseek-chat"
        )
        
        # 测试生成
        response = client.generate("你好，请简单介绍一下深度学习")
        print(f"DeepSeek回复: {response[:100]}...")
        
        # 测试DeepSeek Reasoner
        client.set_model("deepseek-reasoner")
        messages = [{"role": "user", "content": "9.11和9.8，哪个更大？请详细解释"}]
        
        response = client.generate_with_messages(messages)
        print(f"DeepSeek Reasoner回复: {response[:100]}...")
        
        return client
    except Exception as e:
        print(f"DeepSeek示例失败: {e}")
        return None


def demo_bailian():
    """演示使用百炼"""
    print("\n=== 使用阿里云百炼 ===")
    
    try:
        # 初始化百炼客户端
        client = BaiLianClient(
            # api_key="your-api-key-here",  # 或从环境变量DASHSCOPE_API_KEY读取
            model="qwen-plus"
        )
        
        # 测试生成
        response = client.generate("你好，请简单介绍一下通义千问")
        print(f"百炼回复: {response[:100]}...")
        
        return client
    except Exception as e:
        print(f"百炼示例失败: {e}")
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


def main():
    """主函数"""
    print("🚀 AutoForge 多LLM提供商示例\n")
    
    # 检查环境变量
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
    choice = input("\n请选择要运行的示例:\n1. 单独测试各LLM\n2. 使用不同LLM运行AutoForge\n请输入选择(1或2): ")
    
    if choice == "1":
        demo_openai()
        demo_deepseek()
        demo_bailian()
    else:
        demo_autoforge_with_different_llms()


if __name__ == "__main__":
    main() 