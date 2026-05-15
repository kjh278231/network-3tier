cmake_minimum_required(VERSION 3.16)
project(network3tier_solver VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ─── Options ───────────────────────────────────────────────────────────────────
option(BUILD_PYTHON_BINDINGS "Build pybind11 Python bindings" ON)
option(BUILD_TESTS "Build unit tests" ON)

# ─── Core Library ──────────────────────────────────────────────────────────────
add_library(solver_core STATIC
    src/data_model.cpp
    src/constraint_checker.cpp
    src/min_cost_flow.cpp
    src/lns_engine.cpp
    src/solver.cpp
)
target_include_directories(solver_core PUBLIC include)
target_compile_options(solver_core PRIVATE -O2 -Wall -Wextra)

# ─── Python Bindings (pybind11) ────────────────────────────────────────────────
if(BUILD_PYTHON_BINDINGS)
    find_package(pybind11 CONFIG QUIET)
    if(NOT pybind11_FOUND)
        # Fetch pybind11 if not installed system-wide
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.12.0
        )
        FetchContent_MakeAvailable(pybind11)
    endif()

    pybind11_add_module(_solver_core cpp/bindings.cpp)
    target_link_libraries(_solver_core PRIVATE solver_core)
    set_target_properties(_solver_core PROPERTIES
        OUTPUT_NAME "_solver_core"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../src/network3tier"
    )
endif()

# ─── Tests ─────────────────────────────────────────────────────────────────────
if(BUILD_TESTS)
    enable_testing()
    add_executable(test_solver tests/test_main.cpp)
    target_link_libraries(test_solver PRIVATE solver_core)
    add_test(NAME test_solver COMMAND test_solver)
endif()
