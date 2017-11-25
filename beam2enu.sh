#!/bin/bash

echo "Bulding index file"
cat "$1".sen | awk '{split($0, a, " "); print a[3]"-"a[1]"-"a[2]" "a[4]":"a[5]":"a[6]}' > "$1"_index_file
time python beam2enu.py "$1"

