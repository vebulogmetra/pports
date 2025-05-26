#!/usr/bin/env python3
"""
Модуль управления процессами для освобождения портов.
"""

import psutil
import signal
import time
import os
from typing import Optional, List, Dict, Tuple
from enum import Enum
from dataclasses import dataclass


class TerminationResult(Enum):
    """Результат завершения процесса"""
    SUCCESS = "Процесс успешно завершен"
    NOT_FOUND = "Процесс не найден"
    ACCESS_DENIED = "Недостаточно прав для завершения процесса"
    TIMEOUT = "Таймаут при завершении процесса"
    SYSTEM_PROCESS = "Системный процесс - завершение заблокировано"
    ERROR = "Ошибка при завершении процесса"
    ALREADY_TERMINATED = "Процесс уже завершен"


@dataclass
class ProcessTerminationInfo:
    """Информация о завершении процесса"""
    pid: int
    name: str
    result: TerminationResult
    message: str
    duration: float = 0.0


class ProcessManager:
    """Класс для управления процессами и освобождения портов"""
    
    # Список системных процессов, которые нельзя завершать
    PROTECTED_PROCESSES = {
        'systemd', 'kernel', 'kthreadd', 'ksoftirqd', 'migration', 'rcu_', 
        'watchdog', 'systemd-', 'dbus', 'NetworkManager', 'sshd',
        'init', 'swapper', 'idle'
    }
    
    # Системные порты, которые требуют особой осторожности
    SYSTEM_PORTS = {22, 53, 80, 443, 25, 110, 143, 993, 995}
    
    def __init__(self, allow_system_ports: bool = False):
        """
        Инициализация менеджера процессов.
        
        Args:
            allow_system_ports: Разрешить работу с системными портами
        """
        self.allow_system_ports = allow_system_ports
        
    def is_process_protected(self, pid: int) -> bool:
        """
        Проверяет, является ли процесс системным/защищенным.
        
        Args:
            pid: ID процесса
            
        Returns:
            bool: True если процесс защищен от завершения
        """
        try:
            process = psutil.Process(pid)
            process_name = process.name().lower()
            
            # Проверяем имя процесса
            for protected in self.PROTECTED_PROCESSES:
                if protected in process_name:
                    return True
                    
            # Проверяем, не является ли это процессом с PID 1 (init)
            if pid == 1:
                return True
                
            # Проверяем, не является ли это kernel thread
            try:
                if process.ppid() == 2:  # kthreadd
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
            return False
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True  # Если не можем получить информацию, считаем защищенным
    
    def terminate_process_by_pid(self, pid: int, force: bool = False, 
                                timeout: int = 10) -> ProcessTerminationInfo:
        """
        Завершает процесс по PID.
        
        Args:
            pid: ID процесса
            force: Принудительное завершение (SIGKILL)
            timeout: Таймаут ожидания завершения в секундах
            
        Returns:
            ProcessTerminationInfo: Информация о результате операции
        """
        start_time = time.time()
        
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Проверяем, защищен ли процесс
            if self.is_process_protected(pid):
                return ProcessTerminationInfo(
                    pid=pid,
                    name=process_name,
                    result=TerminationResult.SYSTEM_PROCESS,
                    message=f"Процесс {process_name} (PID: {pid}) является системным и защищен от завершения"
                )
            
            # Проверяем, не завершен ли уже процесс
            if not process.is_running():
                return ProcessTerminationInfo(
                    pid=pid,
                    name=process_name,
                    result=TerminationResult.ALREADY_TERMINATED,
                    message=f"Процесс {process_name} (PID: {pid}) уже завершен"
                )
            
            if force:
                # Принудительное завершение
                process.kill()
                signal_used = "SIGKILL"
            else:
                # Мягкое завершение
                process.terminate()
                signal_used = "SIGTERM"
            
            # Ожидаем завершения процесса
            try:
                process.wait(timeout=timeout)
                duration = time.time() - start_time
                
                return ProcessTerminationInfo(
                    pid=pid,
                    name=process_name,
                    result=TerminationResult.SUCCESS,
                    message=f"Процесс {process_name} (PID: {pid}) успешно завершен сигналом {signal_used}",
                    duration=duration
                )
                
            except psutil.TimeoutExpired:
                if not force:
                    # Если мягкое завершение не сработало, пробуем принудительное
                    return self.terminate_process_by_pid(pid, force=True, timeout=timeout//2)
                else:
                    return ProcessTerminationInfo(
                        pid=pid,
                        name=process_name,
                        result=TerminationResult.TIMEOUT,
                        message=f"Таймаут при завершении процесса {process_name} (PID: {pid})"
                    )
                    
        except psutil.NoSuchProcess:
            return ProcessTerminationInfo(
                pid=pid,
                name="Неизвестен",
                result=TerminationResult.NOT_FOUND,
                message=f"Процесс с PID {pid} не найден"
            )
            
        except psutil.AccessDenied:
            return ProcessTerminationInfo(
                pid=pid,
                name="Недоступен",
                result=TerminationResult.ACCESS_DENIED,
                message=f"Недостаточно прав для завершения процесса PID {pid}. Попробуйте запустить с правами администратора."
            )
            
        except Exception as e:
            return ProcessTerminationInfo(
                pid=pid,
                name="Ошибка",
                result=TerminationResult.ERROR,
                message=f"Ошибка при завершении процесса PID {pid}: {str(e)}"
            )
    
    def terminate_process_by_port(self, port: int, protocol: str = "tcp", 
                                 force: bool = False) -> List[ProcessTerminationInfo]:
        """
        Завершает все процессы, использующие указанный порт.
        
        Args:
            port: Номер порта
            protocol: Протокол (tcp/udp)
            force: Принудительное завершение
            
        Returns:
            List[ProcessTerminationInfo]: Список результатов завершения процессов
        """
        # Проверяем системные порты
        if port in self.SYSTEM_PORTS and not self.allow_system_ports:
            return [ProcessTerminationInfo(
                pid=0,
                name="Системный порт",
                result=TerminationResult.SYSTEM_PROCESS,
                message=f"Порт {port} является системным. Для работы с ним включите allow_system_ports=True"
            )]
        
        # Импортируем сканер портов
        from .port_scanner import PortScanner
        
        scanner = PortScanner()
        ports_info = scanner.find_port_by_number(port, protocol)
        
        if not ports_info:
            return [ProcessTerminationInfo(
                pid=0,
                name="Не найден",
                result=TerminationResult.NOT_FOUND,
                message=f"Порт {protocol.upper()}:{port} не используется"
            )]
        
        results = []
        for port_info in ports_info:
            if port_info.pid:
                result = self.terminate_process_by_pid(port_info.pid, force)
                results.append(result)
            else:
                results.append(ProcessTerminationInfo(
                    pid=0,
                    name="Неизвестен",
                    result=TerminationResult.NOT_FOUND,
                    message=f"Не удалось определить процесс для порта {protocol.upper()}:{port}"
                ))
        
        return results
    
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """
        Получает подробную информацию о процессе.
        
        Args:
            pid: ID процесса
            
        Returns:
            Optional[Dict]: Информация о процессе или None
        """
        try:
            process = psutil.Process(pid)
            
            return {
                'pid': pid,
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': process.cmdline(),
                'username': process.username(),
                'create_time': process.create_time(),
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'status': process.status(),
                'num_threads': process.num_threads(),
                'is_protected': self.is_process_protected(pid)
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def list_processes_by_port_range(self, start_port: int, end_port: int) -> Dict[int, List[Dict]]:
        """
        Получает список процессов, использующих порты в указанном диапазоне.
        
        Args:
            start_port: Начальный порт
            end_port: Конечный порт
            
        Returns:
            Dict[int, List[Dict]]: Словарь {порт: [список процессов]}
        """
        from .port_scanner import PortScanner
        
        scanner = PortScanner()
        ports_info = scanner.scan_port_range(start_port, end_port)
        
        result = {}
        for port_info in ports_info:
            if port_info.pid:
                process_info = self.get_process_info(port_info.pid)
                if process_info:
                    if port_info.port not in result:
                        result[port_info.port] = []
                    result[port_info.port].append(process_info)
        
        return result


def main():
    """Тестовая функция для демонстрации работы менеджера процессов"""
    manager = ProcessManager()
    
    print("=== Тестирование Process Manager ===")
    
    # Получаем список процессов на портах 1-1024
    print("\nПроцессы на системных портах (1-1024):")
    processes_by_port = manager.list_processes_by_port_range(1, 1024)
    
    for port, processes in list(processes_by_port.items())[:5]:  # Показываем первые 5
        for proc in processes:
            protected = "🛡️" if proc['is_protected'] else "✅"
            print(f"  Порт {port}: {proc['name']} (PID: {proc['pid']}) {protected}")
    
    print(f"\nВсего портов с процессами: {len(processes_by_port)}")
    
    # Демонстрация проверки защищенных процессов
    print("\nПроверка защищенных процессов:")
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if manager.is_process_protected(proc.info['pid']):
                print(f"  🛡️ {proc.info['name']} (PID: {proc.info['pid']}) - ЗАЩИЩЕН")
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


if __name__ == "__main__":
    main() 