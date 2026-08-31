cmake_minimum_required(VERSION 3.16)
project(IwanMoney VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# MSVC 强制 UTF-8 编译（解决中文/emoji 源码在 GBK 环境下的 C2001/C4819 错误）
if(MSVC)
    add_compile_options("/utf-8")
    add_compile_options("/wd4819")
endif()

# Qt 路径：优先使用环境变量 Qt5_DIR，否则使用默认安装路径
if(NOT DEFINED CMAKE_PREFIX_PATH)
    set(CMAKE_PREFIX_PATH "C:/Qt/5.15.2/msvc2019_64")
endif()

find_package(Qt5 REQUIRED COMPONENTS Widgets Core Gui Sql)

# 源码文件
set(SOURCES
    src/main.cpp
    src/ui/mainwindow.cpp
    src/ui/mainwindow.h
    src/ui/mainwindow.ui
    src/ui/bloggerDialog.cpp
    src/ui/bloggerDialog.h
    src/ui/bloggerDialog.ui
    src/ui/crawlSelectionDialog.cpp
    src/ui/crawlSelectionDialog.h
    src/core/configmanager.cpp
    src/core/configmanager.h
    src/core/database.cpp
    src/core/database.h
    src/core/article.h
    src/core/blogger.h
    src/utils/processrunner.cpp
    src/utils/processrunner.h
    src/utils/themeManager.cpp
    src/utils/themeManager.h
    resources/resources.qrc
)

add_executable(${PROJECT_NAME} ${SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ui
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils
)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt5::Widgets
    Qt5::Core
    Qt5::Gui
    Qt5::Sql
)

# Windows 下设为 WIN32 应用（不弹控制台），调试时可注释
# set_target_properties(${PROJECT_NAME} PROPERTIES WIN32_EXECUTABLE TRUE)

# 拷贝 Python 脚本到构建目录
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/python"
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>/python"
    COMMENT "Copying python scripts to build directory"
)

# 拷贝 temp 目录结构
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>/data/temp"
)

# windeployqt 自动部署（可选，需 Qt bin 在 PATH）
if(WIN32)
    find_program(WINDEPLOYQT_EXECUTABLE windeployqt HINTS "${CMAKE_PREFIX_PATH}/bin")
    if(WINDEPLOYQT_EXECUTABLE)
        add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
            COMMAND "${WINDEPLOYQT_EXECUTABLE}" --no-translations "$<TARGET_FILE:$<TARGET_NAME:${PROJECT_NAME}>>"
            COMMENT "Running windeployqt"
        )
    endif()
endif()

message(STATUS "Qt5 found: ${Qt5_VERSION} at ${CMAKE_PREFIX_PATH}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
