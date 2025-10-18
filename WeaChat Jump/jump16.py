import pyautogui
import time
import tkinter as tk
import math
import numpy as np
from pynput import keyboard
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# 确保中文显示正常
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]

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
listener = None  # 全局键盘监听器
data_points = []  # 存储记录的(距离, 时间)数据点

# 距离与点击时间函数参数
distance_factor = 0.11
time_offset = 0.05

# 拟合函数参数
fitted_factor = distance_factor
fitted_offset = time_offset

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
            return distance_cm
        except ValueError:
            status_label.config(text="错误: 请输入有效的距离值")
            return None
    
    elif measurement_mode == 2:  # 键盘快捷键模式
        if not start_point or not end_point:
            status_label.config(text="请先使用快捷键记录起点和终点")
            return None
        
        # 计算两点之间的像素距离
        distance_px = math.sqrt((end_point[0] - start_point[0]) ** 2 + (end_point[1] - start_point[1]) ** 2)
        # 转换为厘米
        distance_cm = px_to_cm(distance_px)
        
        status_label.config(text=f"测量距离: {distance_px:.2f} 像素 ({distance_cm:.2f} 厘米)")
        
        # 自动填充距离到输入框
        entry_distance.delete(0, tk.END)
        entry_distance.insert(0, str(round(distance_cm, 2)))
        
        return distance_cm

def click_and_hold(duration):
    try:
        # 获取输入的坐标并移动鼠标
        x_pos = int(entry_x.get())
        y_pos = int(entry_y.get())
        
        # 添加鼠标移动操作
        pyautogui.moveTo(x_pos, y_pos)
        
        status_label.config(text=f"正在点击并保持 {duration:.2f} 秒...")
        root.update()
        
        pyautogui.mouseDown()
        time.sleep(duration)
        pyautogui.mouseUp()
        
        # 重置键盘模式的点，允许连续跳跃
        if measurement_mode == 2:
            global start_point, end_point
            start_point = None
            end_point = None
            status_label.config(text="跳跃完成，请按'ctrl'键记录下一次起点...")
        
    except Exception as e:
        status_label.config(text=f"错误: {e}")

def calculate_jump_time(distance_cm, use_fitted=False):
    """根据厘米距离计算跳跃时间"""
    global distance_factor, time_offset, fitted_factor, fitted_offset
    if use_fitted and len(data_points) >= 2:
        return fitted_factor * distance_cm + fitted_offset
    else:
        return distance_factor * distance_cm + time_offset

def update_function_params():
    """更新距离与时间函数的参数"""
    global distance_factor, time_offset
    try:
        distance_factor = float(entry_factor.get())
        time_offset = float(entry_offset.get())
        status_label.config(text=f"已更新函数参数: 时间 = {distance_factor} × 距离 + {time_offset}")
        update_chart()
    except ValueError:
        status_label.config(text="错误: 请输入有效的数值")

def execute_jump():
    """执行跳跃操作"""
    distance_cm = calculate_distance()
    if distance_cm is None:
        return
    
    # 计算跳跃时间
    use_fitted = var_use_fitted.get()
    jump_time = calculate_jump_time(distance_cm, use_fitted)
    
    current_function = "拟合" if use_fitted and len(data_points) >= 2 else "手动"
    status_label.config(text=f"使用{current_function}函数计算跳跃时间: {jump_time:.2f} 秒 (基于 {distance_cm:.2f} 厘米)")
    
    # 更新当前跳跃信息
    current_jump_info.config(text=f"当前跳跃: 距离 {distance_cm:.2f} 厘米, 时间 {jump_time:.2f} 秒")
    
    # 执行跳跃
    click_and_hold(jump_time)

def record_data_point():
    """记录当前数据点"""
    global data_points
    
    try:
        distance_cm = float(entry_distance.get())
        # 计算使用当前参数的跳跃时间
        use_fitted = var_use_fitted.get()
        jump_time = calculate_jump_time(distance_cm, use_fitted)
        
        data_points.append((distance_cm, jump_time))
        status_label.config(text=f"已记录数据点: ({distance_cm:.2f} 厘米, {jump_time:.2f} 秒)")
        
        # 更新数据点显示
        update_data_display()
        
        # 拟合新函数
        fit_function()
        
        # 更新图表
        update_chart()
        
    except ValueError:
        status_label.config(text="错误: 无法记录数据点")

