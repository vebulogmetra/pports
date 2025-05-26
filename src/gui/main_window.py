#!/usr/bin/env python3
"""
Главное окно GUI для PPORTS.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading
import time
from typing import List, Optional
from core.port_scanner import PortScanner, PortInfo, ConnectionStatus
from core.process_manager import ProcessManager, TerminationResult


# Настройка CustomTkinter
ctk.set_appearance_mode("system")  # "light", "dark", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


class PortListFrame(ctk.CTkFrame):
    """Фрейм со списком портов"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.setup_ui()
        self.ports_data: List[PortInfo] = []
        
    def setup_ui(self):
        """Настройка интерфейса фрейма"""
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self, 
            text="📋 Активные Порты", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))
        
        # Фрейм с фильтрами
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(fill="x", padx=10, pady=5)
        
        # Фильтр по протоколу
        self.protocol_label = ctk.CTkLabel(self.filter_frame, text="Протокол:")
        self.protocol_label.pack(side="left", padx=(10, 5))
        
        self.protocol_var = tk.StringVar(value="Все")
        self.protocol_combo = ctk.CTkComboBox(
            self.filter_frame,
            values=["Все", "TCP", "UDP"],
            variable=self.protocol_var,
            command=self.on_filter_change
        )
        self.protocol_combo.pack(side="left", padx=5)
        
        # Фильтр по статусу
        self.status_label = ctk.CTkLabel(self.filter_frame, text="Статус:")
        self.status_label.pack(side="left", padx=(20, 5))
        
        self.status_var = tk.StringVar(value="Все")
        self.status_combo = ctk.CTkComboBox(
            self.filter_frame,
            values=["Все", "LISTEN", "ESTABLISHED", "TIME_WAIT"],
            variable=self.status_var,
            command=self.on_filter_change
        )
        self.status_combo.pack(side="left", padx=5)
        
        # Поиск по порту
        self.search_label = ctk.CTkLabel(self.filter_frame, text="Порт:")
        self.search_label.pack(side="left", padx=(20, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        self.search_entry = ctk.CTkEntry(
            self.filter_frame,
            textvariable=self.search_var,
            placeholder_text="Номер порта",
            width=100
        )
        self.search_entry.pack(side="left", padx=5)
        
        # Кнопка обновления
        self.refresh_btn = ctk.CTkButton(
            self.filter_frame,
            text="🔄",
            width=40,
            command=self.refresh_ports
        )
        self.refresh_btn.pack(side="right", padx=10)
        
        # Список портов (Treeview)
        self.setup_treeview()
        
    def setup_treeview(self):
        """Настройка таблицы портов"""
        # Создаем фрейм для таблицы и скроллбара
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Создаем Treeview
        columns = ("Port", "Protocol", "Status", "Process", "PID", "User")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=15)
        
        # Настройка заголовков
        self.tree.heading("Port", text="Порт")
        self.tree.heading("Protocol", text="Протокол")
        self.tree.heading("Status", text="Статус")
        self.tree.heading("Process", text="Процесс")
        self.tree.heading("PID", text="PID")
        self.tree.heading("User", text="Пользователь")
        
        # Настройка ширины колонок
        self.tree.column("Port", width=80)
        self.tree.column("Protocol", width=80)
        self.tree.column("Status", width=100)
        self.tree.column("Process", width=200)
        self.tree.column("PID", width=80)
        self.tree.column("User", width=120)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Настройка цветов для тегов статусов
        self.tree.tag_configure("LISTEN", foreground="green")
        self.tree.tag_configure("ESTABLISHED", foreground="blue")
        self.tree.tag_configure("TIME_WAIT", foreground="orange")
        self.tree.tag_configure("CLOSE_WAIT", foreground="red")
        
        # Привязка событий
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)  # Правый клик
        
        # Контекстное меню
        self.create_context_menu()
        
    def create_context_menu(self):
        """Создает контекстное меню"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="📋 Показать детали", command=self.show_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⚠️ Завершить процесс", command=self.terminate_process)
        self.context_menu.add_command(label="💥 Принудительно завершить", command=self.force_terminate_process)
        
    def on_filter_change(self, value=None):
        """Обработчик изменения фильтров"""
        self.apply_filters()
        
    def on_search_change(self, *args):
        """Обработчик изменения поиска"""
        self.apply_filters()
        
    def apply_filters(self):
        """Применяет фильтры к списку портов"""
        if not self.ports_data:
            return
            
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Фильтруем данные
        filtered_ports = self.ports_data.copy()
        
        # Фильтр по протоколу
        protocol_filter = self.protocol_var.get()
        if protocol_filter != "Все":
            filtered_ports = [p for p in filtered_ports if p.protocol == protocol_filter]
            
        # Фильтр по статусу
        status_filter = self.status_var.get()
        if status_filter != "Все":
            filtered_ports = [p for p in filtered_ports if p.status.value == status_filter]
            
        # Поиск по порту
        search_text = self.search_var.get().strip()
        if search_text:
            try:
                port_number = int(search_text)
                filtered_ports = [p for p in filtered_ports if p.port == port_number]
            except ValueError:
                # Если не число, ищем в названии процесса
                filtered_ports = [p for p in filtered_ports 
                                if search_text.lower() in (p.process_name or "").lower()]
        
        # Заполняем таблицу
        self.populate_tree(filtered_ports)
        
    def populate_tree(self, ports: List[PortInfo]):
        """Заполняет таблицу данными о портах"""
        for port in ports:
            # Определяем цвет для статуса
            status_colors = {
                ConnectionStatus.LISTEN: "green",
                ConnectionStatus.ESTABLISHED: "blue",
                ConnectionStatus.TIME_WAIT: "orange",
                ConnectionStatus.CLOSE_WAIT: "red"
            }
            
            item = self.tree.insert("", "end", values=(
                port.port,
                port.protocol,
                port.status.value,
                port.process_name or "Неизвестно",
                port.pid or "N/A",
                port.process_username or "N/A"
            ))
            
            # Устанавливаем теги для цветовой кодировки
            if port.status in status_colors:
                self.tree.item(item, tags=(port.status.value,))
        
    def refresh_ports(self):
        """Обновляет список портов"""
        # Запускаем сканирование в отдельном потоке
        self.refresh_btn.configure(state="disabled", text="⏳")
        
        def scan_thread():
            try:
                scanner = PortScanner()
                self.ports_data = scanner.scan_all_ports()
                
                # Обновляем UI в главном потоке
                self.after(0, self.on_scan_complete)
            except Exception as e:
                self.after(0, lambda: self.on_scan_error(str(e)))
                
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def on_scan_complete(self):
        """Вызывается после завершения сканирования"""
        self.refresh_btn.configure(state="normal", text="🔄")
        self.apply_filters()
        
    def on_scan_error(self, error_message):
        """Вызывается при ошибке сканирования"""
        self.refresh_btn.configure(state="normal", text="🔄")
        messagebox.showerror("Ошибка", f"Ошибка при сканировании портов:\n{error_message}")
        
    def get_selected_port(self) -> Optional[PortInfo]:
        """Возвращает информацию о выбранном порте"""
        selection = self.tree.selection()
        if not selection:
            return None
            
        item = selection[0]
        port_number = int(self.tree.item(item)["values"][0])
        protocol = self.tree.item(item)["values"][1]
        
        # Ищем в данных
        for port in self.ports_data:
            if port.port == port_number and port.protocol == protocol:
                return port
        return None
        
    def on_item_double_click(self, event):
        """Обработчик двойного клика"""
        self.show_details()
        
    def on_right_click(self, event):
        """Обработчик правого клика"""
        # Выбираем элемент под курсором
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
            
    def show_details(self):
        """Показывает детальную информацию о порте"""
        port = self.get_selected_port()
        if not port:
            messagebox.showwarning("Предупреждение", "Выберите порт для просмотра деталей")
            return
            
        details = f"""
