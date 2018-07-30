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

import ast, ldap, logging

from flask import current_app

class LDAPServer(object):

  def __init__(self, app=None):
    super(LDAPServer, self)
    self.app = app or current_app
    self.connection = None

  def authenticateAndSearch(self, username, password, searchAccountName):
    authSuccessful = self.authenticate(username, password)
    userDetails = {}
    if authSuccessful:
      userDetails = self.search(searchAccountName)
      self.disconnect()
    return userDetails

  def authenticate(self, username, password):
    user = username+self.app.config['LDAP_USER_DOMAIN']
    index = self.app.config['LDAP_PROVIDERS_USE_INDEX'];
    logging.debug('Connecting to LDAP provider:%s for user:%s', self.app.config['LDAP_PROVIDERS'][index], user)
    self.disconnect()
    connection = ldap.initialize(self.app.config['LDAP_PROVIDERS'][index])
    connection.protocol_version = ldap.VERSION2
    result = False
    try:
      connection.bind_s(user, password, ldap.AUTH_SIMPLE)
      self.connection = connection
      result = True
      logging.info("User logged in:%s",username)
    except ldap.LDAPError as e:
      self.disconnect()
      self.connection = None
      logging.error("LDAPServer.authenticate:Exception while trying for /login request for user:\n" + 
        username + "\n" + repr(e), exc_info=True)
    except Exception as e:
      self.disconnect()
      logging.error("LDAPServer.authenticate:Exception for user:\n" + username + "\n" + 
        repr(e), exc_info=True)
    return result

  def search(self, searchAccountName):
    search_filter = self.app.config['LDAP_SEARCH_CN']+searchAccountName #"CN=Full Name"
    userDetails = {}
    if self.connection is None:
      return userDetails
    try:
      #if authentication was successful, get the full user data
      result = self.connection.search_s(self.app.config['LDAP_BASE_DN'],ldap.SCOPE_SUBTREE,search_filter)
    except Exception as e:
      self.disconnect()
      logging.error("LDAPServer.search:Exception while searching for account:\n" + searchAccountName + "\n" + 
        repr(e), exc_info=True)
      return userDetails
    rawDict = ast.literal_eval(str(result[0]))[1]

    
    data = { k: v for k, v in rawDict.iteritems() }
    userDetails['t'] = data.get('title')[0]
    userDetails['m'] = data.get('mail')[0]
    userDetails['u'] = data.get('name')[0]
    
    logging.debug("Print the data start")
    for key,val in data.items():
      logging.debug("data item: key: {} value {}".format(key, val))
    logging.debug("Print the data end")

    if self.app.config['REVIEWERS_AD_GROUP'] in data.get('memberOf'):
      logging.info("Get the review approved in the REVIEWS AD Group.")
      userDetails['a'] = True
    
    acctName = data.get("sAMAccountName")[0]
    logging.debug("Account Name {}".format(acctName))
    for reviewer in self.app.config['REVIEWERS_ADDITIONAL']:
        logging.debug("Reviewer: {}".format(reviewer))

    if acctName in self.app.config['REVIEWERS_ADDITIONAL']:
      logging.info("Get the review approved in the REVIEWS ADDITIONAL LIST.")
      userDetails['a'] = True
    
    return userDetails

  def disconnect(self):
    if self.connection is not None:
      self.connection.unbind_s()
      logging.info("Disconnected from LDAP provider!")

  def testResponse(self):
    userDetails = {}
    userDetails['t'] = "Test Title"
    userDetails['m'] = "TestEmail@Example.com"
    userDetails['u'] = "Test User"
    userDetails['a'] = True
    return userDetails
