#!/usr/bin/env python3

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


def initiate_search() -> set[str, str, ...]:
    ''' This function starts the regex spree in all directories and does validation. 

    :returns: a list of validated directories 
    '''

    # strip the remaining / off the directory names
    # e.g. /usr/include/ -> /usr/include
    dirs = sys.argv[2].split(",")
    for p in range(len(dirs)):
        dirs[p] = dirs[p].rstrip("/")
    
    dirs = set(dirs)  # unique
    
    # initiates directory checking
    for directory in dirs:
        if not os.path.isdir(directory):
            print(f"path {directory} is not a directory", file=sys.stderr)
            sys.exit(1)
        search_dir(directory)

    return dirs


def get_best_headers(dirs: set[str, str, ...], header_candidates: dict[str, list[str, str, ...]]) -> dict[str, str]:
    ''' selects the best suitable header file when multiple files match.
    the algoritmh is based on the hierarchical filesystem depth.
    /usr/include/string.h is better than /usr/include/pkg/string.h

    :param dirs: the directories in which the header files are located. used for score
    :param header_candidates: the header files in which a symbol was found
    :returns: the best suitable header file
    '''

    score = {}
    for symbol, headers in header_candidates.items():
        score[symbol] = {h: 99999 for h in headers}
        if len(headers) == 0:
            print(f"the definition for {symbol} could not be found", file=sys.stderr)
            sys.exit(1)

        for header in headers:
            for directory in dirs:
                if directory+"/" not in header:
                    continue
                # algorithm for maintaining lowest score
                score[symbol][header] = min(header.count("/")- \
                        directory.count("/"), score[symbol][header])

    # this selects the header file with the lowest score
    return {symbol: min(score[symbol], key=lambda k: score[symbol][k]) for symbol in score}


def make_tree(headers: dict[str, [str, str, ...]]) -> dict[str, dict[str, ...]]:
    ''' [recursively] generates a tree dictionary based on path
    {'/usr/include/string.h': ['strcmp']} -> {'usr': {'include': {'string.h': ['strcmp']}}}

    TL;DR: if a key has a list value, it's a file
               if a key has a dict value, it's a directory

    :param headers: a list of header file path
    :returns: a nested dictionary with header files, like described above
    '''
    
    # par is the parent directory/dict
    # e.g. / for /usr/
    par = {}
    for p in headers.copy().keys():
        # dirs must contain / prefix: /usr/ -> usr/
        op = p
        p = p.lstrip('/')
        if p.count('/') == 0:  
            # because it's a file, it can't have children
            par[p] = headers[p]
            continue
        
        ndir, child = p.split('/', 1)
        headers[child] = headers[op]
        del headers[op]

        # make new key if it doesn't exist already
        if ndir not in par:
            par[ndir] = {}
        par[ndir].update({child: headers[child]})
    
    # can't be optimized because prevent par[ndir].update() will be overwritten
    for p in par:
        # par[p] is the child
        if not isinstance(par[p], list):
            # do this all over again for the directory's subdirs
            par[p] = make_tree(par[p])

    return par

def graph_tree(headers: dict[str, dict[str, ...]], offset: str="") -> str:
    ''' [resursively] generates a tree like the unix `tree` utility
    
    :param headers: a nested dictionary with header files, like described above
    :param offset: a string that's put in front of the file/dir name
    :returns: a string of a graphical tree 
    '''

    symbol = "????????? "
    endsymbol = "????????? "
    output = ""
    
    # sort paths (dict keys) as this can't be done to a dictionary
    sheaders = sorted(headers)
    for path in sheaders:  
        __symbol = symbol
        __offset = "???   "
        if path == sheaders[-1]:  # don't add a "connected" symbol if it's last
            __symbol = endsymbol
            __offset = "    "
        

        output += offset + __symbol + path

        # do this all over again (with an increased offset) for subdirs
        if not isinstance(headers[path], list):
            output += "\n"
            output += graph_tree(headers[path], offset=offset+__offset)
            continue
        
        # add content of header files
        output += " : " + ','.join(headers[path]) + '\n'

    return output


def get_format(t: str) -> str: 
    if t == "char*":
        return '\\"%s\\"'
    
    if "*" in t:
        return '%p'  # 0x gets added automatically
    
    return '%lu'
     


