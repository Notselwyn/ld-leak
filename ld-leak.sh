ld-leak.py $1 /usr/include | gcc -o /tmp/.lib.so -shared -fPIC -xc - -w

chmod 777 /tmp/.lib.so # allow overwriting as another user
echo "======= STARTING PROGRAM ========\n\n"

LD_PRELOAD=/tmp/.lib.so $2

