#!/usr/bin/env python3
"""
CLI интерфейс для PPORTS - тестирование функционала перед созданием GUI.
"""

import sys
import argparse
from typing import List
from core.port_scanner import PortScanner, ConnectionStatus
from core.process_manager import ProcessManager, TerminationResult


def format_port_info(port_info, show_details=False):
    """Форматирует информацию о порте для вывода"""
    status_emoji = {
        ConnectionStatus.LISTEN: "🟢",
        ConnectionStatus.ESTABLISHED: "🔵", 
        ConnectionStatus.TIME_WAIT: "🟡",
        ConnectionStatus.CLOSE_WAIT: "🟠",
    }
    
    emoji = status_emoji.get(port_info.status, "⚫")
    
    basic_info = (f"{emoji} {port_info.protocol}:{port_info.port} "
                 f"[{port_info.status.value}] - "
                 f"{port_info.process_name or 'Неизвестно'} "
                 f"(PID: {port_info.pid or 'N/A'})")
    
    if show_details and port_info.pid:
        details = (f"\n    Адрес: {port_info.local_addr}"
                  f"\n    Пользователь: {port_info.process_username or 'N/A'}"
                  f"\n    Команда: {port_info.process_cmdline or 'N/A'}")
        return basic_info + details
    
    return basic_info


def cmd_scan_all(args):
    """Команда сканирования всех портов"""
    scanner = PortScanner()
    
    print("🔍 Сканирование всех активных портов...")
    ports = scanner.scan_all_ports()
    
    if not ports:
        print("❌ Порты не найдены или недостаточно прав доступа")
        return
    
    print(f"\n📊 Найдено портов: {len(ports)}")
    
    if args.listening_only:
        ports = [p for p in ports if p.status == ConnectionStatus.LISTEN]
        print(f"📊 Прослушиваемых портов: {len(ports)}")
    
    # Группируем по протоколам
    tcp_ports = [p for p in ports if p.protocol == 'TCP']
    udp_ports = [p for p in ports if p.protocol == 'UDP']
    
    if tcp_ports:
        print(f"\n🔷 TCP порты ({len(tcp_ports)}):")
        for port in tcp_ports[:args.limit]:
            print(f"  {format_port_info(port, args.details)}")
        if len(tcp_ports) > args.limit:
            print(f"  ... и еще {len(tcp_ports) - args.limit} портов")
    
    if udp_ports:
        print(f"\n🔶 UDP порты ({len(udp_ports)}):")
        for port in udp_ports[:args.limit]:
            print(f"  {format_port_info(port, args.details)}")
        if len(udp_ports) > args.limit:
            print(f"  ... и еще {len(udp_ports) - args.limit} портов")


def cmd_scan_port(args):
    """Команда сканирования конкретного порта"""
    scanner = PortScanner()
    
    print(f"🔍 Поиск информации о порте {args.protocol.upper()}:{args.port}...")
    ports = scanner.find_port_by_number(args.port, args.protocol)
    
    if not ports:
        print(f"❌ Порт {args.protocol.upper()}:{args.port} не используется")
        return
    
    print(f"✅ Найдено соединений: {len(ports)}")
    for port in ports:
        print(f"  {format_port_info(port, True)}")


def cmd_scan_range(args):
    """Команда сканирования диапазона портов"""
    scanner = PortScanner()
    
    print(f"🔍 Сканирование портов {args.start}-{args.end} ({args.protocol.upper()})...")
    ports = scanner.scan_port_range(args.start, args.end, args.protocol)
    
    if not ports:
        print(f"❌ В диапазоне {args.start}-{args.end} активных {args.protocol.upper()} портов не найдено")
        return
    
    print(f"✅ Найдено портов: {len(ports)}")
    for port in ports:
        print(f"  {format_port_info(port, args.details)}")