class Hook:
    def __init__(self, symbol, signature):
        self.symbol = symbol
        self.signature = signature
        self.rettype = signature.split(" ")[0]
        
        self.__generate_args()
        self.__generate_call()

    def __generate_args(self):
        # parses the signature arguments (used for printf and final hook call)
        self.__args = self.signature[self.signature.index('(')+1:self.signature.index(')')].split(',')
        if self.__args == ['void']:
            self.__args = []

        # the ... which printf may have
        self.has_varargs =  len(self.__args) > 0 and self.__args[-1] == "..."
        #print(__args, file=sys.stderr)
        if self.has_varargs:
            if len(self.__args) != 2:
                print(f'... in the function signature of {self.symbol} are not yet supported', file=sys.stderr)
                print('please try another symbol until this feature has been added', file=sys.stderr)
                sys.exit(1)
        
            self.__args.pop(-1)

        # retrieves the argument type and the name: {'__s1': 'char*'}
        self.args = {x.split(' ')[-1]: x.split(' ')[-2] for x in self.__args}

        # choose what to printf()
        self.printf_args = []
        for name, t in self.args.items():
            self.printf_arg = name + "=" + get_format(t)

            self.printf_args += [self.printf_arg]
        
        # add VARARGS to printf arguments
        if self.has_varargs:
            self.printf_args += ['...']

    def __generate_call(self):
        self.call = ""

        # force the varargs into the function call
        if self.has_varargs:
            self.args['argp'] = 'va_list'
        
        # generates the final function call:
        # ((typeof (&strcmp))__strcmp)(__s1, __s2);
        self.call += self.symbol.upper() + '('
        self.call += ", ".join(self.args.keys())
        self.call += ")"



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
    lib_content += "#include <stdarg.h>\n"

    # other functions may use __printf for the hook
    # it's a dynamic fix I guess

    for symbol in headers:
        lib_content += f"\n#define {symbol.upper()} ((typeof (&{symbol}))__{symbol.upper()})\n"
        lib_content += f"void* __{symbol.upper()};\n"

    lib_content += "\nDl_info __get_dladdr(const void* addr)\n{\n"
    lib_content += "    Dl_info info;\n"
    lib_content += "    dladdr(addr, &info);\n"
    lib_content += "    return info;\n}\n"

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
        
        hook = Hook(symbol, sign)
        print(hook.signature + " + " + hook.call, file=sys.stderr)

        # generates the function signature:
        # int strcmp(const char* __s1,const char* __s2) {
        lib_content += f"\n\n" + hook.signature + "\n{\n"
         
        # adds bloat (like addresses)
        lib_content += "    void* ret = __builtin_return_address(0);\n" 
        if hook.has_varargs:
            lib_content += '       va_list argp;\n'
            lib_content += '       va_start(argp, __format);\n'

        lib_content += "    if ((unsigned long)ret < 0x700000000000) {\n"
        lib_content += "        Dl_info info = __get_dladdr(ret);\n"
        lib_content += "        void* offset = (void*)(ret - info.dli_fbase);\n"

        # the code below generates the printf hook:
        # printf("strcmp(\"%s\", \"%s\") @ 0x%lx\n",
        #     __s1, __s2, (unsigned long)__builtin_return_address(0));
        
        # vvvvvv becomes vvvvvv
 
        # strcmp("PIPESTATUS", "PIPESTATUS") @ 0x55dee0f543e2

        # TO-DO: whenever dprintf is allowed, add toggle to macro
        # redirect all output to /dev/stderr
        lib_content += f'        dprintf(2, "{hook.symbol}('
        lib_content += ", ".join(hook.printf_args)
        lib_content += ') @ %p [%s->%p]'   # for printing the RETADDR
        if hook.rettype == 'void':
            lib_content += ' -> (void)\\n'
        lib_content += '"'

        for k in hook.args.keys():
            lib_content += ", " + k
        
        # prints the return address
        lib_content += ", ret, info.dli_fname, offset);\n"
        
        # returns the return value (if rettype is not void)
        if hook.rettype != 'void':
            lib_content += "        " + hook.rettype + " ret = " + hook.call + ";\n"
            lib_content += '        dprintf(2, " -> ' + get_format(hook.rettype) 
            lib_content += '\\n", ret);\n'
            lib_content += '        return ret;\n'

        # close the if statement and add spaces in case return type void
        lib_content += "    }\n    "        

        # return type void should not have a return statement according to gcc
        if hook.signature.split(" ")[0] != 'void':
            lib_content += 'return '

        lib_content += hook.call + ";\n}\n"

# generates the function loader for original function addresses:
    
    # __attribute__((constructor))
    # static void __load_functions() {
    #     __strcmp = dlsym(RTLD_NEXT, "strcmp");
    # }

    lib_content += "\n\n__attribute__((constructor))\n"
    lib_content += "static void __load_functions()\n{\n"
    for symbol, file in headers.items():
        lib_content += f'    __{symbol.upper()} = dlsym(RTLD_NEXT, "{symbol}");\n'
    lib_content += '}'

    return lib_content


if __name__ == "__main__":
    # enforce arguments
    if len(sys.argv) < 3:
        print("ld-leak.py usage:", file=sys.stderr)
        print("ld-leak.py <symbol1,symbol2,...> <header1,header2,...>", file=sys.stderr)
        sys.exit(1)

    # compile regex query for C functions
    # cannot be refactored due to {s}
    symbols = {}
    for s in sys.argv[1].split(','):
        symbols[s] = re.compile(fr"\n\s*extern\s+(?:[a-zA-Z0-9_]+\*?\s+)+\*?{s}\s*" + \
                        r"\n*\([a-zA-Z0-9_\s\n\*,\.]+\)")

    # the files that match the C function regex (they have the C function(s) in them)
    header_candidates = {s: [] for s in symbols}

    # by using global vars we save mem
    dirs = initiate_search()

    headers = get_best_headers(dirs, header_candidates)

    # this basically shows symbols in which headerfiles
    tree = {}
    for header in headers.values():
        tree[header] = [symbol for symbol in headers if headers[symbol] == header]

    # this converts the paths into a nested dict
    path_dict = make_tree(tree)

    # this nicely displays header tree
    print(graph_tree(path_dict), file=sys.stderr)

    print(generate_lib(headers))

	
