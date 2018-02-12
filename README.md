# Description
A small bash + python scripts for convertion between beam and ENU coordinates in Nortek Aquadopp data.
Bash part reads datetime index, reformats it and saves in separate file. Then not small python script reads a data, making a convertion and saves to .csv files

# Usage
It takes usual files gathered by Nortek software.
Just put both files into folder with data and start .sh script (do not forget to add run rights) with common part of filename as an argument. Without argument script it takes all .hdr files.
In Unix run './beam2enu.sh filename' or just './beam2enu.sh'.
fileneame is a common part of filenames, e.g. if you have files AQUADOPP.v1, .v2… use just AQUADOPP part.
