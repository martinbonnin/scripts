#! /bin/bash

MBONNIN_DIR=/usr/local/home/martin/git/mbonnin.net
cd ${MBONNIN_DIR}

TMP_DIR=/usr/local/home/martin/apache/mbonnin.net
FILE=${TMP_DIR}/${PATH_REQUESTED}

case $FILE in 
    *.html ) TYPE="text/html" ;;
    *.css ) TYPE="text/css" ;;
    * ) TYPE="text/plain" ;;
esac

if [ $TYPE == "text/html" ]
then
    ./generator/generator.py skeleton ${TMP_DIR} >/tmp/generator.error 2>&1 

    if [ $? -ne 0 ]
    then
        echo -e -n "Content-type: text/html\n";
        echo -e -n "Status: 404\n\n"
        echo "<code style=\"white-space: pre;\">"
        cat /tmp/generator.error
        echo "</code>"
        exit 1
    fi
fi

if [ -f ${FILE} ]
then
    echo -e -n "Content-type: ${TYPE}\n";
    echo -e -n "Status: 200\n\n"
    cat ${FILE}
else
    echo -e -n "Status: 404\n\n"
    echo "File not found: ${FILE}"
fi
