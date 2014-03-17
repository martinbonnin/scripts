#!/usr/bin/env python
# coding=utf-8
import smtplib
import sys
import os;
import re;
import random;
import copy;

if (len(sys.argv) != 2):
    print(sys.argv[0] + " [participants_file]");
    sys.exit(1);

fd = open(sys.argv[1], "r");
participants = [];

family = 0;
for line in fd:
    if line[0] != '#':
        m = re.match("([^<]*) *<([^>]*)>", line);
        if (m):
            participants.append({"name": m.group(1), "email": m.group(2), "family": family});
        elif (re.match("^--.*", line)):
            family+=1;
        else: 
            print("participants should be in the form 'name <email>' (and not %s)" % line);
            sys.exit(1);
            
mapping = range(len(participants));

def testMapping():
    for i in xrange(len(participants)):
        if (i == mapping[i]):
            print("same participant %d" % i);
            return False;
        if (participants[i]["family"] == participants[mapping[i]]["family"]):
            print("same family (%d) %d" % (participants[i]["family"], i));
            return False;
    return True;

iteration = 0;
while True:
    print("iteration #" + str(iteration));
    iteration += 1;
    random.shuffle(mapping);
    if (testMapping() == True):
        break;
    
for i in xrange(len(participants)):
    fr = participants[i];
    to = participants[mapping[i]];
    print("%s<%s> \t\t\t\tgives to %s<%s>" % (fr["name"], fr["email"], to["name"], to["email"]));
    
sys.stdout.write("send email [Y/N] ? ");
ret = sys.stdin.readline();
if (ret != "Y\n"):
    print("aborting...");
    sys.exit(2);

for i in xrange(len(participants)):
    fr = participants[i];
    to = participants[mapping[i]];
    print("sending to %s" % to["email"]);
    gmail_user = 'martinbonnin@gmail.com'
    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    smtpserver.login(gmail_user, gmail_pwd)
    header = 'To:' + fr["email"] + '\n' + 'From: Main Innocente <' + gmail_user + '>\n' + 'Subject: la Main Innocente a choisi (version2, j\'espère sans les bugs ce coup ci...).\n'
    header += "Content-Type: text/plain; charset=UTF-8\n";
    msg = header + '\nBonjour ' + fr["name"].strip() + ',\nPour nowel, tu devras offrir un cadeau à ' + to["name"] + '\n';
    msg += 'A bientôt!\nsigné: La Main Innocente\n\n';
    smtpserver.sendmail(gmail_user, fr["email"], msg)
    smtpserver.close()
