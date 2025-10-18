import pyautogui
import time
import tkinter as tk
import math
import cv2
import numpy as np
from PIL import ImageGrab
from pynput import keyboard
import threading
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='jump_assistant.log'
)

# 屏幕物理尺寸（厘米）
SCREEN_WIDTH_CM = 47.6
SCREEN_HEIGHT_CM = 29.9
# 屏幕分辨率
SCREEN_WIDTH_PX = 1920
SCREEN_HEIGHT_PX = 1080

# 计算每像素对应的厘米数
CM_PER_PIXEL_X = SCREEN_WIDTH_CM / SCREEN_WIDTH_PX
CM_PER_PIXEL_Y = SCREEN_HEIGHT_CM / SCREEN_HEIGHT_PX

# 全局变量
measurement_mode = 1  # 1:手动输入 2:键盘快捷键 3:自动识别 4:混合模式
start_point = None
end_point = None
listener = None  # 全局键盘监听器
auto_play_running = False
auto_play_thread = None

# 距离与点击时间函数参数
distance_factor = 0.09
time_offset = -0.05

# 自动识别参数
game_region = (0, 0, SCREEN_WIDTH_PX, SCREEN_HEIGHT_PX)  # 游戏区域，初始为全屏
chess_threshold = 0.8  # 棋子识别阈值
target_threshold = 0.7  # 目标识别阈值

# 新增全局变量用于静止检测
LAST_CHESS_POS = None  # 上一帧棋子位置
STATIONARY_FRAMES = 0   # 连续静止帧数
STATIONARY_THRESHOLD = 3  # 需连续静止的帧数
POSITION_THRESHOLD = 5   # 位置变化阈值（像素）

# 配置参数
class Config:
    AUTO_PLAY_INTERVAL = 1.5  # 自动模式下的跳跃间隔
    SET_REGION_DELAY = 3      # 设置游戏区域时的延迟
    MOVE_DURATION = 0.2       # 鼠标移动持续时间
    UI_UPDATE_INTERVAL = 100  # UI更新间隔(ms)

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
            status_label.config(text=f"手动输入距离: {distance_cm:.2f} 厘米 ({distance_px:.2f} 像素)")
            logging.info(f"手动输入距离: {distance_cm:.2f} 厘米")
            return distance_cm
        except ValueError:
            status_label.config(text="错误: 请输入有效的数值")
            logging.error("手动输入距离格式错误")
            return None
    
    elif measurement_mode in [2, 4]:  # 键盘快捷键模式或混合模式
        if not start_point or not end_point:
            status_label.config(text="请先记录起点和终点")
            return None
        
        # 计算两点之间的像素距离
        distance_px = math.sqrt((end_point[0] - start_point[0]) ** 2 + (end_point[1] - start_point[1]) ** 2)
        # 转换为厘米
        distance_cm = px_to_cm(distance_px)
        
        status_label.config(text=f"测量距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)")
        logging.info(f"键盘测量距离: {distance_cm:.2f} 厘米")
        
        # 自动填充距离到输入框
        entry_distance.delete(0, tk.END)
        entry_distance.insert(0, str(round(distance_cm, 2)))
        
        return distance_cm
    
    elif measurement_mode == 3:  # 自动识别模式
        if not start_point or not end_point:
            status_label.config(text="自动识别失败，请检查游戏区域和参数")
            return None
        
        # 计算两点之间的像素距离
        distance_px = math.sqrt((end_point[0] - start_point[0]) ** 2 + (end_point[1] - start_point[1]) ** 2)
        # 转换为厘米
        distance_cm = px_to_cm(distance_px)
        
        status_label.config(text=f"自动识别距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)")
        logging.info(f"自动识别距离: {distance_cm:.2f} 厘米")
        
        # 自动填充距离到输入框
        entry_distance.delete(0, tk.END)
        entry_distance.insert(0, str(round(distance_cm, 2)))
        
        return distance_cm

