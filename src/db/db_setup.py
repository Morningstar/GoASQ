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

import datetime, fnmatch, json, os, random, string, sqlite3


from dbUtils import dbUtils

ADMIN_USER = "pjha"
ADMIN_USER_EMAIL = "praveen.jha@morningstar.com"
DB_FILE_PATH = "../build/db/GoASQ.db"
DB_BACKUP_FILENAME = "DB_Backup_GoASQ"
INDEX_ANSWERS = "AnswersIndex.txt"
TABLE_ANSWERS_SCHEMA = "Answers.txt"
TABLE_AUDIT_SCHEMA = "Audit.txt"
TABLE_ANSWERS = "Answers"
TABLE_AUDIT = "Audit"
TRIGGER_AFTER_UPDATE_ANSWERS = "After_Update_On_Answers.txt"
TRIGGER_BEFORE_DELETE_ANSWERS = "Before_Delete_On_Answers.txt"
TRIGGER_BEFORE_DELETE_AUDIT = "Before_Delete_On_Audit.txt"
TRIGGER_BEFORE_UPDATE_AUDIT = "Before_Update_On_Audit.txt"

def create_table(sqlite_file, table_schema):
    """
    Creates a new SQLite database file if it doesn't exist yet.
    The database created will consists of table / columns as designated by table_schema
    """
    # open connection to a sqlite file object, create if not existing already
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    schema = 'CREATE TABLE ' + table_schema
    try:
        c.execute(schema)
        conn.commit()
    except:
        print "WARNING! DB Setup encountered an error during creation of table."
    finally:
        conn.close()

def create_trigger(sqlite_file, trigger):
    """Creates a new trigger"""
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    schema = 'CREATE TRIGGER IF NOT EXISTS ' + trigger
    try:
        c.execute(schema)
        conn.commit()
    except:
        print "WARNING! DB Setup encountered an error during setting up trigger."
    finally:
        conn.close()

def create_index(sqlite_file, index):
    """Creates a new index"""
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    schema = 'CREATE INDEX IF NOT EXISTS ' + index
    try:
        c.execute(schema)
        conn.commit()
    except:
        print "WARNING! DB Setup encountered an error during setting up index."
    finally:
        conn.close()

def importRecursivelyFromDirectory(sqlite_file=None, input_dir=None):
    if sqlite_file == "":
        sqlite_file = None
    if input_dir == "":
        input_dir = None
    if sqlite_file is None:
        sqlite_file = DB_FILE_PATH
    if input_dir is None or not os.path.exists(input_dir):
        raise Exception("Input directory path does not exist:\n" + str(input_dir))
    if not os.path.exists(sqlite_file):
        raise Exception("DB File does not exist:\n" + str(sqlite_file))
    root = input_dir
    current_dir_path = ""
    for root, directories, filenames in os.walk(input_dir):
        for filename in sorted(filenames, key=lambda filename: #fnmatch.filter(files, '*.txt'):
                    os.path.getmtime(os.path.join(root, filename))):
            filePath = os.path.join(root, filename)
            dt=os.path.getmtime(filePath)
            lastModified = datetime.datetime.utcfromtimestamp(dt)
            dir_path = os.path.dirname(filePath)
            try:
                with open(filePath, "r") as f:
                    contents = f.read()
                    savedResponse = json.loads(contents)
                    if current_dir_path != dir_path:
                        current_dir_path = dir_path
                        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(12))
                        qid = savedResponse.get('qid', token)
                        print "Now populating for QID:" + qid
                    savedResponse['qid'] = qid
                    savedResponse['app_status'] = savedResponse.get('app_status', "Submitted")
                    savedResponse['login_user'] = savedResponse.get('login_user', ADMIN_USER)
                    savedResponse['login_userMail'] = savedResponse.get('login_userMail', ADMIN_USER_EMAIL)
                    if not savedResponse.get('q_version_0_2'):
                        savedResponse['q_version_0_1'] = "checked"
                    timestamp = lastModified.strftime("%Y-%m-%d %H:%M:%S")
                    dbHelper = dbUtils(sqlite_file)
                    errCode = dbHelper.insertOrUpdateAnswers(savedResponse, timestamp)
                    if errCode != 0:
                        print "WARNING: Failed inserting into DB for " + filePath
            except:
                print "WARNING: Failed loading from " + filePath
                pass

