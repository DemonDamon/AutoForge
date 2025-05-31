"""
AutoForge 基础功能测试
"""

import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")
    
    try:
        from autoforge import AutoForgeAgent
        print("✅ AutoForgeAgent 导入成功")
    except ImportError as e:
        print(f"❌ AutoForgeAgent 导入失败: {e}")
        return False
    
    try:
        from autoforge.docparser import MultiModalDocParser
        print("✅ MultiModalDocParser 导入成功")
    except ImportError as e:
        print(f"❌ MultiModalDocParser 导入失败: {e}")
        return False
    
    try:
        from autoforge.prompts import PromptManager
        print("✅ PromptManager 导入成功")
    except ImportError as e:
        print(f"❌ PromptManager 导入失败: {e}")
        return False
    
    try:
        from autoforge.llm import BaseLLMClient, OpenAIClient
        print("✅ LLM客户端 导入成功")
    except ImportError as e:
        print(f"❌ LLM客户端 导入失败: {e}")
        return False
    
    return True


def test_docparser():
    """测试文档解析器"""
    print("\n🧪 测试文档解析器...")
    
    from autoforge.docparser import MultiModalDocParser
    
    parser = MultiModalDocParser()
    
    # 测试Markdown文件解析
    test_md = "test_doc.md"
    with open(test_md, 'w', encoding='utf-8') as f:
        f.write("# 测试文档\n\n这是一个测试文档。")
    
    try:
        result = parser.parse_file(test_md)
        if result["status"] == "success":
            print("✅ Markdown文件解析成功")
            print(f"   内容预览: {result['content'][:50]}...")
        else:
            print(f"❌ Markdown文件解析失败: {result.get('error')}")
    except Exception as e:
        print(f"❌ 文档解析器测试失败: {e}")
    finally:
        # 清理测试文件
        Path(test_md).unlink(missing_ok=True)


def test_prompt_manager():
    """测试提示词管理器"""
    print("\n🧪 测试提示词管理器...")
    
    from autoforge.prompts import PromptManager
    
    manager = PromptManager()
    
    # 列出可用提示词
    prompts = manager.list_prompts()
    print(f"✅ 找到 {len(prompts)} 个提示词模板")
    
    # 测试提示词格式化
    try:
        prompt = manager.get_prompt(
            "DOCUMENT_UNDERSTANDING",
            document_content="测试文档内容"
        )
        print("✅ 提示词格式化成功")
        print(f"   提示词长度: {len(prompt)} 字符")
    except Exception as e:
        print(f"❌ 提示词格式化失败: {e}")


def test_mock_llm():
    """测试模拟LLM客户端"""
    print("\n🧪 测试LLM客户端接口...")
    
    from autoforge.llm import BaseLLMClient
    
    class MockLLMClient(BaseLLMClient):
        """模拟LLM客户端用于测试"""
        
        def generate(self, prompt, **kwargs):
            return f"模拟响应: 收到提示词长度 {len(prompt)} 字符"
        
        def generate_with_messages(self, messages, **kwargs):
            return f"模拟响应: 收到 {len(messages)} 条消息"
    
    client = MockLLMClient()
    
    # 测试生成
    response = client.generate("测试提示词")
    print(f"✅ LLM生成测试成功: {response}")
    
    # 测试连接验证
    is_valid = client.validate_connection()
    print(f"✅ 连接验证: {'成功' if is_valid else '失败'}")


def main():
    """主测试函数"""
    print("🚀 开始AutoForge基础功能测试\n")
    
    # 1. 测试导入
    if not test_imports():
        print("\n❌ 导入测试失败，请检查项目结构")
        return
    
    # 2. 测试文档解析器
    test_docparser()
    
    # 3. 测试提示词管理器
    test_prompt_manager()
    
    # 4. 测试LLM客户端
    test_mock_llm()
    
    print("\n✅ 所有基础功能测试完成！")
    print("\n💡 提示：")
    print("1. 安装依赖: pip install -r requirements.txt")
    print("2. 配置LLM: 设置OPENAI_API_KEY环境变量")
    print("3. 运行示例: python examples/quick_start.py")


if __name__ == "__main__":
    main() 