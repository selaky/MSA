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
