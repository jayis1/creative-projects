# Canopy Listener Firmware — Pico SDK CMakeLists

cmake_minimum_required(VERSION 3.20)

# Pull in Pico SDK
include(pico_sdk_import.cmake)

project(canopy_listener C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Pico SDK initialization
pico_sdk_init()

# Main executable
add_executable(canopy_listener
    main/main.c
    main/audio_capture.c
    main/wildlife_classify.c
    main/lora_radio.c
    main/gps_module.c
    main/sd_logger.c
    main/env_sensor.c
    main/oled_display.c
    main/power_manager.c
)

# Include paths
target_include_directories(canopy_listener PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/main
    ${CMAKE_CURRENT_SOURCE_DIR}/../../pico-sdk/src/common/pico_stdlib/include
)

# Link Pico SDK libraries
target_link_libraries(canopy_listener
    pico_stdlib
    pico_multicore
    pico_sleep
    hardware_pio
    hardware_spi
    hardware_i2c
    hardware_uart
    hardware_adc
    hardware_dma
    hardware_flash
    hardware_clocks
    hardware_gpio
    hardware_sleep
    hardware_pll
    hardware_vreg
)

# Generate UF2, HEX, MAP, DIS
pico_add_extra_outputs(canopy_listener)

# Enable USB output for debug
pico_enable_stdio_usb(canopy_listener 1)
pico_enable_stdio_uart(canopy_listener 0)