def click_and_hold(duration):
    """点击并按住指定时间"""
    try:
        # 获取输入的坐标并移动鼠标
        x_pos = int(entry_x.get())
        y_pos = int(entry_y.get())
        
        # 添加鼠标移动操作
        pyautogui.moveTo(x_pos, y_pos, duration=Config.MOVE_DURATION)
        
        status_label.config(text=f"正在点击并保持 {duration:.2f} 秒...")
        root.update()
        
        pyautogui.mouseDown()
        time.sleep(duration)
        pyautogui.mouseUp()
        
        # 记录跳跃日志
        logging.info(f"执行跳跃: 时间={duration:.2f}秒, 坐标=({x_pos}, {y_pos})")
        
        # 重置键盘模式的点，允许连续跳跃
        if measurement_mode in [2, 4]:
            global start_point, end_point
            if measurement_mode == 4:  # 混合模式只重置终点
                end_point = None
                # 自动识别下一次起点
                if identify_chess_piece(capture_game_screen()):
                    status_label.config(text=f"已自动识别棋子位置: ({start_point[0]}, {start_point[1]})\n请移动到终点按'X'键")
                else:
                    status_label.config(text="无法识别棋子位置，请重新开始")
                    start_point = None
            else:  # 键盘模式重置起点和终点
                start_point = None
                end_point = None
                status_label.config(text="跳跃完成，请按'Z'记录下一次起点...")
        
    except Exception as e:
        status_label.config(text=f"点击错误: {e}")
        logging.error(f"点击错误: {e}")

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
        logging.info(f"更新函数参数: 系数={distance_factor}, 偏移量={time_offset}")
        # 更新参数后禁用输入框，避免键盘干扰
        entry_factor.config(state=tk.DISABLED)
        entry_offset.config(state=tk.DISABLED)
    except ValueError:
        status_label.config(text="错误: 请输入有效的数值")
        logging.error("函数参数格式错误")

