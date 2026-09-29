#!/bin/bash
# Builds and runs the engine-free rule tests (no Axmol needed): Tests/run_logic_tests.sh
set -e
cd "$(dirname "$0")/.."
mkdir -p build
g++ -std=c++20 -O1 -Wall -ISource Source/logic/*.cpp Tests/PlatformStd.cpp Tests/LogicTests.cpp -o build/logic_tests
CONTENT_ROOT=Content/ build/logic_tests "$@"
