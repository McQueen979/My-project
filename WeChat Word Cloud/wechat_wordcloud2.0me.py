"""
微信聊天记录词云图生成器 - 增强版
优化了词频大小差异
"""

import json
import re
import jieba
from collections import Counter
from wordcloud import WordCloud, ImageColorGenerator
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import math

# ============================================
# 第一部分：设置参数（你可以修改这里）
# ============================================

# 1. 你的JSON文件路径
JSON_FILE = "chat.json"

# 2. 分析谁的消息？
# "all" - 所有人的消息，"me" - 只分析我发的消息，"other" - 只分析对方发的消息
ANALYZE_WHO = "me"

# 3. 排除系统消息吗？
EXCLUDE_SYSTEM_MESSAGES = True

# 4. 词云显示设置
MAX_WORDS = 200           # 最多显示多少个词
BACKGROUND_COLOR = "white"  # 背景颜色
WIDTH = 1000              # 图片宽度（增大）
HEIGHT = 800              # 图片高度（增大）

# 5. 【重要】词频差异增强设置
FONT_SIZE_RANGE = (8, 120)  # 字体大小范围（最小，最大），原为(10, 100)
# 这个值越大，词频差异越明显
# 1.0：线性关系，2.0：平方关系，0.5：平方根关系
FREQUENCY_EXPONENT = 1.8  # 词频指数，建议1.5-2.5之间
USE_LOG_SCALE = True     # 是否使用对数缩放，让大小差异更符合人眼感知
RELATIVE_SCALING = 0.8   # 相对缩放系数，0-1之间，值越大词频差异越明显

# 6. 颜色增强
COLOR_SCHEME = "viridis"  # 颜色方案，可选：viridis, plasma, rainbow, hsv, jet
RANDOM_COLOR = True       # 是否使用随机颜色

# 7. 停用词（可以自己添加）
STOP_WORDS = [
    "的", "了", "在", "是", "我", "有", "和", "就", 
    "不", "人", "都", "一", "一个", "上", "也", "很", 
    "到", "说", "要", "去", "你", "会", "着", "没有", 
    "看", "好", "自己", "这", "中", "就是", "对", "在", 
    "可以", "吧", "啦", "吗", "呢", "啊", "呀", "哦",
    "哈哈", "哈哈哈", "哈哈哈哈", "嘻嘻", "呵呵", "嗯",
    "这个", "那个", "什么", "怎么", "为什么", "因为",
    "所以", "但是", "然后", "而且", "其实", "还是",
    "就是", "就是", "就是", "就是", "就是", "就是"
]

# 8. 排除特定内容
REMOVE_PATTERNS = [
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
    r'\[.*?\]',
    r'【.*?】',
    r'#.*?#',
    r'<.*?>',
]

# 9. 输出文件名
OUTPUT_IMAGE = "wechat_wordcloud_enhanced.png"
OUTPUT_STATS = "word_frequency_enhanced.csv"

# ============================================
# 第二部分：读取和处理数据
# ============================================

