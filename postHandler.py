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

import datetime, json, logging, os, os.path, re, time
import randomizer

from cryptoUtils import Cryptor
from db.dbUtils import dbUtils
from dbHandler import DBHandler
from fileSystemHandler import FileSystemHandler
from flask import abort, current_app, make_response, render_template, request, session
from globals import sharedSession, generate_csrf_token
from ldapUtils import LDAPServer
from nic import NIC
from wsgiref.handlers import format_date_time

nic = NIC()

class PostHandler(object):

  def __init__(self, app=None):
    super(PostHandler, self)
    self.handlers = {'/submit': self.handleSubmit, \
            '/diff': self.handleDiff, \
            '/savedraft': self.handleSaveDraft, \
            '/loadone': self.handleLoadOne, \
            '/status': self.handleStatus, \
            '/submissions': self.handleSubmissions, \
            '/logout': self.handleLogout, \
            '/login': self.handleLogin }
    self.app = app or current_app
    self.dbHandler = DBHandler(app)
    self.fileSystemHandler = FileSystemHandler(app)
    if app is not None:
      self.init_app(app)

  def init_app(self, app):
    self.app.after_request(self.setResponseHeaders)

  def handle_request(self):
    """Handles Post requests from the client."""
    if self.has_permissible_content():
      return self.handlers.get(request.path, self.handleDefault)()
    else:
      abort(413)

  def has_permissible_content(self):
    if request.method == "POST":
      contentLength = request.content_length
      permissibleLength = (self.app.config['PERMISSIBLE_CONTENT_LENGTHS']).get(request.path, 256)
      permissibleContentType = self.app.config['PERMISSIBLE_CONTENT_TYPE']
      logging.debug("Content length for :%s is %d. Permissible Length:%d. Content type:%s", request.path, contentLength, permissibleLength, request.content_type)
      if contentLength is not None and contentLength > permissibleLength and permissibleContentType in request.content_type:
        return False
    return True

  def setResponseHeaders(self, response):
    if request.method == "POST" or request.path == "/loadone":
      now = datetime.datetime.now()
      response.headers.set('Content-Type', "application/json; charset=utf-8")
      response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
      response.headers['Expires'] = '-1'
      response.headers['Last-Modified'] = format_date_time(time.mktime(now.timetuple()))
    return response

  def handleDefault(self):
    abort(403)

  def handleLoadOne(self):
    answers = self.fetchSavedAnswers()
    return '{\"csrf\":\"' + self.csrf_token + \
    '\",\"qid\":\"' + session['qid'] + \
    '\",\"answers\":' + answers + '}'

  def handleSubmissions(self):
    searchType = request.form.get('t')
    qid = request.form.get('id')
    response = self.fetchMetadataFromDB(searchType, qid)
    return '{\"csrf\":\"' + self.csrf_token + \
    '\",\"rows\":' + response + '}'

  def handleLogin(self):
    ldapServer = LDAPServer()
    cryptor = Cryptor()
    username = request.form['u']
    if not re.match(self.app.config['ALLOWED_USERNAME_CHARACTERS'], username):
      logging.error('PostHandler.handle_request:HTTP Bad request. Characters not allowed:' +
        request.path + ':' + username)
      abort(400)
    elif len(username) > self.app.config['LDAP_USERNAME_MAX_LENGTH']:
      logging.error('PostHandler.handle_request:HTTP Bad request. Username too lengthy:' +
          request.path + ':' + username)
      abort(400)
    if self.app.config['ENABLE_TEST_MODE'] == True and self.app.config['DEBUG'] == True:
      if self.app.config['ENABLE_TEST_MODE_LOCAL_ONLY'] == True:
        if request.remote_addr in nic.getNetworkIP():
          results = ldapServer.testResponse()
        else:
          results = ldapServer.authenticateAndSearch(request.form['u'], request.form['p'], request.form['u'])
      else:
        results = ldapServer.testResponse()
    else:
      results = ldapServer.authenticateAndSearch(request.form['u'], request.form['p'], request.form['u'])

    if (results.get('m') is not None):
      session['_sessionId'] = randomizer.Id(128)
      session['_userMail'] = results.get('m')
      session['_userFullName'] = results.get('u')
      session['_user'] = request.form['u']
      session['_auth'] = results.get('a')
      r = make_response('{\"csrf\":\"' + self.csrf_token + \
        '\",\"a\":\"' + str(session['_auth']) + \
        '\",\"u\":\"' + results.get('u') + '\"}')
      r.set_cookie('u', cryptor.encrypt(session['_user']), httponly=True, secure=True)
      return r
    else:
      return '{\"csrf\":\"' + self.csrf_token + \
      '\",\"u\":\"\"}'

  def handleStatus(self):
    if session.get('_auth') == True:
      newStatus = request.form['s']
      qid = request.form['id']
      dbHelper = dbUtils()
      errCode = dbHelper.updateStatus(qid, newStatus)
      if errCode != 0:
        abort(500)
      else:
        self.updateSharedSession(qid, " ", "" if session.get('_app_name') is None else session.get('_app_name'))
        if newStatus == "a":
          logging.critical(self.app.config['MAIL_BODY_APPROVED'])
        else:
          logging.critical(self.app.config['MAIL_BODY_IN_REVIEW'])
      return '{\"csrf\":\"' + self.csrf_token + '\"}'
    else:
      abort(401)

  def handleDiff(self):
    qid = self.getQuestionnaireId()
    dbHelper = dbUtils()
    answers = dbHelper.diffWithLatest(qid)
    return '{\"csrf\":\"' + self.csrf_token + \
    '\",\"qid\":\"' + session['qid'] + \
    '\",\"answers\":' + answers + '}'

  def handleSaveDraft(self):
    qid = self.getQuestionnaireId()
    self.saveQuestionnaireAnswers(qid)
    logging.critical(self.app.config['MAIL_BODY_DRAFT'])
    msg = "This questionnaire (" + qid + ") has been saved as draft."
    return '{\"csrf\":\"' + self.csrf_token + \
    '\",\"msg\":\"'+ msg + \
    '\",\"qid_new\":\"'+ qid + \
    '\",\"qid_saved\":\"'+ qid + '\"}'

  def handleSubmit(self):
    qid = self.getQuestionnaireId()
    self.saveQuestionnaireAnswers(qid)
    self.updateQuestionnaireId()
    logging.critical(self.app.config['MAIL_BODY_SUBMITTED'])
    msg = "Congratulations! This questionnaire (" + qid + ") has been submitted."
    return '{\"csrf\":\"' + self.csrf_token + \
    '\",\"qid_saved\":\"'+ qid + \
    '\",\"msg\":\"'+ msg + \
    '\",\"qid_new\":\"' + session['qid'] + '\"}'

  def handleLogout(self):
    return self.clearAndLogoutSession()

  def clearAndLogoutSession(self):
    for key in session.keys():
      value = session.pop(key)
      logging.info("PostHandler.clearAndLogoutSession: %s popped having value:%s", key, value);
    return '{\"csrf\":\"' + self.csrf_token + '\"}'

  def clearSession(self):
    """Clears the session object"""
    session.pop('qid', None)
    session.pop('_csrf_token', None)

  def getQuestionnaireId(self):
    """Gets the questionnaireId from the request"""
    qid = request.form['id']
    session['qid'] = qid if qid.isalnum() else self.Id
    if session['qid'] == "":
      session['qid'] = self.Id
    return session['qid']

  def updateQuestionnaireId(self):
    """Updates the questionnaireid into the session object"""
    self.clearSession()
    session['qid'] = self.Id

  def saveQuestionnaireAnswers(self, qid):
    """Saves the questionnaire answers from the request"""
    answers = request.form['answers']
    answersDict = json.loads(answers)
    updatedValues = self.updateValues(answersDict)
    appName = "" if updatedValues.get('app_name') is None else updatedValues.get('app_name')
    self.updateSharedSession(qid, self.documentationForUpdatedValues(updatedValues), appName)
    if self.should_use_db:
      self.saveAnswersInDB(updatedValues)
    if self.should_use_file_system:
      self.saveAnswersInFileSystem(updatedValues, qid)

  def saveAnswersInDB(self, answersDict):
    """Saves the questionnaire answers from the request in a database"""
    dbHelper = dbUtils()
    errCode = dbHelper.insertOrUpdateAnswers(answersDict)
    if errCode != 0:
      abort(500)

  def saveAnswersInFileSystem(self, answersDict, qid):
    """Saves the questionnaire answers from the request on file system"""
    global sharedSession
    app = current_app
    namingConvention = json.loads(app.config['FILE_NAMING_CONVENTION'])
    fileName = app.config['UPLOAD_FOLDER'] + qid
    for conventionKey in namingConvention['conventionKeys']:
      if answersDict.get(conventionKey):
        fileName = fileName + '_' + answersDict[conventionKey]
    fileName = fileName + ".txt"
    sharedSession[qid+'_attachment'] = fileName
    answers = json.dumps(answersDict)
    with open(fileName,"wb") as fo:
      fo.write(answers)

  def fetchAnswersFromDB(self):
    """Fetches the questionnaire answers from the database"""
    contents = ''
    app = current_app
    searchQid = request.form['id'] if request.method == 'POST' else request.args.get('id')
    searchTerms = searchQid.split("-")
    if len(searchTerms) > 2:
      abort(400)
    else:
      dbHelper = dbUtils()
      if len(searchTerms) == 2:
        if (searchTerms[0]).isalnum():
          auditId = -1
          try:
            auditId = int(searchTerms[1])
          except Exception as e:
            abort(400)
          finally:
            rows = dbHelper.searchInRevisionHistory(searchTerms[0], auditId)
            if len(rows) != 0:
              rows[0]['app_status'] = "Revision"
        else:
          abort(400)
      else:
        rows = dbHelper.wildCardSearch(searchQid)
    if len(rows) != 0:
      logging.debug("PostHandler.fetchAnswersFromDB:Found %d rows matching the QID:%s", len(rows), searchQid)
      savedResponse = json.loads(rows[0]['app_answer'])
      updatedValues = self.updateValues(savedResponse)
      updatedValues['app_status'] = rows[0]['app_status']
      session['_app_name'] = updatedValues['app_name']
      contents = json.dumps(updatedValues)
      return contents
    logging.debug("PostHandler.fetchAnswersFromDB:Found no row matching the QID:%s", searchQid)
    return '{}'

  def fetchAnswersFromFileSystem(self):
    """Saves the questionnaire answers from file system"""
    contents = ''
    app = current_app
    searchQid = request.form['id'] if request.method == 'POST' else request.args.get('id')
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
      if searchQid.lower() not in file.lower():
        continue
      else:
        filePath = os.path.join(app.config['UPLOAD_FOLDER'], file)
        self.clearSession()
        with open(filePath, "r") as f:
          contents = f.read()
        savedResponse = json.loads(contents)
        updatedValues = self.updateValues(savedResponse)
        contents = json.dumps(updatedValues)
        break
    return contents

  def fetchSavedAnswers(self):
    """Searches for a file based on the search term and then returns the file contents"""
    if self.should_use_db:
      return self.fetchAnswersFromDB()
    if self.should_use_file_system:
      return self.fetchAnswersFromFileSystem()

  def fetchMetadataFromDB(self, searchType, qid):
    """Fetches the questionnaire answer metadata from the database"""
    contents = ''
    app = current_app
    dbHelper = dbUtils()
    statusDict = {'ars': ('Approved', 'In Review', 'Submitted'), \
            'rs': ('In Review', 'Submitted', ''), \
            'ar': ('In Review', 'Approved', ''), \
            'as': ('Submitted', 'Approved', ''), \
            'a': ('Approved','',''), \
            'r': ('In Review','','') }
    if qid is None or qid == "":
      status = statusDict.get(searchType, ('Submitted','',''))
      rows = dbHelper.fetchForSubmissionsStatus(status)
    else:
      rows = dbHelper.loadPreviousRevisions(qid)
    if len(rows) != 0:
      contents = json.dumps(rows)
      return contents
    return '{}'

  def updateValues(self, values):
    """Updates objects(values) that may have been posted based on certain conditions"""
    updatedValues = values.copy()
    if request.path == "/submit":
      qid = session['qid']
      if not values.get('qid'):
        updatedValues['qid'] = qid
      if not values.get('q_version_0_1'):
        updatedValues['q_version_0_2'] = "checked"
      updatedValues['app_status'] = "Submitted"
      updatedValues['login_user'] = session.get('_user')
      updatedValues['login_userMail'] = session.get('_userMail')
      updatedValues['timestamp'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if request.path == "/savedraft":
      updatedValues['app_status'] = "Draft"

    if request.path == "/loadone":
      if values.get('qid'):
        session['qid'] = values['qid']
      else:
        session['qid'] = randomizer.Id()
        updatedValues['qid'] = session['qid']
      if not values.get('q_version_0_1'):
        updatedValues['q_version_0_1'] = "checked"
    return updatedValues

  def updateSharedSession(self, qid, documentation, appName):
    global sharedSession
    if (sharedSession.get('_pending_notifications') is None):
      sharedSession['_pending_notifications'] = []
    (sharedSession['_pending_notifications']).append(qid)
    sharedSession[qid+'_app_documentation'] =  documentation
    sharedSession[qid+'_app_name'] = appName
    sharedSession[qid+'_userMail'] = session['_userMail']
    sharedSession[qid+'_userFullName'] = session['_userFullName']
  
  def documentationForUpdatedValues(self, updatedValues):
    appDocumentation = updatedValues.get('app_documentation')
    appDocumentation = "" if appDocumentation is None else appDocumentation.encode('utf-8')
    significantchanges = updatedValues.get('app_project_significant_change_detail') 
    significantchanges = "" if significantchanges is None else significantchanges.encode('utf-8')
    landscapeChanges = updatedValues.get('app_project_security_change_detail') 
    landscapeChanges = "" if landscapeChanges is None else landscapeChanges.encode('utf-8')
    documentation = "<b>{}:</b><br /><br />{} <br /><br /><b>{}:</b><br /><br />{} <br /><br /><b>{}:</b><br /><br />{}".format("Project overview",
      appDocumentation, 
      "Significant changes",
      significantchanges,
      "Security landscape changes",
      landscapeChanges
      )
    return documentation

  @property
  def Id(self):
    """Gets a unique questionnaire ID"""
    if (request.path == '/submit' or request.path == '/savedraft'):
      if session.get('qid') is not None and (session['qid']).isalnum() and len(session['qid']) == 12:
        qid = session['qid']
      else:
        session['qid'] = randomizer.Id()
    else:
      session['qid'] = randomizer.Id()
    return session['qid']

  @property
  def csrf_token(self):
    """Gets a unique CSRF token"""
    return generate_csrf_token()

  @property
  def local_db_mode(self):
    """Gets the db mode for saving/retrieving responses"""
    db_modes = json.loads(current_app.config['LOCAL_DB_MODE'])
    return db_modes

  @property
  def should_use_db(self):
    return (self.local_db_mode.get('SQLITE') and self.local_db_mode['SQLITE'])

  @property
  def should_use_file_system(self):
    return (self.local_db_mode.get('FILE_SYSTEM') and self.local_db_mode['FILE_SYSTEM'])
