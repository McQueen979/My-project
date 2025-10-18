import pyautogui
import time
import tkinter as tk
from tkinter import ttk, Scale, Label, Frame
from PIL import ImageGrab, ImageFilter
import numpy as np
import math
import cv2
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

# 全局参数（可通过界面调整）
PARAMS = {
    # 游戏区域
    'GAME_AREA_TOP': 0.2,
    'GAME_AREA_BOTTOM': 0.8,
    'GAME_AREA_LEFT': 0.1,
    'GAME_AREA_RIGHT': 0.9,
    
    # 玩家检测参数
    'PLAYER_MIN_Y': 0.4,  # 玩家最小Y位置比例
    'PLAYER_MIN_AREA': 800,  # 玩家最小面积
    'PLAYER_MAX_AREA': 6000,  # 玩家最大面积
    
    # 目标检测参数
    'TARGET_MAX_Y': 0.6,  # 目标最大Y位置比例
    'TARGET_MIN_AREA': 1000,  # 目标最小面积
    'TARGET_MAX_AREA': 20000,  # 目标最大面积
    
    # Canny边缘检测参数
    'CANNY_THRESHOLD1': 50,
    'CANNY_THRESHOLD2': 150,
    
    # 跳跃时间计算参数
    'JUMP_TIME_SLOPE': 0.11,  # 斜率
    'JUMP_TIME_INTERCEPT': 0.05,  # 截距
}

