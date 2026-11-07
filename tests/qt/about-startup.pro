QT += core dbus
QT -= gui
CONFIG += console c++11
CONFIG -= app_bundle
TEMPLATE = app
TARGET = test-about-startup
INCLUDEPATH += ../../patches/control-center
SOURCES += about-startup.cpp
