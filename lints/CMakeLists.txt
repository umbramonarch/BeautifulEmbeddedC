# BeautifulEmbeddedC Dual-Target CMakeLists.txt (Target Cross-Compile + Host CTest Unit Tests)
#
# Copy to your firmware repository root as `CMakeLists.txt`.
# Enforces strict per-layer include-path isolation (`INC_CFG`, `INC_LIBS`, `INC_DRV`, `INC_BSP`,
# `INC_APP`) so upper layers physically cannot `#include` lower-layer or vendor SDK headers.
#
# Usage (Host Unit Tests + Architecture Check):
#   cmake -B build
#   cmake --build build --target arch
#   cmake --build build
#   ctest --test-dir build --output-on-failure

cmake_minimum_required(VERSION 3.20)
project(BeautifulEmbeddedC LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Locked-Door C11 Warning Flags (NASA JPL Rule 10 + MISRA C Essential Type checks)
set(COMMON_WARN_FLAGS
    -Wall
    -Wextra
    -Werror
    -Wpedantic
    -Wconversion
    -Wsign-conversion
    -Wdouble-promotion
    -Wshadow
    -Wundef
    -Wformat=2
    -Wmissing-prototypes
    -Wstrict-prototypes
    -Wold-style-definition
    -Wwrite-strings
    -Wcast-qual
    -Wvla
)

# Strictly isolated per-layer include paths (Beningo 4-Layer + Vertical libs/)
set(INC_CFG "${CMAKE_CURRENT_SOURCE_DIR}/src/config")

file(GLOB LIB_SUBDIRS LIST_DIRECTORIES true "${CMAKE_CURRENT_SOURCE_DIR}/libs/*")
set(INC_LIBS "")
foreach(dir IN LISTS LIB_SUBDIRS)
    if(IS_DIRECTORY "${dir}")
        list(APPEND INC_LIBS "${dir}")
    endif()
endforeach()

file(GLOB DRV_SUBDIRS LIST_DIRECTORIES true "${CMAKE_CURRENT_SOURCE_DIR}/drvs/*")
set(INC_DRV ${INC_CFG} ${INC_LIBS})
foreach(dir IN LISTS DRV_SUBDIRS)
    get_filename_component(drv_name "${dir}" NAME)
    if(IS_DIRECTORY "${dir}" AND NOT drv_name STREQUAL "vendor_sdk")
        list(APPEND INC_DRV "${dir}")
    endif()
endforeach()

set(INC_BSP
    "${CMAKE_CURRENT_SOURCE_DIR}/src/bsp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/bsp/config"
    ${INC_DRV}
)

set(INC_APP
    "${CMAKE_CURRENT_SOURCE_DIR}/src/app"
    ${INC_CFG}
    "${CMAKE_CURRENT_SOURCE_DIR}/src/bsp"
    ${INC_LIBS}
)

# Source discovery across layers
file(GLOB LIB_SRCS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/libs/*/*.c")
file(GLOB BSP_CFG_SRCS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/bsp/config/*.c")
file(GLOB BSP_SRCS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/bsp/*.c")
file(GLOB APP_SRCS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/app/*.c")
file(GLOB FAKE_SRCS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/drvs/*/test/fake_*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/fakes/fake_*.c"
)
file(GLOB TEST_SRCS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/libs/*/test/test_*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/drvs/*/test/test_*.c"
)

# Custom architecture and safety gate target (`check_arch.py`)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/lints/check_arch.py")
    set(CHECK_ARCH_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/lints/check_arch.py")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tools/check_arch.py")
    set(CHECK_ARCH_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/tools/check_arch.py")
endif()

if(DEFINED CHECK_ARCH_SCRIPT)
    add_custom_target(arch
        COMMAND "${Python3_EXECUTABLE}" "${CHECK_ARCH_SCRIPT}" "${CMAKE_CURRENT_SOURCE_DIR}"
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMENT "Running BeautifulEmbeddedC architecture and C11 safety checks..."
        VERBATIM
    )
endif()

# Host CTest unit test targets linking LIB_SRCS, BSP_CFG_SRCS, BSP_SRCS, APP_SRCS, and FAKE_SRCS
if(NOT CMAKE_CROSSCOMPILING)
    include(CTest)
    enable_testing()

    file(GLOB TEST_INC_DIRS LIST_DIRECTORIES true
        "${CMAKE_CURRENT_SOURCE_DIR}/drvs/*/test"
        "${CMAKE_CURRENT_SOURCE_DIR}/libs/*/test"
        "${CMAKE_CURRENT_SOURCE_DIR}/tests"
    )

    foreach(test_src IN LISTS TEST_SRCS)
        get_filename_component(test_name "${test_src}" NAME_WE)
        add_executable("${test_name}"
            "${test_src}"
            ${LIB_SRCS}
            ${BSP_CFG_SRCS}
            ${BSP_SRCS}
            ${APP_SRCS}
            ${FAKE_SRCS}
        )
        target_include_directories("${test_name}" PRIVATE
            ${INC_APP}
            ${INC_BSP}
            ${INC_DRV}
            ${TEST_INC_DIRS}
        )
        target_compile_options("${test_name}" PRIVATE ${COMMON_WARN_FLAGS} -O0 -g3)
        if(TARGET arch)
            add_dependencies("${test_name}" arch)
        endif()
        add_test(NAME "${test_name}" COMMAND "${test_name}")
    endforeach()
endif()
