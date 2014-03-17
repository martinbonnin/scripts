#! /bin/bash

#export all variables so that they are reachable when we are root
set -a

DISTRIB_DIR=precise-chroot

CUR_DIR=$(cd $(dirname $0); pwd)
CHROOT_DIR=$CUR_DIR/$DISTRIB_DIR

HOST_UID=$(id -u)
HOST_GID=$(id -g)
HOST_USER=$(id -un)
HOST_GROUP=$(id -gn)
HOST_HOME=$(cd ~; pwd)

REFCOUNT_FILE=/tmp/chroot.refcount

SETUP=0
ROOT=0

for v;
do
    case $v in
    --help)
        echo "Options:" 
        echo "  --help      this help message" 
        echo "  --setup     makes the actual setup" 
        echo "  --root      login as root" 
        exit 1
        ;;
    --setup)
        SETUP=1
        ;;
    --root)
        ROOT=1
        ;;
    esac
done

if [ $HOST_UID == 0 ]; then echo "please run as normal user"; exit 1; fi

function reverse {
    R=""
    for v
    do
        R="$v $R"
    done
    
    echo -n $R
}

function do-copy-files {
    FILES="/etc/hosts /etc/machine-id /etc/resolv.conf /etc/pulse/client.conf home:.pulse-cookie"
    for f in $FILES
    do
        S=$(echo $f | sed "s#home:#$HOST_HOME/#g")
        D=$(echo $f | sed "s#home:#/home/$HOST_USER/#g")
        cp ${S} ${CHROOT_DIR}${D};
    done
    
    [ -d ${CHROOT_DIR}/var/lib/dbus/ ] || mkdir -p ${CHROOT_DIR}/var/lib/dbus/
    cp /etc/machine-id ${CHROOT_DIR}/var/lib/dbus/
}

BIND_MOUNTS="home:git home:chromium home:.pulse /tmp/ /dev/shm/ /run/"

function do-mounts {
    mount proc $CHROOT_DIR/proc -t proc;
    mount sysfs $CHROOT_DIR/sys -t sysfs;
    mount -o gid=5,mode=620 devpts $CHROOT_DIR/dev/pts -t devpts;

    for m in $BIND_MOUNTS
    do
        #home might not be the same on the host and inside the chroot
        S=$(echo $m | sed "s#home:#$HOST_HOME/#g")
        D=$(echo $m | sed "s#home:#/home/$HOST_USER/#g")
        [ -d ${CHROOT_DIR}${D} ] || mkdir ${CHROOT_DIR}${D}
        echo "mount -o bind $S ${CHROOT_DIR}${D}" 
        mount -o bind $S ${CHROOT_DIR}${D}
    done
}

function do-umounts {
    umount $CHROOT_DIR/dev/pts
    umount $CHROOT_DIR/sys
    umount $CHROOT_DIR/proc

    #umount in reverse order. Not sure this is needed
    for m in $(reverse $BIND_MOUNTS)
    do
        D=$(echo $m | sed "s#home:#/home/$HOST_USER/#g")
        echo "umount ${CHROOT_DIR}${D}" 
        umount ${CHROOT_DIR}${D}
    done
}

function chroot-wrapper {
    COUNT=$(cat $REFCOUNT_FILE); [ -z "$COUNT" ] && COUNT=0
    COUNT=$(( $COUNT + 1 ))
    echo $COUNT > $REFCOUNT_FILE
    if [ "$COUNT" -eq 1 ]
    then
        echo "you are the first user, mouting filesystems and copying files..."
        
        do-mounts
        do-copy-files
        xhost +;
    else 
        echo "$(( $COUNT - 1 )) users are using the chroot besides you."
    fi
    
    chroot $CHROOT_DIR "$@";
    #sometimes bash is still holding file descriptors to the mounted partitions so we cannot unmount them
    #wait a bit for it to terminate correctly....
    sleep 1

    COUNT=$(cat $REFCOUNT_FILE); [ -z "$COUNT" ] && COUNT=0
    COUNT=$(( $COUNT - 1 ))
    echo $COUNT > $REFCOUNT_FILE
    if [ "$COUNT" -eq 0 ]
    then
        echo "you are the last user, cleanup..."
        do-umounts
    else
        echo "$COUNT users still using the chroot."
    fi
}

function run-as-root {
    echo "switching as root to run $1"
    su -c "$*"
}

function run-setup {
    apt-get install locales
    dpkg-reconfigure locales
    addgroup --gid $HOST_GID $HOST_GROUP
    adduser --gid $HOST_GID --uid $HOST_UID $HOST_USER
}

if [ $SETUP -eq 1 ]
then
    #XXX: not sure why I need to do the echo first...
    run-as-root chroot-wrapper "echo beginning setup...;run-setup";
elif [ $ROOT -eq 1 ]
then 
    run-as-root chroot-wrapper /bin/bash -l
else
    run-as-root chroot-wrapper su martin -l
fi
