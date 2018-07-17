# Copyright 2018 Morningstar Inc. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging, logging.handlers, os, urllib 

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import MimeTypes
from threading import Thread

class BufferingSMTPHandler(logging.handlers.BufferingHandler):
    def __init__(self, mailhost, fromaddr, toaddrs, subject, capacity,
                 logging_format, mailbody, files=[], sendAttachments=False, 
                 identifier=None, callback=None, threadapp=None, threadsharedSession=None):
        logging.handlers.BufferingHandler.__init__(self, capacity)
        self.mailhost = mailhost
        self.mailport = None
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.mailbody = mailbody
        self.formatter = logging_format
        self.files = files
        self.sendAttachments = sendAttachments
        self.callback = callback
        self.identifier = identifier
        self.identity = ''
        self.setFormatter(logging.Formatter(logging_format))
        self.threadapp = threadapp
        self.threadsharedSession = threadsharedSession

    def flush(self):
        if len(self.buffer) > 0:
            try:
                if callable(self.identifier):
                    self.identity = self.identifier()
                self.sendEmail()
            except Exception as e:
                self.buffer = []
                logging.warning("BufferingSMTPHandler.flush:Sending email failed.\n\n" + 
                    repr(e), exc_info=True)
                self.handleError(e)

    def sendEmail(self):
        import smtplib
        port = self.mailport
        if not port:
            port = smtplib.SMTP_PORT
        smtp = smtplib.SMTP(self.mailhost, port)
        if not self.canSendMail:
            smtp.quit()
            self.buffer = []
            return
        if self.sendAttachments:
            smtp.sendmail(self.sender, self.recipients, self.multipartMessage.as_string())
        else:
            smtp.sendmail(self.sender, self.recipients, self.simpleMessage)
        smtp.quit()
        self.buffer = []
        logging.info("Sent email:Subject:%s, to:%s, level:%s",
            self.emailSubject, self.csvRecepients, logging.getLevelName(self.level))
        if self.callback is not None and callable(self.callback):
            self.callback(self.identity)

    @property
    def csvRecepients(self):
        if isinstance(self.recipients, list):
            toaddrs = ','.join(self.recipients)
        else:
            toaddrs = self.recipients
        return toaddrs
    
    @property
    def recipients(self):
        if self.level == logging.ERROR:
            recipients = self.toaddrs
        else:
            recipients = self.toaddrs + [self.sender]
        return recipients

    @property
    def sender(self):
        if callable(self.fromaddr):
            fromaddr = self.fromaddr(self.identity)
        else:
            fromaddr = self.fromaddr
        return fromaddr

    @property
    def emailSubject(self):
        if callable(self.subject):
            subject = self.subject(self.identity, self.threadapp, self.threadsharedSession)
        else:
            subject = self.subject
        return subject

    @property
    def messageBody(self):
        msg_body = ""
        for record in self.buffer:
            if record.levelno == self.level:
                s = self.format(record)
                msg_body += s + "\r\n"
            if msg_body != "" and callable(self.mailbody):
                msg_body = self.mailbody(msg_body, self.identity, self.threadapp, self.threadsharedSession)
        return msg_body

    @property
    def fileAttachments(self):
        if callable(self.files):
            files = self.files(self.identity)
        else:
            files = self.files
        return files

    @property
    def simpleMessage(self):
        if self.level == logging.ERROR:
            msg = "From: {}\r\nTo: {}\r\nSubject: {}\r\n\r\n{}".format(self.sender, self.csvRecepients,
                                                                   self.emailSubject, self.messageBody)
        else:
            msg = "From: {}\r\nTo: {}\r\nCC: {}\r\nSubject: {}\r\n\r\n{}".format(self.sender, self.csvRecepients,
                                                                   self.sender, self.emailSubject, self.messageBody)
        return msg

    @property
    def multipartMessage(self):
        msg = MIMEMultipart()
        msg['From'] = self.sender
        msg['To'] = self.csvRecepients
        msg['Subject'] = self.emailSubject
        if self.level != logging.ERROR:
            msg['cc'] = self.sender
        msg.attach(MIMEText(self.messageBody, 'html'))
        for path in self.fileAttachments:
            if path is not None:
                mime = MimeTypes()
                url = urllib.pathname2url(path)
                mime_type = mime.guess_type(url)
                if mime_type[0] == "text/plain":
                    part = MIMEBase('application', "octet-stream")
                    with open(path, 'rb') as file:
                        part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition',
                                    'attachment; filename="{}"'.format(os.path.basename(path)))
                    msg.attach(part)
                else:
                    logging.warning("BufferingSMTPHandler.multipartMessage:Found an unexpected mime-type:%s at path:%s", 
                        mime_type[0], path)
        return msg

    @property
    def canSendMail(self):
        if self.emailSubject == '' or self.sender == '' or self.messageBody == '':
            self.buffer = []
            return False
        return True

class ThreadedSMTPHandler(BufferingSMTPHandler):
    def flush(self):
        thread = Thread(target=super(ThreadedSMTPHandler, self).flush, args=())
        thread.start()
