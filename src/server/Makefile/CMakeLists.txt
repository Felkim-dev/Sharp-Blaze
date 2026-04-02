cmake_minimum_required(VERSION 3.20)
project(SharpBlazeServer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(sharp_blaze_server
    ../main.cpp
    ../network/NetworkManager.cpp
    ../network/clientProtocol.cpp
    ../network/UDPBroadcaster.cpp
    ../network/GameSession.cpp
    ../network/GameEngine.cpp
    ../network/PathFinder.cpp
)

target_include_directories(sharp_blaze_server
    PRIVATE
        ../include
)

if(MSVC)
    target_compile_options(sharp_blaze_server PRIVATE /W4)
else()
    target_compile_options(sharp_blaze_server PRIVATE -Wall -Wextra)
endif()

find_package(Threads REQUIRED)
target_link_libraries(sharp_blaze_server PRIVATE Threads::Threads)

if(WIN32)
    target_link_libraries(sharp_blaze_server PRIVATE ws2_32)
endif()
