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

from flask import Flask
from flask import Response

SERVER_NAME = 'PK'
METHODS_NOT_ALLOWED = "NOT ALLOWED"

class customFlask(Flask):
  def process_response(self, response):
    response.headers['Server'] = SERVER_NAME
    if response.headers.get('Allow') is not None:
      response.headers['Allow'] = METHODS_NOT_ALLOWED
    response.headers['X-Frame-Options'] = 'deny'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; object-src 'none'; img-src 'self'; script-src 'self' 'unsafe-eval' https://www.google.com/js/maia.js; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.google.com/css/maia.css; font-src https://fonts.gstatic.com;"
    super(customFlask, self).process_response(response)
    return(response)
