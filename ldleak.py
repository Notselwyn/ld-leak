import os
import sys
import re


def search_file(header: str) -> None:
    ''' searches a header for C functions using the compiled regex string

    :param header: the filename of the header to be searched
    :returns: None, as it utilizes a global varibale
    '''

    global header_candidates

    with open(header) as f:
        content = f.read()
        for s, regstr in symbols.items():
            findings = re.findall(regstr, content)
            if findings!=[]:
                header_candidates[s] += [header]


def search_dir(directory: str) -> None:
    ''' [recursively] searches all directories for C function signature

    :param directory: the directory string (e.g. /usr/include)
    :returns: None, as it utilizes a global variable
    '''

    for header in os.listdir(directory):
        header = directory + "/" + header
        if os.path.isdir(header):
            search_dir(header)
            continue

        try:
            search_file(header)
        except: ...


def initiate_search() -> None:
    ''' This function starts the regex spree in all directories and does validation. 

    '''

    # strip the remaining / off the directory names
    # e.g. /usr/include/ -> /usr/include
    for p in range(2, len(sys.argv)):
        sys.argv[p] = sys.argv[p].rstrip("/")

    # initiates directory checking
    for directory in sys.argv[2:]:
        if not os.path.isdir(directory):
            print(f"path {directory} is not a directory", file=sys.stderr)
            exit()
        search_dir(directory)


def get_best_headers(header_candidates: dict[str, list[str, str, ...]]) -> dict[str, str]:
    ''' selects the best suitable header file when multiple files match.
    the algoritmh is based on the hierarchical filesystem depth.
    /usr/include/string.h is better than /usr/include/pkg/string.h

    :param header_candidates: the header files in which a symbol was found
    :returns: the best suitable header file
    '''

    score = {}
    for symbol, headers in header_candidates.items():
        score[symbol] = {h: 99999 for h in headers}
        if len(headers) == 0:
            print(f"the definition for {symbol} could not be found", file=sys.stderr)
            exit()

        for header in headers:
            for directory in sys.argv[2:]:
                if directory+"/" not in header:
                    continue
                # algorithm for maintaining lowest score
                score[symbol][header] = min(header.count("/")- \
                        directory.count("/"), score[symbol][header])

    # this selects the header file with the lowest score
    return {symbol: min(score[symbol], key=lambda k: score[symbol][k]) for symbol in score}

def generate_lib(headers: dict[str, str]) -> str:
    ''' this is the most important part of the tool:
    it generates C code for a shared object (.so) file to be used for the LD-preloading.

    :param headers: the C headers in which the hooked functions reside
    :returns: the generated C code
    '''

    # by specifying _GNU_SOURCE we're able to use RTLD_NEXT
    lib_content = "#define _GNU_SOURCE\n"
    lib_content += "#include <stdio.h>\n"
    lib_content += "#include <dlfcn.h>\n"

    # generate function wrappers for all symbols
    for symbol, file in headers.items():
        # clean function signature
        with open(file) as f:
            sign = re.findall(symbols[symbol], f.read())[0]
            sign = sign.replace("\nextern ", "").replace("\n", "").replace("\t", "")
        
        # standardize signature for easy parsing
        while "  " in sign:
            sign = sign.replace("  ", " ")
        
        sign = sign.replace(" (", "(").replace(", ", ",").replace(" *", "* ")
        sign = sign.replace("__restrict ", "")  # gives unnecessary trouble
        
        print(sign, file=sys.stderr)

        # TO-DO: add support for VARARGS
        if "..." in sign:
            print(f'... in the function signature of {symbol} are not yet supported', file=sys.stderr)
            print('please try another symbol until this feature has been added', file=sys.stderr)
            exit()

        # generates the function signature:
        # int strcmp(const char* __s1,const char* __s2) {
        lib_content += f"\n\nvoid* __{symbol};\n" + sign + "\n{\n"
        
        # the code below generates the printf hook:
        # printf("strcmp(\"%s\", \"%s\") @ 0x%lx\n",
        #     __s1, __s2, (unsigned long)__builtin_return_address(0));
        
        # vvvvvv becomes vvvvvv
 
        # strcmp("PIPESTATUS", "PIPESTATUS") @ 0x55dee0f543e2
        lib_content += f'    printf("{symbol}('
        
        # parses the signature arguments (used for printf and final hook call)
        __args = sign[sign.index('(')+1:sign.index(')')].split(',')
        if __args == ['void']:
            __args = []

        # retrieves the argument type and the name: {'__s1': 'char*'}
        args = {x.split(' ')[-1]: x.split(' ')[-2] for x in __args}
        
        # choose what to printf()
        printf_args = []
        for name, t in args.items():
            if t == "char*":
                printf_args += ['\\"%s\\"']
            elif "*" in t:
                printf_args += ['%p']
            else:
                printf_args += ['%lx']

        lib_content += ", ".join(printf_args)
        lib_content += ') @ 0x%lx\\n"'  # for printing the RETADDR

        for k in args.keys():
            lib_content += ", " + k
        
        # prints the return address
        lib_content += ", (unsigned long)__builtin_return_address(0));\n\n    "
        

        # return type void should not have a return statement according to gcc
        if sign.split(" ")[0] != 'void':
            lib_content += 'return '
        
        # generates the final function call:
        # ((typeof (&strcmp))__strcmp)(__s1, __s2);
        lib_content += f'((typeof (&{symbol}))__{symbol})('
        lib_content += ", ".join(args.keys())
        lib_content += ");\n}"

    # generates the function loader for original function addresses:
    
    # __attribute__((constructor))
    # static void __load_functions() {
    #     __strcmp = dlsym(RTLD_NEXT, "strcmp");
    # }

    lib_content += "\n\n__attribute__((constructor))\n"
    lib_content += "static void __load_functions()\n{\n"
    for symbol, file in headers.items():
        lib_content += f'    __{symbol} = dlsym(RTLD_NEXT, "{symbol}");\n'
    lib_content += '}'

    return lib_content


if __name__ == "__main__":
    # enforce arguments
    if len(sys.argv) < 3:
        print("symbols.py usage:", file=sys.stderr)
        print("symbols.py <symbol1,symbol2,...> <headers> [headers headers]", file=sys.stderr)
        exit()

    # compile regex query for C functions
    # cannot be refactored due to {s}
    symbols = {}
    for s in sys.argv[1].split(','):
        symbols[s] = re.compile(fr"\n\s*extern\s+(?:[a-zA-Z0-9_]+\*?\s+)+\*?{s}\s*" + \
                        r"\n*\([a-zA-Z0-9_\s\n\*,\.]+\)")

    # the files that match the C function regex (they have the C function(s) in them)
    header_candidates = {s: [] for s in symbols}

    # by using global vars we save mem
    initiate_search()

    headers = get_best_headers(header_candidates)
    
    print(generate_lib(headers))

