# 🔍 自定义识别（Custom Recognition）新手学习指南

## 📖 目录

1. [什么是自定义识别](#什么是自定义识别)
2. [Recognition 和 Action 的区别](#recognition-和-action-的区别)
3. [代码结构详解](#代码结构详解)
4. [核心知识点](#核心知识点)
5. [如何使用](#如何使用)
6. [进阶技巧](#进阶技巧)
7. [常见问题](#常见问题)

---

## 🎯 什么是自定义识别

### 简单理解

想象你在玩一个需要自动化的游戏：

- **普通识别（OCR、模板匹配）**：就像框架提供的"预设菜单"，只能识别图片、文字等简单内容
- **自定义识别（Custom Recognition）**：就像你自己编写的"智能眼睛"，可以根据复杂的逻辑来判断当前画面

### 工作流程

```
MaaFramework 执行任务
  ↓
读取 JSON 配置节点
  ↓
遇到 Custom Recognition
  ↓
调用你的 Python 识别代码
  ↓
analyze 方法分析画面
  ↓
返回识别结果（坐标、详情）
  ↓
框架根据识别结果决定下一步
```

### 典型应用场景

1. **复杂条件判断**：根据多个因素判断是否应该执行某个操作
2. **组合识别**：需要同时识别多个元素才能做出决策
3. **动态 ROI**：识别区域需要根据之前的识别结果动态调整
4. **数据收集**：在识别过程中收集和记录信息

---

## 🔄 Recognition 和 Action 的区别

### 核心差异

| 特性 | Custom Recognition | Custom Action |
|-----|-------------------|---------------|
| **职责** | **看**（分析画面，返回识别结果） | **做**（执行操作，如点击、滑动） |
| **返回值** | `AnalyzeResult`（包含坐标和详情） | `bool`（True/False） |
| **核心方法** | `analyze()` | `run()` |
| **执行时机** | 在 Action **之前** | 在 Recognition **之后** |
| **主要用途** | 判断"哪里有什么" | 执行"要做什么" |

### 生活类比

想象你要从桌上拿起一个苹果：

1. **Recognition（识别）**：你的眼睛看到桌子，找到苹果的位置（坐标），确认它是红色的（详情）
2. **Action（动作）**：你的手伸向那个位置，把苹果拿起来

### 配合使用

一个完整的 JSON 节点通常同时包含 Recognition 和 Action：

```json
{
    "找到并点击按钮": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "find_button"  // 先识别：找到按钮在哪里
            }
        },
        "action": {
            "type": "Click"  // 再动作：点击识别到的位置
        }
    }
}
```

---

## 📝 代码结构详解

### 完整示例代码

让我们从一个简单的示例开始，逐步拆解每一部分：

```python
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

@AgentServer.custom_recognition("my_reco_222")
class MyRecognition(CustomRecognition):

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        # 在这里编写你的识别逻辑

        return CustomRecognition.AnalyzeResult(
            box=(100, 200, 50, 30),  # 识别到的区域坐标
            detail="找到了目标！"    # 识别详情
        )
```

---

### 第 1 部分：导入必要的模块

```python
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
```

**知识点：每个导入的作用**

- `AgentServer`：用于注册自定义识别，让 JSON 配置能找到你的代码
- `CustomRecognition`：自定义识别的基类，提供基础功能
- `Context`：上下文对象，包含画面、控制器、任务信息等

---

### 第 2 部分：定义识别类

```python
@AgentServer.custom_recognition("my_reco_222")
class MyRecognition(CustomRecognition):
```

**知识点解析：**

#### 1. 装饰器 `@AgentServer.custom_recognition()`

```python
@AgentServer.custom_recognition("my_reco_222")
```

- **作用**：告诉 MaaFramework "我有一个自定义识别叫 `my_reco_222`"
- **类比**：就像给你的识别器贴了一个标签
- **重要**：括号里的名字要和 JSON 配置中的 `custom_recognition` 字段一致

```json
// JSON 配置中这样调用
{
    "recognition": {
        "type": "Custom",
        "param": {
            "custom_recognition": "my_reco_222"  // ← 这里要一致
        }
    }
}
```

#### 2. 类继承

```python
class MyRecognition(CustomRecognition):
```

- **MyRecognition**：你自己取的类名（建议用大驼峰命名法）
- **CustomRecognition**：继承的基类，获得基础识别功能
- **命名建议**：类名可以和装饰器名字不同，但建议相关联以便理解

---

### 第 3 部分：analyze 方法（核心）

```python
def analyze(
    self,
    context: Context,
    argv: CustomRecognition.AnalyzeArg,
) -> CustomRecognition.AnalyzeResult:
```

**参数详解：**

#### 1. `self`

- Python 类方法的标准第一个参数
- 指向当前对象本身
- 可以访问类的属性和方法

#### 2. `context: Context`

上下文对象，包含丰富的信息和功能：

```python
# 获取控制器（用于点击、滑动等）
context.tasker.controller.post_click(100, 200).wait()

# 调用其他识别任务
reco_detail = context.run_recognition(
    "MyCustomOCR",           # 要调用的识别任务名
    argv.image,              # 要识别的图像
    pipeline_override={...}  # 可选：覆盖 pipeline 配置
)

# 克隆上下文（避免污染原始 context）
new_context = context.clone()

# 覆盖 pipeline 配置
context.override_pipeline({"任务名": {"roi": [1, 1, 114, 514]}})

# 设置下一个要执行的节点
context.override_next(argv.node_name, ["任务A", "任务B"])
```

#### 3. `argv: CustomRecognition.AnalyzeArg`

包含从 JSON 传来的参数和当前画面信息：

```python
# argv 包含的属性：
argv.task_detail        # 任务详情
argv.node_name          # 当前节点名称
argv.custom_recognition_name   # 自定义识别名称
argv.custom_recognition_param  # 从 JSON 传来的参数（字符串）
argv.image              # 当前游戏画面（numpy 数组）
argv.roi                # 识别区域（Region of Interest）
```

**重要：`argv.custom_recognition_param` 是字符串！**

```python
# ❌ 错误写法
value = argv.custom_recognition_param['key']

# ✅ 正确写法
import json
params = json.loads(argv.custom_recognition_param)
value = params.get('key', '默认值')
```

#### 4. 返回值 `-> CustomRecognition.AnalyzeResult`

必须返回一个 `AnalyzeResult` 对象：

```python
return CustomRecognition.AnalyzeResult(
    box=(x, y, width, height),  # 识别到的矩形区域
    detail="识别详情"             # 识别的详细信息（字符串或字典）
)
```

---

### 第 4 部分：识别逻辑

识别逻辑是 `analyze` 方法的核心，这里可以：

1. **分析画面**
2. **调用其他识别**
3. **根据数据做判断**
4. **返回识别结果**

#### 示例 1：调用其他识别任务

```python
def analyze(self, context, argv):
    # 调用名为 "MyCustomOCR" 的识别任务
    reco_detail = context.run_recognition(
        "MyCustomOCR",
        argv.image,
        pipeline_override={
            "MyCustomOCR": {
                "roi": [100, 100, 200, 300]  # 指定识别区域
            }
        }
    )

    # 获取识别结果
    if reco_detail:
        ocr_text = reco_detail.best_result.text
        print(f"识别到文字：{ocr_text}")

    return CustomRecognition.AnalyzeResult(
        box=reco_detail.box,
        detail=f"识别结果：{ocr_text}"
    )
```

#### 示例 2：根据数据做判断

```python
import recover_helper

def analyze(self, context, argv):
    # 获取当前药水使用情况
    ap_usage = recover_helper.potion_stats.ap.small.usage
    ap_limit = recover_helper.potion_stats.ap.small.limit

    # 判断是否还能继续使用药水
    if ap_usage < ap_limit:
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail=f"可以使用药水（{ap_usage}/{ap_limit}）"
        )
    else:
        # 返回 None 或空区域表示识别失败
        return CustomRecognition.AnalyzeResult(
            box=None,  # 识别失败
            detail=f"药水已用完（{ap_usage}/{ap_limit}）"
        )
```

#### 示例 3：处理 JSON 参数

```python
import json

def analyze(self, context, argv):
    # 解析 JSON 参数
    try:
        if argv.custom_recognition_param:
            params = json.loads(argv.custom_recognition_param)
            threshold = params.get("threshold", 0.8)
            check_mode = params.get("mode", "normal")
        else:
            threshold = 0.8
            check_mode = "normal"
    except Exception as e:
        print(f"参数解析失败：{e}")
        threshold = 0.8
        check_mode = "normal"

    print(f"使用阈值：{threshold}，模式：{check_mode}")

    # 根据参数执行不同的识别逻辑
    # ...

    return CustomRecognition.AnalyzeResult(
        box=(0, 0, 100, 100),
        detail={"threshold": threshold, "mode": check_mode}
    )
```

---

### 第 5 部分：返回识别结果

```python
return CustomRecognition.AnalyzeResult(
    box=(x, y, width, height),
    detail="识别详情"
)
```

**box 参数详解：**

`box` 是一个元组或列表，表示识别到的矩形区域：

```python
# 格式：(x, y, width, height)
box = (100, 200, 50, 30)
#      ↑    ↑    ↑   ↑
#      x    y    宽  高
```

- **x**：矩形左上角的 X 坐标
- **y**：矩形左上角的 Y 坐标
- **width**：矩形的宽度
- **height**：矩形的高度

**特殊情况：**

```python
# 识别失败（框架会认为这个节点识别失败）
return CustomRecognition.AnalyzeResult(
    box=None,  # 或 (0, 0, 0, 0)
    detail="未找到目标"
)

# 识别成功，但没有具体位置（使用默认值）
return CustomRecognition.AnalyzeResult(
    box=(0, 0, 100, 100),
    detail="识别成功"
)
```

**detail 参数详解：**

`detail` 可以是字符串或字典，用于传递识别的详细信息：

```python
# 字符串形式
detail = "找到了目标按钮"

# 字典形式（可以传递更多信息）
detail = {
    "result": "success",
    "confidence": 0.95,
    "text": "确认",
    "color": "blue"
}
```

**在 Action 中访问识别结果：**

如果你的 Action 需要使用 Recognition 的识别结果：

```python
# 在 Custom Action 中
def run(self, context, argv):
    # 获取识别结果
    reco_detail = argv.reco_detail

    # 访问 detail 内容
    if reco_detail:
        result_text = reco_detail.best_result.text  # OCR 识别的文字
        detail_info = reco_detail.detail            # Custom Recognition 的 detail
        box = reco_detail.box                       # 识别到的区域

    return True
```

---

## 🔧 核心知识点总结

### 1. Recognition 特有概念

| 概念 | 说明 | 用途 |
|-----|------|------|
| **analyze 方法** | 识别的核心方法 | 分析画面，返回识别结果 |
| **AnalyzeArg** | 输入参数 | 包含画面、节点名、参数等 |
| **AnalyzeResult** | 返回结果 | 包含坐标（box）和详情（detail） |
| **box** | 矩形区域 | (x, y, width, height) |
| **detail** | 识别详情 | 字符串或字典 |

### 2. Context 常用方法

```python
# 1. 调用其他识别任务
context.run_recognition(task_name, image, pipeline_override)

# 2. 控制器操作
context.tasker.controller.post_click(x, y).wait()
context.tasker.controller.post_swipe(x1, y1, x2, y2, duration).wait()

# 3. 克隆上下文
new_context = context.clone()

# 4. 覆盖 pipeline 配置
context.override_pipeline({"任务名": {"roi": [1, 1, 100, 100]}})

# 5. 设置下一个任务
context.override_next(current_node_name, ["下一个任务A", "下一个任务B"])
```

### 3. 识别结果的影响

```python
# 识别成功 → 执行 Action
return CustomRecognition.AnalyzeResult(
    box=(100, 200, 50, 30),
    detail="success"
)

# 识别失败 → 跳过这个节点，尝试 next 中的其他节点
return CustomRecognition.AnalyzeResult(
    box=None,
    detail="failed"
)
```

---

## 🚀 如何使用

### 步骤 1：编写 Recognition 代码

在 `agent/` 目录下创建或编辑 `.py` 文件（如 `my_reco.py`）：

```python
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

@AgentServer.custom_recognition("check_potion_available")
class CheckPotionAvailable(CustomRecognition):
    """检查是否还有可用的药水"""

    def analyze(self, context, argv):
        import recover_helper

        # 获取当前药水数据
        ap_small_usage = recover_helper.potion_stats.ap.small.usage
        ap_small_limit = recover_helper.potion_stats.ap.small.limit

        # 判断是否还能使用
        if ap_small_usage < ap_small_limit:
            print(f"✓ 小 AP 药可用（{ap_small_usage}/{ap_small_limit}）")
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 100, 100),
                detail=f"可用：{ap_small_usage}/{ap_small_limit}"
            )
        else:
            print(f"✗ 小 AP 药已用完（{ap_small_usage}/{ap_small_limit}）")
            return CustomRecognition.AnalyzeResult(
                box=None,  # 识别失败
                detail=f"已用完：{ap_small_usage}/{ap_small_limit}"
            )
```

---

### 步骤 2：确保 main.py 加载了这个模块

检查 `agent/main.py`，确保导入了你的识别模块：

```python
# agent/main.py
import recover_action
import recover_reco  # ← 确保导入了识别模块
import my_reco
```

---

### 步骤 3：在 JSON 配置中调用

#### 方式 1：基础用法

```json
{
    "检查药水是否可用": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "check_potion_available"
            }
        },
        "action": {
            "type": "DoNothing"
        },
        "next": [
            "使用药水",
            "药水用完"
        ]
    }
}
```

#### 方式 2：传递参数

```json
{
    "检查药水是否可用": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "check_potion_available",
                "custom_recognition_param": "{\"threshold\": 0.8, \"mode\": \"strict\"}"
            }
        },
        "action": {
            "type": "DoNothing"
        }
    }
}
```

**注意：** `custom_recognition_param` 必须是 JSON 字符串（需要转义引号）

#### 方式 3：简化写法（推荐）

从示例 `custom_demo.json` 中可以看到，还有一种更简洁的写法：

```json
{
    "检查药水是否可用": {
        "recognition": "Custom",
        "custom_recognition": "check_potion_available",
        "custom_recognition_param": {
            "threshold": 0.8,
            "mode": "strict"
        },
        "action": "DoNothing"
    }
}
```

这种写法中，`custom_recognition_param` 可以直接写成对象，不需要手动转义。

---

### 步骤 4：运行测试

1. 运行你的 MaaFramework 项目
2. 观察控制台输出
3. 检查识别是否按预期工作

---

## 🎓 进阶技巧

### 1. 使用 context.clone() 避免污染

```python
def analyze(self, context, argv):
    # 原始 context 会影响整个任务流
    context.override_pipeline({"Task": {"roi": [1, 1, 100, 100]}})

    # 使用 clone() 创建独立的 context
    new_context = context.clone()
    new_context.override_pipeline({"Task": {"roi": [200, 200, 300, 300]}})

    # new_context 的修改不会影响原始 context
    reco_result = new_context.run_recognition("Task", argv.image)

    return CustomRecognition.AnalyzeResult(
        box=reco_result.box,
        detail="使用独立 context 识别"
    )
```

### 2. 动态调整识别区域

```python
def analyze(self, context, argv):
    # 第一步：在较大区域找到目标
    first_reco = context.run_recognition(
        "FindTarget",
        argv.image,
        pipeline_override={
            "FindTarget": {"roi": [0, 0, 1920, 1080]}
        }
    )

    if first_reco and first_reco.box:
        # 第二步：在第一步的结果附近进行精确识别
        x, y, w, h = first_reco.box
        context.run_recognition(
            "PreciseCheck",
            argv.image,
            pipeline_override={
                "PreciseCheck": {
                    "roi": [x - 50, y - 50, w + 100, h + 100]
                }
            }
        )

    return CustomRecognition.AnalyzeResult(
        box=first_reco.box,
        detail="动态调整识别区域"
    )
```

### 3. 组合多个识别结果

```python
def analyze(self, context, argv):
    results = []

    # 识别多个目标
    for task_name in ["Target1", "Target2", "Target3"]:
        reco = context.run_recognition(task_name, argv.image)
        if reco:
            results.append({
                "task": task_name,
                "box": reco.box,
                "text": reco.best_result.text if reco.best_result else ""
            })

    # 判断是否所有目标都找到了
    if len(results) == 3:
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail={"status": "all_found", "results": results}
        )
    else:
        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={"status": "incomplete", "results": results}
        )
```

### 4. 在识别中执行控制操作

虽然通常不推荐在 Recognition 中执行 Action，但在某些特殊情况下可以这样做：

```python
def analyze(self, context, argv):
    # 执行一次点击（谨慎使用！）
    click_job = context.tasker.controller.post_click(100, 200)
    click_job.wait()  # 等待点击完成

    # 然后再进行识别
    reco_result = context.run_recognition("AfterClick", argv.image)

    return CustomRecognition.AnalyzeResult(
        box=reco_result.box if reco_result else None,
        detail="点击后识别"
    )
```

**注意：** 这种做法打破了"识别只负责看，动作负责做"的原则，只在必要时使用。

---

## ❓ 常见问题

### Q1: Recognition 和 Action 什么时候用哪个？

**A:** 记住一个原则：

- **需要判断"看到了什么"** → 用 Custom Recognition
- **需要执行"做什么操作"** → 用 Custom Action

```python
# ✓ 正确：用 Recognition 判断
@AgentServer.custom_recognition("check_hp_low")
class CheckHPLow(CustomRecognition):
    def analyze(self, context, argv):
        # 识别当前 HP 是否过低
        hp_value = get_current_hp(argv.image)
        if hp_value < 30:
            return AnalyzeResult(box=(0,0,1,1), detail="HP低")
        return AnalyzeResult(box=None, detail="HP正常")

# ✓ 正确：用 Action 执行操作
@AgentServer.custom_action("use_healing_item")
class UseHealingItem(CustomAction):
    def run(self, context, argv):
        # 使用治疗道具
        context.controller.post_click(500, 600).wait()
        return True
```

### Q2: `box=None` 和 `box=(0,0,0,0)` 有什么区别？

**A:**

- **`box=None`**：明确表示识别失败，框架会跳过这个节点
- **`box=(0,0,0,0)`**：技术上也表示空区域，但不如 `None` 语义明确
- **`box=(0,0,100,100)`**：表示识别成功，返回一个有效区域

**推荐做法：**

```python
# 识别失败
if not found:
    return CustomRecognition.AnalyzeResult(
        box=None,
        detail="未找到目标"
    )

# 识别成功
return CustomRecognition.AnalyzeResult(
    box=(x, y, w, h),
    detail="找到了目标"
)
```

### Q3: 如何调试我的 Recognition 代码？

**A:** 使用 `print()` 和 `logging` 输出调试信息：

```python
import logging

def analyze(self, context, argv):
    print(f"当前节点：{argv.node_name}")
    print(f"图像尺寸：{argv.image.shape}")
    print(f"ROI 区域：{argv.roi}")

    logging.info(f"开始识别：{argv.custom_recognition_name}")

    # 你的识别逻辑
    result = some_recognition_logic()

    print(f"识别结果：{result}")

    return CustomRecognition.AnalyzeResult(
        box=result.box,
        detail=result.detail
    )
```

### Q4: `argv.custom_recognition_param` 是空的怎么办？

**A:** 总是检查参数是否存在，并提供默认值：

```python
import json

def analyze(self, context, argv):
    # 安全地解析参数
    try:
        if argv.custom_recognition_param:
            params = json.loads(argv.custom_recognition_param)
        else:
            params = {}  # 空字典
    except Exception as e:
        print(f"参数解析失败：{e}")
        params = {}

    # 使用 get() 提供默认值
    threshold = params.get("threshold", 0.8)
    mode = params.get("mode", "normal")

    # 继续你的逻辑...
```

### Q5: 如何在 Recognition 中访问全局数据？

**A:** 可以导入其他模块来共享数据：

```python
# recover_helper.py
class DataManager:
    count = 0
    status = "idle"

data_manager = DataManager()

# my_reco.py
import recover_helper

def analyze(self, context, argv):
    # 读取全局数据
    current_count = recover_helper.data_manager.count

    # 修改全局数据
    recover_helper.data_manager.count += 1
    recover_helper.data_manager.status = "running"

    return CustomRecognition.AnalyzeResult(
        box=(0, 0, 100, 100),
        detail=f"count: {current_count}"
    )
```

### Q6: 识别失败后会怎样？

**A:** 当 Recognition 返回 `box=None` 时：

1. MaaFramework 认为这个节点**识别失败**
2. 跳过这个节点的 Action
3. 尝试执行 `next` 列表中的其他节点
4. 如果没有 `next` 或都失败，任务可能会超时或停止

```json
{
    "检查药水": {
        "recognition": "Custom",
        "custom_recognition": "check_potion",
        "action": "Click",  // 识别失败时不会执行
        "next": [
            "使用药水",     // 识别成功时执行
            "药水用完"      // 识别失败时可能会尝试这个
        ]
    }
}
```

### Q7: 可以在 Recognition 中调用 Action 吗？

**A:** 技术上可以（使用 `context.tasker.controller`），但**强烈不推荐**！

**为什么不推荐：**

- 违反了"识别只看，动作只做"的设计原则
- 让代码逻辑变得混乱，难以维护
- 可能导致意外的副作用

**正确做法：**

```python
# ✗ 不推荐：在 Recognition 中点击
def analyze(self, context, argv):
    context.tasker.controller.post_click(100, 200).wait()
    # ...

# ✓ 推荐：分离识别和动作
# Recognition: 只负责识别
def analyze(self, context, argv):
    # 只做识别逻辑
    return AnalyzeResult(box=(100, 200, 50, 30), detail="found")

# Action: 负责点击
def run(self, context, argv):
    context.controller.post_click(100, 200).wait()
    return True
```

**唯一例外：** 某些极特殊场景下，需要先执行一个操作，再基于结果进行识别（但这种情况很少见）。

---

## 🎯 下一步学习

### 推荐学习路径

1. **实践基础**：修改示例代码，添加简单的判断逻辑
2. **阅读项目代码**：查看 `agent/my_reco.py` 和 `agent/recover_reco.py`
3. **组合使用**：学习如何让 Recognition 和 Action 配合工作
4. **进阶技巧**：尝试使用 `context.clone()` 和动态 ROI

### 练习项目建议

1. **药水检测器**：编写一个 Recognition，检查当前药水是否充足
2. **多目标识别**：同时识别多个按钮，并返回最合适的那个
3. **条件路由**：根据识别结果，动态设置 `next` 节点

---

## 📚 相关资源

- **项目文档**：
  - `docs/learn/README_RECOVER_ACTION.md` - 自定义动作教程（姊妹篇）
  - `agent/my_reco.py` - 识别示例代码
  - `agent/recover_reco.py` - 实际应用示例

- **外部资源**：
  - [MaaFramework 官方文档](https://github.com/MaaXYZ/MaaFramework)
  - [Python 基础教程](https://www.runoob.com/python3/python3-tutorial.html)
  - [JSON 格式说明](https://www.json.org/json-zh.html)

---

## 📝 总结

### 记住这些关键点

1. **Recognition 负责"看"，Action 负责"做"**
2. **`analyze()` 方法必须返回 `AnalyzeResult`**
3. **`box=None` 表示识别失败**
4. **`custom_recognition_param` 是 JSON 字符串，需要解析**
5. **使用 `context.clone()` 避免污染全局 context**

### 最佳实践

✓ 识别逻辑简单清晰
✓ 充分利用 `detail` 传递信息
✓ 使用 `try-except` 处理异常
✓ 添加日志方便调试
✓ 保持 Recognition 和 Action 职责分离

---

**祝你学习愉快！有问题随时问我！** 🎉

---

*文档版本：v1.0*
*最后更新：2025-12-29*