📋 Информация о порте

🔌 Порт: {port.protocol}:{port.port}
📊 Статус: {port.status.value}
🏠 Локальный адрес: {port.local_addr}
🌐 Удаленный адрес: {port.remote_addr or 'N/A'}

🔧 Процесс: {port.process_name or 'Неизвестно'}
🆔 PID: {port.pid or 'N/A'}
👤 Пользователь: {port.process_username or 'N/A'}
📁 Исполняемый файл: {port.process_exe or 'N/A'}
⚡ Командная строка: {port.process_cmdline or 'N/A'}
        """.strip()
        
        messagebox.showinfo("Детали порта", details)
        
    def terminate_process(self):
        """Завершает процесс (мягко)"""
        self._terminate_process(force=False)
        
    def force_terminate_process(self):
        """Принудительно завершает процесс"""
        self._terminate_process(force=True)
        
    def _terminate_process(self, force=False):
        """Внутренний метод завершения процесса"""
        port = self.get_selected_port()
        if not port:
            messagebox.showwarning("Предупреждение", "Выберите порт для завершения процесса")
            return
            
        if not port.pid:
            messagebox.showerror("Ошибка", "Не удалось определить PID процесса")
            return
            
        # Подтверждение
        action = "принудительно завершить" if force else "завершить"
        if not messagebox.askyesno(
            "Подтверждение", 
            f"Вы уверены, что хотите {action} процесс?\n\n"
            f"Процесс: {port.process_name}\n"
            f"PID: {port.pid}\n"
            f"Порт: {port.protocol}:{port.port}"
        ):
            return
            
        # Завершаем процесс в отдельном потоке
        def terminate_thread():
            try:
                manager = ProcessManager()
                result = manager.terminate_process_by_pid(port.pid, force)
                self.after(0, lambda: self.on_terminate_complete(result))
            except Exception as e:
                self.after(0, lambda: self.on_terminate_error(str(e)))
                
        threading.Thread(target=terminate_thread, daemon=True).start()
        
    def on_terminate_complete(self, result):
        """Вызывается после завершения процесса"""
        if result.result == TerminationResult.SUCCESS:
            messagebox.showinfo("Успех", result.message)
            self.refresh_ports()  # Обновляем список
        else:
            messagebox.showerror("Ошибка", result.message)
            
    def on_terminate_error(self, error_message):
        """Вызывается при ошибке завершения процесса"""
        messagebox.showerror("Ошибка", f"Ошибка при завершении процесса:\n{error_message}")


class MainWindow(ctk.CTk):
    """Главное окно приложения PPORTS"""
    
    def __init__(self):
        super().__init__()
        
        self.title("PPORTS - Управление Портами")
        self.geometry("1000x700")
        
        # Иконка (если есть)
        try:
            self.iconbitmap("assets/icon.ico")
        except:
            pass  # Игнорируем если иконки нет
            
        self.setup_ui()
        
        # Автоматическое обновление при запуске
        self.after(1000, self.initial_scan)
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Заголовок приложения
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🚀 PPORTS - Управление Портами и Процессами",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)
        
        # Основной контент
        self.port_list_frame = PortListFrame(self)
        self.port_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Статус бар
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="🔄 Готов к работе",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.count_label = ctk.CTkLabel(
            self.status_frame,
            text="Портов: 0",
            font=ctk.CTkFont(size=12)
        )
        self.count_label.pack(side="right", padx=10, pady=5)
        
    def initial_scan(self):
        """Первоначальное сканирование"""
        self.status_label.configure(text="🔍 Сканирование портов...")
        self.port_list_frame.refresh_ports()
        
    def update_status(self, message: str, port_count: int = 0):
        """Обновляет статус бар"""
        self.status_label.configure(text=message)
        self.count_label.configure(text=f"Портов: {port_count}")


def main():
    """Главная функция для запуска GUI"""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main() 