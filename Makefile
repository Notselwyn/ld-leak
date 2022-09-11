INCLUDE?=/usr/include
OUT?=./lib.so

build:
	python3 ld-leak.py $(SYMBOLS) $(INCLUDE) | gcc -o $(OUT) -shared -fPIC -xc -
	echo "\n\nbuilt lib.so\nusage:\nLD_PRELOAD=$(OUT) *program*"
clean:
	rm lib.c -f
	rm *.swp -f
