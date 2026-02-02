"""
微信聊天记录词云图生成器
适用于你的JSON格式
作者：AI助手
"""

import json
import re
import jieba
from collections import Counter
from wordcloud import WordCloud, ImageColorGenerator
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
import numpy as np
import os

# ============================================
# 第一部分：设置参数（你可以修改这里）
# ============================================

# 1. 你的JSON文件路径（如果文件不在同一目录，需要修改）
JSON_FILE = "chat.json"  # 你的JSON文件名

# 2. 分析谁的消息？（可以修改）
# 可选值：
#   "all" - 所有人的消息
#   "me" - 只分析我发的消息
#   "other" - 只分析对方发的消息
ANALYZE_WHO = "all"

# 3. 排除系统消息吗？（建议设为True）
EXCLUDE_SYSTEM_MESSAGES = True

# 4. 词云设置
MAX_WORDS = 200           # 最多显示多少个词
BACKGROUND_COLOR = "white"  # 背景颜色，可以是："white", "black", "#f0f0f0"
WIDTH = 800              # 图片宽度
HEIGHT = 600             # 图片高度

# 5. 停用词（不想显示的词，可以自己添加）
STOP_WORDS = [
    "的", "了", "在", "是", "我", "有", "和", "就", 
    "不", "人", "都", "一", "一个", "上", "也", "很", 
    "到", "说", "要", "去", "你", "会", "着", "没有", 
    "看", "好", "自己", "这", "中", "就是", "对", "在", 
    "可以", "吧", "啦", "吗", "呢", "啊", "呀", "哦",
    "哈哈", "哈哈哈", "哈哈哈哈", "嘻嘻", "呵呵", "嗯",
    "这个", "那个", "什么", "怎么", "为什么", "因为",
    "所以", "但是", "然后", "而且", "其实", "还是", "是不是",
    "不是", "我们", "一下", "感觉", "应该", "你们" , "的话"
]

# 6. 是否要排除特定内容？（正则表达式）
REMOVE_PATTERNS = [
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # 网址
    r'\[.*?\]',  # 方括号内容，如[表情]
    r'【.*?】',  # 方头括号内容
    r'#.*?#',    # 两个#号之间的内容
    r'<.*?>',    # HTML标签
]

# 7. 输出文件名
OUTPUT_IMAGE = "wechat_wordcloud.png"  # 词云图片
OUTPUT_STATS = "word_frequency.csv"    # 词频统计文件

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
        
        # 检查数据结构
        if 'messages' not in data:
            print("错误：JSON文件中没有找到'messages'字段")
            print(f"JSON文件的结构是: {list(data.keys())}")
            return []
        
        messages = data['messages']
        print(f"成功读取 {len(messages)} 条消息")
        
        # 显示会话信息
        if 'session' in data:
            session_info = data['session']
            print(f"会话名称: {session_info.get('nickname', '未知')}")
            print(f"消息总数: {session_info.get('messageCount', len(messages))}")
            print(f"最后时间: {session_info.get('lastTimestamp', '未知')}")
        
        return messages
        
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        print("请确保：")
        print("1. 文件存在且文件名正确")
        print("2. 文件放在同一目录下")
        return []
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件格式不正确 - {e}")
        return []
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return []

def filter_messages(messages, who="all", exclude_system=True):
    """
    过滤消息
    who: "all"=全部, "me"=自己, "other"=对方
    exclude_system: 是否排除系统消息
    """
    filtered = []
    
    for msg in messages:
        # 获取消息类型
        msg_type = msg.get('type', '')
        content = msg.get('content', '')
        
        # 跳过空内容
        if not content or not isinstance(content, str):
            continue
            
        # 排除系统消息
        if exclude_system and msg_type == "系统消息":
            continue
            
        # 根据发送者过滤
        is_send = msg.get('isSend')
        sender = msg.get('senderDisplayName', '')
        
        if who == "me":
            if is_send != 1:  # 不是自己发送的
                continue
        elif who == "other":
            if is_send != 0:  # 不是对方发送的
                continue
        elif who == "all":
            pass  # 不过滤
        else:
            print(f"警告：未知的过滤条件: {who}")
            continue
            
        # 添加消息
        filtered.append({
            'content': content,
            'type': msg_type,
            'sender': sender,
            'isSend': is_send,
            'time': msg.get('formattedTime', '')
        })
    
    print(f"过滤后得到 {len(filtered)} 条文本消息")
    
    # 显示发送者统计
    if filtered:
        sender_counts = {}
        for msg in filtered:
            sender = msg['sender'] or ("我" if msg['isSend'] == 1 else "对方")
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        print("发送者统计:")
        for sender, count in sender_counts.items():
            print(f"  {sender}: {count} 条")
    
    return filtered

