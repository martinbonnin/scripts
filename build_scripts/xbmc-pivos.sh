#! /bin/bash
set -x;
cd tools/android/depends
./bootstrap
./configure --with-toolchain=/usr/local/home/martin/toolchains/android-ndk-r8e-toolchain-4.7 --prefix=/tmp/xbmc-pivos-deps --host=arm-linux-androideabi --with-sdk=/usr/local/home/martin/adt-bundle-linux-x86_64-20130219/sdk --with-ndk=/usr/local/home/martin/android-ndk-r8e --with-sdk-platform=android-14 --with-tarballs=/tmp/xbmc-pivos-tarballs || exit 1
make || exit 1
cd ../../..
make -C tools/android/depends/xbmc || exit 1
make 
