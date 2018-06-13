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

import logging, os.path, re

class Translator(object):
  """Translates the request paths to the local directory path"""
  DIRECTORY_MAP = {
    "/": "build/",
    "/login/": "build/login/",
    "/login/css/": "build/login/css/",
    "/login/js/": "build/login/js/",
    "/login/img/": "build/login/img/",
    "/static/": "build/static/",
    "/vsaq/": "vsaq/",
    "/vsaq/static/questionnaire/": "vsaq/static/questionnaire/",
    "/javascript/closure/": "third_party/closure-library/closure/goog/",
    "/javascript/vsaq/": "vsaq/",
    "/third_party/closure/":
    "third_party/closure-library/third_party/closure/",
    "/third_party/closure-templates-compiler/":
    "third_party/closure-templates-compiler/",
    "/build/templates/vsaq/static/questionnaire/":
    "build/templates/vsaq/static/questionnaire/"
  }

  def translate_path(self, path):
    """Serves files from different directories."""
    # Remove all parameters from filenames.
    path = re.sub(r"\?.*$", "", path)
    for prefix, dest_dir in Translator.DIRECTORY_MAP.items():
      translatedPath = dest_dir + path[len(prefix):]
      if path.startswith(prefix) and os.path.isfile(translatedPath):
        logging.debug("Translator.translate_path:%s", translatedPath)
        return translatedPath
    logging.debug("Translator.translate_path:NOT_FOUND:%s. Returned: %s", path, "build/index.html")
    return "build/index.html"
