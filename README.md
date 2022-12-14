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
### Script
```console
$ ./ld-leak.sh fopen,fread,read "fdisk -l"
└── usr
    └── include
        ├── stdio.h : fopen,fread
        └── unistd.h : read

FILE* fopen(const char* __filename,const char* __modes) + FOPEN(__filename, __modes)
size_t fread(void* __ptr,size_t __size,size_t __n,FILE* __stream) + FREAD(__ptr, __size, __n, __stream)
ssize_t read(int __fd,void* __buf,size_t __nbytes) + READ(__fd, __buf, __nbytes)
======= STARTING PROGRAM ========


fopen(__filename="/proc/partitions", __modes="r") @ 0x557b71b47fae [fdisk->0x9fae] -> 0x557b72de5cb0
fopen(__filename="/sys/block/nvme0n1/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> 0x557b72deb550
Disk /dev/nvme0n1: 236.47 GiB, 239060514304 bytes, 500008192 sectors
Disk model: *** ******** *****                  
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: gpt
Device             Start       End   Sectors  Size Type
/dev/nvme0n1p1      4096   1023998   1019903  498M EFI System
/dev/nvme0n1p2   1024000   9412606   8388607    4G Microsoft basic data
/dev/nvme0n1p3   9412608 491725486 482312879  230G Linux filesystem
fopen(__filename="/sys/block/nvme0n1p1/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/nvme0n1p1/device/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/nvme0n1p2/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/nvme0n1p2/device/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/nvme0n1p3/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/nvme0n1p3/device/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> (nil)
fopen(__filename="/sys/block/dm-0/dev", __modes="re") @ 0x557b71b4cf42 [fdisk->0xef42] -> 0x557b72deb550
...
```

### Manual
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
