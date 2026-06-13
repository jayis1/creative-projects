# Neuro Sense Puck Firmware — ESP-IDF CMakeLists

cmake_minimum_required(VERSION 3.20)
set(COMPONENTS main)

# ESP-IDF project
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(neuro_sense_puck)