def load_wechat_data(file_path):
    """
    读取微信聊天记录的JSON文件
    """
    print(f"正在读取文件: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'messages' not in data:
            print("错误：JSON文件中没有找到'messages'字段")
            return []
        
        messages = data['messages']
        print(f"成功读取 {len(messages)} 条消息")
        
        if 'session' in data:
            session_info = data['session']
            print(f"会话名称: {session_info.get('nickname', '未知')}")
            print(f"消息总数: {session_info.get('messageCount', len(messages))}")
        
        return messages
        
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return []

def filter_messages(messages, who="all", exclude_system=True):
    """
    过滤消息
    """
    filtered = []
    
    for msg in messages:
        msg_type = msg.get('type', '')
        content = msg.get('content', '')
        
        if not content or not isinstance(content, str):
            continue
            
        if exclude_system and msg_type == "系统消息":
            continue
            
        is_send = msg.get('isSend')
        
        if who == "me" and is_send != 1:
            continue
        elif who == "other" and is_send != 0:
            continue
        elif who not in ["all", "me", "other"]:
            continue
            
        filtered.append({
            'content': content,
            'type': msg_type,
            'sender': msg.get('senderDisplayName', ''),
            'isSend': is_send,
            'time': msg.get('formattedTime', '')
        })
    
    print(f"过滤后得到 {len(filtered)} 条文本消息")
    return filtered

def clean_text(text):
    """
    清洗文本
    """
    if not isinstance(text, str):
        return ""
    
    for pattern in REMOVE_PATTERNS:
        text = re.sub(pattern, '', text)
    
    return text.replace('\n', ' ').replace('\r', ' ').strip()

# ============================================
# 第三部分：增强的词云生成
# ============================================

def enhance_frequency_distribution(word_counts, exponent=1.5, use_log_scale=True):
    """
    增强词频分布，使大小差异更明显
    word_counts: 词频字典
    exponent: 指数，大于1会放大高频词，小于1会缩小高频词
    use_log_scale: 是否使用对数缩放
    """
    if not word_counts:
        return {}
    
    enhanced_counts = {}
    
    # 获取原始频率
    frequencies = list(word_counts.values())
    
    if len(frequencies) < 2:
        return word_counts  # 只有一个词，无需处理
    
    min_freq = min(frequencies)
    max_freq = max(frequencies)
    
    print(f"原始频率范围: {min_freq} - {max_freq}")
    
    for word, freq in word_counts.items():
        if use_log_scale:
            # 使用对数缩放，减小极端值的影响
            enhanced = math.log(freq + 1) ** exponent
        else:
            # 使用指数缩放
            enhanced = freq ** exponent
        
        enhanced_counts[word] = enhanced
    
    # 将增强后的值缩放到合适的范围
    enhanced_values = list(enhanced_counts.values())
    min_enhanced = min(enhanced_values)
    max_enhanced = max(enhanced_values)
    
    # 缩放到1-100的范围
    scaled_counts = {}
    for word, enhanced in enhanced_counts.items():
        if max_enhanced > min_enhanced:
            # 线性缩放
            scaled = 1 + 99 * (enhanced - min_enhanced) / (max_enhanced - min_enhanced)
        else:
            scaled = 50  # 所有值相同的情况
        
        scaled_counts[word] = scaled
    
    return scaled_counts

def analyze_word_frequency_distribution(word_counts):
    """
    分析词频分布
    """
    if not word_counts:
        return
    
    frequencies = list(word_counts.values())
    frequencies.sort(reverse=True)
    
    print("\n" + "="*50)
    print("词频分布分析:")
    print("="*50)
    
    if len(frequencies) > 0:
        print(f"最高频词: {frequencies[0]} 次")
        print(f"最低频词: {frequencies[-1]} 次")
        print(f"词频极差: {frequencies[0] - frequencies[-1]}")
    
    if len(frequencies) >= 10:
        print(f"前10%的词频: {frequencies[:len(frequencies)//10]}")
        print(f"后10%的词频: {frequencies[-len(frequencies)//10:]}")
    
    # 计算基尼系数（衡量不均衡程度）
    total = sum(frequencies)
    if total > 0:
        cumulative_sum = 0
        gini_sum = 0
        n = len(frequencies)
        
        for i, freq in enumerate(sorted(frequencies)):
            cumulative_sum += freq
            gini_sum += (i + 1) * freq
        
        gini = (2 * gini_sum) / (n * total) - (n + 1) / n
        print(f"基尼系数: {gini:.3f} (越接近1表示分布越不均衡)")
    
    print("="*50)

def generate_enhanced_wordcloud(texts, max_words=200, background_color="white"):
    """
    生成增强版的词云图
    """
    if not texts:
        print("错误：没有文本可以生成词云")
        return None, None
    
    print("正在分词和统计词频...")
    
    # 将所有文本合并
    all_text = ' '.join(texts)
    
    # 使用jieba分词
    words = jieba.lcut(all_text)
    
    # 过滤停用词和单字
    filtered_words = []
    for word in words:
        word = word.strip()
        if (len(word) > 1 and
            word not in STOP_WORDS and
            not word.isdigit() and
            not re.match(r'^[^\u4e00-\u9fa5]+$', word)):
            filtered_words.append(word)
    
    # 统计原始词频
    raw_word_counts = Counter(filtered_words)
    
    if not raw_word_counts:
        print("错误：分词后没有有效的词语")
        return None, None
    
    print(f"分词得到 {len(filtered_words)} 个有效词语，{len(raw_word_counts)} 个不同词语")
    
    # 分析原始词频分布
    analyze_word_frequency_distribution(raw_word_counts)
    
    # 增强词频分布
    print(f"\n应用增强参数: 指数={FREQUENCY_EXPONENT}, 对数缩放={USE_LOG_SCALE}")
    enhanced_counts = enhance_frequency_distribution(
        raw_word_counts, 
        exponent=FREQUENCY_EXPONENT,
        use_log_scale=USE_LOG_SCALE
    )
    
    # 显示最常见的20个词
    print("\n原始词频前20名:")
    for word, count in raw_word_counts.most_common(20):
        print(f"  {word}: {count}次")
    
    # 创建词云
    print("\n正在生成增强版词云...")
    
    # 确保有中文字体
    font_path = None
    possible_fonts = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "simhei.ttf",
    ]
    
    for font in possible_fonts:
        if os.path.exists(font):
            font_path = font
            print(f"使用字体: {font}")
            break
    
    if not font_path:
        print("警告：未找到中文字体，词云可能无法显示中文")
        font_path = None
    
    # 生成词云对象
    wc = WordCloud(
        font_path=font_path,
        width=WIDTH,
        height=HEIGHT,
        background_color=background_color,
        max_words=max_words,
        max_font_size=FONT_SIZE_RANGE[1],
        min_font_size=FONT_SIZE_RANGE[0],
        relative_scaling=RELATIVE_SCALING,
        random_state=42,
        collocations=False,
        colormap=COLOR_SCHEME if not RANDOM_COLOR else None,
        prefer_horizontal=0.9,  # 水平词的比例
        scale=2,  # 生成图片的缩放比例
        contour_width=0,  # 轮廓宽度
        contour_color='steelblue',  # 轮廓颜色
    )
    
    # 使用增强后的词频生成词云
    wc.generate_from_frequencies(enhanced_counts)
    
    print(f"词云已生成:")
    print(f"  - 字体大小范围: {FONT_SIZE_RANGE[0]}-{FONT_SIZE_RANGE[1]}")
    print(f"  - 相对缩放系数: {RELATIVE_SCALING}")
    print(f"  - 包含词语数量: {len(wc.words_)}")
    
    return wc, raw_word_counts