def execute_jump():
    """执行跳跃操作"""
    distance_cm = calculate_distance()
    if distance_cm is None:
        return
    
    # 计算跳跃时间
    jump_time = calculate_jump_time(distance_cm)
    status_label.config(text=f"计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    
    # 执行跳跃
    click_and_hold(jump_time)

def set_mode(mode):
    """设置测量模式"""
    global measurement_mode, start_point, end_point, auto_play_running
    measurement_mode = mode
    start_point = None
    end_point = None
    auto_play_running = False
    
    # 启用参数输入框，允许用户修改
    entry_factor.config(state=tk.NORMAL)
    entry_offset.config(state=tk.NORMAL)
    
    if mode == 1:
        status_label.config(text="已切换到方式一：手动输入距离")
        entry_distance.config(state=tk.NORMAL)  # 启用距离输入框
        button_auto_play.config(text="开始自动玩", command=start_auto_play)
        logging.info("切换到手动输入模式")
        
    elif mode == 2:
        status_label.config(text="已切换到方式二：使用键盘快捷键测量")
        entry_distance.config(state=tk.DISABLED)  # 禁用距离输入框
        status_label.config(text="请将鼠标移动到起点位置，按'Z'键记录起点...")
        button_auto_play.config(text="开始自动玩", command=start_auto_play)
        logging.info("切换到键盘快捷键模式")
        
    elif mode == 3:
        status_label.config(text="已切换到方式三：自动识别模式")
        entry_distance.config(state=tk.DISABLED)  # 禁用距离输入框
        button_auto_play.config(text="开始自动玩", command=start_auto_play)
        logging.info("切换到自动识别模式")
        # 自动识别一次，显示识别结果
        if identify_game_elements():
            execute_jump()
            
    elif mode == 4:
        status_label.config(text="已切换到方式四：半自动")
        entry_distance.config(state=tk.DISABLED)  # 禁用距离输入框
        button_auto_play.config(text="开始自动玩", command=start_auto_play)
        logging.info("切换到混合模式")
        
        # 尝试自动识别棋子位置
        if identify_chess_piece(capture_game_screen()):
            status_label.config(text=f"已自动识别棋子位置: ({start_point[0]}, {start_point[1]})\n请移动到终点按'X'键")
        else:
            status_label.config(text="无法识别棋子位置，请检查游戏区域")

def on_key_press(key):
    """处理全局键盘事件"""
    try:
        if key.char == 'z' and measurement_mode == 2:  # Z键记录起点（仅用于模式2）
            x, y = pyautogui.position()
            global start_point
            start_point = (x, y)
            root.after(0, lambda: status_label.config(text=f"已记录起点: ({x}, {y})\n请移动到终点按'X'键"))
            logging.info(f"记录起点: ({x}, {y})")
            
        elif key.char == 'x' and measurement_mode in [2, 4]:  # X键记录终点并跳跃
            if start_point:
                x, y = pyautogui.position()
                global end_point
                end_point = (x, y)
                root.after(0, lambda: status_label.config(text=f"已记录终点: ({x}, {y})\n正在计算跳跃..."))
                logging.info(f"记录终点: ({x}, {y})")
                root.after(0, execute_jump)  # 直接执行跳跃
                
    except AttributeError:
        pass

def start_global_listener():
    """启动全局键盘监听"""
    global listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()

def on_closing():
    """窗口关闭时的清理操作"""
    global listener, auto_play_running
    auto_play_running = False
    if listener:
        listener.stop()
    # 关闭OpenCV窗口
    cv2.destroyAllWindows()
    root.destroy()
    logging.info("程序已关闭")

def capture_game_screen():
    """捕获游戏区域屏幕"""
    global game_region
    try:
        # 截取游戏区域
        screenshot = ImageGrab.grab(bbox=game_region)
        # 转换为OpenCV格式
        game_image = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return game_image
    except Exception as e:
        status_label.config(text=f"屏幕捕获错误: {e}")
        logging.error(f"屏幕捕获错误: {e}")
        return None

def identify_chess_piece(game_image):
    """识别棋子位置并判断是否静止"""
    global LAST_CHESS_POS, STATIONARY_FRAMES, start_point
    
    if game_image is None:
        return False
        
    try:
        # 转换为HSV颜色空间以便颜色识别
        hsv = cv2.cvtColor(game_image, cv2.COLOR_BGR2HSV)
        
        # 定义棋子颜色范围（紫色调）
        lower_purple = np.array([120, 50, 50])
        upper_purple = np.array([160, 255, 255])
        
        # 创建颜色掩码
        mask = cv2.inRange(hsv, lower_purple, upper_purple)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            LAST_CHESS_POS = None  # 未检测到棋子时重置位置
            STATIONARY_FRAMES = 0
            return False
        
        # 找到最大的轮廓（假设为棋子）
        max_contour = max(contours, key=cv2.contourArea)
        
        # 计算轮廓的中心点
        M = cv2.moments(max_contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # 获取轮廓的边界框
            x, y, w, h = cv2.boundingRect(max_contour)
            
            # 将起点位置调整到棋子底部1/4处
            adjusted_y = y + h * 3 // 4  # 从顶部向下3/4的位置，即底部1/4处
            
            # 更新当前位置
            current_pos = (cX + game_region[0], adjusted_y + game_region[1])
            
            # 初始化位移变量，避免首次检测时出错
            total_movement = 0
            
            # ------------------- 新增静止检测逻辑 -------------------
            if LAST_CHESS_POS is None:
                # 首帧直接记录位置，不判断静止
                LAST_CHESS_POS = current_pos
                STATIONARY_FRAMES = 1
            else:
                # 计算当前帧与上一帧的位置差
                dx = abs(current_pos[0] - LAST_CHESS_POS[0])
                dy = abs(current_pos[1] - LAST_CHESS_POS[1])
                total_movement = dx + dy
                
                if total_movement < POSITION_THRESHOLD:
                    # 位置变化小于阈值，静止帧数+1
                    STATIONARY_FRAMES += 1
                    if STATIONARY_FRAMES >= STATIONARY_THRESHOLD:
                        # 达到连续静止帧数，更新起点
                        start_point = current_pos
                        LAST_CHESS_POS = current_pos  # 重置上一帧位置
                        return True
                else:
                    # 位置变化较大，重置静止计数器
                    STATIONARY_FRAMES = 0
                    LAST_CHESS_POS = current_pos  # 更新为当前位置，继续检测
            
            # 在游戏图像上绘制识别结果（无论是否静止）
            display_image = game_image.copy()
            # 绘制棋子位置（绿色圆圈）
            cv2.circle(display_image, (cX, adjusted_y), 10, (0, 255, 0), 2)
            
            # 显示识别结果（确保total_movement已定义）
            cv2.putText(display_image, f"Movement: {total_movement:.1f}px", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_image, f"Stationary: {STATIONARY_FRAMES}/{STATIONARY_THRESHOLD}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("识别结果", display_image)
            cv2.waitKey(1)
            
            return False  # 未达到静止条件时不更新起点
        return False
    except Exception as e:
        status_label.config(text=f"识别棋子错误: {e}")
        logging.error(f"识别棋子错误: {e}")
        LAST_CHESS_POS = None
        STATIONARY_FRAMES = 0
        return False

def identify_target_position(game_image, chess_pos):
    """识别目标位置"""
    if game_image is None or chess_pos is None:
        return None
        
    try:
        # 将屏幕坐标转换为游戏区域坐标
        chess_pos_game = (chess_pos[0] - game_region[0], chess_pos[1] - game_region[1])
        
        # 创建边缘检测图像
        gray = cv2.cvtColor(game_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 移除棋子周围区域，避免干扰
        h, w = edges.shape[:2]
        mask = np.zeros_like(edges)
        cv2.circle(mask, (chess_pos_game[0], chess_pos_game[1]), int(h * 0.15), 255, -1)
        edges = cv2.bitwise_and(edges, edges, mask=cv2.bitwise_not(mask))
        
        # 寻找目标平台的顶部边缘
        target_y = 0
        for y in range(int(chess_pos_game[1] * 0.7), int(chess_pos_game[1])):
            if np.sum(edges[y, :]) > 1000:  # 如果一行中有足够的边缘点
                target_y = y
                break
        
        if target_y == 0:
            return None
        
        # 找到目标平台的中心点
        target_x = np.argmax(edges[target_y, :])
        
        # 转换为屏幕坐标
        return (target_x + game_region[0], target_y + game_region[1])
    except Exception as e:
        status_label.config(text=f"识别目标错误: {e}")
        logging.error(f"识别目标错误: {e}")
        return None

def identify_game_elements():
    """识别游戏元素（棋子和目标位置）"""
    global start_point, end_point
    
    # 捕获游戏屏幕
    game_image = capture_game_screen()
    
    # 识别棋子位置
    if not identify_chess_piece(game_image):
        status_label.config(text="无法识别棋子位置")
        return False
    
    # 识别目标位置
    target_pos = identify_target_position(game_image, start_point)
    if target_pos is None:
        status_label.config(text="无法识别目标位置")
        return False
    
    # 更新全局变量
    end_point = target_pos
    
    # 在游戏图像上绘制识别结果
    if game_image is not None:
        display_image = game_image.copy()
        # 绘制棋子位置（绿色圆圈）
        cv2.circle(display_image, (start_point[0] - game_region[0], start_point[1] - game_region[1]), 10, (0, 255, 0), 2)
        # 绘制目标位置（红色圆圈）
        cv2.circle(display_image, (end_point[0] - game_region[0], end_point[1] - game_region[1]), 10, (0, 0, 255), 2)
        # 绘制连接线
        cv2.line(display_image, 
                (start_point[0] - game_region[0], start_point[1] - game_region[1]), 
                (end_point[0] - game_region[0], end_point[1] - game_region[1]), 
                (255, 0, 0), 2)
        
        # 显示识别结果
        cv2.imshow("识别结果", display_image)
        cv2.waitKey(1)
    
    return True

def auto_play_loop():
    """自动玩游戏的循环"""
    global auto_play_running, start_point, end_point
    
    auto_play_running = True
    button_auto_play.config(text="停止自动玩", command=stop_auto_play)
    logging.info("开始自动游戏")
    
    try:
        while auto_play_running:
            if measurement_mode == 4:  # 混合模式
                # ------------------- 仅在静止时识别起点 -------------------
                if identify_chess_piece(capture_game_screen()):
                    status_label.config(text=f"已自动识别静止棋子位置: ({start_point[0]}, {start_point[1]})\n等待用户确认终点...")
                    
                    # 等待用户按X键确认终点
                    timeout = 10  # 超时时间（秒）
                    start_time = time.time()
                    while auto_play_running and end_point is None:
                        if time.time() - start_time > timeout:
                            status_label.config(text="等待用户操作超时，重新识别棋子...")
                            break
                        time.sleep(0.1)
                    
                    # 如果用户确认了终点
                    if end_point:
                        # 计算距离
                        distance_cm = calculate_distance()
                        if distance_cm is not None:
                            # 计算跳跃时间
                            jump_time = calculate_jump_time(distance_cm)
                            status_label.config(text=f"自动模式 - 距离: {distance_cm:.2f} 厘米, 时间: {jump_time:.2f} 秒")
                            
                            # 执行跳跃
                            click_and_hold(jump_time)
                            
                            # 重置终点，准备下一次跳跃
                            end_point = None
                            
                            # 等待下一次跳跃
                            time.sleep(Config.AUTO_PLAY_INTERVAL)  # 等待游戏动画完成
                else:
                    status_label.config(text="检测到棋子移动，等待静止...")
                    time.sleep(0.5)  # 短间隔重试
            else:  # 普通自动模式
                # 识别游戏元素
                if identify_game_elements():
                    # 计算距离
                    distance_cm = calculate_distance()
                    if distance_cm is not None:
                        # 计算跳跃时间
                        jump_time = calculate_jump_time(distance_cm)
                        status_label.config(text=f"自动模式 - 距离: {distance_cm:.2f} 厘米, 时间: {jump_time:.2f} 秒")
                        
                        # 执行跳跃
                        click_and_hold(jump_time)
                        
                        # 等待下一次跳跃
                        time.sleep(Config.AUTO_PLAY_INTERVAL)  # 等待游戏动画完成
                else:
                    status_label.config(text="自动识别失败，重试中...")
                    logging.warning("自动识别失败")
                    time.sleep(1)
                
    except Exception as e:
        status_label.config(text=f"自动模式错误: {e}")
        logging.error(f"自动模式错误: {e}")
        auto_play_running = False
        
    button_auto_play.config(text="开始自动玩", command=start_auto_play)
    logging.info("停止自动游戏")

def start_auto_play():
    """开始自动玩游戏"""
    global auto_play_thread, measurement_mode
    
    if measurement_mode != 3 and measurement_mode != 4:
        set_mode(3)  # 默认使用纯自动模式
    
    if not auto_play_running:
        auto_play_thread = threading.Thread(target=auto_play_loop)
        auto_play_thread.daemon = True
        auto_play_thread.start()

def stop_auto_play():
    """停止自动玩游戏"""
    global auto_play_running
    auto_play_running = False
    button_auto_play.config(text="开始自动玩", command=start_auto_play)
    logging.info("用户手动停止自动游戏")

def set_game_region():
    """设置游戏区域"""
    global game_region
    
    # 提示用户
    status_label.config(text=f"请将鼠标移动到游戏区域左上角，{Config.SET_REGION_DELAY}秒后自动记录...")
    root.update()
    time.sleep(Config.SET_REGION_DELAY)
    
    # 记录左上角坐标
    x1, y1 = pyautogui.position()
    
    status_label.config(text=f"请将鼠标移动到游戏区域右下角，{Config.SET_REGION_DELAY}秒后自动记录...")
    root.update()
    time.sleep(Config.SET_REGION_DELAY)
    
    # 记录右下角坐标
    x2, y2 = pyautogui.position()
    
    # 设置游戏区域
    game_region = (x1, y1, x2, y2)
    
    status_label.config(text=f"已设置游戏区域: 左上角({x1}, {y1}) 右下角({x2}, {y2})")
    logging.info(f"设置游戏区域: 左上角({x1}, {y1}) 右下角({x2}, {y2})")
    
    # 自动识别一次，验证设置
    if measurement_mode == 3:
        identify_game_elements()
    elif measurement_mode == 4:
        identify_chess_piece(capture_game_screen())

def create_ui():
    """创建用户界面"""
    global root, status_label, button_mode1, button_mode2, button_mode3, button_mode4
    global entry_distance, button_calculate, entry_x, entry_y
    global entry_factor, entry_offset, button_update, button_auto_play
    global button_set_region
    
    # 创建GUI
    root = tk.Tk()
    root.geometry("400x600")
    root.title("微信跳一跳自动助手 (厘米单位)")
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 确保中文显示正常
    root.option_add("*Font", "SimHei 10")
    
    # 状态标签
    status_label = tk.Label(root, text="就绪", fg="blue", font=("SimHei", 10))
    status_label.pack(pady=10)
    
    # 测量模式选择
    label_mode = tk.Label(root, text="选择测量方式:", font=("SimHei", 10, "bold"))
    label_mode.pack(pady=5)
    
    # 第一行模式按钮
    frame_mode1 = tk.Frame(root)
    frame_mode1.pack(pady=5)
    
    button_mode1 = tk.Button(frame_mode1, text="方式一: 手动输入距离", command=lambda: set_mode(1), 
                            width=22, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
    button_mode1.pack(side=tk.LEFT, padx=5)
    
    button_mode2 = tk.Button(frame_mode1, text="方式二: 键盘快捷键", command=lambda: set_mode(2), 
                            width=22, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
    button_mode2.pack(side=tk.LEFT, padx=5)
    
    # 第二行模式按钮
    frame_mode2 = tk.Frame(root)
    frame_mode2.pack(pady=5)
    
    button_mode3 = tk.Button(frame_mode2, text="方式三: 自动识别", command=lambda: set_mode(3), 
                            width=22, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
    button_mode3.pack(side=tk.LEFT, padx=5)
    
    button_mode4 = tk.Button(frame_mode2, text="方式四: 半自动", command=lambda: set_mode(4), 
                            width=22, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
    button_mode4.pack(side=tk.LEFT, padx=5)
    
    # 距离输入区域
    frame_distance = tk.LabelFrame(root, text="跳跃距离", font=("SimHei", 10, "bold"))
    frame_distance.pack(fill="x", padx=10, pady=10)
    
    label_distance = tk.Label(frame_distance, text="距离 (厘米):", font=("SimHei", 10))
    label_distance.pack(side=tk.LEFT, padx=10)
    
    entry_distance = tk.Entry(frame_distance, width=15)
    entry_distance.pack(side=tk.LEFT, padx=5)
    entry_distance.insert(0, "0.0")
    
    button_calculate = tk.Button(frame_distance, text="计算跳跃", command=execute_jump, 
                                bg="#52c41a", fg="white", width=12, height=1)
    button_calculate.pack(side=tk.RIGHT, padx=10)
    
    # 设置点击位置
    frame_position = tk.LabelFrame(root, text="点击位置设置", font=("SimHei", 10, "bold"))
    frame_position.pack(fill="x", padx=10, pady=10)
    
    label_x = tk.Label(frame_position, text="X坐标 (像素):", font=("SimHei", 10))
    label_x.pack(side=tk.LEFT, padx=10)
    
    entry_x = tk.Entry(frame_position, width=10)
    entry_x.pack(side=tk.LEFT, padx=5)
    entry_x.insert(0, "1500")  # 默认X坐标
    
    label_y = tk.Label(frame_position, text="Y坐标 (像素):", font=("SimHei", 10))
    label_y.pack(side=tk.LEFT, padx=10)
    
    entry_y = tk.Entry(frame_position, width=10)
    entry_y.pack(side=tk.LEFT, padx=5)
    entry_y.insert(0, "800")  # 默认Y坐标
    
    # 距离与时间函数参数设置
    frame_function = tk.LabelFrame(root, text="距离与时间函数设置", font=("SimHei", 10, "bold"))
    frame_function.pack(fill="x", padx=10, pady=10)
    
    label_function = tk.Label(frame_function, text="时间 = 系数 × 距离 + 偏移量", font=("SimHei", 9))
    label_function.pack(pady=5)
    
    frame_params = tk.Frame(frame_function)
    frame_params.pack(fill="x", padx=10, pady=5)
    
    label_factor = tk.Label(frame_params, text="系数:", font=("SimHei", 10))
    label_factor.pack(side=tk.LEFT, padx=5)
    
    entry_factor = tk.Entry(frame_params, width=8)
    entry_factor.pack(side=tk.LEFT, padx=5)
    entry_factor.insert(0, str(distance_factor))
    
    label_offset = tk.Label(frame_params, text="偏移量:", font=("SimHei", 10))
    label_offset.pack(side=tk.LEFT, padx=5)
    
    entry_offset = tk.Entry(frame_params, width=8)
    entry_offset.pack(side=tk.LEFT, padx=5)
    entry_offset.insert(0, str(time_offset))
    
    button_update = tk.Button(frame_params, text="更新参数", command=update_function_params, 
                            bg="#1890ff", fg="white")
    button_update.pack(side=tk.RIGHT, padx=5)
    
    # 自动玩游戏按钮
    button_auto_play = tk.Button(root, text="开始自动玩", command=start_auto_play, 
                                bg="#ff4d4f", fg="white", width=15, height=2, font=("SimHei", 10))
    button_auto_play.pack(pady=10)
    
    # 设置游戏区域按钮
    button_set_region = tk.Button(root, text="设置游戏区域", command=set_game_region, 
                                bg="#faad14", fg="white", width=15, height=1)
    button_set_region.pack(pady=5)
    
    # 说明标签
    info_label = tk.Label(
        root, 
        text="使用说明:\n"
             "1. 先将微信跳一跳窗口最大化\n"
             "2. 选择测量方式:\n"
             "   - 方式一: 手动输入距离后点击计算跳跃\n"
             "   - 方式二: 按'Z'键记录起点，'X'键记录终点并直接跳跃\n"
             "   - 方式三: 自动识别模式，自动检测棋子和目标位置\n"
             "   - 方式四: 自动识别棋子位置，用户按'X'键确认终点位置\n"
             "3. 使用'设置游戏区域'按钮校准游戏位置\n"
             "4. 在自动模式下，点击'开始自动玩'按钮让程序自动游戏",
        justify=tk.LEFT,
        font=("SimHei", 9)
    )
    info_label.pack(pady=10)
    
    # 日志记录
    logging.info("程序已启动")
    
    # 启动全局键盘监听
    start_global_listener()
    
    # 启动UI主循环
    root.mainloop()

if __name__ == "__main__":
    create_ui()    