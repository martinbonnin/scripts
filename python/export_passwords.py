import sys;
import subprocess;

if (len(sys.argv) <= 1):
    print("usage: %s file" % sys.argv[0]);

fd=open(sys.argv[1]);
lines = fd.readlines();

for line in lines:
    line = line.rstrip();
    comp = line.split();
    comp = [v for v in comp if v != ""]
    if (len(comp) == 0):
        #print("empty line");
        continue;
    if (len(comp) == 1):
        print("strange line: " + line);
        continue;
    if (len(comp) <= 2):
        comp.insert(-1, "default_login");

    comp = ["_".join(comp[:-2]), comp[-2], comp[-1]]

    p = subprocess.Popen(["/bin/pass", "insert", "-f", "-p", comp[2], comp[0] + "/" + comp[1]], bufsize=0);
    (out,err) = p.communicate();
    if (p.returncode != 0):
        print("error calling pass");
        print("stdout:");
        print(out);
        print("stderr:");
        print(err);
        sys.exit(1);

