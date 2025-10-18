import pyautogui
import time
import tkinter as tk
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

# 游戏区域比例（根据实际情况调整）
GAME_AREA_TOP = 0.2
GAME_AREA_BOTTOM = 0.8
GAME_AREA_LEFT = 0.1
GAME_AREA_RIGHT = 0.9

def px_to_cm(pixels):
    """将像素距离转换为厘米距离"""
    return pixels * (CM_PER_PIXEL_X + CM_PER_PIXEL_Y) / 2

def capture_screen():
    """捕获游戏区域屏幕"""
    screen = ImageGrab.grab()
    width, height = screen.size
    
    # 计算游戏区域
    left = int(width * GAME_AREA_LEFT)
    top = int(height * GAME_AREA_TOP)
    right = int(width * GAME_AREA_RIGHT)
    bottom = int(height * GAME_AREA_BOTTOM)
    
    game_area = screen.crop((left, top, right, bottom))
    return game_area, (left, top)

def detect_player_and_target(image):
    """检测玩家和目标物体"""
    # 转换为OpenCV格式
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 检测玩家（棋子）
    # 使用Canny边缘检测
    edges = cv2.Canny(img_gray, 50, 150)
    
    # 查找轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    player_pos = None
    target_pos = None
    
    # 寻找玩家（通常是画面底部的深色物体）
    player_contour = None
    max_area = 0
    
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        
        # 玩家通常在画面下半部分，且有一定大小
        if y > image.height * 0.4 and area > 1000 and area < 5000:
            if area > max_area:
                max_area = area
                player_contour = contour
    
    if player_contour is not None:
        # 计算玩家位置（棋子底部中心）
        M = cv2.moments(player_contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # 棋子底部位置通常比中心低一些
            player_pos = (cX, cY + 20)
            
            # 在图像上标记玩家
            cv2.circle(img_cv, player_pos, 10, (0, 255, 0), -1)
    
    # 检测目标物体（下一个平台）
    # 查找目标物体通常在玩家前方，且颜色与背景不同
    if player_pos is not None:
        # 只考虑玩家前方的区域
        search_area = img_gray[:, player_pos[0]:]
        
        # 寻找亮度变化较大的区域（平台边缘）
        blur = cv2.GaussianBlur(search_area, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        target_contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_contour = None
        max_area = 0
        
        for contour in target_contours:
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            
            # 目标物体通常有一定大小，且在玩家上方
            if area > 1000 and area < 20000 and y < image.height * 0.6:
                if area > max_area:
                    max_area = area
                    target_contour = contour
        
        if target_contour is not None:
            # 计算目标位置（平台中心）
            M = cv2.moments(target_contour)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"]) + player_pos[0]  # 加上偏移
                cY = int(M["m01"] / M["m00"])
                
                target_pos = (cX, cY)
                
                # 在图像上标记目标
                cv2.circle(img_cv, target_pos, 10, (0, 0, 255), -1)
    
    # 显示检测结果
    if hasattr(root, 'detection_fig'):
        root.detection_fig.clear()
        ax = root.detection_fig.add_subplot(111)
        ax.imshow(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        ax.set_title('物体检测结果')
        ax.axis('off')
        root.detection_canvas.draw()
    
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
    # 调整后的公式，可能需要根据实际情况微调
    return 0.11 * distance_cm + 0.05

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
    
    # 检测玩家和目标
    status_label.config(text="正在识别物体...")
    root.update()
    player_pos, target_pos = detect_player_and_target(game_area)
    
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
            
            # 计算跳跃时间
            jump_time = calculate_jump_time(distance_cm)
            print(f"计算跳跃时间: {jump_time:.2f} 秒")
            status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
            
            # 等待一段时间，让用户准备
            time.sleep(1)
            
            # 执行跳跃
            click_and_hold(jump_time)
            
            # 等待游戏刷新
            time.sleep(2)
        else:
            status_label.config(text="无法计算距离，请调整游戏区域")
    else:
        status_label.config(text="未能识别玩家或目标，请确保游戏画面清晰")

# 创建GUI
root = tk.Tk()
root.geometry("800x600")
root.title("微信跳一跳自动助手 (图像识别版)")

# 状态标签
status_label = tk.Label(root, text="就绪", fg="blue", font=("Arial", 12))
status_label.pack(pady=10)

# 自动游戏功能
label_play = tk.Label(root, text="全自动游戏", font=("Arial", 14, "bold"))
label_play.pack(pady=5)

button_play = tk.Button(root, text="开始全自动游戏", command=auto_play, 
                       bg="green", fg="white", font=("Arial", 12),
                       width=20, height=2)
button_play.pack(pady=10)

# 设置点击位置
label_pos = tk.Label(root, text="设置点击位置 (x,y 像素):", font=("Arial", 10))
label_pos.pack()

entry_x = tk.Entry(root, font=("Arial", 10))
entry_x.insert(0, "960")  # 默认X坐标
entry_x.pack()

entry_y = tk.Entry(root, font=("Arial", 10))
entry_y.insert(0, "800")  # 默认Y坐标
entry_y.pack()

# 创建检测结果显示区域
root.detection_fig = plt.Figure(figsize=(6, 4), dpi=100)
root.detection_canvas = FigureCanvasTkAgg(root.detection_fig, master=root)
root.detection_canvas.get_tk_widget().pack(pady=10)

# 说明标签
info_label = tk.Label(
    root, 
    text="使用说明:\n"
         "1. 将微信跳一跳窗口最大化并置于前台\n"
         "2. 确保游戏界面清晰可见\n"
         "3. 点击'开始全自动游戏'按钮\n"
         "4. 程序会自动识别棋子和目标平台\n"
         "5. 计算距离并执行跳跃\n\n"
         "注意: 请不要遮挡游戏窗口，保持光线充足",
    justify=tk.LEFT,
    font=("Arial", 10)
)
info_label.pack(pady=10)

root.mainloop()    