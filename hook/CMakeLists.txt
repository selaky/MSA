# MSA 后台点击模块 CMake 配置
cmake_minimum_required(VERSION 3.15)

project(msa_hook LANGUAGES C CXX)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows 特定设置
if(WIN32)
    # 设置 MSVC 编码为 UTF-8
    add_compile_options("$<$<CXX_COMPILER_ID:MSVC>:/utf-8>")
    add_compile_options("$<$<C_COMPILER_ID:MSVC>:/utf-8>")

    # 定义 Windows 版本（Windows 10）
    add_definitions(-D_WIN32_WINNT=0x0A00)
    add_definitions(-DWINVER=0x0A00)
    add_definitions(-DUNICODE -D_UNICODE)
endif()

# ==================== 依赖配置 ====================

# MAA Framework 路径（相对于项目根目录）
set(MAA_DEPS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../deps")

# OpenCV 头文件路径（使用本地副本）
set(OPENCV_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/opencv/include")

# 添加 MinHook 子项目
add_subdirectory(third_party/minhook)

# ==================== Hook DLL ====================
set(HOOK_DLL_SOURCES
    dll/dllmain.cpp
    dll/hooks.cpp
    dll/shared_memory.cpp
)

add_library(msa_hook SHARED ${HOOK_DLL_SOURCES})

target_include_directories(msa_hook PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/minhook/include
)

target_link_libraries(msa_hook PRIVATE minhook)

# 设置 DLL 输出名称
set_target_properties(msa_hook PROPERTIES
    OUTPUT_NAME "msa_hook"
    PREFIX ""
)

# ==================== Proxy DLL ====================
set(PROXY_DLL_SOURCES
    proxy/dllmain.cpp
    proxy/exports.cpp
    proxy/control_unit.cpp
)

add_library(msa_proxy SHARED ${PROXY_DLL_SOURCES})

target_include_directories(msa_proxy PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
    ${CMAKE_CURRENT_SOURCE_DIR}/proxy
    ${MAA_DEPS_DIR}/include
    ${OPENCV_INCLUDE_DIR}
)

# 链接库
target_link_libraries(msa_proxy PRIVATE user32 kernel32)

# 注意：不需要链接 OpenCV 库，因为我们只使用 cv::Mat 的引用传递
# 实际的 cv::Mat 操作由原版控制单元完成

# 设置 DLL 输出名称为 MaaWin32ControlUnit.dll
set_target_properties(msa_proxy PROPERTIES
    OUTPUT_NAME "MaaWin32ControlUnit"
    PREFIX ""
)

# 启用 RTTI（用于 dynamic_cast）
if(MSVC)
    target_compile_options(msa_proxy PRIVATE /GR)
endif()

# 输出目录
set_target_properties(msa_proxy PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# 安装目标
install(TARGETS msa_proxy
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION bin
)

message(STATUS "Proxy DLL (MaaWin32ControlUnit.dll) will be built")

# ==================== 测试程序 ====================
set(TEST_SOURCES
    test/click_test.cpp
)

add_executable(click_test ${TEST_SOURCES})

target_include_directories(click_test PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
)

# 链接 Windows 库
target_link_libraries(click_test PRIVATE user32 kernel32)

# 设置测试程序为 Windows 控制台应用
set_target_properties(click_test PROPERTIES
    WIN32_EXECUTABLE FALSE
)

# ==================== 安装配置 ====================
# 将 DLL 和测试程序输出到同一目录
set_target_properties(msa_hook click_test PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# 安装目标
install(TARGETS msa_hook click_test
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION bin
)
