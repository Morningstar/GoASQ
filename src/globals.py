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

import argparse, logging, randomizer

from smtp_handler import ThreadedSMTPHandler
from flask import current_app, request, session
from logging import Formatter
from logging.handlers import RotatingFileHandler

sharedSession = {}

def readonly():
  try:
    hasInvalidSession = (session.get('_sessionId') is None)
    logging.debug("GLOBAL.readonly:" + str(hasInvalidSession));
    logging.debug("GLOBAL.readonly:Session details:%s, %s, %s, %s", 
      session['_sessionId'], 
      session['_userMail'],
      session['_user'],
      session['_userFullName']
      );
    return hasInvalidSession
  except:
    logging.debug("GLOBAL.readonly:" + str(True));
    return True

def getUsername():
  try:
    if (session.get('_userFullName') is not None):
      return session.get('_userFullName')
    else:
      return ''
  except:
    return ''

def getApprovalAuthority():
  try:
      if (session.get('_auth') is not None):
        return session.get('_auth')
      else:
        return False
  except:
    return False

def generate_questionnaireID():
  if (request.method == "GET" and request.path == '/vsaq.html') or \
  (request.method == "POST" and request.path == '/submit'):
    if session.get('qid') is not None and (session['qid']).isalnum() and len(session['qid']) == 12:
      qid = session['qid']
    else:
      session['qid'] = randomizer.Id()
  return session['qid']

def generate_csrf_token():
  if '_csrf_token' not in session or session['_csrf_token'] == None:
    session['_csrf_token'] = randomizer.Id(32)
  return session['_csrf_token']

def setup_Defaults(app=None):
  app.jinja_env.globals['csrf_token'] = generate_csrf_token
  app.jinja_env.globals['q_id'] = generate_questionnaireID
  app.jinja_env.globals['readonly'] = readonly
  app.jinja_env.globals['user'] = getUsername
  app.jinja_env.globals['auth'] = getApprovalAuthority

def setup_Logging(app=None):
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='count', default=0)
  parser.add_argument('-d', '--debug', action='count', default=0)
  parser.add_argument('-t', '--testmode', action='count', default=0)
  args = parser.parse_args()
  levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
  level = levels[min(len(levels)-1,args.verbose)]  # capped to number of levels
  logging.basicConfig(level=level,
                      format="%(asctime)s %(levelname)s %(message)s")
  logging.getLogger().setLevel(level)
  print("Log level set to:" + logging.getLevelName(level))
  if args.debug > 0 and not app.config['DEBUG']:
    logging.warning("################################################################################")
    logging.warning("Server launched with debug config but debug is set to False in app.config.debug.")
    logging.warning("#################################################################################")
  if not app.config['DEBUG']:
    logFile_handler = RotatingFileHandler(app.config['LOG_FILE_NAME'], 
      mode='a', maxBytes=app.config['LOG_FILE_MAX_SIZE'], 
      backupCount=app.config['LOG_FILE_BACKUP_COUNT'], 
      encoding=None, delay=False)
    logFile_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(logFile_handler)
  if args.testmode > 0:
    if not args.debug > 0 or not app.config['DEBUG']:
      logging.warning("Server was attempted to launch in Test-Mode but failed. Please relaunch \
        with --debug in parameter and set app.config.debug variable DEBUG to True.")
    else:
      app.config['ENABLE_TEST_MODE'] = True
      logging.warning("#############################################################################")
      logging.warning("Server launched In TEST-MODE. Test User will be logged-in only from localhost")
      logging.warning("#############################################################################")

def setup_Notification_For_Errors(app=None):
  if not app.config['DEBUG']:
    admins = app.config['SERVER_ADMINS']
    logging_format = '''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    '''
    mail_handler = ThreadedSMTPHandler(mailhost=app.config['MAIL_SERVER_INTERNAL'],
                               fromaddr=app.config['MAIL_SENDER'],
                               toaddrs=admins, 
                               subject='Application failure for EGS',
                               capacity=app.config['ERROR_DIGEST_CAPACITY'],
                               logging_format=logging_format,
                               mailbody='',
                               files=[],
                               sendAttachments=False)
    mail_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(mail_handler)
    logging.info('Mail handler (Errors) set.')

def setup_Notification_For_Reviews(app=None):
  reviewers = app.config['REVIEWERS']
  logging_format = '%(message)s'
  mail_handler = ThreadedSMTPHandler(mailhost=app.config['MAIL_SERVER_INTERNAL'],
                             fromaddr=get_sender_email,
                             toaddrs=reviewers, 
                             subject=mail_subject,
                             capacity=1,
                             logging_format=logging_format,
                             mailbody=mail_body,
                             files=get_attachments,
                             sendAttachments=app.config['MAIL_SEND_ATTACHMENT'],
                             identifier=get_mail_identity, 
                             callback=mail_job_finished)
  mail_handler.setLevel(logging.CRITICAL)
  logging.getLogger().addHandler(mail_handler)
  logging.info('Mail handler (Reviews) set.')

def mail_subject(qid):
  app = current_app
  try:
    global sharedSession
    return (app.config['MAIL_SUBJECT']).format(qid, sharedSession.get(qid+'_app_name'))
  except:
    return ''

def mail_body(record, qid):
  app = current_app
  try:
    global sharedSession
    host = app.config['HOST_HOME_URL'];
    return record.format(host, qid, qid,
      sharedSession.get(qid+'_app_documentation'), sharedSession.get(qid+'_userFullName'))
  except:
    return ''

def get_sender_email(qid):
  try:
    global sharedSession
    return sharedSession.get(qid+'_userMail')
  except:
    return ''

def get_mail_identity():
  try:
    global sharedSession
    pendingNotifications = sharedSession.get('_pending_notifications')
    logging.debug('Pending email notifications:%s', str(pendingNotifications))
    qid = pendingNotifications.pop()
    logging.info('Sending email for QuestionnaireID:%s', qid)
    return qid
  except:
    return ''

def get_attachments(qid):
  try:
    global sharedSession
    return [sharedSession.get(qid+'_attachment')]
  except:
    return []

def mail_job_finished(qid):
    global sharedSession
    sharedSession.pop(qid+'_app_documentation')
    sharedSession.pop(qid+'_app_name')
    sharedSession.pop(qid+'_userMail')
    sharedSession.pop(qid+'_userFullName')
    logging.debug('Pending email notifications:%s', str(sharedSession.get('_pending_notifications')))
