QT += core dbus
QT -= gui
CONFIG += console c++11
CONFIG -= app_bundle
TEMPLATE = app
TARGET = test-security-path
INCLUDEPATH += ../../patches/control-center
SOURCES += security-path.cpp
