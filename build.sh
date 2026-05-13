#!/bin/bash
# Build script for the C++ solver core library and tests.
# Usage: ./build.sh [--test]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/cpp/build"

echo "=== Building Network 3-Tier C++ Solver ==="

# Create build directory
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# Configure with CMake
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=ON \
    -DBUILD_PYTHON_BINDINGS=OFF

# Build
cmake --build . -j$(nproc)

echo ""
echo "=== Build Complete ==="

# Run tests if requested
if [[ "$1" == "--test" ]]; then
    echo ""
    echo "=== Running Tests ==="
    ./test_solver
fi