def fit_function():
    """拟合距离与时间的函数"""
    global data_points, fitted_factor, fitted_offset
    
    if len(data_points) < 2:
        status_label.config(text="数据点不足，无法拟合函数")
        return
    
    # 提取距离和时间数据
    distances = np.array([point[0] for point in data_points])
    times = np.array([point[1] for point in data_points])
    
    # 执行线性回归拟合 y = ax + b
    A = np.vstack([distances, np.ones(len(distances))]).T
    fitted_factor, fitted_offset = np.linalg.lstsq(A, times, rcond=None)[0]
    
    # 更新拟合参数显示
    fitted_factor_label.config(text=f"拟合系数: {fitted_factor:.4f}")
    fitted_offset_label.config(text=f"拟合偏移量: {fitted_offset:.4f}")
    
    # 计算拟合误差
    predicted_times = fitted_factor * distances + fitted_offset
    mse = np.mean((times - predicted_times) ** 2)
    rmse = np.sqrt(mse)
    fit_error_label.config(text=f"拟合误差 (RMSE): {rmse:.4f}")
    
    status_label.config(text="已成功拟合新函数")

def update_data_display():
    """更新数据点显示"""
    if not data_points:
        data_listbox.delete(0, tk.END)
        data_listbox.insert(tk.END, "暂无记录数据")
        return
    
    data_listbox.delete(0, tk.END)
    for i, (distance, time) in enumerate(data_points):
        data_listbox.insert(tk.END, f"{i+1}. 距离: {distance:.2f} 厘米, 时间: {time:.2f} 秒")

def update_chart():
    """更新图表显示"""
    global data_points, distance_factor, time_offset, fitted_factor, fitted_offset
    
    # 清除现有图表
    ax.clear()
    
    # 如果有数据点，绘制它们
    if data_points:
        distances = [point[0] for point in data_points]
        times = [point[1] for point in data_points]
        ax.scatter(distances, times, color='blue', label='记录数据')
    
    # 绘制手动设置的函数线
    min_dist = min([point[0] for point in data_points]) if data_points else 0
    max_dist = max([point[0] for point in data_points]) if data_points else 10
    dist_range = np.linspace(min_dist, max_dist, 100)
    ax.plot(dist_range, distance_factor * dist_range + time_offset, 'r-', 
            label=f'手动函数: 时间={distance_factor:.4f}×距离+{time_offset:.4f}')
    
    # 如果有足够的数据点，绘制拟合函数线
    if len(data_points) >= 2:
        ax.plot(dist_range, fitted_factor * dist_range + fitted_offset, 'g-', 
                label=f'拟合函数: 时间={fitted_factor:.4f}×距离+{fitted_offset:.4f}')
    
    ax.set_xlabel('距离 (厘米)')
    ax.set_ylabel('时间 (秒)')
    ax.set_title('距离与时间关系')
    ax.grid(True)
    ax.legend()
    
    # 刷新画布
    canvas.draw()

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
        status_label.config(text="已切换到方式二：使用键盘快捷键测量")
        entry_distance.config(state=tk.DISABLED)  # 禁用输入框
        status_label.config(text="请将鼠标移动到起点位置，按'ctrl'键记录起点...")

def on_key_press(key):
    """处理全局键盘事件"""
    try:
        if key == keyboard.Key.ctrl and measurement_mode == 2:
            x, y = pyautogui.position()
            global start_point
            start_point = (x, y)
            root.after(0, lambda: status_label.config(text=f"已记录起点: ({x}, {y})\n请移动到终点按'alt'键"))
            
        elif key == keyboard.Key.alt and measurement_mode == 2:
            if start_point:
                x, y = pyautogui.position()
                global end_point
                end_point = (x, y)
                root.after(0, lambda: status_label.config(text=f"已记录终点: ({x}, {y})\n正在执行跳跃..."))
                execute_jump()
                
    except AttributeError:
        pass

def start_global_listener():
    """启动全局键盘监听"""
    global listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()

def clear_data_points():
    """清除所有记录的数据点"""
    global data_points
    data_points = []
    update_data_display()
    fit_function()
    update_chart()
    status_label.config(text="已清除所有记录数据")

def on_closing():
    """窗口关闭时的清理操作"""
    global listener
    if listener:
        listener.stop()
    root.destroy()

# 创建GUI
root = tk.Tk()
root.geometry("900x650")
root.title("微信跳一跳自动助手 (厘米单位) - 增强版")
root.protocol("WM_DELETE_WINDOW", on_closing)

# 确保中文显示正常
root.option_add("*Font", "SimHei 10")

# 主框架
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# 左侧控制面板
left_frame = tk.Frame(main_frame, width=400)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

# 状态标签
status_label = tk.Label(left_frame, text="就绪", fg="blue", font=("SimHei", 10))
status_label.pack(pady=10)

# 当前跳跃信息
current_jump_info = tk.Label(left_frame, text="当前跳跃: 无", fg="green", font=("SimHei", 10))
current_jump_info.pack(pady=5)

# 测量模式选择
label_mode = tk.Label(left_frame, text="选择测量方式:", font=("SimHei", 10, "bold"))
label_mode.pack(pady=5)

