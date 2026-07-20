"""
Godot Kitset 统一 CLI 入口

使用: python tools.py <tool> <command> [args]
     python tools.py list          # 列出所有可用工具
     python tools.py godot ...     # 调用 Godot CLI
     python tools.py scaffold ...  # 创建项目骨架
     python tools.py scene ...     # 场景生成
     python tools.py script ...    # 脚本管理
     python tools.py template ...  # 模板库
     python tools.py plugin ...    # 启动 Godot 通信插件
"""

import os, sys, json, logging, subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('godot_tools')

TOOLS_DIR = Path(__file__).parent / "godot-tools"
GODOX_DIR = Path(__file__).parent.parent / "addons" / "godox"

TOOL_MAP = {
    'godot':    TOOLS_DIR / 'godot_cli.ts',
    'scaffold': TOOLS_DIR / 'scaffolder.ts',
    'scene':    TOOLS_DIR / 'scene_generator.ts',
    'script':   TOOLS_DIR / 'script_manager.ts',
    'res':      TOOLS_DIR / 'resource_resolver.ts',
    'template': TOOLS_DIR / 'template_library.ts',
    'log':      TOOLS_DIR / 'log_capture.ts',
    'parse':    TOOLS_DIR / 'log_parser.ts',
    'logutil':  TOOLS_DIR / 'log_utils.ts',
    'input':    TOOLS_DIR / 'input_simulator.ts',
    'debug':    TOOLS_DIR / 'debug_orchestrator.ts',
    'bridge':   TOOLS_DIR / 'godox_bridge.ts',
}


def list_tools():
    """列出所有可用工具及功能"""
    tools_info = {
        'godot':    '封装 godot CLI 调用（验证/导出/运行）',
        'scaffold': '创建 Godot 4.x 项目骨架 + 目录结构',
        'scene':    '生成和编辑 .tscn 场景文件（增/删/改节点）',
        'script':   '生成 GDScript 并挂载到场景节点',
        'res':      '管理资源导入和路径解析',
        'template': '从内置游戏模板 Fork 完整项目',
        'log':      '捕获/解析 Godot 运行时日志',
        'parse':    '结构化日志解析和摘要',
        'logutil':  'GDScript 日志工具模板',
        'input':    '模拟键盘/鼠标输入，录制回放',
        'debug':    '调试闭环编排 + LLM 分析',
        'bridge':   'Godot 通信桥接（WebSocket JSON-RPC）',
        'plugin':   '启动 Godot 编辑器通信插件（godox）',
    }
    print("\n🎮 Godot Kitset 工具集\n")
    print(f"{'命令':<12} {'功能'}")
    print("-" * 60)
    for name, desc in tools_info.items():
        print(f"{name:<12} {desc}")
    print("\n用法: python tools.py <工具名> <参数>")


def run_tool(tool_name, args=None):
    """代理执行指定 TypeScript 工具"""
    if args is None:
        args = sys.argv[2:]

    if tool_name == 'list':
        list_tools()
        return 0

    if tool_name == 'plugin':
        # 插件操作：启动 Godot 插件 WebSocket 服务
        plugin_script = GODOX_DIR / 'plugin.gd'
        if not plugin_script.exists():
            logger.error(f"Godot 插件不存在: {plugin_script}")
            return 1
        cmd = ['godot', '--headless', '--script', str(plugin_script)] + args
        logger.info(f"启动 Godot 插件: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode

    script_path = TOOL_MAP.get(tool_name)
    if not script_path or not script_path.exists():
        # 尝试直接运行 .ts 文件
        script_path = TOOLS_DIR / f"{tool_name}.ts"
        if not script_path.exists():
            logger.error(f"未知工具: {tool_name}，使用 list 查看可用工具")
            return 1

    # 使用 npx tsx 运行 TypeScript
    cmd = ['npx', 'tsx', str(script_path)] + args
    logger.info(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("用法: python tools.py <tool> <args...>")
        print("     python tools.py list")
        return 1

    cmd = sys.argv[1]
    return run_tool(cmd)


if __name__ == "__main__":
    sys.exit(main())
