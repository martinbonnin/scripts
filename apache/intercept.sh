#! /bin/bash

MBONNIN_DIR=/home/martin/git/mbonnin.net
cd ${MBONNIN_DIR}

FILE=${MBONNIN_DIR}/site/${PATH_REQUESTED}
if [ -f ${FILE} ]
then
    case $FILE in 
        *.html ) TYPE="text/html" ;;
        *.css ) TYPE="text/css" ;;
        * ) TYPE="text/plain" ;;
    esac
    
    if [ $TYPE == "text/html" ]
    then
    ./generator/generator.py src site >/tmp/generator.error 2>&1 

        if [ $? -ne 0 ]
        then
            echo -e -n "Content-type: text/html\n";
            echo -e -n "Status: 404\n\n"
            cat /tmp/generator.error
            exit 1
        fi
    fi

    echo -e -n "Content-type: ${TYPE}\n";
    echo -e -n "Status: 200\n\n"
    cat ${FILE}
else
    echo -e -n "Status: 404\n\n"
    echo "File not found: ${FILE}"
fi
