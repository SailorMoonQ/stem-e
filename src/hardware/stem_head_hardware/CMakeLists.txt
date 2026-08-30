cmake_minimum_required(VERSION 3.16)
project(stem_head_hardware)

find_package(ament_cmake REQUIRED)

# TODO: targets and install rules go here as this package is implemented.

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