frame_mode = tk.Frame(left_frame)
frame_mode.pack(pady=5)

button_mode1 = tk.Button(frame_mode, text="方式一: 手动输入距离", command=lambda: set_mode(1), 
                        width=18, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
button_mode1.pack(side=tk.LEFT, padx=5)

button_mode2 = tk.Button(frame_mode, text="方式二: 键盘快捷键", command=lambda: set_mode(2), 
                        width=18, height=2, bg="#e6f7ff", fg="#1890ff", relief=tk.RAISED)
button_mode2.pack(side=tk.LEFT, padx=5)

# 距离输入区域
frame_distance = tk.LabelFrame(left_frame, text="跳跃距离", font=("SimHei", 10, "bold"))
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
frame_position = tk.LabelFrame(left_frame, text="点击位置设置", font=("SimHei", 10, "bold"))
frame_position.pack(fill="x", padx=10, pady=10)

label_x = tk.Label(frame_position, text="X坐标 (像素):", font=("SimHei", 10))
label_x.pack(side=tk.LEFT, padx=10)

entry_x = tk.Entry(frame_position, width=10)
entry_x.pack(side=tk.LEFT, padx=5)
entry_x.insert(0, "960")  # 默认X坐标

label_y = tk.Label(frame_position, text="Y坐标 (像素):", font=("SimHei", 10))
label_y.pack(side=tk.LEFT, padx=10)

entry_y = tk.Entry(frame_position, width=10)
entry_y.pack(side=tk.LEFT, padx=5)
entry_y.insert(0, "800")  # 默认Y坐标

# 距离与时间函数参数设置
frame_function = tk.LabelFrame(left_frame, text="距离与时间函数设置", font=("SimHei", 10, "bold"))
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
entry_offset.insert

# 拟合函数显示
frame_fit = tk.LabelFrame(left_frame, text="拟合函数结果", font=("SimHei", 10, "bold"))
frame_fit.pack(fill="x", padx=10, pady=10)

fitted_factor_label = tk.Label(frame_fit, text="拟合系数: --", font=("SimHei", 9))
fitted_factor_label.pack(anchor=tk.W, padx=10, pady=2)

fitted_offset_label = tk.Label(frame_fit, text="拟合偏移量: --", font=("SimHei", 9))
fitted_offset_label.pack(anchor=tk.W, padx=10, pady=2)

fit_error_label = tk.Label(frame_fit, text="拟合误差 (RMSE): --", font=("SimHei", 9))
fit_error_label.pack(anchor=tk.W, padx=10, pady=2)

# 使用拟合函数的复选框
var_use_fitted = tk.BooleanVar(value=False)
check_fitted = tk.Checkbutton(frame_fit, text="使用拟合函数进行跳跃计算", variable=var_use_fitted, font=("SimHei", 9))
check_fitted.pack(anchor=tk.W, padx=10, pady=5)

# 数据记录区域
frame_data = tk.LabelFrame(left_frame, text="数据记录", font=("SimHei", 10, "bold"))
frame_data.pack(fill="both", expand=True, padx=10, pady=10)

button_record = tk.Button(frame_data, text="记录当前数据点", command=record_data_point, 
                         bg="#fa8c16", fg="white", width=15, height=1)
button_record.pack(pady=5)

button_clear = tk.Button(frame_data, text="清除所有数据", command=clear_data_points, 
                        bg="#f5222d", fg="white", width=15, height=1)
button_clear.pack(pady=5)

# 数据列表
data_listbox = tk.Listbox(frame_data, height=5)
data_listbox.pack(fill="both", expand=True, padx=5, pady=5)
data_listbox.insert(tk.END, "暂无记录数据")

# 右侧图表区域
right_frame = tk.Frame(main_frame, width=500)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

chart_frame = tk.LabelFrame(right_frame, text="距离与时间关系图", font=("SimHei", 10, "bold"))
chart_frame.pack(fill="both", expand=True, padx=5, pady=5)

# 创建图表
fig = Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=chart_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# 初始化图表
update_chart()

# 说明标签
info_label = tk.Label(
    left_frame, 
    text="使用说明:\n"
         "1. 先将微信跳一跳窗口最大化\n"
         "2. 选择测量方式:\n"
         "   - 方式一: 手动输入距离后点击计算跳跃\n"
         "   - 方式二: 按'/'键记录起点，'*'键记录终点，'-'键执行跳跃\n"
         "3. 当跳跃完美时，点击'记录当前数据点'按钮保存数据\n"
         "4. 数据会自动拟合新的函数，可选择使用拟合函数进行计算",
    justify=tk.LEFT,
    font=("SimHei", 9)
)
info_label.pack(pady=10)

# 启动全局键盘监听
start_global_listener()

root.mainloop()    