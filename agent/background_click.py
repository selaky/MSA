# 后台点击测试模块
# 实现绕过游戏物理指针校验和激活状态校验的后台点击方案

import ctypes
import ctypes.wintypes as wintypes
import logging
import json
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

# Windows API 常量
WM_ACTIVATE = 0x0006
WA_ACTIVE = 1
WA_INACTIVE = 0
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

# 加载 Windows API
user32 = ctypes.windll.user32

# 定义 API 函数签名
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM

user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL

user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL


def make_lparam(x: int, y: int) -> int:
    """将客户区坐标打包为 lParam 格式"""
    return (y << 16) | (x & 0xFFFF)


def find_game_window() -> wintypes.HWND:
    """查找游戏窗口句柄"""
    # 根据 interface.json 中的配置，窗口标题包含 "StarEra"
    hwnd = user32.FindWindowW(None, "StarEra")
    if not hwnd:
        # 尝试模糊匹配
        def enum_callback(hwnd, results):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if "StarEra" in buff.value:
                    results.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        results = []
        user32.EnumWindows(WNDENUMPROC(lambda h, _: enum_callback(h, results)), 0)
        if results:
            hwnd = results[0]

    return hwnd


def get_window_client_size(hwnd: wintypes.HWND) -> tuple:
    """获取窗口客户区大小"""
    rect = wintypes.RECT()
    if user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return (rect.right - rect.left, rect.bottom - rect.top)
    return (0, 0)


def scale_coordinates(maa_x: int, maa_y: int, hwnd: wintypes.HWND) -> tuple:
    """
    将 MAA 缩放后的坐标转换为实际窗口客户区坐标

    MAA 默认将截图缩放到短边 720 像素
    """
    actual_width, actual_height = get_window_client_size(hwnd)
    if actual_width == 0 or actual_height == 0:
        logging.warning("[坐标转换] 无法获取窗口大小，使用原始坐标")
        return (maa_x, maa_y)

    # 计算缩放比例（MAA 默认短边 720）
    short_side = min(actual_width, actual_height)
    scale = short_side / 720.0

    # 转换坐标
    real_x = int(maa_x * scale)
    real_y = int(maa_y * scale)

    logging.info(f"[坐标转换] 窗口大小: {actual_width}x{actual_height}, 缩放比例: {scale:.3f}")
    logging.info(f"[坐标转换] MAA坐标: ({maa_x}, {maa_y}) -> 实际坐标: ({real_x}, {real_y})")

    return (real_x, real_y)


