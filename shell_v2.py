import os
import shutil
import platform
import subprocess
import stat
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from datetime import datetime
from functools import partial
import re
import threading
from tkinter import simpledialog
import getpass
from datetime import datetime

class ImprovedMiniShell:
    def __init__(self, root):
        self.root = root
        self.root.title("ImprovedMiniShell")
        self.cwd = os.getcwd()
        self.history = []
        self.history_index = 0
        self.clipboard = ""
        self.background_tasks = []
        self.create_ui()
        self.load_theme("dark")  # Default theme
        
        # Configure platform-specific settings
        self.system = platform.system()
        if self.system == "Windows":
            self.clear_cmd = "cls"
        else:
            self.clear_cmd = "clear"
            
        self.show_welcome_message()
        self.update_directory_tree()
        self.entry.focus_set()

    def create_ui(self):
        # Create main frames
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save Output", command=self.save_output)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self.copy_selection)
        edit_menu.add_command(label="Paste", command=self.paste_clipboard)
        edit_menu.add_command(label="Clear Terminal", command=self.clear_terminal)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Themes", menu=theme_menu)
        theme_menu.add_command(label="Light Theme", command=lambda: self.load_theme("light"))
        theme_menu.add_command(label="Dark Theme", command=lambda: self.load_theme("dark"))
        theme_menu.add_command(label="Monokai", command=lambda: self.load_theme("monokai"))
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Commands", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Toolbar
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(toolbar, text="←", width=2, command=lambda: self.go_dir("..")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Home", width=5, command=lambda: self.go_dir(os.path.expanduser("~"))).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", width=7, command=self.update_directory_tree).pack(side=tk.LEFT, padx=2)
        
        # Path display
        self.path_var = tk.StringVar()
        self.path_var.set(self.cwd)
        path_entry = ttk.Entry(toolbar, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        path_entry.bind("<Return>", lambda e: self.go_dir(self.path_var.get()))
        
        # Paned window for directory tree and terminal
        paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left panel - directory tree
        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=1)
        
        # Directory Tree with scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dir_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set)
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.dir_tree.yview)
        
        self.dir_tree.heading("#0", text="Directory Structure")
        self.dir_tree.bind("<Double-1>", self.on_tree_double_click)
        self.dir_tree.bind("<Button-3>", self.show_context_menu)

        # Right panel - terminal
        terminal_frame = ttk.Frame(paned)
        paned.add(terminal_frame, weight=3)
        
        # Terminal Output with scrollbar
        self.output = scrolledtext.ScrolledText(
            terminal_frame, 
            height=20, 
            width=80, 
            state='disabled', 
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_configure("error", foreground="red")
        self.output.tag_configure("success", foreground="green")
        self.output.tag_configure("input", foreground="cyan")
        self.output.tag_configure("info", foreground="yellow")
        
        # Bind right-click menu to output
        self.output.bind("<Button-3>", self.show_output_context_menu)
        
        # Command Entry
        entry_frame = ttk.Frame(self.main_frame)
        entry_frame.pack(fill=tk.X, pady=5)
        
        prompt_label = ttk.Label(entry_frame, text="> ")
        prompt_label.pack(side=tk.LEFT)
        
        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.run_command)
        self.entry.bind("<Up>", self.navigate_history_up)
        self.entry.bind("<Down>", self.navigate_history_down)
        self.entry.bind("<Tab>", self.autocomplete)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_theme(self, theme_name):
        """Load a color theme for the shell"""
        if theme_name == "light":
            bg_color = "#ffffff"
            fg_color = "#000000"
            select_bg = "#a6d2ff"
            entry_bg = "#f5f5f5"
        elif theme_name == "dark":
            bg_color = "#282c34"
            fg_color = "#abb2bf"
            select_bg = "#3e4451"
            entry_bg = "#21252b"
        elif theme_name == "monokai":
            bg_color = "#272822"
            fg_color = "#f8f8f2"
            select_bg = "#49483e"
            entry_bg = "#1e1f1c"
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", background=bg_color, foreground=fg_color)
        style.configure("TEntry", fieldbackground=entry_bg)
        style.map("TEntry", fieldbackground=[("focus", entry_bg)])
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=bg_color, foreground=fg_color)
        style.map("TButton", background=[("active", select_bg)])
        
        self.output.config(bg=bg_color, fg=fg_color, insertbackground=fg_color, selectbackground=select_bg)
        # self.dir_tree.configure(background=bg_color, foreground=fg_color)
        style.configure("Treeview",
                background=bg_color,
                foreground=fg_color,
                fieldbackground=bg_color)

        style.map("Treeview",
                background=[("selected", select_bg)],
                foreground=[("selected", fg_color)])

        # Save current theme
        self.current_theme = theme_name
        self.status_var.set(f"Theme changed to {theme_name}")

    # def show_welcome_message(self):
    #     """Display welcome message with basic information"""
    #     welcome_message = f"""
    #     ╔════════════════════════════════════════════════════════╗
    #     ║               IMPROVED MINI SHELL                      ║
    #     ╚════════════════════════════════════════════════════════╝
        
    #     Welcome to ImprovedMiniShell - A powerful shell interface
        
    #     System: {platform.system()} {platform.release()}
    #     Python: {platform.python_version()}
        
    #     Type 'help' to see available commands
    #     """
    #     self.log(welcome_message, "info")

    def show_welcome_message(self):
        """Display a styled welcome message with system info and basic instructions."""
        system_info = f"{platform.system()} {platform.release()}"
        python_info = platform.python_version()
        username = getpass.getuser()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        welcome_message = (
            "\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║                     IMPROVED MINI SHELL                      ║\n"
            "╠══════════════════════════════════════════════════════════════╣\n"
            f"║  User    : {username:<50}║\n"
            f"║  Time    : {current_time:<50}║\n"
            f"║  System  : {system_info:<50}║\n"
            f"║  Python  : {python_info:<50}║\n"
            "╠══════════════════════════════════════════════════════════════╣\n"
            "║  Welcome to ImprovedMiniShell - A powerful shell interface   ║\n"
            "║  Type 'help' to see available commands                       ║\n"
            "╚══════════════════════════════════════════════════════════════╝\n"
        )
        self.log(welcome_message, "info")



    def update_directory_tree(self):
        """Update the directory tree view"""
        self.dir_tree.delete(*self.dir_tree.get_children())
        self.path_var.set(self.cwd)
        
        # Add root directory
        root_node = self.dir_tree.insert("", "end", text=os.path.basename(self.cwd) or self.cwd, 
                                         open=True, values=[self.cwd])
        
        # Add subdirectories and files
        try:
            for item in sorted(os.listdir(self.cwd)):
                item_path = os.path.join(self.cwd, item)
                if os.path.isdir(item_path):
                    dir_node = self.dir_tree.insert(root_node, "end", text=item, values=[item_path])
                    # Add a dummy item to allow expansion
                    self.dir_tree.insert(dir_node, "end", text="Loading...", values=["dummy"])
                else:
                    self.dir_tree.insert(root_node, "end", text=item, values=[item_path])
        except PermissionError:
            self.log(f"Permission denied to read directory: {self.cwd}", "error")
        
        self.status_var.set(f"Current directory: {self.cwd}")

    def on_tree_double_click(self, event):
        """Handle double-click on directory tree"""
        item_id = self.dir_tree.identify('item', event.x, event.y)
        if item_id:
            path = self.dir_tree.item(item_id, "values")[0]
            if os.path.isdir(path):
                self.go_dir(path)
            elif os.path.isfile(path):
                self.open_file_with_default_app(path)

    def expand_tree_item(self, item_id):
        """Expand a tree item and load its children"""
        # Get the path from the item values
        path = self.dir_tree.item(item_id, "values")[0]
        
        # Remove dummy item
        for child in self.dir_tree.get_children(item_id):
            if self.dir_tree.item(child, "values")[0] == "dummy":
                self.dir_tree.delete(child)
        
        # Add actual children
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dir_node = self.dir_tree.insert(item_id, "end", text=item, values=[item_path])
                    # Add a dummy item to allow expansion
                    self.dir_tree.insert(dir_node, "end", text="Loading...", values=["dummy"])
                else:
                    self.dir_tree.insert(item_id, "end", text=item, values=[item_path])
        except PermissionError:
            self.log(f"Permission denied to read directory: {path}", "error")

    def show_context_menu(self, event):
        """Show context menu for directory tree items"""
        item_id = self.dir_tree.identify('item', event.x, event.y)
        if item_id:
            self.dir_tree.selection_set(item_id)
            path = self.dir_tree.item(item_id, "values")[0]
            
            context_menu = tk.Menu(self.root, tearoff=0)
            if os.path.isdir(path):
                context_menu.add_command(label="Open", command=lambda: self.go_dir(path))
                context_menu.add_command(label="Open in File Explorer", command=lambda: self.open_file_with_default_app(path))
                context_menu.add_separator()
            elif os.path.isfile(path):
                context_menu.add_command(label="Open", command=lambda: self.open_file_with_default_app(path))
                context_menu.add_separator()
                
            context_menu.add_command(label="Copy Path", command=lambda: self.copy_to_clipboard(path))
            context_menu.add_command(label="Rename", command=lambda: self.rename_item(path))
            context_menu.add_command(label="Delete", command=lambda: self.delete_item(path))
            context_menu.post(event.x_root, event.y_root)

    def show_output_context_menu(self, event):
        """Show context menu for terminal output"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Copy", command=self.copy_selection)
        context_menu.add_command(label="Select All", command=lambda: self.output.tag_add(tk.SEL, "1.0", tk.END))
        context_menu.add_command(label="Clear", command=self.clear_terminal)
        context_menu.post(event.x_root, event.y_root)

    def log(self, message, tag=None):
        """Write message to the output terminal with optional tag for styling"""
        self.output.config(state='normal')
        if tag:
            self.output.insert(tk.END, message + "\n", tag)
        else:
            self.output.insert(tk.END, message + "\n")
        self.output.see(tk.END)
        self.output.config(state='disabled')

    def run_command(self, event=None):
        """Process and execute the entered command"""
        command = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        
        if not command:
            return
            
        # Add to history
        self.history.append(command)
        self.history_index = len(self.history)
        
        # Log the command with input formatting
        self.log(f"> {command}", "input")
        
        # Parse command and arguments
        args = []
        in_quotes = False
        quote_char = None
        current_arg = ""
        
        # Handle quoted arguments properly
        for char in command:
            if char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif quote_char == char:
                    in_quotes = False
                    quote_char = None
                else:
                    current_arg += char
            elif char.isspace() and not in_quotes:
                if current_arg:
                    args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
                
        if current_arg:
            args.append(current_arg)
            
        if not args:
            return
            
        cmd = args[0].lower()
        
        try:
            # Built-in commands
            if cmd == "ls" or cmd == "dir":
                self.cmd_list_directory(args[1:])
            elif cmd == "cd":
                self.cmd_change_directory(args[1:])
            elif cmd == "mkdir":
                self.cmd_make_directory(args[1:])
            elif cmd == "touch" or cmd == "new-item":
                self.cmd_create_file(args[1:])
            elif cmd == "rm" or cmd == "del":
                self.cmd_remove(args[1:])
            elif cmd == "cp" or cmd == "copy":
                self.cmd_copy(args[1:])
            elif cmd == "mv" or cmd == "move":
                self.cmd_move(args[1:])
            elif cmd == "cat" or cmd == "type":
                self.cmd_cat(args[1:])
            elif cmd == "pwd":
                self.log(self.cwd)
            elif cmd == "echo":
                self.log(" ".join(args[1:]))
            elif cmd == "clear" or cmd == "cls":
                self.clear_terminal()
            elif cmd == "find" or cmd == "search":
                self.cmd_find(args[1:])
            elif cmd == "grep":
                self.cmd_grep(args[1:])
            elif cmd == "chmod":
                self.cmd_chmod(args[1:])
            elif cmd == "history":
                self.cmd_history()
            elif cmd == "zip" or cmd == "compress":
                self.cmd_zip(args[1:])
            elif cmd == "unzip" or cmd == "extract":
                self.cmd_unzip(args[1:])
            elif cmd == "whoami":
                self.cmd_whoami()
            elif cmd == "date":
                self.log(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            elif cmd == "bg":
                self.cmd_background(args[1:])
            elif cmd == "jobs":
                self.cmd_jobs()
            elif cmd == "help":
                self.show_help()
            elif cmd == "exit" or cmd == "quit":
                if len(self.background_tasks) > 0:
                    if messagebox.askyesno("Background Tasks", 
                                          "There are background tasks running. Do you want to exit anyway?"):
                        self.root.quit()
                else:
                    self.root.quit()
            elif cmd.startswith("!"):
                # Execute system command
                if len(cmd) > 1:
                    index = 0
                    try:
                        index = int(cmd[1:])
                        if 0 <= index < len(self.history):
                            self.entry.insert(0, self.history[index])
                            return
                    except ValueError:
                        self.log(f"Invalid history index: {cmd[1:]}", "error")
            else:
                # Try to execute as system command
                if cmd == "python" or cmd == "py":
                    self.run_system_command(args)
                else:
                    self.run_system_command(args)
                    
        except Exception as e:
            self.log(f"Error: {str(e)}", "error")
            
        self.status_var.set("Ready")

    def cmd_list_directory(self, args):
        """Enhanced ls command with formatting and options"""
        path = self.cwd
        show_hidden = False
        show_details = False
        
        # Parse options
        for arg in args:
            if arg == "-a" or arg == "--all":
                show_hidden = True
            elif arg == "-l" or arg == "--long":
                show_details = True
            elif not arg.startswith("-"):
                path = os.path.abspath(os.path.join(self.cwd, arg))
        
        try:
            items = os.listdir(path)
            
            # Filter hidden items if not showing all
            if not show_hidden:
                items = [item for item in items if not item.startswith('.')]
                
            # Sort items (directories first)
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
                else:
                    files.append(item)
                    
            dirs.sort()
            files.sort()
            sorted_items = dirs + files
            
            if not sorted_items:
                self.log("Directory is empty.")
                return
                
            # Display items
            if show_details:
                # Format as a table
                self.log(f"{'Mode':<10} {'Size':<8} {'Modified':<20} {'Name':<30}")
                self.log("-" * 70)
                
                for item in sorted_items:
                    item_path = os.path.join(path, item)
                    stat_info = os.stat(item_path)
                    
                    # Format mode/permissions
                    mode = stat.filemode(stat_info.st_mode)
                    
                    # Format size
                    size = self.format_size(stat_info.st_size)
                    
                    # Format modified time
                    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat_info.st_mtime))
                    
                    # Format name (add trailing slash for directories)
                    name = item
                    if os.path.isdir(item_path):
                        name += "/"
                        
                    self.log(f"{mode:<10} {size:<8} {mtime:<20} {name:<30}")
            else:
                # Simple listing with color coding via tags
                result = ""
                for item in sorted_items:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        self.log(f"  {item}/", "info")
                    else:
                        self.log(f"  {item}")
        except Exception as e:
            self.log(f"Error listing directory: {str(e)}", "error")

    def format_size(self, size):
        """Format file size in human-readable format"""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024:
                if unit == 'B':
                    return f"{size}{unit}"
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}P"

    def cmd_change_directory(self, args):
        """Change the current working directory"""
        if not args:
            # Default to home directory
            new_path = os.path.expanduser("~")
        else:
            new_path = os.path.abspath(os.path.join(self.cwd, args[0]))
            
        try:
            if os.path.isdir(new_path):
                self.go_dir(new_path)
            else:
                self.log(f"Directory not found: {new_path}", "error")
        except Exception as e:
            self.log(f"Error changing directory: {str(e)}", "error")

    def go_dir(self, path):
        """Change to specified directory and update UI"""
        try:
            os.chdir(path)
            self.cwd = os.getcwd()
            self.log(f"Changed to: {self.cwd}", "success")
            self.update_directory_tree()
        except Exception as e:
            self.log(f"Error changing directory: {str(e)}", "error")

    def cmd_make_directory(self, args):
        """Create a new directory"""
        if not args:
            self.log("mkdir requires a directory name", "error")
            return
            
        for arg in args:
            path = os.path.join(self.cwd, arg)
            try:
                os.makedirs(path, exist_ok=True)
                self.log(f"Directory created: {path}", "success")
            except Exception as e:
                self.log(f"Error creating directory: {str(e)}", "error")
                
        self.update_directory_tree()

    def cmd_create_file(self, args):
        """Create a new empty file"""
        if not args:
            self.log("touch requires a file name", "error")
            return
            
        for arg in args:
            path = os.path.join(self.cwd, arg)
            try:
                with open(path, 'a'):
                    os.utime(path, None)
                self.log(f"File created: {path}", "success")
            except Exception as e:
                self.log(f"Error creating file: {str(e)}", "error")
                
        self.update_directory_tree()

    def cmd_remove(self, args):
        """Remove a file or directory"""
        if not args:
            self.log("rm requires a file or directory name", "error")
            return
            
        force = "-f" in args
        recursive = "-r" in args or "-rf" in args or "-fr" in args
        
        # Filter out options
        targets = [arg for arg in args if not arg.startswith("-")]
        
        if not targets:
            self.log("rm requires a file or directory name", "error")
            return
            
        for target in targets:
            path = os.path.join(self.cwd, target)
            try:
                if os.path.isdir(path):
                    if recursive:
                        shutil.rmtree(path)
                        self.log(f"Directory removed: {path}", "success")
                    else:
                        self.log(f"Cannot remove directory {path} without -r option", "error")
                elif os.path.exists(path):
                    os.remove(path)
                    self.log(f"File removed: {path}", "success")
                elif not force:
                    self.log(f"No such file or directory: {path}", "error")
            except Exception as e:
                self.log(f"Error removing {path}: {str(e)}", "error")
                
        self.update_directory_tree()

    def cmd_copy(self, args):
        """Copy files or directories"""
        if len(args) < 2:
            self.log("cp requires source and destination", "error")
            return
            
        recursive = "-r" in args
        
        # Filter out options
        real_args = [arg for arg in args if not arg.startswith("-")]
        
        if len(real_args) < 2:
            self.log("cp requires source and destination", "error")
            return
            
        sources = real_args[:-1]
        destination = os.path.join(self.cwd, real_args[-1])
        
        for source in sources:
            source_path = os.path.join(self.cwd, source)
            try:
                if os.path.isdir(source_path):
                    if recursive:
                        dest_dir = os.path.join(destination, os.path.basename(source_path))
                        shutil.copytree(source_path, dest_dir)
                        self.log(f"Directory copied: {source_path} -> {dest_dir}", "success")
                    else:
                        self.log(f"Cannot copy directory {source_path} without -r option", "error")
                else:
                    if os.path.isdir(destination):
                        dest_file = os.path.join(destination, os.path.basename(source_path))
                    else:
                        dest_file = destination
                    shutil.copy2(source_path, dest_file)
                    self.log(f"File copied: {source_path} -> {dest_file}", "success")
            except Exception as e:
                self.log(f"Error copying {source_path}: {str(e)}", "error")
                
        self.update_directory_tree()

    def cmd_move(self, args):
        """Move files or directories"""
        if len(args) < 2:
            self.log("mv requires source and destination", "error")
            return
            
        sources = args[:-1]
        destination = os.path.join(self.cwd, args[-1])
        
        for source in sources:
            source_path = os.path.join(self.cwd, source)
            try:
                if os.path.isdir(destination):
                    dest_path = os.path.join(destination, os.path.basename(source_path))
                else:
                    dest_path = destination
                    
                shutil.move(source_path, dest_path)
                self.log(f"Moved: {source_path} -> {dest_path}", "success")
            except Exception as e:
                self.log(f"Error moving {source_path}: {str(e)}", "error")
                
        self.update_directory_tree()

    def cmd_cat(self, args):
        """Display the contents of a file"""
        if not args:
            self.log("cat requires a file name", "error")
            return
            
        path = os.path.join(self.cwd, args[0])
        
        try:
            if os.path.isfile(path):
                with open(path, 'r', errors='replace') as f:
                    content = f.read()
                    self.log(f"--- Contents of {path} ---")
                    self.log(content)
                    self.log(f"--- End of {path} ---")
            else:
                self.log(f"Not a file: {path}", "error")
        except Exception as e:
            self.log(f"Error reading file: {str(e)}", "error")

    # def open_file(self):
    #     file_path = filedialog.askopenfilename()
    #     if file_path:
    #         try:
    #             with open(file_path, 'r') as f:
    #                 content = f.read()
    #             self.log(f"Opened file: {file_path}\n{content}")
    #         except Exception as e:
    #             messagebox.showerror("Error", str(e))


    # def cmd_find(self, args):
    #     """Find files and directories"""
    #     if not args:
    #         self.log("find requires a search pattern", "error")
    #         return
            
    #     pattern = args[0]
    #     search_dir = self.cwd
    #     recursive = True
        
    #     # Check for directory argument
    #     if len(args) > 1 and os.path.isdir(os.path.join(self.cwd, args[1])):
    #         search_dir = os.path.join(self.cwd, args[1])
            
    #     self.log(f"Searching for '{pattern}' in {search_dir}...")
        
    #     found_items = []
        
    #     try:
    #         if recursive:
    #             for root, dirs, files in os.walk(search_dir):
    #                 # Match directories
    #                 for d in dirs:
    #                     if pattern.lower() in d.lower():
    #                         rel_path = os.path.relpath(os.path.join(root, d), search_dir)
    #                         found_items.append(f"./{rel_path}")
                            
                    # Match files

    def cmd_find(self, args):
        """Find files and directories"""
        if not args:
            self.log("find requires a search pattern", "error")
            return
        
        pattern = args[0]
        search_dir = self.cwd
        recursive = True
        
        # Check for directory argument
        if len(args) > 1 and os.path.isdir(os.path.join(self.cwd, args[1])):
            search_dir = os.path.join(self.cwd, args[1])
        
        self.log(f"Searching for '{pattern}' in {search_dir}...")
        
        found_items = []
        
        try:
            if recursive:
                for root, dirs, files in os.walk(search_dir):
                    # Match directories
                    for d in dirs:
                        if re.search(pattern, d, re.IGNORECASE):
                            rel_path = os.path.relpath(os.path.join(root, d), search_dir)
                            found_items.append(f"./{rel_path}")
                            
                    # Match files
                    for f in files:
                        if re.search(pattern, f, re.IGNORECASE):
                            rel_path = os.path.relpath(os.path.join(root, f), search_dir)
                            found_items.append(f"./{rel_path}")
            else:
                for item in os.listdir(search_dir):
                    if re.search(pattern, item, re.IGNORECASE):
                        found_items.append(f"./{item}")
            
            if found_items:
                self.log("Found items:")
                for item in found_items:
                    self.log(item)
            else:
                self.log("No items found.")
                
        except Exception as e:
            self.log(f"Error searching: {str(e)}", "error")

    def cmd_grep(self, args):
        """Search for text in files"""
        if len(args) < 2:
            self.log("grep requires a pattern and file name", "error")
            return
        
        pattern = args[0]
        file_name = os.path.join(self.cwd, args[1])
        
        try:
            with open(file_name, 'r', errors='replace') as f:
                lines = f.readlines()
                found_lines = [line for line in lines if re.search(pattern, line)]
                
            if found_lines:
                self.log(f"Found {len(found_lines)} matching lines in {file_name}:")
                for line in found_lines:
                    self.log(line.strip())
            else:
                self.log(f"No matches found in {file_name}.")
                
        except Exception as e:
            self.log(f"Error searching in file: {str(e)}", "error")

    def cmd_chmod(self, args):
        """Change file permissions"""
        if len(args) < 2:
            self.log("chmod requires mode and file name", "error")
            return
        
        mode = args[0]
        file_name = os.path.join(self.cwd, args[1])
        
        try:
            os.chmod(file_name, int(mode, 8))
            self.log(f"Permissions changed for {file_name}", "success")
        except Exception as e:
            self.log(f"Error changing permissions: {str(e)}", "error")

    def cmd_zip(self, args):
        """Compress files into a zip archive"""
        if len(args) < 2:
            self.log("zip requires archive name and files", "error")
            return
        
        archive_name = args[0]
        files = args[1:]
        
        try:
            with zipfile.ZipFile(archive_name, 'w') as zipf:
                for file in files:
                    file_path = os.path.join(self.cwd, file)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                        self.log(f"Added {file_path} to {archive_name}", "success")
                    else:
                        self.log(f"File not found: {file_path}", "error")
        except Exception as e:
            self.log(f"Error creating zip archive: {str(e)}", "error")
    
    def cmd_unzip(self, args):
        """Extract files from a zip archive"""
        if len(args) < 1:
            self.log("unzip requires archive name", "error")
            return
        
        archive_name = args[0]
        
        try:
            with zipfile.ZipFile(archive_name, 'r') as zipf:
                zipf.extractall(self.cwd)
                self.log(f"Extracted {archive_name} to {self.cwd}", "success")
        except Exception as e:
            self.log(f"Error extracting zip archive: {str(e)}", "error")

    def cmd_whoami(self):
        """Display current user information"""
        try:
            user_info = os.getlogin()
            self.log(f"Current user: {user_info}", "info")
        except Exception as e:
            self.log(f"Error retrieving user info: {str(e)}", "error")

    def cmd_background(self, args):
        """Run command in background (not implemented)"""
        self.log("Background tasks are not implemented yet.", "info")

    def cmd_jobs(self):
        """List background jobs (not implemented)"""
        self.log("Background jobs are not implemented yet.", "info")

    def open_file(self):
        """Open a file with the default application"""
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                if platform.system() == "Windows":
                    os.startfile(file_path)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", file_path])
                else:
                    subprocess.call(["xdg-open", file_path])
            except Exception as e:
                self.log(f"Error opening file: {str(e)}", "error")

    def save_output(self):
        """Save the terminal output to a file"""
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.output.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Output saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
    def copy_selection(self):
        """Copy selected text to clipboard"""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.output.get(tk.SEL_FIRST, tk.SEL_LAST))
            self.update_idletasks()
            self.log("Copied to clipboard", "success")
        except tk.TclError:
            self.log("No text selected", "error")
    
    def paste_clipboard(self):
        """Paste text from clipboard into the entry field"""
        try:
            clipboard_text = self.clipboard_get()
            self.entry.insert(tk.END, clipboard_text)
        except tk.TclError:
            self.log("Clipboard is empty", "error")

    def clear_terminal(self):
        """Clear the terminal output"""
        self.output.config(state='normal')
        self.output.delete(1.0, tk.END)
        self.output.config(state='disabled')
        self.log("Terminal cleared", "success")
    
    def cmd_history(self):
        """Display command history"""
        if not self.history:
            self.log("No command history available", "info")
            return
        
        self.log("Command History:")
        for index, command in enumerate(self.history):
            self.log(f"{index}: {command}")

    def navigate_history_up(self, event):  
        """Navigate command history upwards"""
        if self.history_index > 0:
            self.history_index -= 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_index])

    def navigate_history_down(self, event):  
        """Navigate command history downwards"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_index])
        elif self.history_index == len(self.history) - 1:
            self.history_index += 1
            self.entry.delete(0, tk.END)

    def autocomplete(self, event):
        """Autocomplete command or file name"""
        current_text = self.entry.get()
        if not current_text:
            return
        
        # Get the last word typed
        words = current_text.split()
        last_word = words[-1]
        
        # Get possible completions
        completions = [item for item in os.listdir(self.cwd) if item.startswith(last_word)]
        
        if completions:
            # Show first completion
            self.entry.delete(len(current_text) - len(last_word), tk.END)
            self.entry.insert(tk.END, completions[0][len(last_word):])
            return "break"
        
    def open_file_with_default_app(self, file_path):
        """Open a file with the default application"""
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            self.log(f"Error opening file: {str(e)}", "error")

    def show_help(self):
        """Display help information"""
        help_text = """
        Available commands:
        - ls, dir: List directory contents
        - cd: Change directory
        - mkdir: Create a new directory
        - touch: Create a new file
        - rm, del: Remove a file or directory
        - cp, copy: Copy files or directories
        - mv, move: Move files or directories
        - cat, type: Display file contents
        - pwd: Print working directory
        - echo: Print text to terminal
        - clear, cls: Clear terminal output
        - find, search: Find files and directories
        - grep: Search for text in files
        - chmod: Change file permissions
        - history: Show command history
        - zip, compress: Compress files into a zip archive
        - unzip, extract: Extract files from a zip archive
        - whoami: Show current user information
        - date: Show current date and time
        - bg: Run command in background (not implemented)
        - jobs: List background jobs (not implemented)
        """
        
        self.log(help_text, "info")


    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        self.log(f"Copied to clipboard: {text}", "success")

    def rename_item(self, path):
        """Rename a file or directory"""
        new_name = simpledialog.askstring("Rename", "Enter new name:")
        if new_name:
            try:
                new_path = os.path.join(os.path.dirname(path), new_name)
                os.rename(path, new_path)
                self.log(f"Renamed {path} to {new_path}", "success")
                self.update_directory_tree()
            except Exception as e:
                self.log(f"Error renaming item: {str(e)}", "error")

    def delete_item(self, path):
        """Delete a file or directory"""
        if messagebox.askyesno("Delete", f"Are you sure you want to delete {path}?"):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.log(f"Deleted {path}", "success")
                self.update_directory_tree()
            except Exception as e:
                self.log(f"Error deleting item: {str(e)}", "error")
    
    def clipboard_clear(self):
        """Clear the clipboard"""
        self.clipboard_clear()

        self.clipboard_append("")

    def clipboard_get(self):
        """Get text from the clipboard"""
        try:
            return self.clipboard_get()
        except tk.TclError:
            return ""

    def clipboard_append(self, text):
        """Append text to the clipboard"""
        self.clipboard_clear()
        self.clipboard_append(text)

    def update_idletasks(self):
        """Update the idle tasks"""
        self.update_idletasks()

    def show_error(self, message):  
        """Show an error message"""
        messagebox.showerror("Error", message)
    
    def show_info(self, message):   
        """Show an information message"""
        messagebox.showinfo("Info", message)
    
    def simpledialog(self, title, prompt):  
        """Show a simple dialog for user input"""
        return simpledialog.askstring(title, prompt)
    
    def showwarning(self, message):  
        """Show a warning message"""
        messagebox.showwarning("Warning", message)

    def run_system_command(self, args):
        """Run a system command"""
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0:
                self.log(result.stdout)
            else:
                self.log(f"Error: {result.stderr}", "error")
        except Exception as e:
            self.log(f"Error executing command: {str(e)}", "error")

    def show_about(self):
        """Show about information"""
        about_text = """
        ImprovedMiniShell v1.0
        A simple and enhanced shell interface for Python."""
        messagebox.showinfo("About ImprovedMiniShell", about_text)
    
    def show_license(self):
        """Show license information"""
        license_text = """
        ImprovedMiniShell is licensed under the MIT License."""
        messagebox.showinfo("License", license_text)
    
    def open_settings(self):
        """Open settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        
        # Theme selection
        theme_label = tk.Label(settings_window, text="Select Theme:")
        theme_label.pack(pady=5)
        
        theme_var = tk.StringVar(value=self.current_theme)
        themes = ["light", "dark", "monokai"]
        
        for theme in themes:
            radio_button = tk.Radiobutton(settings_window, text=theme.capitalize(), variable=theme_var, 
                                           value=theme, command=lambda: self.load_theme(theme_var.get()))
            radio_button.pack(anchor=tk.W, padx=10)

        # Close button
        close_button = tk.Button(settings_window, text="Close", command=settings_window.destroy)
        close_button.pack(pady=10)

    def quit(self):
        """Quit the application"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.quit()
        self.root.destroy() 


if __name__ == "__main__":
    root = tk.Tk()
    app = ImprovedMiniShell(root)
    root.mainloop()
