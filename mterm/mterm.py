#!/usr/bin/env python

from gi.repository import Gtk, Vte
from gi.repository import GLib
import os, sys, math, argparse
from datetime import datetime

def log(message):
    #sys.stderr.write(message);
    return None;

parser = argparse.ArgumentParser(description='Start several terminals to monitor several boxes.')
parser.add_argument('ips', metavar='ip', type=str, nargs='+',
                   help='ip of each box')
parser.add_argument('-i', metavar='ssh_identity', type=str, nargs=1,
                   help='path to the identity file')
args = parser.parse_args()

count = len(args.ips);
col_count = int(math.ceil(math.sqrt(count)));

vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
grid = Gtk.Grid();
grid.set_column_homogeneous(True)
grid.set_row_homogeneous(True)
grid.set_column_spacing(2)
grid.set_row_spacing(2)

terms = [];

for i in range(count):
    row = i / col_count;
    col = i % col_count;
    term     = Vte.Terminal()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(Gtk.Label(args.ips[i]), False, False, 0);
    box.pack_start(term, True, True, 0);
    grid.attach(box, col, row, 1, 1);
    terms.append(term);
    
vbox.pack_start(grid, True, True, 0);
vbox.pack_start(Gtk.Label("Type below to send a command to all boxes:"), False, False, 0);
entry = Gtk.Entry();

def entry_callback(widget, e):
    text = e.get_text()
    log("Execute: %s" % text)
    e.set_text("")
    for term in terms:
        term.feed_child(text + "\n", -1)

entry.connect("activate", entry_callback, entry)
vbox.pack_start(entry, False, False, 0);

win = Gtk.Window()
win.connect('delete-event', lambda event, data: (log("delete-event\n") or Gtk.main_quit()))
win.set_default_size(1600,800)
win.add(vbox)
win.show_all()

now = datetime.utcnow();
directory = ".mterm/" + now.strftime("logs_%Y_%m_%d_%H_%M_%S");

for term in terms:
    term.fork_command_full(
        Vte.PtyFlags.DEFAULT,
        os.environ['HOME'],
        ["/bin/sh"],
        [],
        GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,
        )

for i in range(count):
    terms[i].feed_child("mkdir -p %s\n" % directory, -1)
    log_file = "%s/%s.txt" % (directory,args.ips[i])
    terms[i].feed_child("script -f %s\n" % log_file, -1)
    terms[i].feed_child("echo \"log_file is %s\"\n" % log_file, -1)
    cmd = "ssh";
    if (len(args.i[0]) > 0):
        cmd += " -i " + args.i[0];
    cmd += " monitor@%s\n" % args.ips[i];
    terms[i].feed_child(cmd, -1)
    
Gtk.main()

