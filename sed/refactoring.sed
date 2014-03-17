# definitions to function pointers: 'int foo(int a);' => 'int (*foo)(int a);'
s/^\(.*[ \*]\)\([a-zA-Z0-9_]*\)\((.*\)/\1(*\2)\3/g

#remove tabs
s/\t/    /g

# definitions to dll resolving: 'int (*foo)(int a);' => RESOLVE_SYMBOL(int, foo, (int a))'
s/^ *\([^(]*\)(\*\([^ ]*\)) *(\(.*\));/RESOLVE_SYMBOL(\1, \2, \3);/g
s/  *\*/ */g
s/ *,/,/g


