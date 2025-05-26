# Makefile для PPORTS - Port Management Tool
.PHONY: help install test clean build appimage run run-cli

# По умолчанию показать справку
help:
	@echo "🚀 PPORTS - Makefile команды"
	@echo "============================"
	@echo ""
	@echo "Основные команды:"
	@echo "  install     - Установить зависимости"
	@echo "  test        - Запустить тесты"
	@echo "  run         - Запустить GUI версию"
	@echo "  run-cli     - Запустить CLI версию"
	@echo "  build       - Собрать с PyInstaller"
	@echo "  appimage    - Создать AppImage"
	@echo "  clean       - Очистить временные файлы"
	@echo ""
	@echo "Пример использования:"
	@echo "  make install"
	@echo "  make run"
	@echo "  make appimage"

# Установка зависимостей
install:
	@echo "📦 Устанавливаю зависимости..."
	pip install -r requirements.txt

# Установка зависимостей для сборки
install-build:
	@echo "🔧 Устанавливаю зависимости для сборки..."
	pip install -r requirements-build.txt

# Запуск GUI версии
run:
	@echo "🖥️ Запускаю PPORTS GUI..."
	cd src && python main.py

# Запуск CLI версии
run-cli:
	@echo "💻 Запускаю PPORTS CLI..."
	cd src && python cli.py --help

# Сборка с PyInstaller
build: install-build
	@echo "🔨 Собираю приложение..."
	pyinstaller --clean \
		--onefile \
		--add-data "assets/pports.svg:assets" \
		--add-data "README.md:." \
		--add-data "src/core:core" \
		--add-data "src/gui:gui" \
		--path src \
		--exclude-module matplotlib \
		--exclude-module numpy \
		--exclude-module pandas \
		--exclude-module scipy \
		--exclude-module IPython \
		--exclude-module jupyter \
		--name pports-gui \
		--windowed \
		--noconfirm \
		src/main.py
	pyinstaller --clean \
		--onefile \
		--add-data "src/core:core" \
		--path src \
		--exclude-module matplotlib \
		--exclude-module numpy \
		--exclude-module pandas \
		--exclude-module scipy \
		--exclude-module IPython \
		--exclude-module jupyter \
		--exclude-module tkinter \
		--exclude-module customtkinter \
		--name pports-cli \
		--console \
		--noconfirm \
		src/cli.py

# Создание AppImage
appimage:
	@echo "📦 Создаю AppImage..."
	./build_appimage.sh

# Быстрый AppImage без очистки (для отладки)
appimage-debug:
	@echo "🐛 Создаю AppImage (режим отладки)..."
	./build_appimage.sh --no-cleanup

# Очистка временных файлов
clean:
	@echo "🧹 Очищаю временные файлы..."
	rm -rf build/ dist/ *.spec
	rm -rf AppDir/ *.AppImage appimagetool
	rm -rf build_env/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Форматирование кода
format:
	@echo "✨ Форматирую код..."
	black src/ tests/

# Проверка кода
lint:
	@echo "🔍 Проверяю код..."
	flake8 src/ tests/

# Установка для разработки
dev-install: install-build
	@echo "👨‍💻 Настройка для разработки..."
	pip install -e .

# Создание документации
docs:
	@echo "📚 Создаю документацию..."
	@echo "Документация создается автоматически в процессе сборки."

# Проверка готовности к релизу
check: test lint
	@echo "✅ Проверка готовности к релизу..."
	@echo "Все проверки пройдены!"

# Полная сборка для релиза
release: clean check build appimage
	@echo "🎉 Релиз готов!"
	@ls -la *.AppImage 