#!/usr/bin/env python3
"""
Главная точка входа приложения PPORTS.
"""

import sys
import argparse
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Главная функция приложения"""
    parser = argparse.ArgumentParser(
        description="PPORTS - Управление портами и процессами",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--cli", 
        action="store_true", 
        help="Запустить в режиме командной строки"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Запустить GUI интерфейс (по умолчанию)"
    )
    
    # Если переданы аргументы для CLI, парсим их отдельно
    if len(sys.argv) > 1 and not any(arg in ['--gui', '--cli'] for arg in sys.argv):
        # Предполагаем что это команды для CLI
        run_cli()
        return
    
    args, remaining = parser.parse_known_args()
    
    if args.cli:
        # Запуск CLI с оставшимися аргументами
        sys.argv = [sys.argv[0]] + remaining
        run_cli()
    else:
        # Запуск GUI (по умолчанию)
        run_gui()


def run_gui():
    """Запуск GUI интерфейса"""
    try:
        from gui.main_window import main as gui_main
        print("🚀 Запуск PPORTS GUI...")
        gui_main()
    except ImportError as e:
        print(f"❌ Ошибка импорта GUI: {e}")
        print("Убедитесь, что установлен customtkinter: pip install customtkinter")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Ошибка при запуске GUI: {e}")
        sys.exit(1)


def run_cli():
    """Запуск CLI интерфейса"""
    try:
        from cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"❌ Ошибка импорта CLI: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Ошибка при запуске CLI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 