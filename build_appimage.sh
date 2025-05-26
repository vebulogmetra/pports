#!/bin/bash
# Скрипт сборки PPORTS в AppImage формат
# Требует: appimagetool, python3, pip

set -e  # Прерывать при ошибках

echo "🔧 Начинаю сборку PPORTS AppImage..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверяем зависимости
check_dependencies() {
    echo "📋 Проверяю зависимости..."
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 не найден${NC}"
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}❌ pip3 не найден${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Зависимости проверены${NC}"
}

# Создаем директории для сборки
setup_directories() {
    echo "📁 Создаю структуру директорий..."
    
    # Удаляем старые артефакты сборки
    rm -rf build dist AppDir *.AppImage appimagetool
    rm -rf build_env .build_env
    
    # Очищаем __pycache__ 
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Создаем новую структуру
    mkdir -p AppDir/usr/bin
    mkdir -p AppDir/usr/share/applications
    mkdir -p AppDir/usr/share/pixmaps
    mkdir -p AppDir/usr/lib/python3/site-packages
    
    echo -e "${GREEN}✅ Директории созданы и очищены${NC}"
}

# Устанавливаем зависимости
install_dependencies() {
    echo "📦 Устанавливаю зависимости..."
    
    # Создаем виртуальное окружение для изоляции
    python3 -m venv build_env
    source build_env/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install pyinstaller
    
    echo -e "${GREEN}✅ Зависимости установлены${NC}"
}

# Собираем приложение с PyInstaller
build_with_pyinstaller() {
    echo "🔨 Собираю приложение с PyInstaller..."
    
    source build_env/bin/activate
    
    # Собираем GUI версию
    pyinstaller --clean --onefile \
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
        --exclude-module PIL \
        --exclude-module Pillow \
        --exclude-module opencv \
        --exclude-module tensorflow \
        --exclude-module torch \
        --name pports-gui \
        --windowed \
        --noconfirm \
        src/main.py
    
    # Собираем CLI версию
    pyinstaller --clean --onefile \
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
        --exclude-module PIL \
        --exclude-module Pillow \
        --exclude-module opencv \
        --exclude-module tensorflow \
        --exclude-module torch \
        --name pports-cli \
        --console \
        --noconfirm \
        src/cli.py
    
    echo -e "${GREEN}✅ Приложения собраны${NC}"
}

# Подготавливаем AppDir
prepare_appdir() {
    echo "📋 Подготавливаю AppDir..."
    
    # Копируем исполняемые файлы
    cp dist/pports-gui AppDir/usr/bin/
    cp dist/pports-cli AppDir/usr/bin/
    
    # Создаем символическую ссылку для основного исполняемого файла
    ln -sf usr/bin/pports-gui AppDir/AppRun
    
    # Копируем .desktop файл
    cp assets/pports.desktop AppDir/
    cp assets/pports.desktop AppDir/usr/share/applications/
    
    # Копируем иконку
    cp assets/pports.svg AppDir/
    cp assets/pports.svg AppDir/usr/share/pixmaps/
    
    # Делаем файлы исполняемыми
    chmod +x AppDir/usr/bin/pports-gui
    chmod +x AppDir/usr/bin/pports-cli
    chmod +x AppDir/AppRun
    
    echo -e "${GREEN}✅ AppDir подготовлен${NC}"
}

# Загружаем appimagetool если нужно
download_appimagetool() {
    if [ ! -f appimagetool ]; then
        echo "⬇️ Загружаю appimagetool..."
        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool
        chmod +x appimagetool
        echo -e "${GREEN}✅ appimagetool загружен${NC}"
    else
        echo -e "${GREEN}✅ appimagetool уже существует${NC}"
    fi
}

# Создаем AppImage
create_appimage() {
    echo "📦 Создаю AppImage..."
    
    ./appimagetool AppDir PPORTS-1.0.0-x86_64.AppImage
    
    echo -e "${GREEN}✅ AppImage создан: PPORTS-1.0.0-x86_64.AppImage${NC}"
}

# Очистка временных файлов
cleanup() {
    echo "🧹 Очищаю временные файлы..."
    
    rm -rf build_env AppDir dist build
    rm -f *.spec
    
    echo -e "${GREEN}✅ Очистка завершена${NC}"
}

# Основная функция
main() {
    echo "🚀 PPORTS AppImage Builder"
    echo "========================="
    
    check_dependencies
    setup_directories
    install_dependencies
    build_with_pyinstaller
    prepare_appdir
    download_appimagetool
    create_appimage
    
    if [ "$1" != "--no-cleanup" ]; then
        cleanup
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Сборка завершена успешно!${NC}"
    echo -e "${YELLOW}📦 Готовый файл: PPORTS-1.0.0-x86_64.AppImage${NC}"
    echo ""
    echo "Для запуска:"
    echo "  chmod +x PPORTS-1.0.0-x86_64.AppImage"
    echo "  ./PPORTS-1.0.0-x86_64.AppImage"
    echo ""
}

# Запускаем основную функцию
main "$@" 