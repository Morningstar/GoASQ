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

import ConfigParser, sys 

config = ConfigParser.ConfigParser()

def getSections(config_file):
  sections = []
  config.read(config_file)
  for section in config.sections():
    sections.append(section)  
  return sections;

def getKeyValueForSection(config_file, inSection, sectionName):
  sections = getSections(config_file)
  for section in sections:
    if section == inSection:
      print "declare -A %s" % (sectionName)
      for key, val in config.items(section):
        print '%s[%s]="%s"' % (sectionName, key, val)
      return
