#!/bin/sh

#cd log4cplus-1.1.0

#make distclean

#export ANALYZER_DISABLE_ANALYSIS=true
#./configure CXX=clang++  CC=clang
#unset ANALYZER_DISABLE_ANALYSIS

#make

pwd

clang++ -fno-stack-protector -no-pie -O0 \
    -I/usr/include/postgresql challenge_buffer_overflow/vuln_app.cpp \
    -o vuln_app \
    $(pkg-config --cflags --libs opencv4) -lpq
