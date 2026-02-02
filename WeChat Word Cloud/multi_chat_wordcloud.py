"""
多微信聊天记录词云图生成器
可以一次性处理多个JSON文件，生成综合词云
"""

import json
import re
import jieba
import os
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import glob

# ============================================
# 第一部分：设置参数
# ============================================

# 1. 文件设置
JSON_FOLDER = "."  # JSON文件所在的文件夹，默认当前文件夹
# 或者指定具体的文件列表（二选一）
# JSON_FILES = ["chat1.json", "chat2.json", "chat3.json"]
JSON_FILES = []  # 如果为空，则自动查找文件夹下所有JSON文件

# 2. 文件过滤设置
FILE_PATTERN = "*.json"  # 文件匹配模式
EXCLUDE_FILES = []  # 要排除的文件名列表

# 3. 分析设置
ANALYZE_WHO = "all"  # "all"=全部, "me"=自己, "other"=对方
EXCLUDE_SYSTEM_MESSAGES = True
INCLUDE_NAMES_IN_WORDS = False  # 是否将聊天对象的名字加入词云

# 4. 词云显示设置
MAX_WORDS = 250
BACKGROUND_COLOR = "white"
WIDTH = 1200
HEIGHT = 800
FONT_SIZE_RANGE = (8, 120)
FREQUENCY_EXPONENT = 1.8
USE_LOG_SCALE = True
RELATIVE_SCALING = 0.8
COLOR_SCHEME = "viridis"

# 5. 输出设置
OUTPUT_IMAGE = "combined_wordcloud.png"
OUTPUT_STATS = "combined_word_frequency.csv"
OUTPUT_SUMMARY = "chat_summary.csv"  # 聊天记录汇总统计

# 6. 停用词
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

# 7. 排除模式
REMOVE_PATTERNS = [
    r'http[s]?://\S+',
    r'\[.*?\]',
    r'【.*?】',
    r'#.*?#',
    r'<.*?>',
    r'微信.*?表情',
    r'视频.*?聊天',
    r'语音.*?消息',
]

# ============================================
# 第二部分：文件处理函数
# ============================================

def get_json_files(folder_path, file_pattern="*.json", exclude_files=None):
    """
    获取指定文件夹下所有的JSON文件
    """
    if exclude_files is None:
        exclude_files = []
    
    # 如果指定了具体的文件列表，就使用它
    if JSON_FILES:
        print(f"使用指定的文件列表: {JSON_FILES}")
        valid_files = []
        for file in JSON_FILES:
            if os.path.exists(file):
                valid_files.append(file)
            else:
                print(f"警告：文件不存在: {file}")
        return valid_files
    
    # 否则自动查找文件夹下的所有JSON文件
    pattern = os.path.join(folder_path, file_pattern)
    all_files = glob.glob(pattern)
    
    # 过滤掉排除的文件
    filtered_files = [f for f in all_files 
                     if os.path.basename(f) not in exclude_files]
    
    # 按文件大小排序（从大到小）
    filtered_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    
    return filtered_files

