#!/usr/bin/env python3
"""
Модуль сканирования портов и получения информации о сетевых соединениях.
"""

import psutil
import socket
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ConnectionStatus(Enum):
    """Статус сетевого соединения"""
    LISTEN = "LISTEN"
    ESTABLISHED = "ESTABLISHED" 
    CLOSE_WAIT = "CLOSE_WAIT"
    TIME_WAIT = "TIME_WAIT"
    SYN_SENT = "SYN_SENT"
    SYN_RECV = "SYN_RECV"
    FIN_WAIT1 = "FIN_WAIT1"
    FIN_WAIT2 = "FIN_WAIT2"
    CLOSING = "CLOSING"
    LAST_ACK = "LAST_ACK"
    UNKNOWN = "UNKNOWN"


@dataclass
class PortInfo:
    """Информация о порте и связанном процессе"""
    port: int
    protocol: str
    status: ConnectionStatus
    local_addr: str
    remote_addr: Optional[str]
    remote_port: Optional[int]
    pid: Optional[int]
    process_name: Optional[str]
    process_exe: Optional[str]
    process_cmdline: Optional[str]
    process_username: Optional[str]
    process_create_time: Optional[float]


class PortScanner:
    """Класс для сканирования портов и получения информации о процессах"""
    
    def __init__(self):
        self._status_mapping = {
            psutil.CONN_LISTEN: ConnectionStatus.LISTEN,
            psutil.CONN_ESTABLISHED: ConnectionStatus.ESTABLISHED,
            psutil.CONN_CLOSE_WAIT: ConnectionStatus.CLOSE_WAIT,
            psutil.CONN_TIME_WAIT: ConnectionStatus.TIME_WAIT,
            psutil.CONN_SYN_SENT: ConnectionStatus.SYN_SENT,
            psutil.CONN_SYN_RECV: ConnectionStatus.SYN_RECV,
            psutil.CONN_FIN_WAIT1: ConnectionStatus.FIN_WAIT1,
            psutil.CONN_FIN_WAIT2: ConnectionStatus.FIN_WAIT2,
            psutil.CONN_CLOSING: ConnectionStatus.CLOSING,
            psutil.CONN_LAST_ACK: ConnectionStatus.LAST_ACK,
        }
    
    def scan_all_ports(self) -> list[PortInfo]:
        """
        Сканирует все активные порты в системе.
        
        Returns:
            List[PortInfo]: Список информации о всех активных портах
        """
        ports = []
        
        # Получаем все сетевые соединения
        try:
            connections = psutil.net_connections(kind='inet')
        except psutil.AccessDenied:
            # Если нет прав, попробуем получить только TCP соединения
            try:
                connections = psutil.net_connections(kind='tcp')
            except psutil.AccessDenied:
                return []
        
        for conn in connections:
            try:
                port_info = self._process_connection(conn)
                if port_info:
                    ports.append(port_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Процесс мог завершиться или быть недоступным
                continue
        
        return sorted(ports, key=lambda x: (x.protocol, x.port))
    
    def scan_listening_ports(self) -> list[PortInfo]:
        """
        Сканирует только прослушиваемые (LISTEN) порты.
        
        Returns:
            List[PortInfo]: Список информации о прослушиваемых портах
        """
        all_ports = self.scan_all_ports()
        return [port for port in all_ports if port.status == ConnectionStatus.LISTEN]
    
    def scan_port_range(self, start_port: int, end_port: int, protocol: str = 'tcp') -> list[PortInfo]:
        """
        Сканирует определенный диапазон портов.
        
        Args:
            start_port: Начальный порт
            end_port: Конечный порт  
            protocol: Протокол ('tcp' или 'udp')
            
        Returns:
            List[PortInfo]: Список информации о портах в диапазоне
        """
        all_ports = self.scan_all_ports()
        return [
            port for port in all_ports 
            if start_port <= port.port <= end_port and port.protocol.lower() == protocol.lower()
        ]
    
    def find_port_by_number(self, port_number: int, protocol: str = None) -> list[PortInfo]:
        """
        Ищет информацию о конкретном порте.
        
        Args:
            port_number: Номер порта
            protocol: Протокол (опционально)
            
        Returns:
            List[PortInfo]: Список информации о найденных портах
        """
        all_ports = self.scan_all_ports()
        result = [port for port in all_ports if port.port == port_number]
        
        if protocol:
            result = [port for port in result if port.protocol.lower() == protocol.lower()]
            
        return result
    
    def _process_connection(self, conn) -> Optional[PortInfo]:
        """
        Обрабатывает одно сетевое соединение и извлекает информацию.
        
        Args:
            conn: Объект соединения от psutil
            
        Returns:
            Optional[PortInfo]: Информация о порте или None
        """
        if not conn.laddr:
            return None
            
        local_addr = conn.laddr.ip if conn.laddr else None
        local_port = conn.laddr.port if conn.laddr else None
        remote_addr = conn.raddr.ip if conn.raddr else None
        remote_port = conn.raddr.port if conn.raddr else None
        
        # Определяем статус соединения
        status = self._status_mapping.get(conn.status, ConnectionStatus.UNKNOWN)
        
        # Определяем протокол
        protocol = 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP'
        
        # Получаем информацию о процессе
        process_info = self._get_process_info(conn.pid)
        
        return PortInfo(
            port=local_port,
            protocol=protocol,
            status=status,
            local_addr=local_addr,
            remote_addr=remote_addr,
            remote_port=remote_port,
            **process_info
        )
    
    def _get_process_info(self, pid: Optional[int]) -> dict[str, Optional[str]]:
        """
        Получает информацию о процессе по PID.
        
        Args:
            pid: ID процесса
            
        Returns:
            Dict: Словарь с информацией о процессе
        """
        if pid is None:
            return {
                'pid': None,
                'process_name': None,
                'process_exe': None,
                'process_cmdline': None,
                'process_username': None,
                'process_create_time': None
            }
        
        try:
            process = psutil.Process(pid)
            return {
                'pid': pid,
                'process_name': process.name(),
                'process_exe': process.exe(),
                'process_cmdline': ' '.join(process.cmdline()),
                'process_username': process.username(),
                'process_create_time': process.create_time()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {
                'pid': pid,
                'process_name': f"PID:{pid} (недоступен)",
                'process_exe': None,
                'process_cmdline': None,
                'process_username': None,
                'process_create_time': None
            }


def main():
    """Тестовая функция для демонстрации работы сканера"""
    scanner = PortScanner()
    
    print("=== Все активные порты ===")
    all_ports = scanner.scan_all_ports()
    for port in all_ports[:10]:  # Показываем первые 10
        print(f"{port.protocol}:{port.port} - {port.process_name} (PID: {port.pid}) - {port.status.value}")
    
    print(f"\nВсего найдено портов: {len(all_ports)}")
    
    print("\n=== Прослушиваемые порты ===")
    listening_ports = scanner.scan_listening_ports()
    for port in listening_ports:
        print(f"{port.protocol}:{port.port} - {port.process_name} (PID: {port.pid})")
    
    print(f"\nВсего прослушиваемых портов: {len(listening_ports)}")


if __name__ == "__main__":
    main() 