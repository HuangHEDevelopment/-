#!/usr/bin/env python
#-*- coding:utf-8 -*-
import tkinter as tk
import threading
import pyaudio
import wave
import time
import urllib
import hashlib
import base64
import urllib.request
import urllib.parse
import json
import gc
import os
import sys
import codecs
#from xpinyin import Pinyin
from mypinyin import Pinyin             #为了打包install，修改源文件
from configobj import ConfigObj

#变量声明
global audio_record,on_hit,in_path,recit_text,lessondic,lessonfile,lessontitle,lesson_text
global list_count    #听写分句字数
global Gurl,Gapi_key ,Gx_appid   #讯飞网址,api_key，appid
global Gchunk ,Gchannels ,Grate  #录音块，通道，频率

on_hit=False

#课文单击事件处理
def click_List(event):
    if recitelist.curselection() != ():
        print(recitelist.grab_current())
        lessontitle = recitelist.get(recitelist.curselection()[0])
    else:
        return
    lesson_text.delete('1.0', 'end')
    #lesson_text.insert(1.0,lessondic[lessontitle])

def disp_List():
    if recitelist.curselection() != ():
        print(recitelist.grab_current())
        lessontitle = recitelist.get(recitelist.curselection()[0])
    else:
        return
    lesson_text.delete('1.0', 'end')
    lesson_text.insert(1.0,lessondic[lessontitle])

#汉字转拼音处理
def joinpinyin(origin_str):
    pinlist = pypinyin.pinyin(origin_str, style=pypinyin.NORMAL)
    str_n = '-'
    newlist = []
    for listi in pinlist:
        newlist.append(listi[0])
    str_n = '-'.join(newlist)
    return str_n

def init_lessonlist():
    global lessondic,lessonfile


    #无签名处理
    mf = open(lessonfile, 'rb')
    if mf.read(3)==codecs.BOM_UTF8:
        #print("包含bom")
        f_body=mf.read()
        mf.close()
        mf=open(lessonfile, 'wb')
        mf.write(f_body)
        mf.close()
    else:
        mf.close()

    mf=open(lessonfile,'r',encoding='utf-8')
    filecontent=mf.read().replace(' ','')
    filecontent=filecontent.replace(' ','')
    filecontent=filecontent.replace('\r','')
    filecontent = filecontent.replace('\n', '')

    mf.close()
    #过滤中文字符，所有双引号替换为单引号
    strip_chars = '"“”'
    filecontent = filecontent.translate(str.maketrans(dict.fromkeys(strip_chars, "'")))
    #所有的中文逗号替换为英文逗号
    filecontent=filecontent.replace("，",",")
    # 所有的中文冒号替换为英文冒号
    filecontent = filecontent.replace("：", ":")
    lessondic=eval(filecontent)
    #lessondic=json.loads(filecontent)
    recitelist.delete('0','end')
    for lessonname in lessondic.keys():
        recitelist.insert('end', lessonname)
    recitelist.selection_set(0,False)

class RecordThread(threading.Thread):
    def __init__(self, audiofile='record.wav'):
        global Gchunk, Gchannels, Grate  # 录音块，通道，频率
        threading.Thread.__init__(self)
        self.bRecord = True
        self.audiofile = audiofile
        self.chunk = Gchunk
        self.format = pyaudio.paInt16
        self.channels = Gchannels
        self.rate = Grate

    def run(self):
        audio = pyaudio.PyAudio()
        wavfile = wave.open(self.audiofile, 'wb')
        wavfile.setnchannels(self.channels)
        wavfile.setsampwidth(audio.get_sample_size(self.format))
        wavfile.setframerate(self.rate)
        wavstream = audio.open(format=self.format,
                               channels=self.channels,
                               rate=self.rate,
                               input=True,
                               frames_per_buffer=self.chunk)
        while self.bRecord:
            wavfile.writeframes(wavstream.read(self.chunk))
        wavstream.stop_stream()
        wavstream.close()
        audio.terminate()

    def stoprecord(self):
        self.bRecord = False


def init_config(AIconfigfile):
    global Gurl, Gapi_key, Gx_appid  # 讯飞网址,api_key，appid
    global Gchunk, Gchannels, Grate  # 录音块，通道，频率
    config = ConfigObj(AIconfigfile, encoding='UTF8')
    # 读配置文件
    Gurl = config["xfyun"]["url"]
    Gapi_key = config['xfyun']['api_key']
    Gx_appid = config['xfyun']['x_appid']
    Gchunk = int(config['audio']['chunk'])
    Gchannels = int(config['audio']['channels'])
    Grate = int(config['audio']['rate'])
    print(Gurl)
    print(Gapi_key)
    print(Gx_appid)
    print(Gchunk)
    print(Gchannels)
    print(Grate)

