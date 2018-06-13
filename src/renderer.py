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

import datetime, os.path, time
import randomizer

from flask import abort, current_app, make_response, render_template, request, session
from translator import Translator
from wsgiref.handlers import format_date_time

class Renderer(Translator):

  def __init__(self, app=None):
    super(Renderer, self)
    self.handlers = {'html': self.htmlResponse, \
            '/': self.htmlResponse, \
            'css': self.staticContentResponse, \
            'gif': self.staticContentResponse, \
            'js': self.staticContentResponse, \
            'json': self.jsonContentResponse, \
            'svg': self.staticContentResponse }
    self.contentTypes = {'css': "text/css", \
            'gif': "image/gif", \
            'html': "text/html; charset=utf-8", \
            'js': "application/javascript", \
            'json': "application/json; charset=utf-8", \
            'svg': "image/svg+xml" }
    self.app = app or current_app
    if app is not None:
      self.init_app(app)

  def init_app(self, app):
    self.app.after_request(self.setResponseHeaders)

  def handle_request(self):
    """Serves questionnaire page to the browser."""
    if self.needsFullResponse:
      extension = request.path.split(".")[-1]
      return self.handlers.get(extension, self.defaultResponse)()
    else:
      return make_response("", 304)

  def htmlResponse(self):
    args = request.args.copy()
    response = self.translate_path(request.path)
    if args.get('qpath') is not None:
      qpath = args['qpath']
      return render_template(response, qpath=qpath)
    else:
      return render_template(response)

  def staticContentResponse(self):
    extension = request.path.split(".")[-1]
    response = self.translate_path(request.path)
    r = make_response(render_template(response))
    return r

  def jsonContentResponse(self):
    questionnaires = self.app.config['QUESTIONNAIRES_SERVED']
    for questionnaire in questionnaires:
      if questionnaire in request.path:
        return self.staticContentResponse()
    return self.defaultResponse()

  def defaultResponse(self):
    abort(400)

  def setResponseHeaders(self, response):
    if request.method == "GET" and (response.status_code == 200 or response.status_code == 304):
      now = datetime.datetime.now()
      expires_time = now + datetime.timedelta(seconds=self.app.config['SEND_FILE_MAX_AGE_DEFAULT'])
      expires_time = expires_time.replace(second=0, microsecond=0)
      extension = request.path.split(".")[-1]
      response.headers.set('Content-Type', self.contentTypes.get(extension, "text/html"))
      response.headers['Cache-Control'] = 'public, max-age=' + str(self.app.config['SEND_FILE_MAX_AGE_DEFAULT'])
      response.headers['Expires'] = format_date_time(time.mktime(expires_time.timetuple()))
      response.headers['Last-Modified'] = self.fileLastModified
    elif request.method == "GET":
      response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
      response.headers['Expires'] = '-1'
    return response

  @property
  def fileLastModified(self):
    filePath = self.translate_path(request.path)
    try:
      dt=os.path.getmtime(os.path.join(self.app.root_path, filePath))
      localLastModified = format_date_time(time.mktime(datetime.datetime.utcfromtimestamp(dt).timetuple()))
      return localLastModified
    except:
      pass
    now = datetime.datetime.now()
    return format_date_time(time.mktime(now.timetuple()))

  @property
  def needsFullResponse(self):
    if request.headers.get('If-Modified-Since') is not None:
      remoteLastModified = request.headers.get('If-Modified-Since')
      if self.fileLastModified == remoteLastModified:
        return False
    return True

  @property
  def Id(self):
    """Gets a unique questionnaire ID"""
    qid = ''
    if request is not None and request.path == '/vsaq.html':
      if session.get('qid') is not None and (session['qid']).isalnum() and len(session['qid']) == 12:
        qid = session['qid']
      else:
        qid = randomizer.Id()
        session['qid'] = qid
    else:
      qid = randomizer.Id()
      session['qid'] = qid
    return qid
