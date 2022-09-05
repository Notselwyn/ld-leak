#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

int main() {
    char buf[256];

    printf("now you see me\n");

    char secret[14] = "now you";
    char final[] = "\xa3\xe7\xec\xed\xa4\xf7";
    for (int i=0; i<6; i++) {
        final[i] ^= 0x83;
    }

    strcat(secret, final);

    read(1, buf, 128);
    buf[strlen(buf)-1] = '\x00';

    if (!strcmp(buf, secret)) {
        system("exit");
    }
}
