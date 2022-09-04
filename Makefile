INCLUDE?=/usr/include

install:
	python3 ldleak.py $(SYMBOLS) $(INCLUDE) | gcc -o lib.so -shared -fPIC -xc -w -
	echo "\n\nbuilt lib.so\nusage:\nLD_PRELOAD=./lib.so *program*"