def save_enhanced_results(wordcloud, word_counts):
    """
    保存结果
    """
    if not wordcloud:
        return False
    
    # 保存词云图片
    try:
        wordcloud.to_file(OUTPUT_IMAGE)
        print(f"词云图片已保存: {OUTPUT_IMAGE}")
    except Exception as e:
        print(f"保存图片失败: {e}")
        return False
    
    # 保存词频统计
    try:
        df = pd.DataFrame(
            word_counts.most_common(),
            columns=['词语', '频次']
        )
        df.to_csv(OUTPUT_STATS, index=False, encoding='utf-8-sig')
        print(f"词频统计已保存: {OUTPUT_STATS}")
        
        # 显示前20个词
        print("\n词频前20名:")
        for i, row in df.head(20).iterrows():
            print(f"  {i+1:2d}. {row['词语']:10s}: {row['频次']:4d}次")
        
        # 计算并显示差异统计
        if len(df) >= 2:
            max_freq = df.iloc[0]['频次']
            min_freq = df.iloc[-1]['频次']
            ratio = max_freq / min_freq if min_freq > 0 else 0
            print(f"\n词频差异统计:")
            print(f"  最高频词 '{df.iloc[0]['词语']}': {max_freq} 次")
            print(f"  最低频词 '{df.iloc[-1]['词语']}': {min_freq} 次")
            print(f"  频次比: {ratio:.1f}:1")
            
    except Exception as e:
        print(f"保存词频统计失败: {e}")
    
    return True