def clean_text(text):
    """
    清洗文本，移除不需要的内容
    """
    if not isinstance(text, str):
        return ""
    
    # 移除各种模式匹配的内容
    for pattern in REMOVE_PATTERNS:
        text = re.sub(pattern, '', text)
    
    # 移除空格和换行
    text = text.replace('\n', ' ').replace('\r', ' ').strip()
    
    return text

# ============================================
# 第三部分：生成词云
# ============================================

def generate_wordcloud(texts, max_words=200, background_color="white"):
    """
    生成词云图
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
        if (len(word) > 1 and  # 长度大于1
            word not in STOP_WORDS and  # 不在停用词中
            not word.isdigit() and  # 不是纯数字
            not re.match(r'^[^\u4e00-\u9fa5]+$', word)):  # 不是纯非中文字符
            filtered_words.append(word)
    
    # 统计词频
    word_counts = Counter(filtered_words)
    
    if not word_counts:
        print("错误：分词后没有有效的词语")
        return None, None
    
    print(f"分词得到 {len(filtered_words)} 个有效词语，{len(word_counts)} 个不同词语")
    
    # 显示最常见的20个词
    print("\n最常见的20个词语:")
    for word, count in word_counts.most_common(20):
        print(f"  {word}: {count}次")
    
    # 创建词云
    print("\n正在生成词云...")
    
    # 确保有中文字体
    font_path = None
    possible_fonts = [
        "C:/Windows/Fonts/simhei.ttf",  # Windows黑体
        "C:/Windows/Fonts/msyh.ttc",    # Windows微软雅黑
        "C:/Windows/Fonts/simsun.ttc",  # Windows宋体
        "simhei.ttf",  # 当前目录
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
        max_font_size=100,
        min_font_size=10,
        random_state=42,
        collocations=False
    )
    
    # 生成词云
    wc.generate_from_frequencies(word_counts)
    
    print(f"词云已生成，包含 {len(wc.words_)} 个词语")
    
    return wc, word_counts

def save_results(wordcloud, word_counts):
    """
    保存结果
    """
    if not wordcloud:
        return False
    
    # 1. 保存词云图片
    try:
        wordcloud.to_file(OUTPUT_IMAGE)
        print(f"词云图片已保存: {OUTPUT_IMAGE}")
    except Exception as e:
        print(f"保存图片失败: {e}")
        return False
    
    # 2. 保存词频统计
    try:
        df = pd.DataFrame(
            word_counts.most_common(),
            columns=['词语', '频次']
        )
        df.to_csv(OUTPUT_STATS, index=False, encoding='utf-8-sig')
        print(f"词频统计已保存: {OUTPUT_STATS}")
        
        # 显示前10个词
        print("\n词频前10名:")
        for i, row in df.head(10).iterrows():
            print(f"  {i+1}. {row['词语']}: {row['频次']}次")
    except Exception as e:
        print(f"保存词频统计失败: {e}")
    
    return True

def display_wordcloud(wordcloud):
    """
    显示词云
    """
    if not wordcloud:
        return
    
    plt.figure(figsize=(12, 8))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title("微信聊天记录词云图", fontsize=16)
    
    # 添加统计信息
    stats_text = f"总词语数: {len(wordcloud.words_)}"
    plt.figtext(0.5, 0.01, stats_text, 
                ha="center", fontsize=10, 
                bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})
    
    plt.tight_layout()
    plt.show()

# ============================================
# 第四部分：主程序
# ============================================

def main():
    """
    主函数
    """
    print("=" * 50)
    print("微信聊天记录词云图生成器")
    print("=" * 50)
    
    # 检查文件是否存在
    if not os.path.exists(JSON_FILE):
        print(f"错误：找不到文件 '{JSON_FILE}'")
        print("请将JSON文件放在同一目录下，或修改JSON_FILE变量")
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
        if cleaned:  # 只添加非空文本
            texts.append(cleaned)
    
    print(f"清洗后得到 {len(texts)} 条有效文本")
    
    # 4. 生成词云
    wordcloud, word_counts = generate_wordcloud(
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
    save_results(wordcloud, word_counts)
    
    print("\n正在显示词云图...")
    print("提示：如果图片窗口没有弹出，请检查:")
    print("1. 图片已保存为 wechat_wordcloud.png")
    print("2. 可以在文件夹中直接打开查看")
    display_wordcloud(wordcloud)
    
    print("\n" + "=" * 50)
    print("处理完成！")
    print(f"1. 词云图片: {OUTPUT_IMAGE}")
    print(f"2. 词频统计: {OUTPUT_STATS}")
    print("=" * 50)
    
    input("按回车键退出程序...")

# 运行主程序
if __name__ == "__main__":
    main()