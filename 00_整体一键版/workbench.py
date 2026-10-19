"""Local one-click launcher. Only the configured planning gateway may use the network."""
from pathlib import Path
import os
import threading
import tkinter as tk
from tkinter import filedialog,messagebox
from engine.common import load
from engine.delivery import export_user_project
from engine.provider import read_source,plan_source


def main():
    root=tk.Tk();root.title('AI漫剧 V5.1.5 · H3 双语一键生成');root.geometry('760x340')
    vals={k:tk.StringVar() for k in ['input','assets','output','config']}
    labels={'input':'小说 / 剧本 / 已确认 JSON','assets':'人物、场景、道具图片目录','output':'用户资料包输出目录','config':'规划模型配置（自然语言输入需要）'}
    for n,(k,label) in enumerate(labels.items()):
        tk.Label(root,text=label).grid(row=n,column=0,sticky='w',padx=10,pady=10)
        tk.Entry(root,textvariable=vals[k],width=48).grid(row=n,column=1)
        def choose(key=k):
            v=filedialog.askdirectory() if key in ['assets','output'] else filedialog.askopenfilename()
            if v:vals[key].set(v)
        tk.Button(root,text='选择',command=choose).grid(row=n,column=2,padx=8)
    status=tk.StringVar(value='确认输入与素材后，点击一次生成双语 MD。')
    tk.Label(root,textvariable=status,wraplength=730).grid(row=5,column=0,columnspan=3,pady=15)
    def start():
        args={k:v.get() for k,v in vals.items()}
        if any(not args[k] for k in ['input','assets','output']):messagebox.showerror('缺少输入','请选择输入、素材目录和输出目录。');return
        button.config(state='disabled');status.set('正在规划、校验、生成中文版与英文版……')
        def work():
            try:
                path=Path(args['input']);config=load(args['config']) if args['config'] else None
                r=load(path) if path.suffix.lower()=='.json' and load(path).get('schema_version') in ['5.0','5.1'] else plan_source(read_source(path),args['assets'],config=config)
                out=export_user_project(r,args['assets'],args['output'])
                root.after(0,lambda:status.set('READY：'+str(out)+'；已输出使用说明、素材提示词、分镜和中英文各一份H3提示词。'))
            except Exception as exc:
                msg=str(exc);root.after(0,lambda:status.set('生成未通过：'+msg));root.after(0,lambda:messagebox.showerror('校验未通过',msg))
            finally:root.after(0,lambda:button.config(state='normal'))
        threading.Thread(target=work,daemon=True).start()
    button=tk.Button(root,text='一键生成 H3 · 中文 + English',command=start,width=38,height=2)
    button.grid(row=4,column=0,columnspan=3,pady=15)
    root.mainloop()


if __name__=='__main__':main()
