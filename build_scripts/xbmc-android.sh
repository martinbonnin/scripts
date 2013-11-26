#! /bin/bash
set -x
cd tools/depends 
./configure --with-toolchain=/usr/local/home/martin/toolchains/android-ndk-r8e-toolchain-4.7 --prefix=/tmp/xbmc-deps --host=arm-linux-androideabi --with-sdk-path=/usr/local/home/martin/adt-bundle-linux-x86_64-20130219/sdk --with-ndk=/usr/local/home/martin/android-ndk-r8e --with-sdk=android-14 --with-tarballs=/tmp/xbmc-tarballs || exit 1
make -j 20 || exit 1
cd ../..
make -C tools/depends/target/xbmc || exit 1
make -j 20 || exit 1