def deleteSubmission(sqlite_file=None, q_id=None):
    if sqlite_file == "":
        sqlite_file = None
    if q_id == "":
        q_id = None
    if sqlite_file is None:
        sqlite_file = DB_FILE_PATH
    if q_id is None or not q_id.isalnum() or len(q_id) != 12:
        raise Exception("Invalid Questionnaire ID:\n" + str(q_id))
    if not os.path.exists(sqlite_file):
        raise Exception("DB File does not exist:\n" + str(sqlite_file))
    try:
        dbHelper = dbUtils(sqlite_file)
        errCode = dbHelper.deleteSubmission(q_id)
        if errCode != 0:
            print "WARNING: Failed deleting from DB for " + str(q_id)
        else:
            print "Deleting submission from DB for " + str(q_id)
    except:
        print "WARNING: Failed deleting from DB for " + str(q_id)
        pass

def restoreFromBackup(sqlite_file=None, input_dir=None):
    return "NOT YET IMPLEMENTED"

def exportToJSON(sqlite_file=None, output_dir=None):
    if sqlite_file == "":
        sqlite_file = None
    if output_dir == "":
        output_dir = None
    if sqlite_file is None:
        sqlite_file = DB_FILE_PATH
    if output_dir is not None and not os.path.exists(output_dir):
        raise Exception("Path does not exist:\n" + output_dir)
    if os.path.exists(sqlite_file):
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        c.row_factory = lambda cursor, row: row[0]
        tableList = "SELECT name FROM sqlite_master WHERE type='table';"
        try:
            c.execute(tableList)
            all_tables = c.fetchall()
            dbJSON = {}
            for table in all_tables:
                columnList = "pragma table_info("+table+");"
                c.row_factory = lambda cursor, row: row[1]
                c.execute(columnList)
                all_columns = c.fetchall()
                c.row_factory = None
                c.execute('SELECT * FROM '+table)
                all_rows = c.fetchall()
                result = []
                rowNumber = 0
                columnNumber = 0
                for row in all_rows:
                    result.append({})
                    for column in all_columns:
                        result[rowNumber][str(column)] = row[columnNumber]
                        columnNumber = columnNumber + 1
                    rowNumber = rowNumber + 1
                    columnNumber = 0
                dbJSON[str(table)] = result
            dbBackup = json.dumps(dbJSON)
            timeStamp = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")
            fileName = DB_BACKUP_FILENAME + "_" + timeStamp + ".txt"
            if output_dir is not None:
                fileName = os.path.join(output_dir, fileName)
                with open(fileName,"wb") as fo:
                    fo.write(dbBackup)
            else:
                fileName = os.getcwd() + "/" + fileName
        except IndexError:
            raise
        conn.close()
    else:
        raise Exception("DB File does not exist:\n" + sqlite_file)
    return fileName

def first_time_setup():
    table_schemas = [TABLE_ANSWERS_SCHEMA, TABLE_AUDIT_SCHEMA]
    for schema in table_schemas:
        with open("table_schemas/"+schema, "r") as f:
            tableSchema = f.read()
            create_table(DB_FILE_PATH, tableSchema)

    triggers = [TRIGGER_AFTER_UPDATE_ANSWERS, TRIGGER_BEFORE_DELETE_ANSWERS, TRIGGER_BEFORE_DELETE_AUDIT, TRIGGER_BEFORE_UPDATE_AUDIT]
    for trigger in triggers:
        with open("triggers/"+trigger, "r") as f:
            triggerSchema = f.read()
            create_trigger(DB_FILE_PATH, triggerSchema)
    indices = [INDEX_ANSWERS]
    for index in indices:
        with open("index/"+index, "r") as f:
            indexSchema = f.read()
            create_index(DB_FILE_PATH, indexSchema)
