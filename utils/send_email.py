#!/usr/bin/env python
from __future__ import print_function, division
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime, sys, smtplib, subprocess

EMAILLIST=["maggiec","fitzgepe","jailwalapa","finneyr","zhaoyong","nelsong","lobanovav","kopardevn","abdelmaksoudaa","meyertj","wongnw","stonelakeak","sevillas2","homanpj","pehrssonec","nousomedr","bianjh"]
EMAILLIST = list(map(lambda x:x+"@nih.gov",EMAILLIST))

def _get_ccbr_email_list():
    """
    Use unix commands to get the list of usernames/emails for all group members of CCBR group on biowulf
    """
    cmd = "grep ^CCBR: /etc/group | awk -F\":\" '{print $NF}'"
    proc = subprocess.run(cmd,shell=True,capture_output=True,text=True)
    exitcode = proc.returncode
    if str(exitcode) == "0":
        userlist = proc.stdout
        userlist = userlist.strip().split(",")
        userlist = list(map(lambda x:x+"@nih.gov",userlist))
        return userlist
    else:
        return EMAILLIST

def send_email(email_subject, email_text, attachment, from_sender="kopardevn@nih.gov", to_receiver="kopardevn@nih.gov"):
    """
    Sends email from sender to receiver attaches email text and html to body
    :param from_sender: <str>
    :param to_receiver: <str>
    :param email_subject: <str>
    :param email_text: <str>
    :param email_html: <str>
    :return:
    """

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = email_subject
    msg['From'] = from_sender
    msg['To'] = ", ".join(to_receiver)

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(email_text, 'plain')
    msg.attach(part1)
    with open(attachment, "rb") as fil:
        part2 = MIMEApplication(fil.read(),Name=basename(attachment))

    # After the file is closed
    part2['Content-Disposition'] = 'attachment; filename="%s"' % basename(attachment)
    msg.attach(part2)

    # Send the message via local SMTP server.
    s = smtplib.SMTP('localhost')
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(from_sender, to_receiver, msg.as_string())
    s.quit()

    return

def main():
    attachment=sys.argv[1]
    email_subject = "CCBR mount weekly disk utilization report!"
    email_text = "Good Morning!\n"
    email_text += "You are receiving this email because you are a member of the \"CCBR\" group on Biowulf. The attached report illustrates:\n"
    email_text += " a. per-user disk utilization\n"
    email_text += " b. per-user duplication\n"
    email_text += " c. list of folders with most duplication\n"
    email_text += " d. searchable details per folder\n"
    email_text += " e. spacesavers score distribution and\n"
    email_text += "other important metrics and visuals."
    email_text += "Please use this report to prioritize your de-duplication efforts and regularly track the 200TB CCBR data mount storage utilization. You will receive an updated report every week.\n"
    email_text += "Have a good day!\n"
    email_text += "Vishal Koparde, Ph.D., CCBR\n"
    #test
    #send_email(email_subject=email_subject,email_text=email_text,attachment=attachment,to_receiver=['kopardevn@nih.gov','vishal.koparde@gmail.com'])
    #prod
    send_email(email_subject=email_subject,email_text=email_text,attachment=attachment,to_receiver=_get_ccbr_email_list())


if __name__ == '__main__':
    main()
