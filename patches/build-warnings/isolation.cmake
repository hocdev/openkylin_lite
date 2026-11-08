# Interpret debhelper's legacy isolation flags through current CMake variables.
if(CMAKE_EXPORT_NO_PACKAGE_REGISTRY)
    set(CMAKE_EXPORT_PACKAGE_REGISTRY OFF)
endif()
if(CMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY)
    set(CMAKE_FIND_USE_PACKAGE_REGISTRY OFF)
endif()
foreach(_openkylin_lite_policy IN ITEMS CMAKE_EXPORT_NO_PACKAGE_REGISTRY
        CMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY CMAKE_FIND_USE_PACKAGE_REGISTRY
        FETCHCONTENT_FULLY_DISCONNECTED)
    if(DEFINED ${_openkylin_lite_policy})
        message(STATUS "Build isolation ${_openkylin_lite_policy}=${${_openkylin_lite_policy}}")
    endif()
endforeach()