def display_enhanced_wordcloud(wordcloud, word_counts):
    """
    显示增强版词云
    """
    if not wordcloud:
        return
    
    # 创建子图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # 左图：词云
    ax1.imshow(wordcloud, interpolation="bilinear")
    ax1.axis("off")
    ax1.set_title("微信聊天记录词云图（增强版）", fontsize=16, fontweight='bold')
    
    # 添加参数信息
    params_text = f"参数设置:\n"
    params_text += f"字体大小: {FONT_SIZE_RANGE[0]}-{FONT_SIZE_RANGE[1]}\n"
    params_text += f"词频指数: {FREQUENCY_EXPONENT}\n"
    params_text += f"对数缩放: {USE_LOG_SCALE}\n"
    params_text += f"相对缩放: {RELATIVE_SCALING}"
    
    ax1.text(0.02, 0.98, params_text, 
             transform=ax1.transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontsize=9)
    
    # 右图：词频分布柱状图
    if word_counts and len(word_counts) > 0:
        # 获取前20个高频词
        top_words = dict(word_counts.most_common(20))
        
        words = list(top_words.keys())
        freqs = list(top_words.values())
        
        # 创建水平柱状图
        y_pos = range(len(words))
        bars = ax2.barh(y_pos, freqs, align='center', alpha=0.7, color='steelblue')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(words, fontproperties='SimHei')
        ax2.invert_yaxis()  # 最高的在顶部
        ax2.set_xlabel('出现次数')
        ax2.set_title('高频词排行榜（前20）')
        
        # 在柱状图上显示数值
        for i, (bar, freq) in enumerate(zip(bars, freqs)):
            width = bar.get_width()
            ax2.text(width + max(freqs)*0.01, bar.get_y() + bar.get_height()/2,
                    f'{freq}', va='center', fontsize=9)
    
    plt.suptitle(f"词云分析结果 - 共 {len(word_counts)} 个不同词语", fontsize=14)
    plt.tight_layout()
    plt.show()

# ============================================
# 第四部分：主程序
# ============================================

def main():
    """
    主函数
    """
    print("=" * 60)
    print("微信聊天记录词云图生成器 - 增强版")
    print("=" * 60)
    print(f"参数设置:")
    print(f"  - 字体大小范围: {FONT_SIZE_RANGE[0]}-{FONT_SIZE_RANGE[1]}")
    print(f"  - 词频指数: {FREQUENCY_EXPONENT}")
    print(f"  - 对数缩放: {USE_LOG_SCALE}")
    print(f"  - 相对缩放系数: {RELATIVE_SCALING}")
    print("=" * 60)
    
    # 检查文件是否存在
    if not os.path.exists(JSON_FILE):
        print(f"错误：找不到文件 '{JSON_FILE}'")
        print("请将JSON文件放在同一目录下")
        input("按回车键退出...")
        return
    
    # 1. 加载数据
    messages = load_wechat_data(JSON_FILE)
    if not messages:
        print("没有可处理的消息")
        input("按回车键退出...")
        return
    
    # 2. 过滤消息
    print(f"\n正在过滤消息 (分析对象: {ANALYZE_WHO})...")
    filtered_messages = filter_messages(
        messages, 
        who=ANALYZE_WHO,
        exclude_system=EXCLUDE_SYSTEM_MESSAGES
    )
    
    if not filtered_messages:
        print("过滤后没有消息可分析")
        input("按回车键退出...")
        return
    
    # 3. 提取和清洗文本
    print("\n正在清洗文本...")
    texts = []
    for msg in filtered_messages:
        cleaned = clean_text(msg['content'])
        if cleaned:
            texts.append(cleaned)
    
    print(f"清洗后得到 {len(texts)} 条有效文本")
    
    # 4. 生成增强版词云
    wordcloud, word_counts = generate_enhanced_wordcloud(
        texts, 
        max_words=MAX_WORDS,
        background_color=BACKGROUND_COLOR
    )
    
    if not wordcloud:
        print("生成词云失败")
        input("按回车键退出...")
        return
    
    # 5. 保存和显示结果
    print("\n正在保存结果...")
    save_enhanced_results(wordcloud, word_counts)
    
    print("\n正在显示词云图...")
    display_enhanced_wordcloud(wordcloud, word_counts)
    
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"1. 词云图片: {OUTPUT_IMAGE}")
    print(f"2. 词频统计: {OUTPUT_STATS}")
    print("\n提示：可以调整以下参数获得不同效果：")
    print("  - 增大 FONT_SIZE_RANGE 的第一个值，让最小字更大")
    print("  - 增大 FONT_SIZE_RANGE 的第二个值，让最大字更大")
    print("  - 增大 FREQUENCY_EXPONENT (1.5-3.0)，增强词频差异")
    print("  - 调整 RELATIVE_SCALING (0.5-1.0)，控制缩放系数")
    print("=" * 60)
    
    input("按回车键退出程序...")

# 运行主程序
if __name__ == "__main__":
    main()