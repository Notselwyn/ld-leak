INCLUDE?=/usr/include

install:
	python3 ldleak.py $(SYMBOLS) $(INCLUDE) > lib.c
	gcc lib.c -o lib.so -shared -fPIC -w
	echo "\n\nbuilt lib.so\nusage:\nLD_PRELOAD=./lib.so *program*"
clean:
	rm lib.c