def cmd_terminate(args):
    """Команда завершения процесса"""
    manager = ProcessManager(allow_system_ports=args.allow_system)
    
    if args.pid:
        print(f"⚠️  Завершение процесса PID {args.pid}...")
        if not args.force and not confirm_action(f"завершить процесс PID {args.pid}"):
            return
        
        result = manager.terminate_process_by_pid(args.pid, args.force)
        print_termination_result(result)
        
    elif args.port:
        protocol = args.protocol or 'tcp'
        print(f"⚠️  Завершение процессов на порту {protocol.upper()}:{args.port}...")
        
        # Сначала покажем что будет завершено
        scanner = PortScanner()
        ports = scanner.find_port_by_number(args.port, protocol)
        
        if not ports:
            print(f"❌ Порт {protocol.upper()}:{args.port} не используется")
            return
        
        print("Будут завершены процессы:")
        for port in ports:
            if port.pid:
                protected = "🛡️" if manager.is_process_protected(port.pid) else "✅"
                print(f"  {protected} {port.process_name} (PID: {port.pid})")
        
        if not args.force and not confirm_action(f"завершить процессы на порту {protocol.upper()}:{args.port}"):
            return
        
        results = manager.terminate_process_by_port(args.port, protocol, args.force)
        for result in results:
            print_termination_result(result)


def print_termination_result(result):
    """Выводит результат завершения процесса"""
    emoji_map = {
        TerminationResult.SUCCESS: "✅",
        TerminationResult.NOT_FOUND: "❌",
        TerminationResult.ACCESS_DENIED: "🔒",
        TerminationResult.TIMEOUT: "⏰",
        TerminationResult.SYSTEM_PROCESS: "🛡️",
        TerminationResult.ERROR: "💥",
        TerminationResult.ALREADY_TERMINATED: "☠️"
    }
    
    emoji = emoji_map.get(result.result, "❓")
    print(f"  {emoji} {result.message}")
    
    if result.duration > 0:
        print(f"    ⏱️  Время: {result.duration:.2f}с")


def confirm_action(action_description):
    """Запрашивает подтверждение действия"""
    response = input(f"❓ Вы уверены, что хотите {action_description}? (да/нет): ").lower()
    return response in ['да', 'yes', 'y', 'д']


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description="PPORTS CLI - Управление портами и процессами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s scan --all                    # Все активные порты
  %(prog)s scan --all --listening        # Только прослушиваемые порты
  %(prog)s scan --port 80                # Информация о порте 80
  %(prog)s scan --range 8000 9000        # Порты в диапазоне 8000-9000
  %(prog)s kill --port 8080              # Завершить процессы на порту 8080
  %(prog)s kill --pid 1234               # Завершить процесс PID 1234
  %(prog)s kill --port 22 --force        # Принудительно завершить SSH
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда scan
    scan_parser = subparsers.add_parser('scan', help='Сканирование портов')
    scan_group = scan_parser.add_mutually_exclusive_group(required=True)
    scan_group.add_argument('--all', action='store_true', help='Сканировать все порты')
    scan_group.add_argument('--port', type=int, help='Сканировать конкретный порт')
    scan_group.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help='Диапазон портов')
    
    scan_parser.add_argument('--protocol', choices=['tcp', 'udp'], default='tcp', help='Протокол (по умолчанию: tcp)')
    scan_parser.add_argument('--listening', dest='listening_only', action='store_true', help='Только прослушиваемые порты')
    scan_parser.add_argument('--details', action='store_true', help='Подробная информация')
    scan_parser.add_argument('--limit', type=int, default=20, help='Лимит выводимых портов (по умолчанию: 20)')
    
    # Команда kill
    kill_parser = subparsers.add_parser('kill', help='Завершение процессов')
    kill_group = kill_parser.add_mutually_exclusive_group(required=True)
    kill_group.add_argument('--pid', type=int, help='PID процесса для завершения')
    kill_group.add_argument('--port', type=int, help='Порт для освобождения')
    
    kill_parser.add_argument('--protocol', choices=['tcp', 'udp'], help='Протокол (для --port)')
    kill_parser.add_argument('--force', action='store_true', help='Принудительное завершение (SIGKILL)')
    kill_parser.add_argument('--allow-system', action='store_true', help='Разрешить работу с системными портами')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'scan':
            if args.all:
                cmd_scan_all(args)
            elif args.port:
                cmd_scan_port(args)
            elif args.range:
                args.start, args.end = args.range
                cmd_scan_range(args)
        
        elif args.command == 'kill':
            cmd_terminate(args)
            
    except KeyboardInterrupt:
        print("\n\n⚡ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 