def audio2txt(filepath):
    global Gurl, Gapi_key, Gx_appid  # 讯飞网址,api_key，appid
    f = open(filepath, 'rb')  # rb表示二进制格式只读打开文件
    file_content = f.read()
    # file_content 是二进制内容，bytes类型
    # 由于Python的字符串类型是str，在内存中以Unicode表示，一个字符对应若干个字节。
    # 如果要在网络上传输，或者保存到磁盘上，就需要把str变为以字节为单位的bytes
    # 以Unicode表示的str通过encode()方法可以编码为指定的bytes
    base64_audio = base64.b64encode(file_content)  # base64.b64encode()参数是bytes类型，返回也是bytes类型
    body = urllib.parse.urlencode({'audio': base64_audio})

    url = Gurl
    api_key = Gapi_key
    x_appid = Gx_appid
    param = {"engine_type": "sms16k", "aue": "raw"}


    x_param = base64.b64encode(json.dumps(param).replace(' ', '').encode('utf-8'))  # 改('''')
    # 这是3.x的用法，因为3.x中字符都为unicode编码，而b64encode函数的参数为byte类型，
    # 所以必须先转码为utf-8的bytes
    x_param = str(x_param, 'utf-8')

    x_time = int(int(round(time.time() * 1000)) / 1000)
    x_checksum = hashlib.md5((api_key + str(x_time) + x_param).encode('utf-8')).hexdigest()  # 改
    x_header = {'X-Appid': x_appid,
                'X-CurTime': x_time,
                'X-Param': x_param,
                'X-CheckSum': x_checksum}
    req = urllib.request.Request(url=url, data=body.encode('utf-8'), headers=x_header, method='POST')
    result = urllib.request.urlopen(req)
    result = result.read().decode('utf-8')
    #print(result)
    return result

