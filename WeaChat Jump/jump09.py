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

# 距离与点击时间函数参数
distance_factor = 0.11
time_offset = 0.05

def find_pos():
    x, y = pyautogui.position()
    print(f"当前鼠标位置: ({x}, {y}) 像素")
    status_label.config(text=f"当前鼠标位置: ({x}, {y}) 像素")
    return x, y

def px_to_cm(pixels):
    """将像素距离转换为厘米距离（取X/Y方向的平均值）"""
    return pixels * (CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2

def calculate_distance():
    """根据选择的模式计算距离"""
    global measurement_mode, start_point, end_point
    
    if measurement_mode == 1:  # 手动输入模式
        try:
            distance_cm = float(entry_distance.get())
            distance_px = distance_cm / ((CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2)
            print(f"手动输入距离: {distance_px:.2f} 像素 = {distance_cm:.2f} 厘米")
            status_label.config(text=f"手动输入距离: {distance_cm:.2f} 厘米")
            return distance_cm
        except ValueError:
            print("请输入有效的距离值")
            status_label.config(text="错误: 请输入有效的距离值")
            return None
    
    elif measurement_mode == 2:  # 键盘快捷键模式
        if not start_point or not end_point:
            status_label.config(text="请先使用快捷键记录起点和终点")
            return None
        
        # 计算两点之间的像素距离
        distance_px = math.sqrt((end_point.x - start_point.x) ** 2 + (end_point.y - start_point.y) ** 2)
        # 转换为厘米
        distance_cm = px_to_cm(distance_px)
        
        print(f"两点距离: {distance_px:.2f} 像素 = {distance_cm:.2f} 厘米")
        status_label.config(text=f"测量距离: {distance_cm:.2f} 厘米")
        
        # 自动填充距离到输入框
        entry_distance.delete(0, tk.END)
        entry_distance.insert(0, str(distance_cm))
        
        return distance_cm

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
    """根据厘米距离计算跳跃时间"""
    global distance_factor, time_offset
    return distance_factor * distance_cm + time_offset

def update_function_params():
    """更新距离与时间函数的参数"""
    global distance_factor, time_offset
    try:
        distance_factor = float(entry_factor.get())
        time_offset = float(entry_offset.get())
        status_label.config(text=f"已更新函数参数: 时间 = {distance_factor} × 距离 + {time_offset}")
    except ValueError:
        status_label.config(text="错误: 请输入有效的数值")

def execute_jump():
    """执行跳跃操作"""
    distance_cm = calculate_distance()
    if distance_cm is None:
        return
    
    # 计算跳跃时间
    jump_time = calculate_jump_time(distance_cm)
    print(f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    
    # 执行跳跃
    click_and_hold(jump_time)

def set_mode(mode):
    """设置测量模式"""
    global measurement_mode, start_point, end_point
    measurement_mode = mode
    start_point = None
    end_point = None
    
    if mode == 1:
        status_label.config(text="已切换到方式一：手动输入距离")
        entry_distance.config(state=tk.NORMAL)  # 启用输入框
    else:
        status_label.config(text="已切换到方式二：使用数字键盘快捷键测量")
        entry_distance.config(state=tk.DISABLED)  # 禁用输入框
        status_label.config(text="请将鼠标移动到起点位置，按数字键盘'/'记录起点...")

def keyboard_listener():
    """键盘监听器线程"""
    global measurement_mode, start_point, end_point
    
    while True:
        # 等待数字键盘按键
        event = keyboard.read_event(suppress=True)
        
        if event.event_type == keyboard.KEY_DOWN:
            if measurement_mode == 2:  # 仅在键盘模式下响应
                if event.name == 'numpad_divide':  # 记录起点
                    start_point = pyautogui.position()
                    print(f"已记录起点: ({start_point.x}, {start_point.y}) 像素")
                    status_label.config(text=f"已记录起点: ({start_point.x}, {start_point.y}) 像素\n请移动到终点按数字键盘'*'")
                
                elif event.name == 'numpad_multiply':  # 记录终点
                    if not start_point:
                        status_label.config(text="请先记录起点位置")
                        continue
                        
                    end_point = pyautogui.position()
                    print(f"已记录终点: ({end_point.x}, {end_point.y}) 像素")
                    
                    # 计算两点之间的像素距离
                    distance_px = math.sqrt((end_point.x - start_point.x) ** 2 + (end_point.y - start_point.y) ** 2)
                    # 转换为厘米
                    distance_cm = px_to_cm(distance_px)
                    
                    status_label.config(text=f"已计算距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)\n按数字键盘'-'执行跳跃")
                
                elif event.name == 'numpad_subtract':  # 执行跳跃
                    if start_point and end_point:
                        execute_jump()
                    else:
                        status_label.config(text="请先记录起点和终点位置")

# 创建GUI
root = tk.Tk()
root.geometry("500x450")
root.title("微信跳一跳自动助手 (厘米单位)")

# 状态标签
status_label = tk.Label(root, text="就绪", fg="blue", font=("Arial", 10))
status_label.pack(pady=10)

# 测量模式选择
label_mode = tk.Label(root, text="选择测量方式:", font=("Arial", 10, "bold"))
label_mode.pack(pady=5)

frame_mode = tk.Frame(root)
frame_mode.pack(pady=5)

button_mode1 = tk.Button(frame_mode, text="方式一: 手动输入距离", command=lambda: set_mode(1), 
                        width=18, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
button_mode1.pack(side=tk.LEFT, padx=5)

button_mode2 = tk.Button(frame_mode, text="方式二: 键盘快捷键", command=lambda: set_mode(2), 
                        width=18, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
button_mode2.pack(side=tk.LEFT, padx=5)

# 距离输入区域
frame_distance = tk.LabelFrame(root, text="跳跃距离", font=("Arial", 10, "bold"))
frame_distance.pack(fill="x", padx=10, pady=10)

label_distance = tk.Label(frame_distance, text="距离 (厘米):")
label_distance.pack(side=tk.LEFT, padx=10)

entry_distance = tk.Entry(frame_distance, width=15)
entry_distance.pack(side=tk.LEFT, padx=5)
entry_distance.insert(0, "0.0")

button_calculate = tk.Button(frame_distance, text="计算跳跃", command=execute_jump, 
                            bg="#52c41a", fg="white", width=12, height=1)
button_calculate.pack(side=tk.RIGHT, padx=10)

# 设置点击位置
frame_position = tk.LabelFrame(root, text="点击位置设置", font=("Arial", 10, "bold"))
frame_position.pack(fill="x", padx=10, pady=10)

label_x = tk.Label(frame_position, text="X坐标 (像素):")
label_x.pack(side=tk.LEFT, padx=10)

entry_x = tk.Entry(frame_position, width=10)
entry_x.pack(side=tk.LEFT, padx=5)
entry_x.insert(0, "960")  # 默认X坐标

label_y = tk.Label(frame_position, text="Y坐标 (像素):")
label_y.pack(side=tk.LEFT, padx=10)

entry_y = tk.Entry(frame_position, width=10)
entry_y.pack(side=tk.LEFT, padx=5)
entry_y.insert(0, "800")  # 默认Y坐标

# 距离与时间函数参数设置
frame_function = tk.LabelFrame(root, text="距离与时间函数设置", font=("Arial", 10, "bold"))
frame_function.pack(fill="x", padx=10, pady=10)

label_function = tk.Label(frame_function, text="时间 = 系数 × 距离 + 偏移量", font=("Arial", 9))
label_function.pack(pady=5)

frame_params = tk.Frame(frame_function)
frame_params.pack(fill="x", padx=10, pady=5)

label_factor = tk.Label(frame_params, text="系数:")
label_factor.pack(side=tk.LEFT, padx=5)

entry_factor = tk.Entry(frame_params, width=8)
entry_factor.pack(side=tk.LEFT, padx=5)
entry_factor.insert(0, str(distance_factor))

label_offset = tk.Label(frame_params, text="偏移量:")
label_offset.pack(side=tk.LEFT, padx=5)

entry_offset = tk.Entry(frame_params, width=8)
entry_offset.pack(side=tk.LEFT, padx=5)
entry_offset.insert(0, str(time_offset))

button_update = tk.Button(frame_params, text="更新参数", command=update_function_params, 
                         bg="#1890ff", fg="white")
button_update.pack(side=tk.RIGHT, padx=5)

# 说明标签
info_label = tk.Label(
    root, 
    text="使用说明:\n"
         "1. 先将微信跳一跳窗口最大化\n"
         "2. 选择测量方式:\n"
         "   - 方式一: 手动输入距离后点击计算跳跃\n"
         "   - 方式二: 按数字键盘'/'记录起点，'*'记录终点，'-'执行跳跃\n"
         "3. 可调整距离与时间函数参数以优化跳跃精度",
    justify=tk.LEFT,
    font=("Arial", 9)
)
info_label.pack(pady=10)

# 启动键盘监听器线程
keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
keyboard_thread.start()

root.mainloop()