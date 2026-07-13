# Bobanana 5.0 — CL出口修复 + 仪表盘自动弹出 技术说明

## 目标
1. client-gate (CL) 成为管线**唯一出口**，没有其他节点能到达 terminal
2. bobanana.py 增加功能：管线完成后自动弹出 EUI-NEO 仪表盘窗口

## 状态机拓扑（v3）
```
Boss → 架构师 → fullstack-dev → 架构师验收 → client-gate → DONE (score≥9)
                                                      ↓ (score<9)
                                                    架构师 (打回修复)
```

## Bobanana.py 修改规格 (fullstack-dev 执行)

### 新增函数 `dash_launch()`
```python
def dash_launch():
    """管线完成后自动弹出仪表盘"""
    dashboard_exe = os.path.join('eui_neo_app', 'build-eui', 'bobanana_gui.exe')
    if os.path.exists(dashboard_exe):
        subprocess.Popen([dashboard_exe], cwd='.')
        log("仪表盘已启动", 'ok')
    else:
        log("仪表盘未编译，请先运行: cmake --build eui_neo_app/build-eui", 'warn')
```

### 调用时机
- 在 `run_pipeline()` 成功完成管线后调用
- 在 CLI 交互菜单中用户选择"运行管线"完成后调用
- 在 `check_env()` 末尾可选调用（如果已编译）

### 验收标准
- `dash_launch()` 执行后弹出 bobanana_gui.exe 窗口
- 如果 exe 不存在，输出提示而非崩溃
- 无需等待仪表盘关闭，异步启动
