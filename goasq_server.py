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

"""Runs a server for General Open Architecture Security Questionnaire (GOASQ)."""

import logging, os.path, ssl

from cryptoUtils import Cryptor
from customflask import customFlask
from datetime import timedelta
from flask import abort, Flask, jsonify, request, send_from_directory, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sslify import SSLify
from flask.views import MethodView
from functools import wraps
from globals import generate_csrf_token, sharedSession, setup_Defaults, setup_Logging, setup_Notification_For_Errors, setup_Notification_For_Reviews
from postHandler import PostHandler
from renderer import Renderer
from translator import Translator
from werkzeug.exceptions import default_exceptions, HTTPException

template_dir = os.path.dirname(__file__)
app = customFlask(__name__, template_folder=template_dir)
app.config.from_envvar('APP_SETTINGS', silent=True)
translator = Translator()
renderer = Renderer(app)
postHandler = PostHandler(app)

class ServerRequestHandler(MethodView):
  """Request handler for EGS server."""

  def get(self, pathParam):
    logging.debug("ServerRequestHandler.get:%s, pathParam:%s", request.remote_addr, pathParam);
    if request.path == "/loadone":
      return postHandler.handle_request()
    else:
      return renderer.handle_request()

  def post(self, pathParam):
    logging.debug("ServerRequestHandler.post:%s, pathParam:%s", request.remote_addr, pathParam);
    return postHandler.handle_request()

  def head(self, pathParam):
    logging.debug("ServerRequestHandler.head:%s, pathParam:%s", request.remote_addr, pathParam);
    logging.error("ServerRequestHandler.head: Unsupported HEAD request from remote IP: %s, pathParam:%s", request.remote_addr, pathParam);
    return jsonify(error="Not Allowed")
  
  def options(self, pathParam):
    logging.debug("ServerRequestHandler.options:%s, pathParam:%s", request.remote_addr, pathParam);
    logging.error("ServerRequestHandler.options: Unsupported OPTIONS request from remote IP: %s, pathParam:%s", request.remote_addr, pathParam);
    return jsonify(error="Not Allowed")

@app.errorhandler(Exception)
def handle_error(e):
  code = 500
  logging.error('goasq_server.errorhandler:Error in server application:\n\n' + 
    repr(e), exc_info=True)
  if isinstance(e, HTTPException):
      code = e.code
  error = "No donuts for you!"
  if app.config['DEBUG']:
    error = str(e)
  r = jsonify(error=error, csrf=generate_csrf_token())
  logging.error('ServerRequestHandler.handle_error:' + str(r) + '\n\n' + repr(e), exc_info=True)
  return r, code

@app.before_request
def csrf_protect():
  session.permanent = True
  if request.method == "POST":
    token = session.pop('_csrf_token', None)
    if app.config['CERF_STRICT'] == True and (token is None or token != request.form.get('_xsrf_')):
      logging.debug("GLOBAL.csrf_protect:Token mismatch(Session: %s, Request: %s)", 
        str(token), 
        str(request.form.get('_xsrf_')))
      postHandler.clearAndLogoutSession()
      abort(403)
    if request.path != "/login" and request.path != "/logout":
      eUsername = request.cookies.get('u')
      cryptor = Cryptor()
      if eUsername is not None:
        dUsername = cryptor.decrypt(eUsername)
        if session.get('_eUser') != eUsername or session.get('_user') != dUsername:
          postHandler.clearAndLogoutSession()
          abort(401)
      else:
        postHandler.clearAndLogoutSession()
        abort(401)

@app.after_request
def update_response_header(response):
  extension = request.path.split(".")[-1]
  if extension != "html" and "text/html" in response.headers.get('Content-Type'):
    response.headers.set('Content-Type', "application/json; charset=utf-8")
  return response

@app.route('/favicon.ico')
def favicon():
  return send_from_directory(os.path.join(app.root_path, 'build/static'),
    'favicon.ico', mimetype='image/vnd.microsoft.icon')

def add_url_rules():
  viewCounter = 0
  for key in app.config['URL_RULES']:
    if key == '/':
      app.add_url_rule(key, view_func=ServerRequestHandler.as_view('GOASQ_'+str(viewCounter)), defaults={'pathParam': ''})
    else:
      app.add_url_rule(key, view_func=ServerRequestHandler.as_view('GOASQ_'+str(viewCounter)))
    viewCounter += 1

def run_app():
  if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.load_cert_chain(app.config['CERTIFICATE_FILE'], app.config['PRIVATE_KEY_FILE'])
    SSLify(app, ssl_debug=app.config['DEBUG'])
    for ex in default_exceptions:
      app.register_error_handler(ex, handle_error)
    Limiter(app,
      key_func=get_remote_address,
      default_limits=app.config['RATE_LIMITING_DEFAULTS'])
    logging.debug("Rate limiting set to:%s", app.config['RATE_LIMITING_DEFAULTS'])
    app.run(host='0.0.0.0', 
      port=app.config['PORT'], 
      ssl_context=context, 
      threaded=app.config['THREADED'], 
      debug=app.config['DEBUG'])

print("------############################################------")
setup_Defaults(app)
add_url_rules()
setup_Logging(app)
if not app.config['DEBUG']:
  setup_Notification_For_Errors(app)
  setup_Notification_For_Reviews(app)
run_app()
