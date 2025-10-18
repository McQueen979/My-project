import pyautogui
import time
import tkinter as tk
from tkinter import ttk, Scale, Label, Frame, Canvas, Scrollbar
from PIL import ImageGrab, Image, ImageDraw
import numpy as np
import math
import cv2
import keyboard
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 屏幕物理尺寸（厘米）
SCREEN_WIDTH_CM = 47.7
SCREEN_HEIGHT_CM = 29.9
# 屏幕分辨率
SCREEN_WIDTH_PX = 1920
SCREEN_HEIGHT_PX = 1080

# 计算每像素对应的厘米数
CM_PER_PIXEL_X = SCREEN_WIDTH_CM / SCREEN_WIDTH_PX
CM_PER_PIXEL_Y = SCREEN_HEIGHT_CM / SCREEN_HEIGHT_PX

# 全局参数
PARAMS = {
    'JUMP_TIME_SLOPE': 0.11,  # 斜率
    'JUMP_TIME_INTERCEPT': 0.05,  # 截距
}

# 记录坐标
start_pos = None
end_pos = None

def px_to_cm(pixels):
    """将像素距离转换为厘米距离"""
    return pixels * (CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2

def calculate_distance(start_pos, end_pos):
    """计算两点之间的距离"""
    if start_pos and end_pos:
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance_px = math.sqrt(dx**2 + dy**2)
        distance_cm = px_to_cm(distance_px)
        return distance_px, distance_cm
    return None, None

def calculate_jump_time(distance_cm):
    """根据厘米距离计算跳跃时间"""
    return PARAMS['JUMP_TIME_SLOPE'] * distance_cm + PARAMS['JUMP_TIME_INTERCEPT']

def move_mouse(x_pos, y_pos):
    """移动鼠标到指定位置"""
    try:
        pyautogui.moveTo(x_pos, y_pos)
    except Exception as e:
        print(f"移动鼠标时出错: {e}")
        status_label.config(text=f"错误: {e}")

def click_and_hold(duration):
    """点击并按住鼠标指定时间"""
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

def capture_screen():
    """捕获屏幕"""
    screen = ImageGrab.grab()
    return screen

def start_manual_mode():
    """开始手动测量模式"""
    global start_pos, end_pos
    start_pos = None
    end_pos = None
    
    status_label.config(text="手动测量模式已启动，请按以下步骤操作：")
    status_label2.config(text="1. 将鼠标移动到起始位置，按键盘 '1' 键记录")
    status_label3.config(text="2. 将鼠标移动到结束位置，按键盘 '2' 键记录")
    status_label4.config(text="3. 按键盘 '3' 键开始跳跃")
    
    # 清除之前的标记
    if hasattr(root, 'mark_image'):
        root.mark_image = None
        update_image_display()
    
    # 启动键盘监听线程
    keyboard_thread = threading.Thread(target=listen_for_keys)
    keyboard_thread.daemon = True
    keyboard_thread.start()

def listen_for_keys():
    """监听键盘按键"""
    global start_pos, end_pos
    
    while True:
        keyboard.wait()  # 等待任意按键
        
        if keyboard.is_pressed('1'):
            # 记录起始位置
            x, y = pyautogui.position()
            start_pos = (x, y)
            status_label2.config(text=f"起始位置已记录: ({x}, {y})")
            update_image_display()
            
        elif keyboard.is_pressed('2'):
            # 记录结束位置
            x, y = pyautogui.position()
            end_pos = (x, y)
            status_label3.config(text=f"结束位置已记录: ({x}, {y})")
            
            # 计算距离
            distance_px, distance_cm = calculate_distance(start_pos, end_pos)
            if distance_px and distance_cm:
                distance_var.set(f"{distance_cm:.2f} 厘米")
                time_var.set(f"{calculate_jump_time(distance_cm):.2f} 秒")
            
            update_image_display()
            
        elif keyboard.is_pressed('3'):
            # 开始跳跃
            if start_pos and end_pos:
                distance_px, distance_cm = calculate_distance(start_pos, end_pos)
                if distance_px and distance_cm:
                    jump_time = calculate_jump_time(distance_cm)
                    status_label4.config(text=f"正在计算跳跃时间: {jump_time:.2f} 秒")
                    click_and_hold(jump_time)
            else:
                status_label4.config(text="请先记录起始和结束位置！")

def update_image_display():
    """更新图像显示"""
    if not hasattr(root, 'mark_image'):
        # 捕获当前屏幕
        root.mark_image = capture_screen()
        root.original_img = root.mark_image.copy()
    
    # 创建可绘制的副本
    marked_img = root.original_img.copy()
    draw = ImageDraw.Draw(marked_img)
    
    # 绘制起始位置
    if start_pos:
        draw.ellipse((start_pos[0]-10, start_pos[1]-10, 
                     start_pos[0]+10, start_pos[1]+10), 
                     fill=(0, 255, 0))
        draw.text((start_pos[0]+15, start_pos[1]-10), "起点", fill=(0, 255, 0))
    
    # 绘制结束位置
    if end_pos:
        draw.ellipse((end_pos[0]-10, end_pos[1]-10, 
                     end_pos[0]+10, end_pos[1]+10), 
                     fill=(255, 0, 0))
        draw.text((end_pos[0]+15, end_pos[1]-10), "终点", fill=(255, 0, 0))
    
    # 绘制连接线
    if start_pos and end_pos:
        draw.line([start_pos, end_pos], fill=(0, 0, 255), width=3)
        # 计算距离
        distance_px, distance_cm = calculate_distance(start_pos, end_pos)
        if distance_px and distance_cm:
            mid_x = (start_pos[0] + end_pos[0]) // 2
            mid_y = (start_pos[1] + end_pos[1]) // 2
            draw.text((mid_x, mid_y), f"{distance_cm:.2f}cm", fill=(0, 0, 255))
    
    # 更新显示
    root.original_fig.clear()
    ax = root.original_fig.add_subplot(111)
    ax.imshow(marked_img)
    ax.set_title('手动标记位置')
    ax.axis('off')
    root.original_canvas.draw()

def create_param_slider(parent, param_name, label_text, min_val, max_val, step, default_val):
    """创建参数滑块"""
    frame = Frame(parent)
    frame.pack(fill=tk.X, padx=10, pady=5)
    
    # 标签
    Label(frame, text=label_text, width=25, anchor='w').pack(side=tk.LEFT)
    
    # 当前值显示
    var = tk.DoubleVar(value=default_val)
    value_label = Label(frame, text=f"{default_val:.2f}", width=8)
    value_label.pack(side=tk.RIGHT)
    
    # 滑块
    slider = Scale(
        frame,
        from_=min_val,
        to=max_val,
        resolution=step,
        orient=tk.HORIZONTAL,
        length=200,
        variable=var
    )
    slider.pack(side=tk.RIGHT, padx=10)
    
    # 绑定事件
    def update_param(*args):
        PARAMS[param_name] = var.get()
        value_label.config(text=f"{var.get():.2f}")
    var.trace_add("write", update_param)
    
    return slider

# 创建GUI
root = tk.Tk()
root.geometry("1200x700")
root.title("微信跳一跳手动测量助手")

# 创建主框架
main_frame = Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# 左侧控制区
control_frame = Frame(main_frame, width=300)
control_frame.pack(side=tk.LEFT, fill=tk.Y)

# 创建画布和滚动条
canvas = Canvas(control_frame)
scrollbar = Scrollbar(control_frame, orient="vertical", command=canvas.yview)
scrollable_frame = Frame(canvas)

# 配置画布滚动
scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

# 状态标签
status_label = tk.Label(scrollable_frame, text="就绪", fg="blue", font=("Arial", 12))
status_label.pack(pady=10)

status_label2 = tk.Label(scrollable_frame, text="", font=("Arial", 10))
status_label2.pack(pady=2)

status_label3 = tk.Label(scrollable_frame, text="", font=("Arial", 10))
status_label3.pack(pady=2)

status_label4 = tk.Label(scrollable_frame, text="", font=("Arial", 10))
status_label4.pack(pady=2)

# 手动测量功能
button_manual = tk.Button(
    scrollable_frame, 
    text="开始手动测量", 
    command=start_manual_mode, 
    bg="green", 
    fg="white", 
    font=("Arial", 12),
    width=20,
    height=2
)
button_manual.pack(pady=10)

# 显示距离和时间
stats_frame = Frame(scrollable_frame)
stats_frame.pack(fill=tk.X, padx=10, pady=10)

Label(stats_frame, text="计算距离:", font=("Arial", 10)).pack(side=tk.LEFT)
distance_var = tk.StringVar(value="--")
Label(stats_frame, textvariable=distance_var, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

Label(stats_frame, text="跳跃时间:", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
time_var = tk.StringVar(value="--")
Label(stats_frame, textvariable=time_var, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

# 设置点击位置
Label(scrollable_frame, text="点击位置设置", font=("Arial", 12, "bold")).pack(pady=5)

entry_x = tk.Entry(scrollable_frame, font=("Arial", 10))
entry_x.insert(0, "960")  # 默认X坐标
entry_x.pack(fill=tk.X, padx=10, pady=2)

entry_y = tk.Entry(scrollable_frame, font=("Arial", 10))
entry_y.insert(0, "800")  # 默认Y坐标
entry_y.pack(fill=tk.X, padx=10, pady=2)

# 跳跃时间参数
Label(scrollable_frame, text="跳跃时间参数", font=("Arial", 12, "bold")).pack(pady=10)
create_param_slider(scrollable_frame, 'JUMP_TIME_SLOPE', '斜率', 0.05, 0.2, 0.005, PARAMS['JUMP_TIME_SLOPE'])
create_param_slider(scrollable_frame, 'JUMP_TIME_INTERCEPT', '截距', 0.01, 0.2, 0.005, PARAMS['JUMP_TIME_INTERCEPT'])

# 放置画布和滚动条
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# 右侧图像显示区
image_frame = Frame(main_frame)
image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# 原始图像显示
root.original_fig = plt.Figure(figsize=(6, 4), dpi=100)
root.original_canvas = FigureCanvasTkAgg(root.original_fig, master=image_frame)
root.original_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

root.mainloop()    