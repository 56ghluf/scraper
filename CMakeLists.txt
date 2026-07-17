cmake_minimum_required(VERSION 3.28)

project(scraper)

################################################################

# settings
set(CMAKE_CXX_STANDARD 23)
set(PROJECT_WARNING_FLAGS
    -pedantic
    -Wall
    -Wextra
    -Wold-style-cast
    -Woverloaded-virtual
    -Wfloat-equal
    -Wshadow
    -Wwrite-strings
    -Wpointer-arith
    -Wcast-qual
    -Wcast-align
    -Wconversion
)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

################################################################

# so we don't get warnings with curl's examples
set(BUILD_EXAMPLES OFF CACHE BOOL "build libcurl examples" FORCE)

include(FetchContent)
FetchContent_Declare(cpr GIT_REPOSITORY https://github.com/libcpr/cpr.git
                         GIT_TAG 1.14.2) # Replace with your desired git commit from: https://github.com/libcpr/cpr/releases

set(LEXBOR_BUILD_SHARED OFF CACHE BOOL "build lexbor shared library" FORCE)

FetchContent_Declare(lexbor GIT_REPOSITORY https://github.com/lexbor/lexbor.git
                            GIT_TAG master)

FetchContent_MakeAvailable(cpr lexbor)

################################################################

# project
add_executable(get_openinsider_data get_openinsider_data.cpp)
target_compile_options(get_openinsider_data PRIVATE ${PROJECT_WARNING_FLAGS})
target_link_libraries(get_openinsider_data cpr lexbor_static dates search_result_parsing timing)

add_library(dates dates.cpp)
target_include_directories(dates PUBLIC ${PROJECT_SOURCE_DIR})
target_compile_options(dates PRIVATE ${PROJECT_WARNING_FLAGS})

add_library(search_result_parsing search_result_parsing.cpp)
target_include_directories(search_result_parsing PUBLIC ${PROJECT_SOURCE_DIR})
target_compile_options(search_result_parsing PRIVATE ${PROJECT_WARNING_FLAGS})
target_link_libraries(search_result_parsing lexbor_static)

add_library(timing timing.cpp)
target_include_directories(timing PUBLIC ${PROJECT_SOURCE_DIR})
target_compile_options(timing PRIVATE ${PROJECT_WARNING_FLAGS})

#add_library(engine engine.cpp particles.cpp obstacles.cpp receiver_agent.cpp dust.cpp comet.cpp bouncer.cpp sources.cpp)
#target_include_directories(engine PUBLIC ${PROJECT_SOURCE_DIR}/engine)
#target_compile_options(engine PRIVATE ${PROJECT_WARNING_FLAGS})
#target_link_libraries(engine project_options math_utils drawing logging_utils)