def load_single_chat_file(file_path):
    """
    加载单个聊天记录文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        filename = os.path.basename(file_path)
        
        # 检查数据结构
        if 'messages' not in data:
            print(f"警告：{filename} 中没有找到'messages'字段，跳过此文件")
            return None, filename
        
        messages = data['messages']
        
        # 获取聊天信息
        chat_info = {
            'filename': filename,
            'message_count': len(messages),
            'chat_name': '未知聊天',
            'last_time': '未知',
            'type': '未知'
        }
        
        if 'session' in data:
            session = data['session']
            chat_info['chat_name'] = session.get('nickname', 
                                               session.get('remark', 
                                                         session.get('displayName', '未知聊天')))
            chat_info['last_time'] = session.get('lastTimestamp', '未知')
            chat_info['type'] = session.get('type', '未知')
            chat_info['message_count'] = session.get('messageCount', len(messages))
        
        print(f"  ✓ 已加载: {filename}")
        print(f"    聊天对象: {chat_info['chat_name']}")
        print(f"    消息数量: {chat_info['message_count']}")
        
        return messages, chat_info
        
    except json.JSONDecodeError as e:
        print(f"错误：{file_path} 不是有效的JSON文件 - {e}")
        return None, None
    except Exception as e:
        print(f"读取 {file_path} 时出错: {e}")
        return None, None

def load_all_chat_files():
    """
    加载所有聊天记录文件
    """
    print("正在扫描JSON文件...")
    
    # 获取所有JSON文件
    json_files = get_json_files(JSON_FOLDER, FILE_PATTERN, EXCLUDE_FILES)
    
    if not json_files:
        print(f"错误：在 '{JSON_FOLDER}' 文件夹中没有找到JSON文件！")
        print("请检查：")
        print(f"1. JSON文件是否在 '{JSON_FOLDER}' 文件夹中")
        print(f"2. 文件扩展名是否为 .json")
        return [], []
    
    print(f"找到 {len(json_files)} 个JSON文件:")
    for i, file in enumerate(json_files, 1):
        size_mb = os.path.getsize(file) / (1024 * 1024)
        print(f"  {i:2d}. {os.path.basename(file)} ({size_mb:.1f} MB)")
    
    print("\n开始加载文件...")
    
    all_messages = []
    chat_infos = []
    skipped_files = []
    
    for file_path in json_files:
        messages, chat_info = load_single_chat_file(file_path)
        
        if messages is not None and chat_info is not None:
            all_messages.extend(messages)
            chat_infos.append(chat_info)
        else:
            skipped_files.append(os.path.basename(file_path))
    
    print(f"\n文件加载完成:")
    print(f"  ✓ 成功加载: {len(chat_infos)} 个文件")
    print(f"  ✗ 跳过文件: {len(skipped_files)} 个")
    if skipped_files:
        print(f"    跳过的文件: {', '.join(skipped_files)}")
    
    return all_messages, chat_infos

# ============================================
# 第三部分：数据处理函数
# ============================================

def filter_messages(messages, who="all", exclude_system=True):
    """
    过滤消息
    """
    filtered = []
    stats = {
        'total': len(messages),
        'text': 0,
        'system': 0,
        'me': 0,
        'other': 0,
        'other_names': set()
    }
    
    for msg in messages:
        msg_type = msg.get('type', '')
        content = msg.get('content', '')
        
        if not content or not isinstance(content, str):
            continue
        
        # 统计系统消息
        if msg_type == "系统消息":
            stats['system'] += 1
            if exclude_system:
                continue
        else:
            stats['text'] += 1
        
        # 获取发送者信息
        is_send = msg.get('isSend')
        sender_name = msg.get('senderDisplayName', '')
        
        # 统计发送者
        if is_send == 1:
            stats['me'] += 1
        elif is_send == 0 and sender_name:
            stats['other'] += 1
            stats['other_names'].add(sender_name)
        
        # 根据发送者过滤
        if who == "me" and is_send != 1:
            continue
        elif who == "other" and is_send != 0:
            continue
        elif who not in ["all", "me", "other"]:
            continue
        
        # 添加消息
        filtered.append({
            'content': content,
            'type': msg_type,
            'sender': sender_name,
            'isSend': is_send,
            'time': msg.get('formattedTime', '')
        })
    
    print(f"\n消息统计:")
    print(f"  总消息数: {stats['total']}")
    print(f"  文本消息: {stats['text']}")
    print(f"  系统消息: {stats['system']}")
    print(f"  我发送的: {stats['me']}")
    print(f"  对方发送: {stats['other']}")
    if stats['other_names']:
        print(f"  聊天对象: {', '.join(stats['other_names'])}")
    
    print(f"过滤后得到 {len(filtered)} 条有效消息")
    return filtered, stats

def clean_text(text, remove_patterns=None):
    """
    清洗文本
    """
    if remove_patterns is None:
        remove_patterns = REMOVE_PATTERNS
    
    if not isinstance(text, str):
        return ""
    
    cleaned = text
    for pattern in remove_patterns:
        cleaned = re.sub(pattern, '', cleaned)
    
    # 移除多余空白字符
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def extract_texts_from_messages(messages, include_names=False, names=None):
    """
    从消息中提取文本
    """
    texts = []
    word_count = 0
    
    for msg in messages:
        content = msg.get('content', '')
        if not content:
            continue
        
        cleaned = clean_text(content)
        if cleaned:
            texts.append(cleaned)
            word_count += len(cleaned)
            
            # 如果需要，添加聊天对象名字到文本中
            if include_names and names:
                sender = msg.get('sender', '')
                if sender in names:
                    # 将名字按单个字拆分，避免jieba分词识别
                    for char in sender:
                        if char not in STOP_WORDS and len(char) > 0:
                            texts.append(char)
    
    print(f"提取到 {len(texts)} 条文本，共约 {word_count} 个字符")
    return texts

# ============================================
# 第四部分：词云生成函数
# ============================================

def enhance_frequency_distribution(word_counts, exponent=1.5, use_log_scale=True):
    """
    增强词频分布
    """
    if not word_counts:
        return {}
    
    enhanced_counts = {}
    
    frequencies = list(word_counts.values())
    if len(frequencies) < 2:
        return word_counts
    
    min_freq = min(frequencies)
    max_freq = max(frequencies)
    
    for word, freq in word_counts.items():
        if use_log_scale:
            enhanced = math.log(freq + 1) ** exponent
        else:
            enhanced = freq ** exponent
        enhanced_counts[word] = enhanced
    
    # 缩放到1-100范围
    enhanced_values = list(enhanced_counts.values())
    min_enhanced = min(enhanced_values)
    max_enhanced = max(enhanced_values)
    
    scaled_counts = {}
    for word, enhanced in enhanced_counts.items():
        if max_enhanced > min_enhanced:
            scaled = 1 + 99 * (enhanced - min_enhanced) / (max_enhanced - min_enhanced)
        else:
            scaled = 50
        scaled_counts[word] = scaled
    
    return scaled_counts

def generate_combined_wordcloud(texts, chat_infos=None):
    """
    生成综合词云
    """
    if not texts:
        print("错误：没有文本可以生成词云")
        return None, None
    
    print(f"\n正在处理 {len(texts)} 条文本...")
    
    # 合并所有文本
    all_text = ' '.join(texts)
    
    # 使用jieba分词
    print("正在分词...")
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
    
    # 统计词频
    word_counts = Counter(filtered_words)
    
    if not word_counts:
        print("错误：分词后没有有效的词语")
        return None, None
    
    print(f"分词得到 {len(filtered_words)} 个有效词语，{len(word_counts)} 个不同词语")
    
    # 显示最常见的30个词
    print("\n最常见的30个词语:")
    for i, (word, count) in enumerate(word_counts.most_common(30), 1):
        print(f"  {i:2d}. {word:10s}: {count:6d}次")
    
    # 增强词频分布
    print(f"\n应用增强参数: 指数={FREQUENCY_EXPONENT}, 对数缩放={USE_LOG_SCALE}")
    enhanced_counts = enhance_frequency_distribution(
        word_counts, 
        exponent=FREQUENCY_EXPONENT,
        use_log_scale=USE_LOG_SCALE
    )
    
    # 查找字体
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
        print("警告：未找到中文字体，使用默认字体")
    
    # 创建词云对象
    print("正在生成词云...")
    wc = WordCloud(
        font_path=font_path,
        width=WIDTH,
        height=HEIGHT,
        background_color=BACKGROUND_COLOR,
        max_words=MAX_WORDS,
        max_font_size=FONT_SIZE_RANGE[1],
        min_font_size=FONT_SIZE_RANGE[0],
        relative_scaling=RELATIVE_SCALING,
        random_state=42,
        collocations=False,
        colormap=COLOR_SCHEME,
        prefer_horizontal=0.9,
        scale=2,
        contour_width=0,
        contour_color='steelblue',
    )
    
    # 生成词云
    wc.generate_from_frequencies(enhanced_counts)
    
    print(f"词云生成完成，包含 {len(wc.words_)} 个词语")
    
    return wc, word_counts

# ============================================
# 第五部分：结果保存和显示
# ============================================

def save_combined_results(wordcloud, word_counts, chat_infos, stats):
    """
    保存综合结果
    """
    if not wordcloud:
        return False
    
    # 保存词云图片
    try:
        wordcloud.to_file(OUTPUT_IMAGE)
        print(f"\n词云图片已保存: {OUTPUT_IMAGE}")
    except Exception as e:
        print(f"保存图片失败: {e}")
        return False
    
    # 保存词频统计
    try:
        df_word_freq = pd.DataFrame(
            word_counts.most_common(),
            columns=['词语', '频次']
        )
        df_word_freq.to_csv(OUTPUT_STATS, index=False, encoding='utf-8-sig')
        print(f"词频统计已保存: {OUTPUT_STATS}")
        
        # 显示前20个词
        print("\n词频前20名:")
        for i, row in df_word_freq.head(20).iterrows():
            print(f"  {i+1:2d}. {row['词语']:10s}: {row['频次']:6d}次")
        
        # 统计信息
        if len(df_word_freq) >= 2:
            max_word = df_word_freq.iloc[0]['词语']
            max_freq = df_word_freq.iloc[0]['频次']
            min_word = df_word_freq.iloc[-1]['词语']
            min_freq = df_word_freq.iloc[-1]['频次']
            ratio = max_freq / min_freq if min_freq > 0 else 0
            
            print(f"\n词频差异统计:")
            print(f"  最高频词 '{max_word}': {max_freq} 次")
            print(f"  最低频词 '{min_word}': {min_freq} 次")
            print(f"  频次比: {ratio:.1f}:1")
            
    except Exception as e:
        print(f"保存词频统计失败: {e}")
    
    # 保存聊天记录汇总
    try:
        if chat_infos:
            df_summary = pd.DataFrame(chat_infos)
            df_summary = df_summary[['filename', 'chat_name', 'message_count', 'type', 'last_time']]
            df_summary.to_csv(OUTPUT_SUMMARY, index=False, encoding='utf-8-sig')
            print(f"聊天汇总已保存: {OUTPUT_SUMMARY}")
            
            print("\n聊天记录汇总:")
            for i, info in enumerate(chat_infos, 1):
                print(f"  {i:2d}. {info['chat_name']:20s} ({info['filename']}): {info['message_count']} 条消息")
    
    except Exception as e:
        print(f"保存聊天汇总失败: {e}")
    
    return True

def display_combined_wordcloud(wordcloud, word_counts, chat_infos, stats):
    """
    显示综合词云
    """
    if not wordcloud:
        return
    
    # 创建大图
    fig = plt.figure(figsize=(18, 10))
    
    # 1. 词云图
    ax1 = plt.subplot2grid((2, 3), (0, 0), colspan=2, rowspan=2)
    ax1.imshow(wordcloud, interpolation="bilinear")
    ax1.axis("off")
    
    # 添加标题
    if chat_infos:
        chat_names = [info['chat_name'] for info in chat_infos]
        title = f"综合词云图 - 共{len(chat_infos)}个聊天记录"
        if len(chat_names) <= 5:
            title += f"\n({', '.join(chat_names)})"
        else:
            title += f"\n({', '.join(chat_names[:3])} 等)"
    else:
        title = "微信聊天记录综合词云图"
    
    ax1.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # 2. 高频词柱状图
    ax2 = plt.subplot2grid((2, 3), (0, 2))
    if word_counts and len(word_counts) > 0:
        top_words = dict(word_counts.most_common(15))
        words = list(top_words.keys())
        freqs = list(top_words.values())
        
        y_pos = range(len(words))
        bars = ax2.barh(y_pos, freqs, align='center', alpha=0.7, color='steelblue')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(words, fontproperties='SimHei')
        ax2.invert_yaxis()
        ax2.set_xlabel('出现次数')
        ax2.set_title('高频词Top 15')
        
        # 添加数值
        for i, (bar, freq) in enumerate(zip(bars, freqs)):
            width = bar.get_width()
            ax2.text(width + max(freqs)*0.01, bar.get_y() + bar.get_height()/2,
                    f'{freq}', va='center', fontsize=9)
    
    # 3. 聊天记录统计
    ax3 = plt.subplot2grid((2, 3), (1, 2))
    
    if chat_infos and len(chat_infos) > 0:
        # 只显示前10个聊天的消息数
        display_infos = chat_infos[:10]
        chat_labels = [info['chat_name'] for info in display_infos]
        message_counts = [info['message_count'] for info in display_infos]
        
        y_pos = range(len(chat_labels))
        bars = ax3.barh(y_pos, message_counts, align='center', alpha=0.7, color='lightcoral')
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels(chat_labels, fontproperties='SimHei', fontsize=9)
        ax3.invert_yaxis()
        ax3.set_xlabel('消息数量')
        ax3.set_title('聊天记录统计')
        
        # 添加总计
        total_messages = sum(message_counts)
        if len(chat_infos) > 10:
            ax3.text(0.98, 0.02, f"总计: {total_messages} 条\n(显示前10个)",
                    transform=ax3.transAxes, ha='right', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:
            ax3.text(0.98, 0.02, f"总计: {total_messages} 条",
                    transform=ax3.transAxes, ha='right', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle(f"多聊天记录词云分析 - 共 {len(word_counts)} 个不同词语", fontsize=18, y=0.98)
    plt.tight_layout()
    plt.show()

# ============================================
# 第六部分：主程序
# ============================================

import math  # 用于enhance_frequency_distribution函数中的math.log

def main():
    """
    主函数
    """
    print("=" * 70)
    print("多微信聊天记录词云图生成器")
    print("=" * 70)
    print(f"搜索文件夹: {JSON_FOLDER}")
    print(f"文件模式: {FILE_PATTERN}")
    print(f"分析对象: {ANALYZE_WHO}")
    print(f"排除系统消息: {EXCLUDE_SYSTEM_MESSAGES}")
    print("=" * 70)
    
    # 1. 加载所有聊天记录
    all_messages, chat_infos = load_all_chat_files()
    
    if not all_messages or not chat_infos:
        print("错误：没有可用的聊天记录数据")
        input("按回车键退出...")
        return
    
    print(f"\n✓ 成功加载 {len(chat_infos)} 个聊天记录，共 {len(all_messages)} 条消息")
    
    # 2. 过滤消息
    print(f"\n正在过滤消息 (分析对象: {ANALYZE_WHO})...")
    filtered_messages, stats = filter_messages(
        all_messages, 
        who=ANALYZE_WHO,
        exclude_system=EXCLUDE_SYSTEM_MESSAGES
    )
    
    if not filtered_messages:
        print("过滤后没有消息可分析")
        input("按回车键退出...")
        return
    
    # 3. 提取文本
    print("\n正在提取和清洗文本...")
    
    # 获取所有聊天对象的名字
    other_names = set()
    for msg in filtered_messages:
        if msg.get('isSend') == 0:  # 对方发送
            sender = msg.get('sender', '')
            if sender:
                other_names.add(sender)
    
    texts = extract_texts_from_messages(
        filtered_messages, 
        include_names=INCLUDE_NAMES_IN_WORDS,
        names=other_names
    )
    
    if not texts:
        print("错误：没有提取到有效文本")
        input("按回车键退出...")
        return
    
    # 4. 生成综合词云
    wordcloud, word_counts = generate_combined_wordcloud(texts, chat_infos)
    
    if not wordcloud:
        print("生成词云失败")
        input("按回车键退出...")
        return
    
    # 5. 保存和显示结果
    print("\n正在保存结果...")
    save_combined_results(wordcloud, word_counts, chat_infos, stats)
    
    print("\n正在显示词云图...")
    display_combined_wordcloud(wordcloud, word_counts, chat_infos, stats)
    
    print("\n" + "=" * 70)
    print("处理完成！")
    print("=" * 70)
    print(f"📁 分析文件: {len(chat_infos)} 个聊天记录")
    print(f"💬 总消息数: {len(all_messages)} 条")
    print(f"📊 有效消息: {len(filtered_messages)} 条")
    print(f"🔤 不同词语: {len(word_counts)} 个")
    print(f"🖼️  词云图片: {OUTPUT_IMAGE}")
    print(f"📈 词频统计: {OUTPUT_STATS}")
    if chat_infos:
        print(f"📋 聊天汇总: {OUTPUT_SUMMARY}")
    print("=" * 70)
    
    input("按回车键退出程序...")

# 运行主程序
if __name__ == "__main__":
    main()