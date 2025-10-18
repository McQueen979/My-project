import pyautogui
import time
import tkinter as tk
from PIL import ImageGrab
import numpy as np
import math
import threading
import keyboard  # 需要安装：pip install keyboard

# 屏幕物理尺寸（厘米）
SCREEN_WIDTH_CM = 47.7
SCREEN_HEIGHT_CM = 29.9
# 屏幕分辨率
SCREEN_WIDTH_PX = 1920
SCREEN_HEIGHT_PX = 1080

# 计算每像素对应的厘米数
CM_PER_PIXEL_X = SCREEN_WIDTH_CM / SCREEN_WIDTH_PX
CM_PER_PIXEL_Y = SCREEN_HEIGHT_CM / SCREEN_HEIGHT_PX

# 全局变量
measurement_mode = 1  # 1:手动输入 2:键盘快捷键
start_point = None
end_point = None

def find_pos():
    x, y = pyautogui.position()
    print(f"当前鼠标位置: ({x}, {y}) 像素")
    status_label.config(text=f"已记录位置: ({x}, {y}) 像素")
    return x, y

def capture_screen():
    """捕获当前屏幕并返回图像"""
    return ImageGrab.grab()

def get_color_difference(pixel1, pixel2):
    """计算两个像素之间的颜色差异"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(pixel1, pixel2)))

def px_to_cm(pixels):
    """将像素距离转换为厘米距离（取X/Y方向的平均值）"""
    return pixels * (CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2

def detect_two_points():
    """检测屏幕上的两个点（起点和终点）"""
    global measurement_mode, start_point, end_point
    
    if measurement_mode == 1:  # 手动输入模式
        try:
            distance_cm = float(entry.get())
            distance_px = distance_cm / ((CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2)
            print(f"手动输入距离: {distance_px:.2f} 像素 = {distance_cm:.2f} 厘米")
            status_label.config(text=f"手动输入距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)")
            return 0, 0, 0, 0, distance_px, distance_cm
        except ValueError:
            print("请输入有效的距离值")
            status_label.config(text="错误: 请输入有效的距离值")
            return None
    
    elif measurement_mode == 2:  # 键盘快捷键模式
        print("请将鼠标移动到起点位置，按数字键盘'/'记录起点...")
        status_label.config(text="请将鼠标移动到起点位置，按数字键盘'/'记录起点...")
        
        # 等待用户按数字键盘/
        keyboard.wait('numpad_divide')
        start_point = pyautogui.position()
        print(f"已记录起点: ({start_point.x}, {start_point.y}) 像素")
        status_label.config(text=f"已记录起点: ({start_point.x}, {start_point.y}) 像素\n请移动到终点按数字键盘'*'")
        
        # 等待用户按数字键盘*
        keyboard.wait('numpad_multiply')
        end_point = pyautogui.position()
        print(f"已记录终点: ({end_point.x}, {end_point.y}) 像素")
        
        # 计算两点之间的像素距离
        distance_px = math.sqrt((end_point.x - start_point.x) ** 2 + (end_point.y - start_point.y) ** 2)
        # 转换为厘米
        distance_cm = px_to_cm(distance_px)
        
        print(f"两点距离: {distance_px:.2f} 像素 = {distance_cm:.2f} 厘米")
        status_label.config(text=f"已计算距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)\n按数字键盘'-'执行跳跃")
        
        # 自动填充距离到输入框（使用厘米单位）
        entry.delete(0, tk.END)
        entry.insert(0, str(distance_cm))
        
        return start_point.x, start_point.y, end_point.x, end_point.y, distance_px, distance_cm

def move_mouse(x_pos, y_pos):
    try:
        pyautogui.moveTo(x_pos, y_pos)
    except Exception as e:
        print(f"移动鼠标时出错: {e}")
        status_label.config(text=f"错误: {e}")

def click_and_hold(duration):
    try:
        # 获取输入的坐标
        x_pos = int(entry_x.get())
        y_pos = int(entry_y.get())
        
        # 移动到指定位置并点击保持
        move_mouse(x_pos, y_pos)
        status_label.config(text=f"正在点击并保持 {duration:.2f} 秒...")
        root.update()
        
        pyautogui.mouseDown()
        time.sleep(duration)
        pyautogui.mouseUp()
        
        status_label.config(text=f"已完成点击，持续时间: {duration:.2f} 秒")
    except Exception as e:
        print(f"点击操作出错: {e}")
        status_label.config(text=f"错误: {e}")

def calculate_jump_time(distance_cm):
    """根据厘米距离计算跳跃时间（需要重新拟合函数）"""
    # 使用新的拟合函数（示例值，可能需要根据实际情况调整）
    return 0.11 * distance_cm + 0.05

def auto_play():
    """自动检测两点并执行跳跃"""
    status_label.config(text="开始自动游戏...")
    root.update()
    
    # 检测两点
    result = detect_two_points()
    if result is None:
        return
    
    start_x, start_y, end_x, end_y, distance_px, distance_cm = result
    
    # 计算跳跃时间（使用厘米单位）
    jump_time = calculate_jump_time(distance_cm)
    print(f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    
    # 执行跳跃
    click_and_hold(jump_time)

def digi():
    try:
        # 获取输入的距离（厘米）
        newlength_cm = float(entry.get())
        # 计算跳跃时间
        jump_time = calculate_jump_time(newlength_cm)
        print(f"输入距离: {newlength_cm:.2f} 厘米, 计算跳跃时间: {jump_time:.2f} 秒")
        status_label.config(text=f"输入距离: {newlength_cm:.2f} 厘米, 跳跃时间: {jump_time:.2f} 秒")
        # 执行点击
        click_and_hold(jump_time)
    except ValueError:
        print("请输入有效的距离值")
        status_label.config(text="错误: 请输入有效的距离值")
    except Exception as e:
        print(f"执行跳跃时出错: {e}")
        status_label.config(text=f"错误: {e}")

def set_mode(mode):
    """设置测量模式"""
    global measurement_mode
    measurement_mode = mode
    
    if mode == 1:
        status_label.config(text="已切换到方式一：手动输入距离")
        entry.config(state=tk.NORMAL)  # 启用输入框
    else:
        status_label.config(text="已切换到方式二：使用数字键盘快捷键测量")
        entry.config(state=tk.DISABLED)  # 禁用输入框

def keyboard_listener():
    """键盘监听器线程"""
    global measurement_mode, start_point, end_point
    
    while True:
        # 等待数字键盘-键
        keyboard.wait('numpad_subtract')
        
        # 只有在模式2且两点都已记录时执行
        if measurement_mode == 2 and start_point and end_point:
            # 计算距离
            distance_px = math.sqrt((end_point.x - start_point.x) ** 2 + (end_point.y - start_point.y) ** 2)
            distance_cm = px_to_cm(distance_px)
            
            # 计算跳跃时间
            jump_time = calculate_jump_time(distance_cm)
            print(f"执行跳跃: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
            status_label.config(text=f"执行跳跃: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
            
            # 执行点击
            click_and_hold(jump_time)

# 创建GUI
root = tk.Tk()
root.geometry("500x400")
root.title("微信跳一跳自动助手 (厘米单位)")

# 状态标签
status_label = tk.Label(root, text="就绪", fg="blue", font=("Arial", 10))
status_label.pack(pady=10)

# 测量模式选择
label_mode = tk.Label(root, text="选择测量方式:")
label_mode.pack()

frame_mode = tk.Frame(root)
frame_mode.pack()

button_mode1 = tk.Button(frame_mode, text="方式一: 手动输入距离", command=lambda: set_mode(1))
button_mode1.pack(side=tk.LEFT, padx=5)

button_mode2 = tk.Button(frame_mode, text="方式二: 键盘快捷键", command=lambda: set_mode(2))
button_mode2.pack(side=tk.LEFT, padx=5)

# 寻找鼠标位置功能
label_find = tk.Label(root, text="鼠标位置探测")
label_find.pack()

button_find = tk.Button(root, text="记录当前鼠标位置", command=find_pos)
button_find.pack()

# 自动检测两点距离功能
label_auto = tk.Label(root, text="自动检测功能")
label_auto.pack()

button_auto = tk.Button(root, text="自动检测两点距离", command=detect_two_points)
button_auto.pack()

# 自动游戏功能
label_play = tk.Label(root, text="自动游戏")
label_play.pack()

button_play = tk.Button(root, text="开始自动游戏", command=auto_play, bg="green", fg="white")
button_play.pack()

# 设置点击位置
label_pos = tk.Label(root, text="设置点击位置 (x,y 像素):")
label_pos.pack()

entry_x = tk.Entry(root)
entry_x.insert(0, "960")  # 默认X坐标（1920分辨率中点）
entry_x.pack()

entry_y = tk.Entry(root)
entry_y.insert(0, "800")  # 默认Y坐标（1080分辨率偏下）
entry_y.pack()

# 手动输入距离（厘米）
label = tk.Label(root, text="输入距离 (厘米):")
label.pack()

entry = tk.Entry(root)
entry.pack()

button = tk.Button(root, text="手动执行跳跃", command=digi)
button.pack()

# 说明标签
info_label = tk.Label(
    root, 
    text="使用说明:\n"
         "1. 先将微信跳一跳窗口最大化\n"
         "2. 选择测量方式:\n"
         "   - 方式一: 手动输入距离后点击按钮\n"
         "   - 方式二: 按数字键盘'/'记录起点，'*'记录终点，'-'执行跳跃\n"
         "3. 设置点击位置（默认为屏幕中央偏下）\n"
         "4. 点击开始自动游戏或使用快捷键执行跳跃",
    justify=tk.LEFT,
    font=("Arial", 9)
)
info_label.pack(pady=10)

# 启动键盘监听器线程
keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
keyboard_thread.start()

root.mainloop()