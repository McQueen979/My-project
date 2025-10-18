import pyautogui
import time
import tkinter as tk
from PIL import ImageGrab
import numpy as np
import math

def find_pos():
    x, y = pyautogui.position()
    print(f"当前鼠标位置: ({x}, {y})")
    status_label.config(text=f"已记录位置: ({x}, {y})")
    return x, y

def capture_screen():
    """捕获当前屏幕并返回图像"""
    return ImageGrab.grab()

def get_color_difference(pixel1, pixel2):
    """计算两个像素之间的颜色差异"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(pixel1, pixel2)))

def detect_two_points():
    """检测屏幕上的两个点（起点和终点）"""
    print("请将鼠标移动到起点位置，3秒后开始检测...")
    status_label.config(text="请将鼠标移动到起点位置，3秒后开始检测...")
    root.update()
    time.sleep(3)
    start_x, start_y = find_pos()
    
    print("请将鼠标移动到终点位置，3秒后开始检测...")
    status_label.config(text="请将鼠标移动到终点位置，3秒后开始检测...")
    root.update()
    time.sleep(3)
    end_x, end_y = find_pos()
    
    # 计算两点之间的距离
    distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
    print(f"两点距离: {distance:.2f} 像素")
    status_label.config(text=f"已计算距离: {distance:.2f} 像素")
    
    # 自动填充距离到输入框
    entry.delete(0, tk.END)
    entry.insert(0, str(distance))
    
    return start_x, start_y, end_x, end_y, distance

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

def calculate_jump_time(distance):
    """根据距离计算跳跃时间"""
    # 使用二次函数拟合距离和时间的关系
    return -0.00800896 * (distance - 14.2091) ** 2 + 1.48245

def auto_play():
    """自动检测两点并执行跳跃"""
    status_label.config(text="开始自动游戏...")
    root.update()
    
    # 检测两点
    start_x, start_y, end_x, end_y, distance = detect_two_points()
    
    # 计算跳跃时间
    jump_time = calculate_jump_time(distance)
    print(f"计算跳跃时间: {jump_time:.2f} 秒")
    status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒")
    
    # 执行跳跃
    click_and_hold(jump_time)

def digi():
    try:
        # 获取输入的距离
        newlength = float(entry.get())
        # 计算跳跃时间
        jump_time = calculate_jump_time(newlength)
        print(f"输入距离: {newlength}, 计算跳跃时间: {jump_time:.2f} 秒")
        status_label.config(text=f"输入距离: {newlength}, 跳跃时间: {jump_time:.2f} 秒")
        # 执行点击
        click_and_hold(jump_time)
    except ValueError:
        print("请输入有效的距离值")
        status_label.config(text="错误: 请输入有效的距离值")
    except Exception as e:
        print(f"执行跳跃时出错: {e}")
        status_label.config(text=f"错误: {e}")

# 创建GUI
root = tk.Tk()
root.geometry("500x350")
root.title("微信跳一跳自动助手")

# 状态标签
status_label = tk.Label(root, text="就绪", fg="blue", font=("Arial", 10))
status_label.pack(pady=10)

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
label_pos = tk.Label(root, text="设置点击位置 (x,y):")
label_pos.pack()

entry_x = tk.Entry(root)
entry_x.insert(0, "540")  # 默认X坐标
entry_x.pack()

entry_y = tk.Entry(root)
entry_y.insert(0, "1300")  # 默认Y坐标
entry_y.pack()

# 手动输入距离
label = tk.Label(root, text="输入距离 (像素):")
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
         "2. 使用自动检测功能获取两点距离\n"
         "3. 或者手动输入距离\n"
         "4. 设置点击位置（默认为屏幕中央偏下）\n"
         "5. 点击开始自动游戏或手动执行跳跃",
    justify=tk.LEFT,
    font=("Arial", 9)
)
info_label.pack(pady=10)

root.mainloop()    