def background_click(hwnd: wintypes.HWND, client_x: int, client_y: int) -> bool:
    """
    执行后台点击操作

    核心流程：
    1. 保存现场：记录当前物理鼠标坐标
    2. 伪造激活：向游戏窗口发送激活消息
    3. 物理瞬移：将物理鼠标强制移动到游戏按钮坐标
    4. 同步按下：发送鼠标按下指令
    5. 同步抬起：发送鼠标抬起指令
    6. 归位现场：立即将物理鼠标瞬移回原始坐标
    7. 状态复原：发送失去焦点消息

    Args:
        hwnd: 游戏窗口句柄
        client_x: 客户区 X 坐标
        client_y: 客户区 Y 坐标

    Returns:
        bool: 操作是否成功
    """
    if not hwnd:
        logging.error("[后台点击] 无效的窗口句柄")
        return False

    # 1. 保存现场：记录当前物理鼠标坐标
    original_pos = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(original_pos)):
        logging.error("[后台点击] 获取鼠标位置失败")
        return False

    logging.info(f"[后台点击] 原始鼠标位置: ({original_pos.x}, {original_pos.y})")

    # 计算屏幕坐标（用于 SetCursorPos）
    screen_point = wintypes.POINT(client_x, client_y)
    if not user32.ClientToScreen(hwnd, ctypes.byref(screen_point)):
        logging.error("[后台点击] 坐标转换失败")
        return False

    logging.info(f"[后台点击] 目标屏幕坐标: ({screen_point.x}, {screen_point.y})")

    # 构造 lParam（客户区坐标）
    lparam = make_lparam(client_x, client_y)

    try:
        # 2. 伪造激活：向游戏窗口发送激活消息
        # 先发送消息利用其阻塞时间处理游戏内部状态
        user32.SendMessageW(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
        logging.info("[后台点击] 已发送激活消息")

        # 3. 物理瞬移：将物理鼠标强制移动到游戏按钮坐标
        # 鼠标劫持窗口期开始
        user32.SetCursorPos(screen_point.x, screen_point.y)
        logging.info("[后台点击] 已移动鼠标到目标位置")

        # 4. 同步按下：发送鼠标按下指令
        user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        logging.info("[后台点击] 已发送鼠标按下消息")

        # 5. SendMessage 的阻塞特性产生的自然开销即可满足时序要求

        # 6. 同步抬起：发送鼠标抬起指令
        # 必须使用 SendMessage 确保游戏处理完 UP 事件前，物理鼠标绝对不动
        user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
        logging.info("[后台点击] 已发送鼠标抬起消息")

        # 7. 归位现场：立即将物理鼠标瞬移回原始坐标
        # 鼠标劫持窗口期结束
        user32.SetCursorPos(original_pos.x, original_pos.y)
        logging.info("[后台点击] 已恢复鼠标位置")

        # 8. 状态复原：发送失去焦点消息
        user32.SendMessageW(hwnd, WM_ACTIVATE, WA_INACTIVE, 0)
        logging.info("[后台点击] 已发送失活消息")

        return True

    except Exception as e:
        logging.error(f"[后台点击] 执行过程中发生异常: {e}")
        # 尝试恢复鼠标位置
        user32.SetCursorPos(original_pos.x, original_pos.y)
        return False


@AgentServer.custom_action("background_click_test")
class BackgroundClickTest(CustomAction):
    """后台点击测试动作"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        logging.info("[后台点击测试] 开始执行")

        # 解析参数
        try:
            params = json.loads(argv.custom_action_param)
            target_x = int(params.get("x", 0))
            target_y = int(params.get("y", 0))
        except Exception as e:
            logging.error(f"[后台点击测试] 参数解析失败: {e}")
            return False

        logging.info(f"[后台点击测试] 目标坐标: ({target_x}, {target_y})")

        # 查找游戏窗口
        hwnd = find_game_window()
        if not hwnd:
            logging.error("[后台点击测试] 未找到游戏窗口")
            return False

        logging.info(f"[后台点击测试] 找到游戏窗口句柄: {hwnd}")

        # 执行后台点击
        result = background_click(hwnd, target_x, target_y)

        if result:
            logging.info("[后台点击测试] 点击成功")
        else:
            logging.error("[后台点击测试] 点击失败")

        return result


@AgentServer.custom_action("background_click_reco")
class BackgroundClickWithReco(CustomAction):
    """基于识别结果的后台点击动作"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        logging.info("[后台点击(识别)] 开始执行")

        # 从识别结果获取点击位置
        if argv.reco_detail and argv.reco_detail.best_result:
            box = argv.reco_detail.best_result.box
            # 计算中心点（MAA 缩放后的坐标）
            maa_x = box[0] + box[2] // 2
            maa_y = box[1] + box[3] // 2
            logging.info(f"[后台点击(识别)] 从识别结果获取坐标: box={box}, center=({maa_x}, {maa_y})")
        else:
            logging.error("[后台点击(识别)] 无识别结果")
            return False

        # 查找游戏窗口
        hwnd = find_game_window()
        if not hwnd:
            logging.error("[后台点击(识别)] 未找到游戏窗口")
            return False

        logging.info(f"[后台点击(识别)] 找到游戏窗口句柄: {hwnd}")

        # 坐标转换：MAA 缩放坐标 -> 实际窗口坐标
        target_x, target_y = scale_coordinates(maa_x, maa_y, hwnd)

        # 执行后台点击
        result = background_click(hwnd, target_x, target_y)

        if result:
            logging.info("[后台点击(识别)] 点击成功")
        else:
            logging.error("[后台点击(识别)] 点击失败")

        return result
