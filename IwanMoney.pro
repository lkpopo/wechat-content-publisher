# IwanMoney.pro - qmake 备选构建（推荐 CMake）
# 使用： C:\Qt\5.15.2\msvc2019_64\bin\qmake.exe IwanMoney.pro && nmake

QT       += core gui widgets sql
CONFIG   += c++17

TARGET = IwanMoney
TEMPLATE = app

# MSVC UTF-8
msvc: QMAKE_CXXFLAGS += /utf-8

SOURCES += \
    src/main.cpp \
    src/ui/mainwindow.cpp \
    src/core/configmanager.cpp \
    src/core/database.cpp \
    src/utils/processrunner.cpp \
    src/utils/themeManager.cpp

HEADERS += \
    src/ui/mainwindow.h \
    src/core/configmanager.h \
    src/core/database.h \
    src/core/article.h \
    src/utils/processrunner.h \
    src/utils/themeManager.h

FORMS += \
    src/ui/mainwindow.ui

RESOURCES += \
    resources/resources.qrc

INCLUDEPATH += \
    src \
    src/ui \
    src/core \
    src/utils

# 部署 Python 脚本
# QMAKE_POST_LINK += $$quote(cmd /c xcopy /E /I /Y $$PWD\\python $$OUT_PWD\\python)
