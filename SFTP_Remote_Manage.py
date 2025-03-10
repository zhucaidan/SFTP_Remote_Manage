import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import paramiko
import json
import os
import threading
import time
from pathlib import Path
from queue import Queue
import re  # 添加正则表达式模块用于解析ANSI代码

class SSHSFTPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SFTP远程文件下载工具")
        self.root.geometry("900x800")  # 修改窗口大小为800x800
        
        # 使窗口居中显示
        self.center_window(900, 800)
        
        # 创建配置文件路径
        self.config_path = "config.json"
        
        # 创建SSH客户端
        self.ssh_client = None
        self.sftp_client = None
        self.current_channel = None  # 添加当前通道变量，用于中断命令
        
        # 添加消息队列和上次更新时间
        self.message_queue = Queue()
        self.last_update_time = 0
        self.update_interval = 0.01  # 更新间隔减少到0.01秒，提高实时性
        
        # 创建界面
        self.create_widgets()
        
        # 配置文本标签颜色
        self.setup_text_tags()
        
        # 启动定时更新
        self.start_status_updater()
        
        # 程序启动后自动加载配置
        self.root.after(500, self.load_config)  # 延迟500毫秒后加载配置，确保界面已完全初始化
    
    def center_window(self, width, height):
        """使窗口在屏幕中居中显示"""
        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算窗口左上角坐标
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    def setup_text_tags(self):
        """设置文本标签颜色"""
        # 基本颜色
        self.status_text.tag_configure("black", foreground="black")
        self.status_text.tag_configure("red", foreground="red")
        self.status_text.tag_configure("green", foreground="green")
        self.status_text.tag_configure("yellow", foreground="yellow")
        self.status_text.tag_configure("blue", foreground="blue")
        self.status_text.tag_configure("magenta", foreground="magenta")
        self.status_text.tag_configure("cyan", foreground="cyan")
        self.status_text.tag_configure("white", foreground="white")
        
        # 亮色
        self.status_text.tag_configure("bright_black", foreground="gray")
        self.status_text.tag_configure("bright_red", foreground="#ff5555")
        self.status_text.tag_configure("bright_green", foreground="#55ff55")
        self.status_text.tag_configure("bright_yellow", foreground="#ffff55")
        self.status_text.tag_configure("bright_blue", foreground="#5555ff")
        self.status_text.tag_configure("bright_magenta", foreground="#ff55ff")
        self.status_text.tag_configure("bright_cyan", foreground="#55ffff")
        self.status_text.tag_configure("bright_white", foreground="white")
        
        # 背景色
        self.status_text.tag_configure("bg_black", background="black")
        self.status_text.tag_configure("bg_red", background="red")
        self.status_text.tag_configure("bg_green", background="green")
        self.status_text.tag_configure("bg_yellow", background="yellow")
        self.status_text.tag_configure("bg_blue", background="blue")
        self.status_text.tag_configure("bg_magenta", background="magenta")
        self.status_text.tag_configure("bg_cyan", background="cyan")
        self.status_text.tag_configure("bg_white", background="white")
        
        # 文本样式
        self.status_text.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
        self.status_text.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
        self.status_text.tag_configure("underline", underline=True)
    
    def create_widgets(self):
        # 顶部框架 - 输入参数
        top_frame = ttk.LabelFrame(self.root, text="连接参数")
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 服务器IP
        ttk.Label(top_frame, text="服务器IP:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.server_ip = ttk.Entry(top_frame, width=60)
        self.server_ip.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # SSH端口
        ttk.Label(top_frame, text="SSH端口:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.ssh_port = ttk.Entry(top_frame, width=10)
        self.ssh_port.insert(0, "22")  # 默认端口
        self.ssh_port.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 用户名
        ttk.Label(top_frame, text="用户名:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.username = ttk.Entry(top_frame, width=30)
        self.username.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 密码
        ttk.Label(top_frame, text="密码:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.password = ttk.Entry(top_frame, width=30, show="*")
        self.password.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # SSH私钥
        ttk.Label(top_frame, text="SSH私钥:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.key_path = ttk.Entry(top_frame, width=73)
        self.key_path.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(top_frame, text="浏览...", command=self.browse_key_file).grid(row=2, column=3, padx=5, pady=5)
        
        # 远程命令
        ttk.Label(top_frame, text="远程命令:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.remote_command = ttk.Entry(top_frame, width=70)
        self.remote_command.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # 远程文件路径
        ttk.Label(top_frame, text="远程文件路径:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.remote_path = ttk.Entry(top_frame, width=70)
        self.remote_path.grid(row=4, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # 本地接收文件路径
        ttk.Label(top_frame, text="本地接收路径:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.local_path = ttk.Entry(top_frame, width=73)
        self.local_path.grid(row=5, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(top_frame, text="浏览...", command=self.browse_local_dir).grid(row=5, column=3, padx=5, pady=5)
        
        # 为所有文本框添加右键菜单
        self.create_context_menu()
        self.bind_context_menu_to_entries()
        
        # 中部框架 - 按钮
        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 按钮
        ttk.Button(mid_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="读取配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="清空配置", command=self.clear_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="开始连接SSH", command=self.start_ssh_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="断开连接SSH", command=self.disconnect_ssh).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="执行远程命令", command=self.execute_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="下载远程文件", command=self.download_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="删除远程文件", command=self.delete_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="清屏", command=self.clear_status).pack(side=tk.LEFT, padx=5)
        
        # 底部框架 - 状态输出
        bottom_frame = ttk.LabelFrame(self.root, text="执行状态")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 状态输出文本框 - 修改背景颜色为深蓝色 #002945
        self.status_text = tk.Text(bottom_frame, wrap=tk.WORD, bg="#002945", fg="white")
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
    def start_status_updater(self):
        """启动状态栏更新器"""
        def update_status():
            current_time = time.time()
            
            # 检查是否需要更新（限制更新频率）
            if current_time - self.last_update_time >= self.update_interval:
                messages = []
                # 一次性获取所有可用消息，但限制数量避免过多
                try:
                    while len(messages) < 200 and not self.message_queue.empty():  # 增加单次处理消息数量
                        messages.append(self.message_queue.get_nowait())
                except:
                    pass
                
                if messages:
                    # 批量更新状态栏，但需要处理ANSI颜色代码
                    for msg in messages:
                        timestamp = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        self.status_text.insert(tk.END, timestamp)
                        
                        # 解析并插入带颜色的文本
                        self.insert_colored_text(msg)
                        self.status_text.insert(tk.END, "\n")
                    
                    self.status_text.see(tk.END)
                    
                    # 如果状态栏内容太多，删除旧的内容
                    if int(self.status_text.index('end-1c').split('.')[0]) > 1000:
                        self.status_text.delete('1.0', '500.0')
                    
                    self.last_update_time = current_time
            
            # 继续定时更新，减少更新间隔提高实时性
            self.root.after(10, update_status)  # 从50ms减少到10ms
        
        # 启动更新循环
        self.root.after(10, update_status)  # 从50ms减少到10ms
    
    def insert_colored_text(self, text):
        """解析ANSI颜色代码并插入带颜色的文本"""
        # ANSI颜色代码正则表达式
        ansi_pattern = re.compile(r'\x1b\[([\d;]*)m')
        
        # 当前活动的标签
        active_tags = []
        
        # 分割文本
        segments = ansi_pattern.split(text)
        
        # 第一段是纯文本
        if segments:
            self.status_text.insert(tk.END, segments[0])
        
        # 处理剩余的段落（代码和文本交替）
        i = 1
        while i < len(segments):
            if i % 2 == 1:  # 奇数索引是ANSI代码
                codes = segments[i].split(';')
                for code in codes:
                    if not code:
                        continue
                    code = int(code)
                    
                    # 重置所有格式
                    if code == 0:
                        active_tags = []
                    
                    # 文本样式
                    elif code == 1:
                        active_tags.append("bold")
                    elif code == 3:
                        active_tags.append("italic")
                    elif code == 4:
                        active_tags.append("underline")
                    
                    # 前景色（标准）
                    elif 30 <= code <= 37:
                        color_map = {
                            30: "black", 31: "red", 32: "green", 33: "yellow",
                            34: "blue", 35: "magenta", 36: "cyan", 37: "white"
                        }
                        # 移除任何现有的颜色标签
                        active_tags = [tag for tag in active_tags if not tag.startswith("bright_") and not tag in color_map.values()]
                        active_tags.append(color_map[code])
                    
                    # 前景色（亮色）
                    elif 90 <= code <= 97:
                        color_map = {
                            90: "bright_black", 91: "bright_red", 92: "bright_green", 93: "bright_yellow",
                            94: "bright_blue", 95: "bright_magenta", 96: "bright_cyan", 97: "bright_white"
                        }
                        # 移除任何现有的颜色标签
                        active_tags = [tag for tag in active_tags if not tag in color_map.values() and not tag in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]]
                        active_tags.append(color_map[code])
                    
                    # 背景色
                    elif 40 <= code <= 47:
                        bg_map = {
                            40: "bg_black", 41: "bg_red", 42: "bg_green", 43: "bg_yellow",
                            44: "bg_blue", 45: "bg_magenta", 46: "bg_cyan", 47: "bg_white"
                        }
                        # 移除任何现有的背景色标签
                        active_tags = [tag for tag in active_tags if not tag.startswith("bg_")]
                        active_tags.append(bg_map[code])
            else:  # 偶数索引是文本
                if segments[i]:  # 如果文本不为空
                    self.status_text.insert(tk.END, segments[i], tuple(active_tags) if active_tags else "")
            i += 1
    
    def _execute_command(self):
        if not self.connect_ssh():
            return
        
        command = self.remote_command.get()
        if not command:
            self.log_status("请输入要执行的命令")
            return
        
        try:
            self.log_status(f"执行命令: {command}")
            
            # 使用get_transport().open_session()创建通道
            channel = self.ssh_client.get_transport().open_session()
            channel.get_pty(term='xterm')  # 请求xterm类型的伪终端，更好地支持Linux终端输出
            channel.exec_command(command)
            
            # 设置通道为非阻塞模式
            channel.setblocking(0)
            
            # 实时读取输出并显示
            buffer_size = 1024  # 增加缓冲区大小，避免字符分割
            last_flush_time = time.time()
            output_buffer = ""
            
            while True:
                # 检查命令是否完成
                if channel.exit_status_ready() and not (channel.recv_ready() or channel.recv_stderr_ready()):
                    # 显示命令执行状态
                    exit_status = channel.recv_exit_status()
                    self.log_status(f"\x1b[32m命令执行完成，退出状态码: {exit_status}\x1b[0m")  # 添加绿色ANSI代码
                    break
                
                # 读取标准输出并立即显示
                if channel.recv_ready():
                    data = channel.recv(buffer_size).decode('utf-8', errors='replace')
                    if data:
                        output_buffer += data
                        # 如果收到换行符或者缓冲区已经积累了一定量的数据，立即显示
                        if '\n' in output_buffer or len(output_buffer) > 80 or (time.time() - last_flush_time) > 0.1:
                            self.log_status(output_buffer)
                            output_buffer = ""
                            last_flush_time = time.time()
                
                # 读取标准错误并立即显示
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(buffer_size).decode('utf-8', errors='replace')
                    if data:
                        self.log_status(f"\x1b[31m{data}\x1b[0m")  # 添加红色ANSI代码
                
                # 处理剩余的缓冲区
                if output_buffer and (time.time() - last_flush_time) > 0.1:
                    self.log_status(output_buffer)
                    output_buffer = ""
                    last_flush_time = time.time()
                
                # 短暂休眠，避免CPU占用过高，但减少休眠时间提高响应速度
                time.sleep(0.001)  # 从0.05减少到0.001秒
                
                # 强制更新UI
                self.root.update_idletasks()
            
            # 确保最后的输出被显示
            if output_buffer:
                self.log_status(output_buffer)
            
            # 关闭通道
            channel.close()
            self.current_channel = None
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            self.log_status(f"\x1b[31m执行命令失败: {str(e)}\x1b[0m")  # 添加红色ANSI代码
            self.log_status(f"\x1b[31m错误详情: {error_msg}\x1b[0m")  # 添加红色ANSI代码
            self.current_channel = None
    
    def download_files(self):
        """启动下载文件线程"""
        threading.Thread(target=self._download_files_thread).start()
    
    def _download_files_thread(self):
        """在后台线程中执行下载文件的操作"""
        if not self.connect_ssh():
            return
        
        remote_path = self.remote_path.get()
        local_path = self.local_path.get()
        
        if not remote_path or not local_path:
            self.log_status("请输入远程和本地路径")
            return
        
        try:
            # 创建SFTP客户端仅用于列出文件
            temp_sftp = self.ssh_client.open_sftp()
            
            # 确保本地目录存在
            os.makedirs(local_path, exist_ok=True)
            
            # 列出远程目录中的文件
            try:
                files = temp_sftp.listdir(remote_path)
            except Exception as e:
                self.log_status(f"无法列出远程目录: {str(e)}")
                temp_sftp.close()
                return
            
            if not files:
                self.log_status("远程目录中没有文件")
                temp_sftp.close()
                return
            
            self.log_status(f"找到 {len(files)} 个文件，开始检查...")
            
            # 初始化进度跟踪字典
            self._last_percent = {}
            
            # 检查哪些文件已经存在
            existing_files = []
            for file in files:
                remote_file = os.path.join(remote_path, file).replace('\\', '/')
                local_file = os.path.join(local_path, file)
                
                # 检查是否是文件而不是目录
                try:
                    file_attr = temp_sftp.stat(remote_file)
                    if not self._is_directory(file_attr) and os.path.exists(local_file):
                        existing_files.append(file)
                except Exception as e:
                    self.log_status(f"检查文件 {file} 失败: {str(e)}")
            
            # 如果有文件已存在，弹出提示框
            overwrite_all = False
            if existing_files:
                # 创建一个事件来同步线程
                overwrite_event = threading.Event()
                
                # 在主线程中显示对话框
                def show_dialog():
                    nonlocal overwrite_all
                    files_str = "\n".join(existing_files[:10])
                    if len(existing_files) > 10:
                        files_str += f"\n... 等共 {len(existing_files)} 个文件"
                    
                    # 创建自定义对话框
                    dialog = tk.Toplevel(self.root)
                    dialog.title("文件已存在")
                    
                    # 使对话框居中
                    dialog_width = 500
                    dialog_height = 200
                    screen_width = dialog.winfo_screenwidth()
                    screen_height = dialog.winfo_screenheight()
                    x = (screen_width - dialog_width) // 2
                    y = (screen_height - dialog_height) // 2
                    dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
                    
                    # 设置为模态对话框
                    dialog.transient(self.root)
                    dialog.grab_set()
                    
                    # 添加消息
                    message = f"以下文件已存在于本地目录中:\n{files_str}\n\n是否覆盖这些文件?"
                    tk.Label(dialog, text=message, justify=tk.LEFT, wraplength=380).pack(padx=20, pady=20)
                    
                    # 添加按钮
                    btn_frame = tk.Frame(dialog)
                    btn_frame.pack(pady=10)
                    
                    def on_overwrite():
                        nonlocal overwrite_all
                        overwrite_all = True
                        dialog.destroy()
                        overwrite_event.set()  # 设置事件，通知下载线程继续
                    
                    def on_cancel():
                        dialog.destroy()
                        overwrite_event.set()  # 设置事件，通知下载线程继续
                    
                    tk.Button(btn_frame, text="覆盖", command=on_overwrite).pack(side=tk.LEFT, padx=10)
                    tk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=10)
                    
                    # 确保对话框关闭时也会设置事件
                    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
                
                # 在主线程中显示对话框
                self.root.after(0, show_dialog)
                
                # 等待用户做出选择
                overwrite_event.wait()
                
                if not overwrite_all:
                    self.log_status("下载已取消")
                    temp_sftp.close()
                    return
                else:
                    self.log_status("将覆盖已存在的文件")
            
            self.log_status(f"开始下载文件...")
            
            # 限制最大并发下载线程数
            max_concurrent_downloads = 2  # 降低并发数以减少连接问题
            active_threads = []
            all_threads = []
            
            for file in files:
                remote_file = os.path.join(remote_path, file).replace('\\', '/')
                local_file = os.path.join(local_path, file)
                
                # 检查是否是文件而不是目录
                try:
                    file_attr = temp_sftp.stat(remote_file)
                    if not self._is_directory(file_attr):
                        # 控制并发下载数量
                        while len(active_threads) >= max_concurrent_downloads:
                            # 清理已完成的线程
                            active_threads = [t for t in active_threads if t.is_alive()]
                            time.sleep(0.5)
                        
                        thread = threading.Thread(
                            target=self._download_single_file,
                            args=(remote_file, local_file)
                        )
                        thread.start()
                        active_threads.append(thread)
                        all_threads.append(thread)
                    else:
                        self.log_status(f"跳过目录: {remote_file}")
                except Exception as e:
                    self.log_status(f"检查文件 {file} 失败: {str(e)}")
            
            # 关闭临时SFTP连接
            temp_sftp.close()
            
            # 等待所有下载完成
            for thread in all_threads:
                thread.join()
            
            self.log_status("所有文件下载完成")
        except Exception as e:
            self.log_status(f"下载文件失败: {str(e)}")
    
    def _download_single_file(self, remote_file, local_file):
        """下载单个文件（每个线程独立的方法）"""
        max_retries = 3  # 最大重试次数
        retry_count = 0
        thread_sftp = None
        
        while retry_count < max_retries:
            try:
                self.log_status(f"正在下载: {remote_file} -> {local_file}")
                
                # 每次尝试都创建新的SFTP连接
                if thread_sftp:
                    try:
                        thread_sftp.close()
                    except:
                        pass
                
                thread_sftp = self.ssh_client.open_sftp()
                if not thread_sftp:
                    raise Exception("无法创建SFTP连接")
                
                # 获取文件大小
                file_attr = thread_sftp.stat(remote_file)
                file_size = file_attr.st_size
                self.log_status(f"文件大小: {self._format_size(file_size)}")
                
                # 初始化进度信息
                file_name = os.path.basename(remote_file)
                progress_data = {
                    'last_percent': -1,
                    'file_size': file_size,
                    'file_name': file_name
                }
                
                # 使用线程独立的SFTP客户端下载文件，添加进度回调
                with open(local_file, 'wb') as f:
                    thread_sftp.getfo(
                        remote_file, 
                        f, 
                        callback=lambda transferred, total: self._show_progress(transferred, total, progress_data)
                    )
                
                self.log_status(f"\x1b[32m下载完成: {remote_file}\x1b[0m")  # 绿色提示成功
                
                # 显示100%进度
                self._show_progress(file_size, file_size, progress_data)
                
                # 关闭SFTP连接
                thread_sftp.close()
                thread_sftp = None
                
                return  # 下载成功，退出循环
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                self.log_status(f"\x1b[33m下载 {remote_file} 出错 ({retry_count}/{max_retries}): {error_msg}\x1b[0m")  # 黄色警告
                
                # 如果是最后一次重试仍然失败
                if retry_count >= max_retries:
                    self.log_status(f"\x1b[31m下载 {remote_file} 失败，已达到最大重试次数\x1b[0m")  # 红色错误
                    # 删除可能部分下载的文件
                    try:
                        if os.path.exists(local_file):
                            os.remove(local_file)
                            self.log_status(f"已删除不完整的文件: {local_file}")
                    except Exception as del_err:
                        self.log_status(f"删除不完整文件失败: {str(del_err)}")
                else:
                    # 等待一段时间再重试
                    time.sleep(2 * retry_count)  # 随着重试次数增加等待时间
            finally:
                # 确保SFTP连接被关闭
                if thread_sftp:
                    try:
                        thread_sftp.close()
                    except:
                        pass
                    thread_sftp = None
    
    def _show_progress(self, transferred, total, progress_data):
        """显示下载进度条"""
        if total <= 0:
            return
        
        percent = int(transferred * 100 / total)
        
        # 避免过于频繁的更新，每1%更新一次
        if percent != progress_data['last_percent']:
            progress_data['last_percent'] = percent
            
            # 创建进度条
            bar_length = 20
            filled_length = int(bar_length * transferred / total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # 计算下载速度
            current_time = time.time()
            if 'start_time' not in progress_data:
                progress_data['start_time'] = current_time
                progress_data['last_time'] = current_time
                progress_data['last_bytes'] = 0
            
            time_diff = current_time - progress_data['last_time']
            if time_diff >= 1:  # 每秒更新一次速度
                bytes_diff = transferred - progress_data['last_bytes']
                speed = bytes_diff / time_diff
                progress_data['last_time'] = current_time
                progress_data['last_bytes'] = transferred
                progress_data['speed'] = speed
            
            # 显示下载速度
            speed_str = ""
            if 'speed' in progress_data:
                speed = progress_data['speed']
                if speed < 1024:
                    speed_str = f"{speed:.1f} B/s"
                elif speed < 1024 * 1024:
                    speed_str = f"{speed/1024:.1f} KB/s"
                else:
                    speed_str = f"{speed/(1024*1024):.1f} MB/s"
            
            # 估计剩余时间
            eta_str = ""
            if 'speed' in progress_data and progress_data['speed'] > 0:
                remaining_bytes = total - transferred
                eta_seconds = remaining_bytes / progress_data['speed']
                if eta_seconds < 60:
                    eta_str = f"{int(eta_seconds)}秒"
                elif eta_seconds < 3600:
                    eta_str = f"{int(eta_seconds/60)}分{int(eta_seconds%60)}秒"
                else:
                    eta_str = f"{int(eta_seconds/3600)}时{int((eta_seconds%3600)/60)}分"
            
            # 构建进度信息
            file_name = progress_data['file_name']
            if len(file_name) > 20:  # 如果文件名太长，截断显示
                file_name = file_name[:17] + "..."
                
            progress_msg = f"下载 [{file_name}] [{bar}] {percent}% "
            if speed_str:
                progress_msg += f"| {speed_str} "
            if eta_str:
                progress_msg += f"| 剩余: {eta_str}"
                
            # 使用不同颜色显示进度
            if percent < 30:
                self.log_status(f"\x1b[33m{progress_msg}\x1b[0m")  # 黄色
            elif percent < 70:
                self.log_status(f"\x1b[36m{progress_msg}\x1b[0m")  # 青色
            else:
                self.log_status(f"\x1b[32m{progress_msg}\x1b[0m")  # 绿色
    
    def _format_size(self, size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"
    
    def _download_files(self):
        if not self.connect_ssh():
            return
        
        remote_path = self.remote_path.get()
        local_path = self.local_path.get()
        
        if not remote_path or not local_path:
            self.log_status("请输入远程和本地路径")
            return
        
        try:
            # 创建SFTP客户端
            self.sftp_client = self.ssh_client.open_sftp()
            
            # 确保本地目录存在
            os.makedirs(local_path, exist_ok=True)
            
            # 列出远程目录中的文件
            try:
                files = self.sftp_client.listdir(remote_path)
            except Exception as e:
                self.log_status(f"无法列出远程目录: {str(e)}")
                return
            
            if not files:
                self.log_status("远程目录中没有文件")
                return
            
            self.log_status(f"找到 {len(files)} 个文件，开始下载...")
            
            # 关闭主SFTP客户端，让每个线程创建自己的连接
            self.sftp_client.close()
            self.sftp_client = None
            
            # 限制最大并发下载线程数
            max_concurrent_downloads = 3
            active_threads = []
            all_threads = []
            
            for file in files:
                remote_file = os.path.join(remote_path, file).replace('\\', '/')
                local_file = os.path.join(local_path, file)
                
                # 创建临时SFTP客户端检查文件类型
                temp_sftp = self.ssh_client.open_sftp()
                try:
                    file_attr = temp_sftp.stat(remote_file)
                    is_dir = self._is_directory(file_attr)
                    temp_sftp.close()
                    
                    if not is_dir:
                        # 控制并发下载数量
                        while len(active_threads) >= max_concurrent_downloads:
                            # 清理已完成的线程
                            active_threads = [t for t in active_threads if t.is_alive()]
                            time.sleep(0.5)
                        
                        thread = threading.Thread(
                            target=self._download_file,
                            args=(remote_file, local_file)
                        )
                        thread.start()
                        active_threads.append(thread)
                        all_threads.append(thread)
                    else:
                        self.log_status(f"跳过目录: {remote_file}")
                except Exception as e:
                    temp_sftp.close()
                    self.log_status(f"检查文件 {file} 失败: {str(e)}")
            
            # 等待所有下载完成
            for thread in all_threads:
                thread.join()
            
            self.log_status("所有文件下载完成")
        except Exception as e:
            self.log_status(f"下载文件失败: {str(e)}")
            if self.sftp_client:
                try:
                    self.sftp_client.close()
                    self.sftp_client = None
                except:
                    pass
    
    def _is_directory(self, file_attr):
        """检查文件属性是否为目录"""
        # 在SFTP中，目录的模式位通常是0o40000 (16384)
        return (file_attr.st_mode & 0o40000) == 0o40000
    
    def _download_file(self, remote_file, local_file):
        """下载单个文件"""
        try:
            self.log_status(f"正在下载: {remote_file} -> {local_file}")
            self.sftp_client.get(remote_file, local_file)
            self.log_status(f"下载完成: {remote_file}")
        except Exception as e:
            self.log_status(f"下载 {remote_file} 失败: {str(e)}")
    
    def delete_files(self):
        """删除远程文件"""
        threading.Thread(target=self._delete_files).start()
    
    def _delete_files(self):
        """在后台线程中执行删除远程文件的操作"""
        if not self.connect_ssh():
            return
        
        remote_path = self.remote_path.get()
        
        if not remote_path:
            self.log_status("请输入远程文件路径")
            return
        
        try:
            # 创建SFTP客户端
            self.sftp_client = self.ssh_client.open_sftp()
            
            # 列出远程目录中的文件
            try:
                files = self.sftp_client.listdir(remote_path)
            except Exception as e:
                self.log_status(f"无法列出远程目录: {str(e)}")
                return
            
            if not files:
                self.log_status("远程目录中没有文件")
                return
            
            self.log_status(f"找到 {len(files)} 个文件，开始删除...")
            
            # 删除文件
            deleted_count = 0
            for file in files:
                remote_file = os.path.join(remote_path, file).replace('\\', '/')
                
                # 检查是否是文件而不是目录
                try:
                    file_attr = self.sftp_client.stat(remote_file)
                    if not self._is_directory(file_attr):
                        self.sftp_client.remove(remote_file)
                        self.log_status(f"已删除: {remote_file}")
                        deleted_count += 1
                    else:
                        self.log_status(f"跳过目录: {remote_file}")
                except Exception as e:
                    self.log_status(f"删除 {remote_file} 失败: {str(e)}")
            
            self.log_status(f"删除完成，共删除 {deleted_count} 个文件")
        except Exception as e:
            self.log_status(f"删除文件失败: {str(e)}")
    
    def process_terminal_output(self, text):
        """处理终端输出，移除控制序列"""
        # 移除所有ANSI控制序列（除了颜色代码）
        # 这个正则表达式匹配大多数控制序列，但保留颜色代码
        text = re.sub(r'\x1b\[\d*[ABCDEFGHJKSTfsu]', '', text)
        text = re.sub(r'\x1b\[\d*;\d*[Hf]', '', text)  # 光标位置
        text = re.sub(r'\x1b\[\?[0-9;]*[hlsr]', '', text)  # 终端模式设置
        text = re.sub(r'\x1b\]0;.*?\x07', '', text)  # 终端标题设置
        
        # 处理进度条更新（通常是通过\r回车符实现的）
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # 如果行中有回车符，只保留最后一个部分
            if '\r' in line:
                parts = line.split('\r')
                processed_lines.append(parts[-1])
            else:
                processed_lines.append(line)
        
        # 移除不可打印字符和控制字符（除了基本的ASCII和颜色代码）
        result = ""
        i = 0
        while i < len(text):
            if text[i] == '\x1b' and i + 1 < len(text) and text[i+1] == '[':
                # 保留ANSI颜色代码
                j = i + 2
                while j < len(text) and text[j] != 'm':
                    j += 1
                if j < len(text):
                    result += text[i:j+1]
                    i = j + 1
                    continue
            
            # 只保留可打印ASCII字符和基本控制字符
            if ord(text[i]) >= 32 or text[i] in '\n\t\r':
                result += text[i]
            i += 1
            
        return result
    
    def log_status(self, message):
        """向消息队列添加消息"""
        if not message:
            return
        
        # 处理终端输出
        message = self.process_terminal_output(message)
        
        # 将消息放入队列
        for line in message.split('\n'):
            if line.strip():
                self.message_queue.put(line.strip())
    
    def browse_key_file(self):
        """浏览并选择SSH私钥文件"""
        file_path = filedialog.askopenfilename(
            title="选择SSH私钥文件",
            filetypes=[("所有文件", "*.*"), ("PEM文件", "*.pem"), ("PPK文件", "*.ppk")]
        )
        if file_path:
            self.key_path.delete(0, tk.END)
            self.key_path.insert(0, file_path)
            self.log_status(f"已选择SSH私钥文件: {file_path}")
    
    def browse_local_dir(self):
        """浏览并选择本地接收文件夹"""
        dir_path = filedialog.askdirectory(title="选择本地接收文件夹")
        if dir_path:
            self.local_path.delete(0, tk.END)
            self.local_path.insert(0, dir_path)
            self.log_status(f"已选择本地接收文件夹: {dir_path}")
    
    def save_config(self):
        """保存当前配置到文件"""
        config = {
            "server_ip": self.server_ip.get(),
            "ssh_port": self.ssh_port.get(),
            "username": self.username.get(),
            "key_path": self.key_path.get(),
            "remote_path": self.remote_path.get(),
            "local_path": self.local_path.get(),
            "remote_command": self.remote_command.get()
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.log_status(f"配置已保存到: {self.config_path}")
        except Exception as e:
            self.log_status(f"保存配置失败: {str(e)}")
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if not os.path.exists(self.config_path):
                self.log_status(f"配置文件不存在: {self.config_path}")
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 清空并设置各个字段
            self.server_ip.delete(0, tk.END)
            self.server_ip.insert(0, config.get("server_ip", ""))
            
            self.ssh_port.delete(0, tk.END)
            self.ssh_port.insert(0, config.get("ssh_port", "22"))
            
            self.username.delete(0, tk.END)
            self.username.insert(0, config.get("username", ""))
            
            self.key_path.delete(0, tk.END)
            self.key_path.insert(0, config.get("key_path", ""))
            
            self.remote_path.delete(0, tk.END)
            self.remote_path.insert(0, config.get("remote_path", ""))
            
            self.local_path.delete(0, tk.END)
            self.local_path.insert(0, config.get("local_path", ""))
            
            self.remote_command.delete(0, tk.END)
            self.remote_command.insert(0, config.get("remote_command", ""))
            
            self.log_status(f"已从 {self.config_path} 加载配置")
        except Exception as e:
            self.log_status(f"加载配置失败: {str(e)}")
    
    def connect_ssh(self):
        """连接到SSH服务器"""
        if self.ssh_client and self.ssh_client.get_transport() and self.ssh_client.get_transport().is_active():
            return True
            
        server_ip = self.server_ip.get()
        ssh_port = int(self.ssh_port.get())
        username = self.username.get()
        password = self.password.get()
        key_path = self.key_path.get()
        
        if not server_ip or not username:
            self.log_status("请输入服务器IP和用户名")
            return False
        
        try:
            self.log_status(f"正在连接到 {username}@{server_ip}:{ssh_port}...")
            
            # 创建SSH客户端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 尝试使用密钥连接
            if key_path:
                try:
                    self.ssh_client.connect(
                        hostname=server_ip,
                        port=ssh_port,
                        username=username,
                        key_filename=key_path,
                        timeout=10
                    )
                    self.log_status("使用SSH密钥连接成功")
                    return True
                except Exception as e:
                    self.log_status(f"使用SSH密钥连接失败: {str(e)}")
                    # 如果密钥连接失败且有密码，尝试密码连接
                    if not password:
                        raise
            
            # 使用密码连接
            if password:
                self.ssh_client.connect(
                    hostname=server_ip,
                    port=ssh_port,
                    username=username,
                    password=password,
                    timeout=10
                )
                self.log_status("使用密码连接成功")
                return True
            else:
                self.log_status("请提供密码或有效的SSH密钥")
                return False
                
        except Exception as e:
            self.log_status(f"\x1b[31m连接SSH失败: {str(e)}\x1b[0m")
            return False
    
    def start_ssh_connection(self):
        """启动SSH连接（在单独的线程中）"""
        threading.Thread(target=self._start_ssh_connection).start()
    
    def _start_ssh_connection(self):
        """在后台线程中执行SSH连接"""
        if self.connect_ssh():
            self.log_status("\x1b[32mSSH连接已建立\x1b[0m")
        else:
            self.log_status("\x1b[31mSSH连接失败\x1b[0m")
    
    def disconnect_ssh(self):
        """断开SSH连接"""
        # 先尝试中断当前正在执行的命令
        if self.current_channel:
            try:
                self.log_status("正在中断当前命令...")
                self.current_channel.close()
                self.current_channel = None
                self.log_status("\x1b[33m已强制中断当前命令\x1b[0m")  # 黄色警告
            except Exception as e:
                self.log_status(f"\x1b[31m中断命令时出错: {str(e)}\x1b[0m")
        
        if self.sftp_client:
            try:
                self.sftp_client.close()
                self.sftp_client = None
                self.log_status("SFTP连接已关闭")
            except Exception as e:
                self.log_status(f"关闭SFTP连接时出错: {str(e)}")
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
                self.ssh_client = None
                self.log_status("SSH连接已关闭")
            except Exception as e:
                self.log_status(f"关闭SSH连接时出错: {str(e)}")
    
    def execute_command(self):
        """执行远程命令（在单独的线程中）"""
        threading.Thread(target=self._execute_command).start()
    
    def clear_status(self):
        """清空状态文本框"""
        self.status_text.delete(1.0, tk.END)
        self.log_status("状态栏已清空")
    
    def clear_config(self):
        """清空当前填写的所有配置数据"""
        # 清空服务器IP
        self.server_ip.delete(0, tk.END)
        
        # 重置SSH端口为默认值22
        self.ssh_port.delete(0, tk.END)
        self.ssh_port.insert(0, "22")
        
        # 清空用户名
        self.username.delete(0, tk.END)
        
        # 清空密码
        self.password.delete(0, tk.END)
        
        # 清空SSH私钥
        self.key_path.delete(0, tk.END)
        
        # 清空远程命令
        self.remote_command.delete(0, tk.END)
        
        # 清空远程文件路径
        self.remote_path.delete(0, tk.END)
        
        # 清空本地接收路径
        self.local_path.delete(0, tk.END)
        
        self.log_status("已清空所有配置")
    
    def close(self):
        """关闭连接并退出"""
        if self.sftp_client:
            try:
                self.sftp_client.close()
            except:
                pass
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
    
    def create_context_menu(self):
        """创建右键上下文菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="粘贴", command=self.paste_text)
        
    def bind_context_menu_to_entries(self):
        """将右键菜单绑定到所有文本框"""
        entries = [
            self.server_ip, self.ssh_port, self.username, self.password,
            self.key_path, self.remote_command, self.remote_path, self.local_path
        ]
        
        for entry in entries:
            entry.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 记录当前触发事件的控件
        self.current_entry = event.widget
        # 在鼠标位置显示菜单
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # 确保菜单正确关闭
            self.context_menu.grab_release()
    
    def paste_text(self):
        """执行粘贴操作"""
        try:
            # 获取剪贴板内容
            clipboard_text = self.root.clipboard_get()
            # 如果当前有选中的文本，则先删除选中部分
            try:
                sel_start = self.current_entry.index("sel.first")
                sel_end = self.current_entry.index("sel.last")
                self.current_entry.delete(sel_start, sel_end)
                # 在选中位置插入剪贴板内容
                self.current_entry.insert(sel_start, clipboard_text)
            except tk.TclError:
                # 如果没有选中文本，则在当前光标位置插入
                current_pos = self.current_entry.index(tk.INSERT)
                self.current_entry.insert(current_pos, clipboard_text)
        except Exception as e:
            self.log_status(f"粘贴操作失败: {str(e)}")

# 主程序入口
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SSHSFTPApp(root)
        
        # 设置关闭窗口时的操作
        root.protocol("WM_DELETE_WINDOW", lambda: (app.close(), root.destroy()))
        
        # 添加初始化消息，确认程序已启动
        app.log_status("程序已启动，GUI已初始化")
        
        # 确保主循环在主线程中运行
        root.mainloop()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"程序启动失败: {str(e)}")
        print(f"错误详情: {error_msg}")
        
        # 如果GUI未启动，尝试使用简单的消息框显示错误
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("启动错误", f"程序启动失败: {str(e)}\n\n{error_msg}")
        except:
            pass
        
        # 保持控制台窗口打开
        input("按Enter键退出...")