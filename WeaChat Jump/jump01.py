import pyautogui
import time
import tkinter as tk

def find_pos():
    x,y=pyautogui.position()
    print(f"the position is ({x},{y})")

def move_mouse():
    x_pos=int(entry_x.get())
    y_pos=int(entry_y.get())
    pyautogui.moveTo(x_pos,y_pos)

def click_and_hold(duration):
    #pyautogui.moveTo(1335,704)
    move_mouse()
    pyautogui.mouseDown()
    time.sleep(duration)
    pyautogui.mouseUp()

def digi():
    newlength=float(entry.get())
    new(newlength)
    
def new(a):
    thetime=-0.00800896*(a-14.2091)**2+1.48245
    click_and_hold(thetime)
    #print(thetime)

root=tk.Tk()
root.geometry("400x250")
root.title("JUMP,JUMP,JUMP")


label_find=tk.Label(root,text="seek your mouse")
label_find.pack()

button_find=tk.Button(root,text="start to seek",command=find_pos)
button_find.pack()


label_pos=tk.Label(root,text="input the place (x,y) to click:")
label_pos.pack()
entry_x=tk.Entry(root)
entry_x.pack()
entry_y=tk.Entry(root)
entry_y.pack()

#button_pos=tk.Button(root,text="move the mouse",command=move_mouse)
#button_pos.pack()



label=tk.Label(root,text="input the length:")
label.pack()
entry=tk.Entry(root)
entry.pack()

button=tk.Button(root,text="click",command=digi)
button.pack()


root.mainloop()


