# Bobanana 5.0 — EUI-NEO 桌面端 CMake 项目
#
# 编译步骤:
#   1. 克隆 EUI-NEO: git clone https://github.com/sudoevolve/EUI-NEO.git external/EUI-NEO
#   2. 构建:  cmake -S eui_neo_app -B build-eui
#   3. 编译:  cmake --build build-eui
#   4. 运行:  ./build-eui/bobanana_gui
#
# 前置条件:
#   - CMake 3.14+
#   - C++17 编译器 (MSVC/GCC/Clang)
#   - OpenGL 开发文件
#   - Git

cmake_minimum_required(VERSION 3.14)
project(bobanana-gui LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── 引入 EUI-NEO ──────────────────────────────
option(EUI_NEO_BUNDLED "Use bundled EUI-NEO source" OFF)

if(EUI_NEO_BUNDLED OR EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/external/EUI-NEO/CMakeLists.txt")
    # 方式 A: 本地已克隆
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/external/EUI-NEO)
else()
    # 方式 B: FetchContent 自动下载
    include(FetchContent)
    FetchContent_Declare(
        eui_neo
        GIT_REPOSITORY https://github.com/sudoevolve/EUI-NEO.git
        GIT_TAG        v0.5.2
        GIT_SHALLOW    TRUE
    )
    set(EUI_BUILD_USER_APPS OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(eui_neo)
endif()

# ── 应用源码 ────────────────────────────────────
set(APP_SOURCES
    src/main.cpp
)

add_executable(bobanana_gui
    ${CMAKE_SOURCE_DIR}/external/EUI-NEO/core/app/glfw_app_main.cpp
    ${APP_SOURCES}
)

target_include_directories(bobanana_gui PRIVATE src)

# ── 链接 EUI-NEO ──────────────────────────────
target_link_libraries(bobanana_gui PRIVATE eui_neo)

# ── 资源 ────────────────────────────────────────
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/assets/ DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/assets)
