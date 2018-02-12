#!/bin/bash

echo "Bulding index file"
if [ -z "$1" ]
    then
        hdr_files=`ls *.hdr`
    else
        hdr_files="$1.hdr"
fi
for hdr_file in $hdr_files
    do
    hdr_filename=${hdr_file%'.hdr'}
    cat "$hdr_filename".sen | awk '{split($0, a, " "); print a[3]"-"a[1]"-"a[2]" "a[4]":"a[5]":"a[6]}' > "$hdr_filename"_index_file
    time python beam2enu.py "$hdr_filename"
done
