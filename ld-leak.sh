echo $1

make SYMBOLS=$1 OUT=/tmp/.lib.so
LD_PRELOAD=/tmp/.lib.so $2

