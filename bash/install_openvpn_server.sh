#!/usr/bin/env bash

function usage()
{
    echo "usage:"
    echo "    install_openvpn_server.sh install_directory user@host domain email" 
    echo ""
    echo "    domain and email are used to generate certificates"
    exit 1;
}

if [[ $# -lt 4 ]]
then
    usage
fi

mkdir -p $1
BASEDIR=$(cd $1; pwd)
HOST=$2
NAME=$3
EMAIL=$4

(echo $NAME | grep ' ') && { echo "domain cannot contain spaces"; exit 1; }

set -e

cd $BASEDIR
if [[ ! -d easy-rsa ]]
then
    git clone https://github.com/OpenVPN/easy-rsa.git
    cd easy-rsa; git checkout 2.2.2
fi

cd $BASEDIR/easy-rsa/easy-rsa/2.0/
sed -i 's/export KEY_COUNTRY=.*/export KEY_COUNTRY=FR/g' vars
sed -i 's/export KEY_PROVINCE=.*/export KEY_PROVINCE=IdF/g' vars
sed -i 's/export KEY_CITY=.*/export KEY_CITY=Paris/g' vars
sed -i 's/export KEY_ORG=.*/export KEY_ORG='"$NAME/g" vars
sed -i 's/export KEY_EMAIL=.*/export KEY_EMAIL='"$EMAIL/g" vars
sed -i 's/export KEY_OU=.*/export KEY_OU=Organisation Unit/g' vars
sed -i 's/export KEY_NAME=.*/export KEY_NAME=openVPN/g' vars

source ./vars

./clean-all

SERVER_NAME=${NAME}_openvpn_server
export KEY_CN="$NAME openvpn ca"
./build-ca
./build-dh
./build-key-server $SERVER_NAME

cat > $BASEDIR/server.conf << EOF
dev tun
ifconfig 10.8.0.1 10.8.0.2
keepalive 10 60
ping-timer-rem
persist-tun
persist-key
push redirect-gateway
auth sha1
comp-lzo no

server 10.8.0.0 255.255.255.0

ca /etc/openvpn/ca.crt
cert /etc/openvpn/${SERVER_NAME}.crt
key /etc/openvpn/${SERVER_NAME}.key
dh /etc/openvpn/dh2048.pem
EOF

cat > $BASEDIR/install.sh << EOF
apt-get install openvpn
echo "1" > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
/etc/init.d/openvpn restart
EOF

cd $BASEDIR/easy-rsa/easy-rsa/2.0/keys
scp dh2048.pem ${SERVER_NAME}.key ${SERVER_NAME}.crt ca.crt $BASEDIR/server.conf $BASEDIR/install.sh $HOST:/etc/openvpn

ssh $HOST "cd /etc/openvpn; chmod +x ./install.sh; ./install.sh"

