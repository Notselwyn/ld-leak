# LD-Leak: your tool for a hooking pool
LD-Leak (Load Dynamic Leak) is a tool which can be used to track dynamically linked function calls, such as `strcmp()`. It may be useful when a user has `--x--x--x` (executable only) permissions and wants to dynamically analyze a binary, wants to dynamically hunt for secrets, or just wants to get a grip on the control flow.

## How it works
LD-Leak utilizes the `LD_PRELOAD`ing technique to intercept function calls to dynamic libraries such as `GLIBC`. `LD_PRELOAD`ing ensures that all dynamically loaded functions should first be checked in the specified library. By adding a hook in this library we can intercept function calls without even reading or modifying the original binary.

## Showcase
`---x--x--x 1 root root 16216 poc`

Without LD-Leak
```
$ ./poc
now you see me
> hello? where am I?

```

With LD-Leak:
```
$ LD_PRELOAD=./lib.so ./poc
now you see me
strcat("now you", " don't") @ 0x55fc3e7b42cd
read(1, 0x0x7ffeaa07d240, 128) @ 0x55fc3e7b42e6
> now you don't
strcmp("now you don't", "now you don't") @ 0x55fc3e7b431a
system("/bin/sh") @ 0x55fc3e7b432d
```

## Install
```console
$ git clone https://github.com/Notselwyn/ldleak
```

## Usage
```console
$ make SYMBOLS=*function1*,*function2*,*...* INCLUDE=/usr/include,*...*
$ LD_PRELOAD=./lib.so *program*
```

```console
$ make SYMBOLS=fopen,fwrite,write INCLUDE=/usr/include
python3 ldleak.py fopen,fwrite,write /usr/include > lib.c
FILE* fopen(const char* __filename,const char* __modes)
size_t fwrite(const void* __ptr,size_t __size,size_t __n,FILE* __s)
ssize_t write(int __fd,const void* __buf,size_t __n)
gcc lib.c -o lib.so -shared -fPIC -w
echo "\n\nbuilt lib.so\nusage:\nLD_PRELOAD=./lib.so *program*"


built lib.so
usage:
LD_PRELOAD=./lib.so *program*

$ sudo LD_PRELOAD=./lib.so fdisk -l
fopen("/lib/terminfo/x/xterm-256color", "rb") @ 0x7fdbbad32346
fread(0x0x7ffe934e72f0, 1, 32769, 0x0x557f16cc60c0) @ 0x7fdbbad32369
fopen("/proc/partitions", "r") @ 0x557f161aefae
fopen("/sys/block/nvme0n1/dev", "re") @ 0x557f161b3f42
read(4, 0x0x557f16ccb960, 512) @ 0x7fdbbad70a62
read(4, 0x0x557f16ccb960, 512) @ 0x7fdbbad70a62
read(4, 0x0x557f16ccbb70, 512) @ 0x7fdbbad970ee
read(4, 0x0x557f16ccc800, 16384) @ 0x7fdbbad971dc
read(4, 0x0x557f16ccbd80, 512) @ 0x7fdbbad970ee
read(4, 0x0x557f16cd0810, 16384) @ 0x7fdbbad971dc
Disk /dev/nvme0n1: 238.47 GiB, 256060514304 bytes, 500118192 sectors
read(6, 0x0x7ffe934f6350, 8191) @ 0x7fdbbad9aba8
...
```
