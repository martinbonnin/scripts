#!/usr/bin/env bash

function usage()
{
    echo "usage:"
    echo "    install_openvpn_server.sh directory user@host" 
    exit 1;
}

if [[ $# -lt 2 ]]
then
    usage
fi

mkdir -p $1
BASEDIR=$(cd $1; pwd)
HOST=$2

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
sed -i 's/export KEY_ORG=.*/export KEY_ORG=Organisation/g' vars
sed -i 's/export KEY_EMAIL=.*/export KEY_EMAIL=Email/g' vars
sed -i 's/export KEY_OU=.*/export KEY_OU=Organisation Unit/g' vars
sed -i 's/export KEY_NAME=.*/export KEY_NAME=openVPN/g' vars

source ./vars

./clean-all
./build-ca
./build-dh
./build-key-server server

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

ca ca.crt
cert server.crt
key server.key
dh dh2048.pem
EOF

cat > $BASEDIR/run_openvpn.sh << EOF
echo "1" > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
openvpn --config server.conf
EOF

cd $BASEDIR/easy-rsa/easy-rsa/2.0/keys
scp dh2048.pem server.key server.crt ca.crt $BASEDIR/server.conf $BASEDIR/run_openvpn.sh $HOST:
ssh $HOST "./run_openvpn.sh"