def recite_click():
    global on_hit,audio_record,in_path,recit_text,lessontitle
    global list_count
    list_count=2
    if on_hit == False:
        # 检查当前选中行，如果没有选中，则输出没有选中的课文
        #print(recitelist.curselection())
        recit_text.delete('1.0','end')
        lesson_text.delete('1.0', 'end')
        if recitelist.curselection()!=():
            lessontitle=recitelist.get(recitelist.curselection())
        else:
            recit_text.insert(1.0, '没有选中的课文')
            return
        on_hit=True

        recit_text.insert(1.0, '开始听写:' + lessontitle)
        varbutton.set("停止")
        audio_record = RecordThread(in_path)
        audio_record.start()

    else:
        on_hit=False
        recit_text.delete('1.0','end')
        recit_text.insert(1.0,"听写完毕，正在检查，请稍后......")
        varbutton.set("背诵")

        #听写内容，利用讯飞，转换为文字
        audio_record.stoprecord()
        txtline = json.loads(audio2txt(in_path))
        datatxt = txtline['data']
        #print(datatxt)

        #开始比较听写结果
        recit_text.delete('1.0', 'end')
        recit_text.tag_config('ok', foreground='green')
        recit_text.tag_config('wrong', foreground='red')
        recit_text.tag_config('miss', background='yellow')
        lesson_text.delete('1.0', 'end')
        lesson_text.tag_config('ok', foreground='green')
        lesson_text.tag_config('wrong', foreground='red')
        lesson_text.tag_config('miss', background='yellow')
        # 使用TAG 'a'来指定文本属性
        #展示说明
        '''
        recit_text.insert(0.0, '正确的句子', 'ok')
        recit_text.insert(tk.INSERT, "   ")
        recit_text.insert(tk.INSERT, '错误的句子', 'wrong')
        recit_text.insert(tk.INSERT, "   ")
        recit_text.insert(tk.INSERT, '错过的句子', 'miss')
        '''
        pin = Pinyin()
        #处理课文内容
        lessoncontent_origin=lessondic[lessontitle]
        strip_chars = '？"。.，,《》[]〖〗“”'
        lessoncontent_unify = lessoncontent_origin.translate(str.maketrans(dict.fromkeys(strip_chars, '#')))
        lessoncontent_unify_replace= lessoncontent_unify.replace("#","")
        #计算取消#后新字符串的位置，并且记录下来
        lesson_loc=[]
        for i in range(len(lessoncontent_unify)):
            if lessoncontent_unify[i]!='#':
                lesson_loc.append(i)

        lessoncontent_unify_replace_pinyin=pin.get_pinyin(lessoncontent_unify_replace)
        lessoncontent_unify_replace_pinyin = lessoncontent_unify_replace_pinyin.replace("ing", "in")
        lessoncontent_unify_replace_pinyin = lessoncontent_unify_replace_pinyin.replace("eng", "en")
        #recit_text.insert(tk.END, lessoncontent_origin, 'miss')
        #print(lessoncontent_unify_replace)
        #print(lessoncontent_unify_replace_pinyin)
        #开始处理听写内容

        audio_record.stoprecord()
        txtline = json.loads(audio2txt(in_path))
        datatxt = txtline['data']

        #datatxt='各不同。不识庐词山钟'y
        #print(datatxt)

        strip_chars = '？"。.，,《》[]〖〗“”'


        #把听写句子拆分成为list进行比较，一种用数量list_count，一种用中文标点分,另外一种综合二者来做
        #使用数量
        #datatxt = datatxt.translate(str.maketrans(dict.fromkeys(strip_chars, '')))
        #if len(datatxt)%2==0:
        #    temp_count=len(datatxt)//2
        #else:
        #    temp_count=len(datatxt)//2+1
        #txtlist=[]
        #for i in range(temp_count-1):
        #    txtlist.append(datatxt[i*2:(i+1)*2])
        #txtlist.append(datatxt[(temp_count-1)*2:])
        # 使用标点分词
        #datatxt = datatxt.translate(str.maketrans(dict.fromkeys(strip_chars, '#')))
        #txtlist = datatxt.split('#')      #使用标点分list
        # 使用标点符号来分，再使用数量细分
        datatxt = datatxt.translate(str.maketrans(dict.fromkeys(strip_chars, '#')))
        temp_txtlist = datatxt.split('#')  # 使用标点分list
        txtlist=[]
        for temp_str in temp_txtlist:
            if len(temp_str)%2==0:
                temp_count=len(temp_str)//2
            else:
                temp_count=len(temp_str)//2+1

            for i in range(temp_count-1):
                txtlist.append(temp_str[i*2:(i+1)*2])
            txtlist.append(temp_str[(temp_count-1)*2:])
        #print(txtlist)
        #设定开始匹配位置
        start_find=0
        last_loc=0
        py_start_loc=0
        for i in range(len(txtlist)):
            if len(txtlist[i].strip()) > 0:     #只处理非空的字符串
                #转换为拼音，过滤后鼻音
                txtlist_pinyin = pin.get_pinyin(txtlist[i])
                txtlist_pinyin = txtlist_pinyin.replace("ing", "in")
                txtlist_pinyin = txtlist_pinyin.replace("eng", "en")
                #在原文中查找对应的拼音
                #py_first_loc=lessoncontent_unify_replace_pinyin.find(txtlist_pinyin,start_find)
                py_first_loc = lessoncontent_unify_replace_pinyin.find(txtlist_pinyin, py_start_loc)
                #print(py_start_loc)
                #print(txtlist_pinyin)
                #print(lessoncontent_unify_replace_pinyin)
                #print(lessoncontent_unify_replace_pinyin[py_start_loc:1000])
                #转化为字符位置
                if py_first_loc>=0:        #原文中找到了
                    first_loc = lessoncontent_unify_replace_pinyin[:py_first_loc].count("-")
                    last_loc = first_loc + txtlist_pinyin.count('-') + 1
                    if first_loc!=start_find+1:   # 有句子漏了，补充黄色原文：start_find:first_loc
                        #补充原句
                        origin_start=lesson_loc[start_find]     #找到原句中的开始位置
                        origin_end=lesson_loc[first_loc]        #找到原句中的结束位置
                        lesson_text.insert(tk.INSERT, lessoncontent_origin[origin_start:origin_end], 'miss')
                        start_find=first_loc

                    #听写正确的部分，补充绿色原文
                    origin_start = lesson_loc[start_find]  # 找到原句中的开始位置
                    if last_loc >= len(lesson_loc):    #如果最后一个字符超出长度，则让它等于长度
                        recit_text.insert(tk.INSERT, lessoncontent_origin[origin_start:], 'ok')
                        lesson_text.insert(tk.INSERT, lessoncontent_origin[origin_start:], 'ok')
                        #last_loc=last_loc-1
                        start_find = last_loc
                    else:
                        origin_end = lesson_loc[last_loc]  # 找到原句中的结束位置
                        recit_text.insert(tk.INSERT, lessoncontent_origin[origin_start:origin_end], 'ok')
                        lesson_text.insert(tk.INSERT, lessoncontent_origin[origin_start:origin_end], 'ok')
                        start_find = last_loc
                    py_start_loc=py_first_loc+len(txtlist_pinyin)
                else:                  #原文中没有找到，红色输出
                    #print("下面的句子没有找到")
                    #print(txtlist_pinyin)
                    start_find = last_loc
                    recit_text.insert(tk.INSERT, txtlist[i], 'wrong')
        #听写处理完了，但是原文还有剩下没有匹配的
        #print("最后的last_loc")
        #print(last_loc)
        #print(len(lesson_loc))
        if last_loc<=len(lesson_loc)-1:   #最后一个字符不是原文的最后一个字，则输出原文
            #print(lessoncontent_origin)
            #print(lessoncontent_origin[lesson_loc[last_loc]:])
            lesson_text.insert(tk.INSERT, lessoncontent_origin[lesson_loc[last_loc]:], 'miss')

        #处理线程

        del audio_record
        gc.collect()

