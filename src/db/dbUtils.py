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

import datetime, json, logging, re, sqlite3, time

from flask import request, session

SQLITE_FILE = "build/db/EGS.db"
ANSWERS_TABLE = 'Answers'
AUDIT_TABLE = 'Audit'
ID_COLUMN = 'qid'
ANSWER_COLUMN = 'answer'
NAMESPACE = 'Morningstar:'

class dbUtils(object):

  def __init__(self, sqliteFile=SQLITE_FILE):
    self.sqliteFile = sqliteFile

  def insertOrUpdateAnswers(self, values, timestamp_override=None):
    """Handles a insert/update request."""
    errCode = 0
    tid = ''
    pid = ''
    if values.get(NAMESPACE+'app_tid'):
      tid = self._sanitizeInput(values.get(NAMESPACE+'app_tid'))
    if values.get(NAMESPACE+'app_pid'):
      pid = self._sanitizeInput(values.get(NAMESPACE+'app_pid'))
    if timestamp_override is not None:
      timestamp = timestamp_override
    else:
      timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    try:
      actionItems = self.findActionItems(values)
      c.execute('SELECT 1 FROM {tn} WHERE {cn} = ? '.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), (self._sanitizeInput(values.get('qid')),))
      id_exists = c.fetchone()
      if id_exists:
        c.execute('''UPDATE {tn} \
          SET app_tid = ?, \
          app_pid = ?, \
          app_status = ?, \
          app_name = ?, \
          app_champion = ?, \
          app_team_email = ?, \
          user_name = ?, \
          answer = ?, \
          submitter_email = ?, \
          action_items = ?, \
          timestamp = ? \
          WHERE {cn} = ? '''.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), \
        (tid, \
          pid, \
          self._sanitizeInput(values.get('app_status')), \
          self._sanitizeInput(values.get('app_name')), \
          self._sanitizeInput(values.get('app_champion')), \
          self._sanitizeInput(values.get('app_team_email')), \
          self._sanitizeInput(values.get('login_user')) , \
          json.dumps(values), \
          self._sanitizeInput(values.get('login_userMail')), \
          "" if actionItems is None else actionItems, \
          timestamp, \
          self._sanitizeInput(values.get('qid'))))
      else:
        c.execute('''INSERT OR REPLACE INTO \
          {tn} (qid, app_status, app_tid, app_pid, app_name, app_champion, app_team_email, user_name, submitter_email, action_items , timestamp, answer) \
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''.\
        format(tn=ANSWERS_TABLE), \
          (values.get('qid'), \
            self._sanitizeInput(values.get('app_status')), \
            tid, \
            pid, \
            self._sanitizeInput(values.get('app_name')), \
            self._sanitizeInput(values.get('app_champion')), \
            self._sanitizeInput(values.get('app_team_email')), \
            self._sanitizeInput(values.get('login_user')), \
            self._sanitizeInput(values.get('login_userMail')), \
            "" if actionItems is None else actionItems, \
            timestamp, \
            json.dumps(values)))
    except sqlite3.Error as e:
      errCode = -1
      logging.error('dbUtils.insertOrUpdateAnswers:Error while inserting or updating answers:' + 
        json.dumps(values) + '\n\n' + repr(e), exc_info=True)
    except Exception as e:
      errCode = -2
      logging.error('dbUtils.insertOrUpdateAnswers:General exception during insert/update:' + 
        json.dumps(values) + '\n\n' + repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return errCode

  def updateStatus(self, qid, status, user):
    """Handles a status update request."""
    errCode = 0
    reviewStatus = "In Review"
    if status == "a":
      reviewStatus = "Approved"
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    try:
      c.execute('SELECT answer FROM {tn} WHERE {cn} = ? '.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), (self._sanitizeInput(qid),))
      id_exists = c.fetchone()
      if id_exists:
        answers = json.loads(id_exists[0])
        answers['app_status'] = reviewStatus
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        answers['timestamp'] = timestamp
        c.execute('''UPDATE {tn} \
          SET app_status = ?, \
          user_name = ?, \
          answer = ?, \
          timestamp = ? \
          WHERE {cn} = ? '''.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), (reviewStatus, user, json.dumps(answers), timestamp, self._sanitizeInput(qid)))
      else:
        errCode = 500
    except sqlite3.Error as e:
      errCode = -1
      logging.error('dbUtils.updateStatus:Error while updating status:' + 
        '\n\n' + repr(e), exc_info=True)
    except Exception as e:
      errCode = -2
      logging.error('dbUtils.updateStatus:General exception during status update:' + 
        '\n\n' + repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return errCode

  def wildCardSearch(self, keyword):
    """Handles a search/lookup request for a wild card keyword."""
    keyword = self._sanitizeInput(keyword)
    errCode = 0
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    rows = []
    try:
      c.execute('''SELECT * FROM {tn} \
        WHERE app_tid like ? or \
        app_name like ? or \
        app_champion like ? or \
        qid like ? or \
        app_pid like ?'''.\
        format(tn=ANSWERS_TABLE), \
        ('%'+keyword+'%', '%'+keyword+'%', '%'+keyword+'%', '%'+keyword+'%', '%'+keyword+'%'))
      all_rows = c.fetchall()
      rows = [{'qid':tup[0],
      'app_status':tup[1],
      'app_tid':tup[2],
      'app_pid':tup[3],
      'app_name':tup[4],
      'app_champion':tup[5],
      'app_team_email':tup[6],
      'modified_by':tup[7], 
      'last_modified':tup[8],
      'app_answer':tup[9],
      'comments':tup[10],
      'action_items':tup[11],
      'submitter_email':tup[12]} for tup in all_rows]
    except sqlite3.Error as e:
      logging.error('dbUtils.wildCardSearch:Error while searching for ' + str(keyword) + ' in answers:\n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.wildCardSearch:General exception during wildCardSearch for ' + str(keyword) + ' in answers:\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return rows

  def searchInRevisionHistory(self, qid, auditId):
    """Handles a search/lookup request for a given QID and audit ID."""
    errCode = 0
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    rows = []
    try:
      c.execute('''SELECT app_status, app_name, answer FROM {tn} \
        WHERE audit_id = ? and \
        qid = ? '''.\
        format(tn=AUDIT_TABLE), \
        (self._sanitizeInput(auditId), self._sanitizeInput(qid)))
      all_rows = c.fetchall()
      rows = [{'app_status':tup[0],
      'app_name':tup[1],
      'app_answer':tup[2]} for tup in all_rows]
    except sqlite3.Error as e:
      logging.error('dbUtils.searchInRevisionHistory:Error while searching for auditId:' + str(auditId) + ' in audit:\n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.searchInRevisionHistory:General exception while searching for auditId:' + str(auditId) + ' in Audit:\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return rows

  def fetchForSubmissionsStatus(self, status):
    """Handles a load submissions request."""
    errCode = 0
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    rows = []
    try:
      c.execute('''SELECT qid, app_status, app_tid, app_pid, app_name, app_champion, app_team_email, user_name, timestamp, submitter_email, action_items FROM {tn} \
        WHERE app_status in (?, ?, ?, ?) order by app_name asc, timestamp desc'''.\
        format(tn=ANSWERS_TABLE), \
        status)
      all_rows = c.fetchall()
      rows = [{'Col0_qid':tup[0],
      'Col1_app_status':tup[1],
      'Col5_app_tid':tup[2],
      'Col6_app_pid':tup[3],
      'Col2_app_name':tup[4],
      'Col3_app_champion':tup[5],
      'Col4_app_team_email':tup[6],
      'Col7_last_modified_by':tup[7], 
      'Col8_last_modified':tup[8],
      'Col9_submitter_email':tup[9],
      'ColA_action_items':tup[10]} for tup in all_rows]
    except sqlite3.Error as e:
      logging.error('dbUtils.fetchForSubmissionsStatus:Error while fetching submissions \n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.fetchForSubmissionsStatus:General exception while fetching submissions:\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return rows

  def diffWithLatest(self, qid):
    """Handles a search/lookup request in history for diff against the latest."""
    qid = self._sanitizeInput(qid)
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    result = ''
    try:
      c.execute('SELECT 1 FROM {tn} WHERE {cn} = ? '.\
        format(tn=AUDIT_TABLE, cn=ID_COLUMN), (qid,))
      id_exists = c.fetchone()
      if id_exists:
        c.execute('''SELECT {cn1} FROM {tn} 
          WHERE {cn2} = ?
          ORDER BY audit_timestamp DESC
          LIMIT 1'''.\
          format(tn=AUDIT_TABLE, cn1=ANSWER_COLUMN, cn2=ID_COLUMN), (qid,))
        result = c.fetchone()
      else:
        c.execute('''SELECT {cn1} FROM {tn} 
          WHERE {cn2} = ?
          ORDER BY timestamp DESC
          LIMIT 1'''.\
          format(tn=ANSWERS_TABLE, cn1=ANSWER_COLUMN, cn2=ID_COLUMN), (qid,))
        result = c.fetchone()
    except sqlite3.Error as e:
      logging.error('dbUtils.diffWithLatest:SQLite Error while auditing/diff for QID:' + str(qid) + ' :\n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.diffWithLatest:General exception while auditing/diff for QID:' + str(qid) + ' :\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return '{}' if result is None else result[0]

  def loadPreviousRevisions(self, qid):
    """Handles a search/lookup request for revisions."""
    qid = self._sanitizeInput(qid)
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    rows = []
    try:
      c.execute('''SELECT (qid || "-" || audit_id) AS audit_id, app_status, app_tid, app_pid, app_name, \
        app_champion, app_team_email, user_name, timestamp, submitter_email, action_items \
        FROM {tnRight} \
        where qid = ? \
        union all \
        SELECT qid, app_status, app_tid, app_pid, app_name, \
        app_champion, app_team_email, user_name, timestamp, submitter_email, action_items \
        FROM {tnLeft} \
        where qid = ? \
        order by timestamp desc'''.\
        format(tnLeft=ANSWERS_TABLE, tnRight=AUDIT_TABLE), \
        (qid,qid))
      all_rows = c.fetchall()
      rows = [{'Col0_qid':tup[0],
      'Col1_app_status':tup[1],
      'Col5_app_tid':tup[2],
      'Col6_app_pid':tup[3],
      'Col2_app_name':tup[4],
      'Col3_app_champion':tup[5],
      'Col4_app_team_email':tup[6],
      'Col7_last_modified_by':tup[7], 
      'Col8_last_modified':tup[8],
      'Col9_submitter_email':tup[9],
      'ColA_action_items':tup[10]} for tup in all_rows]
    except sqlite3.Error as e:
      logging.error('dbUtils.loadPreviousRevisions:SQLite Error while loading revisions for QID:' + str(qid) + ' :\n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.loadPreviousRevisions:General exception loading revisions for QID:' + str(qid) + ' :\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.commit()
      conn.close()
    return rows

  def deleteSubmission(self, qid):
    """Deletes an existing submission with given questionnaireID."""
    qid = self._sanitizeInput(qid)
    conn = sqlite3.connect(self.sqliteFile)
    conn.text_factory = str
    c = conn.cursor()
    errCode = 500
    questionnaireID = self._sanitizeInput(qid)
    try:
      c.execute('SELECT qid FROM {tn} WHERE {cn} = ? '.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), (questionnaireID,))
      id_exists = c.fetchone()
      if id_exists:
        c.execute('''DELETE FROM {tn} \
          WHERE {cn} = ? '''.\
        format(tn=ANSWERS_TABLE, cn=ID_COLUMN), (questionnaireID,))
        conn.commit()
        errCode = 0
    except sqlite3.Error as e:
      logging.error('dbUtils.deleteSubmission:SQLite Error while deleting for QID:' + str(questionnaireID) + ' :\n\n' + 
        repr(e), exc_info=True)
    except Exception as e:
      logging.error('dbUtils.deleteSubmission:General exception deleting for QID:' + str(questionnaireID) + ' :\n\n' + 
        repr(e), exc_info=True)
    finally:
      conn.close()
    return errCode

  def findActionItems(self, answersDict):
    JIRA_REGEX = '[A-Z]{2,}-\d+'
    jira_issue_regex = re.compile(JIRA_REGEX)
    actionItems = None
    for key in answersDict:
      value = answersDict[key]
      matches = jira_issue_regex.findall(value)
      if len(matches) > 0:
        for JIRA in matches:
          if actionItems is None:
            actionItems = JIRA
          else:
            actionItems = actionItems + "," + JIRA
    logging.debug("All action items for QID: %s :%s", answersDict.get('qid','NA'), str(actionItems))
    return actionItems

  def _sanitizeInput(self, input):
    if input is not None:
      input = str(input)
      for ch in ['\'',';', '--', '|']:
        if ch in input:
          input=input.replace(ch,"")
    return input
