import pyperclip    
import re           
import random      
import time        
import hashlib     
from collections import OrderedDict 
import tkinter as tk   
from tkinter import messagebox  

def extract_english_words(text: str) -> str:
    words = re.findall(r"\b[a-zA-Z]+(?:['’][a-zA-Z]+)*\b", text)
    seen = set()                   
    unique_words = []               
    for word in words:
        lower_word = word.lower()  
        if lower_word not in seen:
            seen.add(lower_word)
            unique_words.append(word)   
    random.shuffle(unique_words)  
    
    if len(unique_words) > 1000:
        return "⚠️ 文本超限（1000词）\n" + "\n".join(unique_words[:1000])
    return "\n".join(unique_words)  

def process_clipboard():
    """单次剪贴板处理函数"""
    try:
        current_content = pyperclip.paste().strip()   
        if not current_content:
            return "⛔ 剪贴板为空或非文本内容"   
            
        processed_text = extract_english_words(current_content)
        pyperclip.copy(processed_text)                         
        word_count = len(processed_text.splitlines())          

        return f"✅ 已提取 {word_count} 个单词\n直接粘贴即可使用" + \
               (" (已截断前1000词)" if "⚠️" in processed_text else "")
    
    except pyperclip.PyperclipException as e:
        return f"🔧 剪贴板错误: {e}"
    except Exception as e:                   
        return f"⚠️ 未知错误: {e}"

def main():
    """主函数带GUI弹窗控制"""
    root = tk.Tk()
    root.withdraw()  
     
    result = process_clipboard()
    messagebox.showinfo("剪贴板处理结果", result)
   
    from pystray import Icon, Menu, MenuItem
    from PIL import Image
    import threading
    
    def on_quit():  
        icon.stop()
        root.destroy()
    
    menu = Menu(
        MenuItem('处理剪贴板', lambda: messagebox.showinfo(
            "处理结果", process_clipboard())),
        MenuItem('退出', on_quit)
    )
    
    image = Image.new('RGB', (64, 64), 'white')
    icon = Icon("clipboard_processor", image, "英文提取工具", menu)
    
    threading.Thread(target=icon.run, daemon=True).start()

    root.bind('<Control-c>', lambda e: on_quit())
    
    root.mainloop()

if __name__ == "__main__":
    main() 