def edit_click():
    global lessonfile
    os.system("notepad "+lessonfile)
if __name__=='__main__':
    global in_path,  recit_text,lessonfile
    in_path = os.getcwd()+"\\TEST.WAV"
    configfile=os.getcwd()+"\\AIconfig.ini"
    lessonfile= os.getcwd()+"\\lessontxt.txt"

    #测试当前目录
    print("os.path.realpath(__file__)",os.path.realpath(__file__))
    print("os.path.split(os.path.realpath(__file__))[0]",os.path.split(os.path.realpath(__file__))[0])
    print("os.getcwd()",os.getcwd())
    print("sys.path[0]",sys.path[0])
    #datatxt='昨晚日当午，汗滴禾下土。谁知盘中餐，粒粒皆辛苦。'

    window=tk.Tk()
    window.title("轻松背课文")
    window.geometry('695x400')
    #各个标签
    tk.Label(window,text="课文列表", fg='black', font=('Arial', 10), width=10, height=1).place(x=10, y=5 , anchor='nw')
    tk.Label(window, text='背诵内容', fg='black', font=('Arial', 10), width=10, height=1).place(x=410, y=5, anchor='nw')
    #创建一个listbox，用于展示课文列表
    varlist=tk.StringVar()
    varlist=((1,2,3,4))
    recitelist=tk.Listbox(window,listvariable=varlist,width=30,height=17)
    recitelist.place(x=20,y=30,anchor='nw')
    #背诵内容，文本框
    recit_text=tk.Text(window,width=38,height=7,font=('Arial', 14))
    recit_text.place(x=250, y=30)
    # 说明： bg为背景，fg为字体颜色，font为字体，width为长，height为高，这里的长和高是字符的长和高，比如height=2,就
    #课文内容，文本框
    lesson_text=tk.Text(window,width=38,height=6,font=('Arial', 14))
    lesson_text.place(x=250, y=200)
    # 说明： bg为背景，fg为字体颜色，font为字体，width为长，height为高，这里的长和高是字符的长和高，比如height=2,就
    # 初始化按钮
    b_fresh = tk.Button(window, text='刷新', font=('Arial', 10), width=5, height=1, command= init_lessonlist)
    b_fresh.place(x=50, y=350,anchor='nw')
    #编辑按钮
    b_edit = tk.Button(window, text='编辑', font=('Arial', 10), width=5, height=1, command=edit_click)
    b_edit.place(x=150,y=350,anchor='nw')
    #开始按钮
    varbutton=tk.StringVar()
    varbutton.set("背诵")
    b_recite = tk.Button(window, textvariable=varbutton, font=('Arial', 10), width=10, height=1, command=recite_click)
    b_recite.place(x=500,y=350,anchor='nw')
    # 原文按钮
    varbutton_less = tk.StringVar()
    varbutton_less.set("原文")
    b_less = tk.Button(window, textvariable=varbutton_less, font=('Arial', 10), width=10, height=1, command=disp_List)
    b_less.place(x=300, y=350, anchor='nw')

    #初始化课文列表
    init_lessonlist()
    #绑定re单击事件
    recitelist.bind('<Button-1>', click_List)
    init_config(configfile)
    on_hit=False
    window.mainloop()