def px_to_cm(pixels):
    """将像素距离转换为厘米距离"""
    return pixels * (CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2

def capture_screen():
    """捕获游戏区域屏幕"""
    screen = ImageGrab.grab()
    width, height = screen.size
    
    # 使用可调整的游戏区域参数
    left = int(width * PARAMS['GAME_AREA_LEFT'])
    top = int(height * PARAMS['GAME_AREA_TOP'])
    right = int(width * PARAMS['GAME_AREA_RIGHT'])
    bottom = int(height * PARAMS['GAME_AREA_BOTTOM'])
    
    game_area = screen.crop((left, top, right, bottom))
    return game_area, (left, top)

def detect_player_and_target(image):
    """检测玩家和目标物体"""
    # 转换为OpenCV格式
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 使用可调整的Canny参数
    edges = cv2.Canny(img_gray, PARAMS['CANNY_THRESHOLD1'], PARAMS['CANNY_THRESHOLD2'])
    
    # 查找轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    player_pos = None
    target_pos = None
    
    # 寻找玩家
    player_contour = None
    max_area = 0
    
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        
        # 使用可调整的玩家检测参数
        if y > image.height * PARAMS['PLAYER_MIN_Y'] and \
           area > PARAMS['PLAYER_MIN_AREA'] and \
           area < PARAMS['PLAYER_MAX_AREA']:
            if area > max_area:
                max_area = area
                player_contour = contour
    
    if player_contour is not None:
        # 计算玩家位置
        M = cv2.moments(player_contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            player_pos = (cX, cY + 20)  # 棋子底部位置通常比中心低一些
            cv2.circle(img_cv, player_pos, 10, (0, 255, 0), -1)
            cv2.drawContours(img_cv, [player_contour], -1, (0, 255, 0), 2)
    
    # 检测目标物体
    if player_pos is not None:
        # 只考虑玩家前方的区域
        search_area = img_gray[:, player_pos[0]:]
        
        # 寻找亮度变化较大的区域
        blur = cv2.GaussianBlur(search_area, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        target_contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_contour = None
        max_area = 0
        
        for contour in target_contours:
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            
            # 使用可调整的目标检测参数
            if area > PARAMS['TARGET_MIN_AREA'] and \
               area < PARAMS['TARGET_MAX_AREA'] and \
               y < image.height * PARAMS['TARGET_MAX_Y']:
                if area > max_area:
                    max_area = area
                    target_contour = contour
        
        if target_contour is not None:
            # 计算目标位置
            M = cv2.moments(target_contour)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"]) + player_pos[0]  # 加上偏移
                cY = int(M["m01"] / M["m00"])
                
                target_pos = (cX, cY)
                cv2.circle(img_cv, target_pos, 10, (0, 0, 255), -1)
                cv2.drawContours(img_cv, [target_contour], -1, (0, 0, 255), 2)
    
    # 保存中间处理结果用于调试
    if hasattr(root, 'debug_images'):
        root.debug_images = {
            'original': np.array(image),
            'gray': img_gray,
            'edges': edges,
            'thresh': thresh,
            'result': img_cv
        }
    
    return player_pos, target_pos

def calculate_distance(player_pos, target_pos):
    """计算玩家和目标之间的距离"""
    if player_pos and target_pos:
        dx = target_pos[0] - player_pos[0]
        dy = target_pos[1] - player_pos[1]
        distance_px = math.sqrt(dx**2 + dy**2)
        distance_cm = px_to_cm(distance_px)
        return distance_px, distance_cm
    return None, None

def calculate_jump_time(distance_cm):
    """根据厘米距离计算跳跃时间"""
    # 使用可调整的跳跃时间参数
    return PARAMS['JUMP_TIME_SLOPE'] * distance_cm + PARAMS['JUMP_TIME_INTERCEPT']

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

def auto_play():
    """全自动游戏"""
    status_label.config(text="开始自动游戏...")
    root.update()
    
    # 捕获屏幕
    status_label.config(text="正在捕获屏幕...")
    root.update()
    game_area, offset = capture_screen()
    
    # 更新原始图像显示
    update_image_display('original', game_area)
    
    # 检测玩家和目标
    status_label.config(text="正在识别物体...")
    root.update()
    player_pos, target_pos = detect_player_and_target(game_area)
    
    # 更新处理后图像显示
    update_image_display('processed', root.debug_images['result'])
    
    if player_pos and target_pos:
        # 调整为全局坐标
        player_global_pos = (player_pos[0] + offset[0], player_pos[1] + offset[1])
        target_global_pos = (target_pos[0] + offset[0], target_pos[1] + offset[1])
        
        # 计算距离
        distance_px, distance_cm = calculate_distance(player_pos, target_pos)
        
        if distance_px and distance_cm:
            print(f"检测到玩家位置: {player_pos}")
            print(f"检测到目标位置: {target_pos}")
            print(f"两点距离: {distance_px:.2f} 像素 = {distance_cm:.2f} 厘米")
            status_label.config(text=f"已计算距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)")
            
            # 更新距离显示
            distance_var.set(f"{distance_cm:.2f} 厘米")
            
            # 计算跳跃时间
            jump_time = calculate_jump_time(distance_cm)
            print(f"计算跳跃时间: {jump_time:.2f} 秒")
            status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
            
            # 更新时间显示
            time_var.set(f"{jump_time:.2f} 秒")
            
            # 等待一段时间，让用户准备
            time.sleep(1)
            
            # 执行跳跃
            click_and_hold(jump_time)
            
            # 等待游戏刷新
            time.sleep(2)
        else:
            status_label.config(text="无法计算距离，请调整游戏区域")
    else:
        status_label.config(text="未能识别玩家或目标，请调整参数")

def update_image_display(mode, image=None):
    """更新图像显示"""
    if mode == 'original' and image:
        root.original_fig.clear()
        ax = root.original_fig.add_subplot(111)
        ax.imshow(image)
        ax.set_title('原始游戏区域')
        ax.axis('off')
        root.original_canvas.draw()
    elif mode == 'processed' and hasattr(root, 'debug_images'):
        root.processed_fig.clear()
        ax = root.processed_fig.add_subplot(111)
        ax.imshow(cv2.cvtColor(root.debug_images['result'], cv2.COLOR_BGR2RGB))
        ax.set_title('处理后图像')
        ax.axis('off')
        root.processed_canvas.draw()
    elif mode == 'debug' and hasattr(root, 'debug_images'):
        root.debug_fig.clear()
        
        # 显示原始图像
        ax1 = root.debug_fig.add_subplot(231)
        ax1.imshow(root.debug_images['original'])
        ax1.set_title('原始')
        ax1.axis('off')
        
        # 显示灰度图像
        ax2 = root.debug_fig.add_subplot(232)
        ax2.imshow(root.debug_images['gray'], cmap='gray')
        ax2.set_title('灰度')
        ax2.axis('off')
        
        # 显示边缘检测
        ax3 = root.debug_fig.add_subplot(233)
        ax3.imshow(root.debug_images['edges'], cmap='gray')
        ax3.set_title('边缘')
        ax3.axis('off')
        
        # 显示阈值处理
        ax4 = root.debug_fig.add_subplot(234)
        ax4.imshow(root.debug_images['thresh'], cmap='gray')
        ax4.set_title('阈值')
        ax4.axis('off')
        
        # 显示最终结果
        ax5 = root.debug_fig.add_subplot(235)
        ax5.imshow(cv2.cvtColor(root.debug_images['result'], cv2.COLOR_BGR2RGB))
        ax5.set_title('结果')
        ax5.axis('off')
        
        root.debug_canvas.draw()

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

def show_debug_view():
    """显示调试视图"""
    if not hasattr(root, 'debug_window') or not root.debug_window.winfo_exists():
        root.debug_window = tk.Toplevel(root)
        root.debug_window.title("调试视图")
        root.debug_window.geometry("900x600")
        
        # 创建调试图像显示
        root.debug_fig = plt.Figure(figsize=(8, 5), dpi=100)
        root.debug_canvas = FigureCanvasTkAgg(root.debug_fig, master=root.debug_window)
        root.debug_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 刷新按钮
        refresh_btn = tk.Button(root.debug_window, text="刷新", command=lambda: update_image_display('debug'))
        refresh_btn.pack(pady=10)
        
        # 自动刷新复选框
        auto_refresh_var = tk.BooleanVar(value=False)
        auto_refresh_check = tk.Checkbutton(root.debug_window, text="自动刷新", variable=auto_refresh_var)
        auto_refresh_check.pack(pady=5)
        
        def auto_refresh_loop():
            if auto_refresh_var.get():
                update_image_display('debug')
                root.debug_window.after(1000, auto_refresh_loop)
        
        auto_refresh_check.config(command=auto_refresh_loop)
        
        # 初始显示
        update_image_display('debug')

# 创建GUI
root = tk.Tk()
root.geometry("1200x700")
root.title("微信跳一跳自动助手 (参数可调版)")

# 创建主框架
main_frame = Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# 左侧控制区
control_frame = Frame(main_frame, width=300)
control_frame.pack(side=tk.LEFT, fill=tk.Y)

# 状态标签
status_label = tk.Label(control_frame, text="就绪", fg="blue", font=("Arial", 12))
status_label.pack(pady=10)

# 自动游戏功能
Label(control_frame, text="游戏控制", font=("Arial", 14, "bold")).pack(pady=5)

button_play = tk.Button(
    control_frame, 
    text="开始全自动游戏", 
    command=auto_play, 
    bg="green", 
    fg="white", 
    font=("Arial", 12),
    width=20,
    height=2
)
button_play.pack(pady=10)

# 显示距离和时间
stats_frame = Frame(control_frame)
stats_frame.pack(fill=tk.X, padx=10, pady=10)

Label(stats_frame, text="计算距离:", font=("Arial", 10)).pack(side=tk.LEFT)
distance_var = tk.StringVar(value="--")
Label(stats_frame, textvariable=distance_var, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

Label(stats_frame, text="跳跃时间:", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
time_var = tk.StringVar(value="--")
Label(stats_frame, textvariable=time_var, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

# 设置点击位置
Label(control_frame, text="点击位置设置", font=("Arial", 12, "bold")).pack(pady=5)

entry_x = tk.Entry(control_frame, font=("Arial", 10))
entry_x.insert(0, "960")  # 默认X坐标
entry_x.pack(fill=tk.X, padx=10, pady=2)

entry_y = tk.Entry(control_frame, font=("Arial", 10))
entry_y.insert(0, "800")  # 默认Y坐标
entry_y.pack(fill=tk.X, padx=10, pady=2)

# 调试按钮
debug_btn = tk.Button(control_frame, text="显示调试视图", command=show_debug_view)
debug_btn.pack(pady=10)

# 参数调整面板
Label(control_frame, text="参数调整", font=("Arial", 14, "bold")).pack(pady=10)

# 游戏区域参数
Label(control_frame, text="游戏区域参数", font=("Arial", 10, "bold")).pack(pady=5)
create_param_slider(control_frame, 'GAME_AREA_TOP', '上边界比例', 0.1, 0.4, 0.01, PARAMS['GAME_AREA_TOP'])
create_param_slider(control_frame, 'GAME_AREA_BOTTOM', '下边界比例', 0.6, 0.9, 0.01, PARAMS['GAME_AREA_BOTTOM'])
create_param_slider(control_frame, 'GAME_AREA_LEFT', '左边界比例', 0.05, 0.2, 0.01, PARAMS['GAME_AREA_LEFT'])
create_param_slider(control_frame, 'GAME_AREA_RIGHT', '右边界比例', 0.8, 0.95, 0.01, PARAMS['GAME_AREA_RIGHT'])

# 玩家检测参数
Label(control_frame, text="玩家检测参数", font=("Arial", 10, "bold")).pack(pady=5)
create_param_slider(control_frame, 'PLAYER_MIN_Y', '最小Y比例', 0.2, 0.6, 0.01, PARAMS['PLAYER_MIN_Y'])
create_param_slider(control_frame, 'PLAYER_MIN_AREA', '最小面积', 500, 2000, 100, PARAMS['PLAYER_MIN_AREA'])
create_param_slider(control_frame, 'PLAYER_MAX_AREA', '最大面积', 4000, 10000, 100, PARAMS['PLAYER_MAX_AREA'])

# 目标检测参数
Label(control_frame, text="目标检测参数", font=("Arial", 10, "bold")).pack(pady=5)
create_param_slider(control_frame, 'TARGET_MAX_Y', '最大Y比例', 0.4, 0.8, 0.01, PARAMS['TARGET_MAX_Y'])
create_param_slider(control_frame, 'TARGET_MIN_AREA', '最小面积', 500, 2000, 100, PARAMS['TARGET_MIN_AREA'])
create_param_slider(control_frame, 'TARGET_MAX_AREA', '最大面积', 10000, 30000, 100, PARAMS['TARGET_MAX_AREA'])

# 边缘检测参数
Label(control_frame, text="边缘检测参数", font=("Arial", 10, "bold")).pack(pady=5)
create_param_slider(control_frame, 'CANNY_THRESHOLD1', '阈值1', 10, 100, 5, PARAMS['CANNY_THRESHOLD1'])
create_param_slider(control_frame, 'CANNY_THRESHOLD2', '阈值2', 50, 200, 5, PARAMS['CANNY_THRESHOLD2'])

# 跳跃时间参数
Label(control_frame, text="跳跃时间参数", font=("Arial", 10, "bold")).pack(pady=5)
create_param_slider(control_frame, 'JUMP_TIME_SLOPE', '斜率', 0.05, 0.2, 0.005, PARAMS['JUMP_TIME_SLOPE'])
create_param_slider(control_frame, 'JUMP_TIME_INTERCEPT', '截距', 0.01, 0.2, 0.005, PARAMS['JUMP_TIME_INTERCEPT'])

# 右侧图像显示区
image_frame = Frame(main_frame)
image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# 原始图像显示
root.original_fig = plt.Figure(figsize=(6, 4), dpi=100)
root.original_canvas = FigureCanvasTkAgg(root.original_fig, master=image_frame)
root.original_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# 处理后图像显示
root.processed_fig = plt.Figure(figsize=(6, 4), dpi=100)
root.processed_canvas = FigureCanvasTkAgg(root.processed_fig, master=image_frame)
root.processed_canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

root.mainloop()    