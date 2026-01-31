# -*- coding: utf-8 -*-
"""
考研词汇替换工具 - 最终修正版
修复了所有已知问题，可以安全打包
"""

import json
import random
import pyperclip
import jieba
import os
import sys
import time
import traceback

def show_message(title, message, is_error=False):
    """显示Windows消息框"""
    try:
        import ctypes
        if is_error:
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x10)
        else:
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x40)
    except:
        pass  # 如果弹窗失败，静默处理

class VocabularyReplacer:
    def __init__(self, vocab_file="词汇.json"):
        self.vocab_dict = {}
        self.load_vocabulary(vocab_file)
    
    def load_vocabulary(self, vocab_file):
        """加载词汇库JSON文件"""
        try:
            # 获取正确的文件路径
            if getattr(sys, 'frozen', False):
                # 打包后运行
                base_dir = sys._MEIPASS
            else:
                # 正常Python运行
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            vocab_path = os.path.join(base_dir, vocab_file)
            
            if not os.path.exists(vocab_path):
                show_message("错误", f"找不到词汇库文件：{vocab_file}", True)
                return False
            
            with open(vocab_path, 'r', encoding='utf-8') as f:
                vocab_data = json.load(f)
            
            # 构建词汇映射字典
            for word_info in vocab_data:
                # 添加单词本身
                chinese_translation = word_info['translations'][0]['translation']
                english_word = word_info['word']
                self.vocab_dict[chinese_translation] = english_word
                
                # 添加短语
                for phrase in word_info.get('phrases', []):
                    chinese_phrase = phrase['translation']
                    english_phrase = phrase['phrase']
                    self.vocab_dict[chinese_phrase] = english_phrase
            
            return True
            
        except Exception as e:
            show_message("错误", f"加载词汇库失败：{str(e)}", True)
            return False
    
    def replace_vocabulary(self, text, replace_ratio=0.2):
        """替换文本中的词汇 - 修复版"""
        if not self.vocab_dict:
            return text, {"total_words": 0, "replaceable": 0, "replaced": 0}
        
        # 使用jieba进行中文分词
        words = list(jieba.cut(text, cut_all=False))
        total_words = len(words)
        
        # 找出可以替换的词汇
        replaceable_indices = []
        for i, word in enumerate(words):
            if word in self.vocab_dict:
                replaceable_indices.append(i)
        
        replaceable_count = len(replaceable_indices)
        
        # 计算目标替换数量（基于总词汇数的20%）
        target_replace_count = max(1, int(total_words * replace_ratio))
        
        # 实际可替换的数量
        actual_replace_count = min(target_replace_count, replaceable_count)
        
        # 随机选择要替换的词汇
        selected_indices = []
        if replaceable_indices and actual_replace_count > 0:
            if actual_replace_count >= len(replaceable_indices):
                # 替换所有可替换的词汇
                selected_indices = replaceable_indices
            else:
                # 随机选择部分词汇替换
                selected_indices = random.sample(replaceable_indices, actual_replace_count)
        
        # 执行替换
        result_words = words.copy()
        for idx in selected_indices:
            chinese_word = words[idx]
            english_word = self.vocab_dict[chinese_word]
            result_words[idx] = f"{english_word}({chinese_word})"
        
        result_text = ''.join(result_words)
        
        stats = {
            'total_words': total_words,
            'replaceable_count': replaceable_count,
            'target_replace_count': target_replace_count,
            'actual_replace_count': len(selected_indices)
        }
        
        return result_text, stats

def main():
    """主函数 - 完全没有input()函数"""
    try:
        # 初始化替换器
        replacer = VocabularyReplacer()
        if not replacer.vocab_dict:
            return
        
        # 读取剪贴板
        try:
            original_text = pyperclip.paste()
        except:
            show_message("错误", "无法读取剪贴板\n请确保已复制文本", True)
            return
        
        if not original_text or not original_text.strip():
            show_message("提示", "剪贴板为空\n请先复制中文文本", False)
            return
        
        # 执行替换
        replaced_text, stats = replacer.replace_vocabulary(original_text, replace_ratio=0.2)
        
        # 复制回剪贴板
        try:
            pyperclip.copy(replaced_text)
        except:
            show_message("错误", "无法写入剪贴板", True)
            return
        
        # 显示结果
        result_msg = f"""
✅ 替换完成！

📊 统计信息：
总词汇数：{stats['total_words']} 个
可替换词汇：{stats['replaceable_count']} 个
目标替换（20%）：{stats['target_replace_count']} 个
实际替换：{stats['actual_replace_count']} 个

📋 已复制到剪贴板
直接粘贴使用即可
"""
        show_message("词汇替换工具", result_msg, False)
        
    except Exception as e:
        show_message("错误", f"程序出错：\n{str(e)}", True)

# 程序入口
if __name__ == "__main__":
    main()  # 没有input()，执行完自动退出