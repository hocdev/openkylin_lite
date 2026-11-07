QT += core network
QT -= gui
CONFIG += console c++11
CONFIG -= app_bundle
TEMPLATE = app
TARGET = test-about-network
INCLUDEPATH += ../../patches/control-center
SOURCES += about-network.cpp
