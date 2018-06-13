/**
 * @license
 * Copyright 2016 Google Inc. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @fileoverview Reference implementation for VSAQ (client side only).
 */

goog.provide('vsaq');
goog.provide('vsaq.Qpage');

goog.require('goog.Uri');
goog.require('goog.debug.Error');
goog.require('goog.dom');
goog.require('goog.events.EventType');
goog.require('goog.json');
goog.require('goog.net.XhrIo');
goog.require('goog.object');
goog.require('goog.storage.Storage');
goog.require('goog.storage.mechanism.HTML5LocalStorage');
goog.require('goog.string.path');
goog.require('goog.structs');
goog.require('vsaq.QpageBase');
goog.require('vsaq.QuestionnaireEditor');
goog.require('vsaq.utils');



/**
 * Initialize the questionnaire page.
 * @extends {vsaq.QpageBase}
 * @constructor
 */
vsaq.Qpage = function() {
  goog.base(this);
  var mechanism = new goog.storage.mechanism.HTML5LocalStorage();
  this.storage = new goog.storage.Storage(mechanism);
  this.questionnaireID = '';
  this.remoteQuestionnaireID = goog.dom.getElement('q_id').innerText;
  this.questionnaire.setReadOnlyMode(this.isReadOnly);

  var uploadAnswersDom = document.getElementById('answer_file');
  if (uploadAnswersDom)
    uploadAnswersDom.addEventListener('change',
        goog.bind(this.loadAnswersFromFile, this), false);

  try {
    this.loadQuestionnaire();
  } catch (e) {
    alert('An error occurred loading the questionnaire: ' + e);
    throw e;
  }
};
goog.inherits(vsaq.Qpage,
              vsaq.QpageBase);


/**
 * Submits the active questionnaire to a backend.
 *
 * This submits all questionnaire answers to the backend. Customize this 
 * to meet your needs.
 * The answers field submitted to the backend is a dictionary that maps
 * ids of ValueItems to answers. E.g.:
 *   answers:{"application_name":"Test","application_description":"Lorem Ipsum"}
 *
 * @param {string} id Id of the questionnaire session. Allows matching of
 *     answers to teams or individuals.
 * @param {string} server Destination to which the questionnaire should
 *     get submitted. E.g. /ajax?f=SubmitQuestionnaire
 * @param {string} xsrf Xsrf token to send with the questionnaire submission.
 * @param {(string|Function)=} opt_redirect Where to redirect the user after
 *     successful submission, or callback to execute on success.
 * @private
 */
vsaq.Qpage.prototype.submitQuestionnaireToServer_ = function(
  id, server, xsrf, opt_redirect) {

  if (this.isReadOnly) {
    alert('This questionnaire is readonly and can therefore not be submitted.');
    return;
  }

  var answers = this.questionnaire.getValuesAsJson();
  goog.net.XhrIo.send(server,
      goog.bind(function(e) {
        if (!e.target.isSuccess()) {
          this.makeReadonly_(true);
          vsaq.showToastbar('Saving the questionnaire failed! Please sign-in and try again.');
        } else {
          var response = e.target.getResponseJson();
          this.updateStorage_(
            /** @type {!Object.<string, string>} */
            (JSON.parse("{\"qid\":\"" + response['qid_saved'] + "\"}")));
          alert(response['msg']);
          if (response['qid_saved'] !== id) {
            this.remoteQuestionnaireID = response['qid_saved'];
            this.updateDownloadAnswersUrl();
          }
          this.saveAndPrepareForNewSubmission(e);
          if (opt_redirect) {
            if (typeof(opt_redirect) == 'function') {
              opt_redirect();
            } else {
              document.location = opt_redirect;
            }
          }
        }
      }, this), 'POST', goog.string.format(
          'id=%s&_xsrf_=%s&answers=%s', encodeURIComponent(id),
          encodeURIComponent(xsrf), encodeURIComponent(answers)),{},0,true);
};


/**
 * Loads saved answers from a Backend.
 *
 * This loads answers from a backend given the search term. This can
 * be used to display answers of a completed questionnaire using the backend
 * that stores questionnaire answers (e.g. the answers field received through
 * submitQuestionnaireToServer_).
 *
 * @param {string} searchTerm Any search term. Allows matching of answers using
 * one of the saved fields under application metadata.
 * @param {string} server Backend from where the questionnaire answers should
 *     get loaded. E.g. /ajax?f=LoadQuestionnaireAnswers
 * @param {string} xsrf Xsrf token to send with the questionnaire submission.
 * @param {string} method HTTP method - one of GET or POST.
 * @private
 */
vsaq.Qpage.prototype.loadAnswersFromServer_ = function(searchTerm, server, xsrf, method) {
  goog.net.XhrIo.send(server, goog.bind(function(e) {
        var text = e.target.getResponseText();
        if (e.target.isSuccess()) {
          var response = JSON.parse(e.target.getResponseText());
          goog.dom.getElement("_csrf_token").value = response['csrf'];
          this.remoteQuestionnaireID = response['qid'];
          // Render the questionnaire's template.
          this.questionnaire.render();
          this.questionnaire.setValues(response['answers']);
          this.updateStorage_(response['answers']);
          this.updateFields(response['answers']);
        } else {
          this.makeReadonly_(true);
          vsaq.showToastbar('Loading the answers failed! Please sign-in and try again.');
        }
      }, this), method, goog.string.format(
          'id=%s&_xsrf_=%s', encodeURIComponent(searchTerm), encodeURIComponent(xsrf)),{},0,true);
};

/**
 * Loads submitted answers metadata
 *
 * This loads submission metadata from a backend. This can be used to 
 * display a list of a completed questionnaires.
 *
 * searchTypes:
 * s = submitted only
 * sr = submitted and in-review
 * sra = submitted, in-review and approved ones.
 *
 * @param {string} searchType whether to load just the unapproved ones or load 
 * the approved ones as well.
 * @param {string} server Backend from where the questionnaires should
 *     get loaded. E.g. /ajax?f=LoadQuestionnaireAnswers
 * @param {string} opt_qid questionnaire ID of the answer if loading previous revisions
 * @param {string} xsrf Xsrf token to send with the questionnaire submission.
 * @param {Object} callbackHandler the callback handler object that will handle 
 * the response.
 * @param {(string|Function)=} opt_callback Where to send the callback after 
 * results are received.
 * @private
 */
vsaq.Qpage.prototype.loadSubmissionsFromServer_ = function(searchType, server, xsrf, opt_qid, callbackHandler, opt_callback) {
  goog.net.XhrIo.send(server, goog.bind(function(e) {
        var text = e.target.getResponseText();
        var response = JSON.parse(e.target.getResponseText());
        goog.dom.getElement("_csrf_token").value = response['csrf'];
        if (e.target.isSuccess()) {
          var mode = goog.dom.getElement('_submissions_mode_').value;
          if (mode == "submissions") {
            vsaq.updateCheckStates(false);
          }
          if (opt_callback && callbackHandler) {
            if (typeof(opt_callback) == 'function') {
              opt_callback(callbackHandler, response);
            }
          }
        } else {
          alert('Couldn\'t load submissions! Please try again.');
        }
      }, this), 'POST', goog.string.format(
          't=%s&id=%s&_xsrf_=%s', encodeURIComponent(searchType), encodeURIComponent(opt_qid), encodeURIComponent(xsrf)),{},0,true);
};

/**
 * Loads the last updated answers from a Backend for looking at the changes 
 * in the current answers with those saved at server/backend.
 *
 * This loads answers from a backend given the questionnaire ID. This can
 * be used to display changes in answers of a previously saved answers in backend
 * that stores questionnaire answers (e.g. the answers field received through
 * submitQuestionnaireToServer_).
 *
 * @param {string} id Id of the questionnaire session. Allows matching of
 *     answers to companies or individuals.
 * @param {string} server Backend from where the questionnaire answers should
 *     get loaded. E.g. /ajax?f=LoadQuestionnaireAnswers
 * @param {string} xsrf Xsrf token to send with the questionnaire submission.
 * @private
 */
vsaq.Qpage.prototype.loadLastSubmittedAnswerFromServer_ = function(id, server, xsrf) {
  goog.net.XhrIo.send(server, goog.bind(function(e) {
        var text = e.target.getResponseText();
        if (e.target.isSuccess()) {
          var response = JSON.parse(e.target.getResponseText());
          goog.dom.getElement("_csrf_token").value = response['csrf'];
          var storageData = this.readStorage_();
          var thisDict = {};
          var lastSavedDict = (
              /** @type {!Object.<string, string>} */
            (response["answers"]));
          if (storageData) {
            thisDict = (
              /** @type {!Object.<string, string>} */
            (JSON.parse(storageData)));
          }
          var isModified = false;
          for(var key in thisDict) {
            if (key.startsWith("q_version")) { continue; }
            var thisValue = thisDict[key];
            var savedValue = lastSavedDict[key];
            if (thisValue !== savedValue) {
              var modifiedElement = goog.dom.getElement(key)
              if (modifiedElement != null) {
                var parent = modifiedElement.parentElement;
                parent.classList.add("modified");
                if (modifiedElement.offsetParent != null) {
                  if (!isModified){
                    isModified = !isModified;
                  }
                  var para = document.createElement("p");
                  var anchor = document.createElement("a");
                  anchor.href = '#' + key;
                  anchor.innerText = key;
                  para.appendChild(anchor);
                  var element = document.getElementById("footer-diff-container");
                  element.appendChild(para);
                }
              }
            }
          }
          if (!isModified) {
              alert('The answers have not been modified since these were last saved.');
          } else {
            var element = document.getElementById("footer-diff");
            element.style.display = 'block';
          }
        } else {
          this.makeReadonly_(true);
          vsaq.showToastbar('Loading the last submitted answers failed! Please sign-in and try again.');
        }
      }, this), 'POST', goog.string.format(
          'id=%s&_xsrf_=%s', encodeURIComponent(id), encodeURIComponent(xsrf)),{},0,true);
};

/**
 * Submits the status change request to a backend.
 *
 * @param {string} id Id of the questionnaire session. Allows matching of
 *     answers to companies or individuals.
 * @param {string} server Destination to which the questionnaire should
 *     get submitted. E.g. /ajax?f=SubmitQuestionnaire
 * @param {string} xsrf Xsrf token to send with the questionnaire submission.
 * @param {string} status the status that needs to be submitted.
 * @private
 */
vsaq.Qpage.prototype.submitStatus_ = function(
  id, server, xsrf, status) {

  if (this.isReadOnly) {
    alert('This questionnaire is readonly and the form status can therefore not be changed.');
    return;
  }

  goog.net.XhrIo.send(server,
      goog.bind(function(e) {
        if (!e.target.isSuccess()) {
          this.makeReadonly_(true);
          vsaq.showToastbar('Status change request failed! Please sign-in and try again.');
        } else {
          var response = e.target.getResponseJson();
          goog.dom.getElement("_csrf_token").value = response['csrf'];
          if (status == 'r') {
            goog.dom.getElement("_app_status").innerText = "(In Review)";
          } else if (status == 'a') {
            goog.dom.getElement("_app_status").innerText = "(Approved)";
          }
          alert('Status saved !');
          location.reload();
        }
      }, this), 'POST', goog.string.format(
          'id=%s&_xsrf_=%s&s=%s', encodeURIComponent(id),
          encodeURIComponent(xsrf), encodeURIComponent(status)),{},0,true);
};

/**
 * Sends a login request to the server and updates the username from response. 
 *
 * @param {string} u username of the user trying to login.
 * @param {string} p user's password.
 * @param {string} server the server endpoint that handles the login request.
 * @param {string} xsrf the XSRF token unique for every post request.
 * @private
 */
vsaq.Qpage.prototype.login_ = function(u,p, server, xsrf) {
  goog.net.XhrIo.send(server, goog.bind(function(e) {
        var text = e.target.getResponseText();
        var loginBtn = goog.dom.getElement('pk-signin-btn');
        loginBtn.value = 'Login';
        var response = JSON.parse(e.target.getResponseText());
        goog.dom.getElement("_csrf_token").value = response['csrf'];
        if (e.target.isSuccess()) {
          if (response['u'] !== '') {
            goog.dom.getElement("_user_").value = response['u'];
            this.makeReadonly_(false);
            var modal = goog.dom.getElement('pk-signin-modal');
            if (modal !== undefined) {
              modal.click();
            }
            if (response['a'] == 'True') {
              var reviewBtn = goog.dom.getElement('_vsaq_review_questionnaire');
              reviewBtn.className = 'maia-button eh-review';
              var approveBtn = goog.dom.getElement('_vsaq_approve_questionnaire');
              approveBtn.className = 'maia-button eh-approve';
            }
          } else {
            alert('Login failed.');
          }
        } else {
          alert('Login failed.');
        }
      }, this), 'POST', goog.string.format(
          'u=%s&p=%s&_xsrf_=%s', encodeURIComponent(u),encodeURIComponent(p), encodeURIComponent(xsrf)),{},0,true);
};

/**
 * Sends a logout request to the server. 
 *
 * @param {string} server the server endpoint that handles the login request.
 * @param {string} xsrf the XSRF token unique for every DELETE request.
 * @private
 */
vsaq.Qpage.prototype.logout_ = function(server, xsrf) {
  goog.net.XhrIo.send(server, goog.bind(function(e) {
        var text = e.target.getResponseText();
        if (e.target.isSuccess()) {
          var response = JSON.parse(e.target.getResponseText());
          goog.dom.getElement("_csrf_token").value = response['csrf'];
          goog.dom.getElement("_rom_").value = 'true';
        }
        this.makeReadonly_(true);
      }, this), 'POST', goog.string.format(
          '_xsrf_=%s', encodeURIComponent(xsrf)), {}, 0, true);
};

/**
 * Updates the readonly status for the questionnaire before rendering.
 * @param {boolean} isReadOnly true if the questionnaire is readonly.
 * @private
 */
vsaq.Qpage.prototype.makeReadonly_ = function(isReadOnly) {
  this.isReadOnly = isReadOnly;
  this.questionnaire.setReadOnlyMode(this.isReadOnly);
  this.questionnaire.render();
  var user = goog.dom.getElement('_user-detail');
  var signOut = goog.dom.getElement('_user-sign-out');
  var signinStatus = goog.dom.getElement('_vsaq_signin_status');
  var reviewBtn = goog.dom.getElement('_vsaq_review_questionnaire');
  var approveBtn = goog.dom.getElement('_vsaq_approve_questionnaire');
  var auth = goog.dom.getElement("_auth_").value == 'True' ? true : false;
  if (isReadOnly) {
    this.statusIndicator.className = "pk-invisible";
    signinStatus.className = "pk-visible";
    user.className = 'pk-invisible';
    signOut.className = 'pk-invisible';
    goog.dom.setTextContent(user,'');
    goog.dom.setTextContent(signOut,'');
    reviewBtn.className = 'maia-button eh-review maia-button-disabled';
    approveBtn.className = 'maia-button eh-approve maia-button-disabled';
  } else {
    user.className = 'pk-main-nav__item pk-signed-in-user';
    signOut.className = 'pk-main-nav__item pk-sign-out eh-signout';
    goog.dom.setTextContent(user,goog.dom.getElement("_user_").value);
    goog.dom.setTextContent(signOut,"Sign out");
    this.makeEditable();
    signinStatus.className = "pk-invisible";
    this.statusIndicator.className = "pk-visible";
    goog.dom.setTextContent(this.statusIndicator, 'No changes.');
    if (auth) {
      reviewBtn.className = 'maia-button eh-review';
      approveBtn.className = 'maia-button eh-approve';
    }
    vsaq.updateActionables();
  }
};

/**
 * Updates the local storage with new questionnaire answers.
 * @param {Object} data Dictionary containing new key/value pairs.
 * @private
 */
vsaq.Qpage.prototype.updateStorage_ = function(data) {
  if (!this.questionnaireID)
    return;
  var newStorageData = null;
  var storageData = this.readStorage_();
  if (storageData) {
    storageData = new Object(JSON.parse(storageData));
    goog.object.extend(storageData, data);
    newStorageData = goog.json.serialize(storageData);
  } else {
    newStorageData = goog.json.serialize(data);
  }

  this.storage.set(this.questionnaireID, newStorageData);
};


/**
 * Fetches all answers from the local storage.
 * @return {?string}
 * @private
 */
vsaq.Qpage.prototype.readStorage_ = function() {
  if (!this.questionnaireID)
    return null;
  return /** @type {?string} */ (this.storage.get(this.questionnaireID));
};


/**
 * Clears the answers in Localstorage.
 */
vsaq.Qpage.prototype.clearStorage = function() {
  if (this.questionnaireID)
    this.storage.remove(this.questionnaireID);
};


/** @inheritDoc */
vsaq.Qpage.prototype.sendUpdate = function() {
  window.clearTimeout(this.saveTimeout);
  if (!this.isReadOnly && goog.structs.getCount(this.changes) > 0) {
    this.updateStorage_(this.changes);
    this.updateDownloadAnswersUrl();

    this.changes = {};
    if (!goog.structs.getCount(this.changes))
      goog.dom.setTextContent(this.statusIndicator, 'Draft Saved Locally.');
  }
  this.scheduleNextUpdate(false);
};


/**
 * Read answers from a file.
 * @param {Event} evt The change event for the upload field.
 */
vsaq.Qpage.prototype.loadAnswersFromFile = function(evt) {
  var answer_file = evt.target.files[0];
  var reader = new FileReader();
  reader.onload = goog.bind(function(f) {
    return goog.bind(function(e) {
      var answers = new Object(JSON.parse(e.target.result));
      if ((answers['q_version_0_1'] === undefined) && (answers['q_version_0_2'] === undefined)) {
        answers['q_version_0_1'] = "checked";
      }
      this.questionnaire.setValues(
          /** @type {!Object.<string, string>} */ (answers));
      this.updateFields(answers);
    }, this);
  }, this)(answer_file);
  reader.readAsText(answer_file);
  if (this.isReadOnly) {
    vsaq.showToastbar();
  }
};


/**
 * Update link to allow users to download questionnaire answers as a file.
 */
vsaq.Qpage.prototype.updateDownloadAnswersUrl = function() {
  var downloadLink = goog.dom.getElement('_vsaq_export_questionnaire');
  var storageData = this.readStorage_();
  if (!downloadLink || !storageData) {
    if (downloadLink.hasAttribute("download")) {
      downloadLink.removeAttribute("download");
    }
    if (downloadLink.hasAttribute("href")) {
      downloadLink.removeAttribute("href");
    }
    return;
  }
  var MIME_TYPE = 'text/plain';
  var textFileAsBlob = new Blob([storageData], {type: MIME_TYPE});
  var items = this.questionnaire.getItems();
  var appName = items["app_name"].getValue();
  var teamEmail = items["app_team_email"].getValue();
  var questionnaireID = this.questionnaireID;
  if (appName && teamEmail) {
    questionnaireID = appName + '_' + teamEmail + '.json';
    questionnaireID = questionnaireID.replace(/\,[^/,]+$/, '');
    questionnaireID = questionnaireID.replace(/\//, '_');
  }
  var fileNameToSaveAs = 'answers_' + this.remoteQuestionnaireID + '_' + questionnaireID;
  downloadLink.download = fileNameToSaveAs;
  window.URL = window.URL || window.webkitURL;
  downloadLink.href = window.URL.createObjectURL(textFileAsBlob);
  downloadLink.className = 'maia-button';
};


/**
 * Load the extension json then proceed with loading the questionnaire.
 * @param {!string} questionnaire_path The path to the questionnaire json.
 * @param {!string} extension_path The path to the questionnaire extension json
 */
vsaq.Qpage.prototype.loadExtensionThenQuestionnaire = function(
    questionnaire_path, extension_path) {
  goog.net.XhrIo.send(extension_path,
      goog.bind(function(e) {
        var text = e.target.getResponseText();
        if (!e.target.isSuccess()) {
          this.makeReadonly_(true);
          vsaq.showToastbar('Loading the questionnaire failed! Please try again.');
        } else {
          text = vsaq.utils.vsaqonToJson(text);
          var extension = {};
          try {
            extension = new Object(JSON.parse(text));
          } catch (err) {
            alert('Loading the extension failed. It does not appear to be ' +
                  'valid json');
          }

          this.loadQuestionnaire(questionnaire_path, extension);
        }
      }, this), 'GET');
};


/**
 * @inheritDoc
 * @param {string=} opt_path The path to the questionnaire json.
 * @param {Object=} opt_extension The questionnaire extension json.
 */
vsaq.Qpage.prototype.loadQuestionnaire = function(opt_path, opt_extension) {
  var uri = new goog.Uri(document.location.search);
  this.questionnaire.setUnrolledMode(
      uri.getQueryData().get('unroll', '') == 'true');

  if (opt_path) {
    // Remove file extensions and some characters from the path to create a
    // unique questionnaire ID.
    this.questionnaireID = goog.string.path.baseName(opt_path);
    this.questionnaireID = this.questionnaireID.replace(/\.[^/.]+$/, '');
    this.questionnaireID = this.questionnaireID.replace(/\//, '_');
    goog.net.XhrIo.send(opt_path,
        goog.bind(function(e) {
          var text = e.target.getResponseText();
          if (!e.target.isSuccess()) {
            this.makeReadonly_(true);
            vsaq.showToastbar('Loading the questionnaire failed! Please try again.');
          } else {
            text = vsaq.utils.vsaqonToJson(text);
            var template = {};
            try {
              template = new Object(JSON.parse(text));
            } catch (err) {
              alert('Loading the template failed. It does not appear to be ' +
                    'valid json');
              return;
            }
            if (!template) {
              alert('Empty template!');
              return;
            }
            if (opt_extension) {
              this.questionnaire.setMultipleTemplates(template, opt_extension);
            } else {
              this.questionnaire.setTemplate(template['questionnaire']);
            }
            // Render the questionnaire's template.
            this.questionnaire.render();
            this.installToolTips();
            if (this.isReadOnly) {
                vsaq.showToastbar();
            } else {
              goog.dom.setTextContent(goog.dom.getElement('_user-detail'),
                    goog.dom.getElement("_user_").value);
              goog.dom.setTextContent(goog.dom.getElement('_user-sign-out'),
                    "Sign out");
            }

            // Load answers from localStorage (if available).
            var storageData = this.readStorage_();
            if (storageData) {
              var storedValues = JSON.parse(storageData);
              this.questionnaire.setValues(
                  /** @type {!Object.<string, string>} */
                  (storedValues));
              this.updateDownloadAnswersUrl();
              this.updateFields(
                /** @type {!Object.<string, string>} */
                  (storedValues));
            }

            this.questionnaire.listen(
            goog.events.EventType.CHANGE, goog.bind(function(e) {
              goog.structs.forEach(e.changedValues, function(val, key) {
                this.changes[key] = val;
              }, this);
              if (!this.isReadOnly && goog.structs.getCount(this.changes) > 0) {
                goog.dom.setTextContent(this.statusIndicator,
                    'Changes pending...');
                this.updateFields(this.changes);
              }
            }, this));
            var qid = uri.getQueryData().get('q', '');
            if (qid != '') {
              vsaq.resetQuestionnaire(false);
              this.loadAnswersFromServer_(
                (/** @type {string} */ (qid)),
                '/loadone?id='+qid,
                '',
                'GET');
            }
            this.scheduleNextUpdate(false);

          }
        }, this), 'GET');
  }
  this.makeReadonly_(this.isReadOnly);
};

/**
 * Saves the existing answers to user's desktop and resets for new submission.
 * @param {Object=} e response event object.
 */
vsaq.Qpage.prototype.saveAndPrepareForNewSubmission = function(e) {
  goog.dom.getElement('_vsaq_export_questionnaire').click();
  var response = e.target.getResponseJson();
  goog.dom.getElement("_csrf_token").value = response['csrf'];
  goog.dom.getElement("q_id").innerText = response['qid_new'];
  vsaq.resetQuestionnaire(true);
  this.remoteQuestionnaireID = response['qid_new'];
  this.updateDownloadAnswersUrl();
  goog.dom.setTextContent(this.statusIndicator, 'No changes.');
};

/**
 * Updates the questionnaire fields based on details already entered so far.
 * @param {Object.<string, string>} obj Object containing the changeset.
 */
vsaq.Qpage.prototype.updateFields = function(obj) {
  var bugTrackerFilterHref = "[BUG_TRACKER_FILTER_HREF]=[BUG_TRACKER_FILTER_QUERY]"
  var appContactEmailPlaceholder = "[TEAM_CONTACT_EMAIL_HREF]?CC=[TEAM_CONTACT_EMAIL]&Subject=[EMAIL_SUBJECT_ARCHITECTURE_REVIEW]"
  var appName = obj['app_name'];
  var teamContact = obj['app_team_email'];
  var projectName = obj['app_static_code_project_name'];
  if (projectName !== undefined) {
    var bugTrackerLink = goog.dom.getElement('_bugtracker_issue_filter');
    bugTrackerLink.href = bugTrackerFilterHref + '%22' + projectName + '%22';
  }
  if (appName !== undefined && teamContact !== undefined) {
    var appContactEmailHref = goog.dom.getElement('_app_contact_email');
    appContactEmailHref.href = appContactEmailPlaceholder.replace('TEAM_DEVELOPER_EMAIL', teamContact).replace('APPLICATION_NAME', appName);
  }
  var qid = obj['qid'];
  if (qid !== undefined) {
    goog.dom.getElement("q_id").innerText = qid;
    this.remoteQuestionnaireID = qid;
  }
  var diffBtn = goog.dom.getElement('_vsaq_diff');
  diffBtn.className = 'maia-button eh-diff';
  var revisionsBtn = goog.dom.getElement('_vsaq_revisions');
  revisionsBtn.className = 'maia-button eh-revisions js-submissions-modal-trigger';
  var appStatus = obj['app_status'];
  if (appStatus) {
    goog.dom.getElement("_app_status").innerText = appStatus ? ' (' + appStatus + ') ' : "";
  }
  this.updateStorage_(
            /** @type {!Object.<string, string>} */
            (JSON.parse("{\"qid\":\"" + goog.dom.getElement("q_id").innerText + "\"}")));
  if (appStatus) {
    vsaq.updateActionables();
  }
};

/**
 * Returns true if the page is readonly
*/
vsaq.Qpage.prototype.getReadonly = function() {
  return this.isReadOnly;
};

/**
 * Initializes VSAQ.
 * @return {?vsaq.QpageBase} The current questionnaire instance.
 */
vsaq.initQuestionnaire = function() {
  if (vsaq.qpageObject_)
    return vsaq.qpageObject_;

  vsaq.qpageObject_ = new vsaq.Qpage();
  // Load questionnaire.
  var templatePattern = new RegExp(/^\/?questionnaires\/[a-z0-9_]+\.json$/i);
  var uri = new goog.Uri(document.location.search);
  var questionnairePath =
      /** @type {string} */ (uri.getQueryData().get('qpath', ''));
  if (questionnairePath && !templatePattern.test(questionnairePath))
    throw new goog.debug.Error(
        'qpath must be a relative path and must match this pattern: ' +
        templatePattern.toString());

  var extensionPath =
      /** @type {string} */ (uri.getQueryData().get('extension', ''));
  if (extensionPath) {
    if (!templatePattern.test(extensionPath))
      throw new goog.debug.Error(
          'extension must be a relative path and must match this pattern: ' +
          templatePattern.toString());
    vsaq.qpageObject_.loadExtensionThenQuestionnaire(
        questionnairePath, extensionPath);
  } else {
    vsaq.qpageObject_.loadQuestionnaire(questionnairePath);
  }

  return vsaq.qpageObject_;
};

/**
 * Clears the answers of the current questionnaire.
 */
vsaq.clearAnswers = function() {
  if (confirm('Are you sure that you want to delete all answers?')) {
    vsaq.resetQuestionnaire(true);
    goog.dom.getElement("q_id").innerText = "NOT-GENERATED";
    vsaq.qpageObject_.questionnaireID = "NOT-GENERATED";
    vsaq.qpageObject_.remoteQuestionnaireID = "NOT-GENERATED";
    var diffBtn = goog.dom.getElement('_vsaq_diff');
    diffBtn.className = 'maia-button eh-diff maia-button-disabled';
    var revisionsBtn = goog.dom.getElement('_vsaq_revisions');
    revisionsBtn.className = 'maia-button eh-revisions js-submissions-modal-trigger maia-button-disabled';
    vsaq.qpageObject_.remoteQuestionnaireID = "";
    var uri = new goog.Uri(document.location.search);
    var qid = uri.getQueryData().get('q', '');
    if (qid != '') {
      window.location = document.location.origin + document.location.pathname + '?qpath=' + uri.getQueryData().get('qpath', '') + '&extension=' + uri.getQueryData().get('extension', '');
    } else {
      vsaq.updateActionables();
    }
  }
};

vsaq.resetQuestionnaire = function(shouldInit) {
  if (vsaq.qpageObject_) {
      vsaq.qpageObject_.clearStorage();
  }
  goog.dom.getElement("answer_file").value = "";
  goog.dom.getElement("_app_status").innerText = "";
  if (shouldInit) {
    vsaq.qpageObject_ = null;
    vsaq.initQuestionnaire();
  }
}

/**
 * Submits the answers of the current questionnaire to server.
 */
vsaq.submitAnswers = function() {
    if (vsaq.checkRequiredFields() && vsaq.qpageObject_) {
      if (vsaq.qpageObject_.getReadonly()) {
        vsaq.showToastbar();
        return;
      }
      var storageData = vsaq.qpageObject_.readStorage_();
      if (!storageData) {
        return;
      }

      if (confirm('Are you sure that you want to submit answers ? ')) {
        vsaq.qpageObject_.submitQuestionnaireToServer_(
        goog.dom.getElement('q_id').innerText, 
        '/submit', 
        goog.dom.getElement("_csrf_token").value);
      }
  }
};

/**
 * Saves the answers of the current questionnaire to server as draft.
 */
vsaq.saveAnswersAsDraft = function() {
  if (vsaq.qpageObject_.getReadonly()) {
    vsaq.showToastbar();
    return;
  }
  var storageData = vsaq.qpageObject_.readStorage_();
  if (!storageData) {
    return;
  }
  if (vsaq.checkRequiredFields() && vsaq.qpageObject_) {
    vsaq.qpageObject_.submitQuestionnaireToServer_(
      goog.dom.getElement('q_id').innerText, 
      '/savedraft', 
      goog.dom.getElement("_csrf_token").value
      );
  }
};

/**
 * Shows a toast message to inform the users about signing in.
 * @param {(string)=} htmlContent the content of the toast message.
 * @param {(boolean)=} hide whether to hide the toast message.
 */
vsaq.showToastbar = function(htmlContent, hide) {
  if (!htmlContent) {
    htmlContent = "This questionnaire is readonly. Please use the link at the bottom to <a class=\"js-signin-modal-trigger pk-main-nav__item\" data-signin=\"login\">Sign in</a> and edit/save."
  }
  var toastBar = document.getElementById("toastbar");
  if (toastBar) {
    toastBar.innerHTML = htmlContent;
    toastBar.className = hide? "" : "show";
    if (!hide) {
      setTimeout(function() {
        toastBar.className = toastBar.className.replace("show", ""); 
      }, 9500);
    } else {
      toastBar.className = ""; 
    }
  }
};

/**
 * Updates the action button status based on the form status.
 */
vsaq.updateActionables = function() {
  if (vsaq.qpageObject_) {
    var reviewBtn = goog.dom.getElement('_vsaq_review_questionnaire');
    var approveBtn = goog.dom.getElement('_vsaq_approve_questionnaire');
    var saveBtn = goog.dom.getElement('_vsaq_save_questionnaire');
    var submitBtn = goog.dom.getElement('_vsaq_submit_questionnaire');
    var auth = goog.dom.getElement("_auth_").value == 'True' ? true : false;
    var storageData = vsaq.qpageObject_.readStorage_();
    if (storageData) {
      var storedValues = JSON.parse(storageData);
      saveBtn.className = 'maia-button eh-save maia-button-disabled';
      reviewBtn.className = 'maia-button eh-review maia-button-disabled';
      approveBtn.className = 'maia-button eh-approve maia-button-disabled';
      submitBtn.className = 'maia-button eh-submit maia-button-disabled';
      if (storedValues["app_status"] == "Revision") {
        vsaq.showToastbar("There is a more recent version of the answers that you can view by clicking on the \"Revisions\" button.");
      } else {
        vsaq.showToastbar("", true);
        if (storedValues["app_status"] == "Draft") {
          saveBtn.className = 'maia-button eh-save';
          submitBtn.className = 'maia-button eh-submit';
        } else if (storedValues["app_status"] == "In Review") {
          submitBtn.className = 'maia-button eh-submit';
          if (auth) {
            approveBtn.className = 'maia-button eh-approve';
          }
        } else if (storedValues["app_status"] == "Approved" && auth) {
          reviewBtn.className = 'maia-button eh-review';
        } else if (storedValues["app_status"] == "Submitted") {
          submitBtn.className = 'maia-button eh-submit';
          if (auth) {
            reviewBtn.className = 'maia-button eh-review';
          }
        }
      }
    }
  }
};

/**
 * Loads the answers from server into the current questionnaire.
 */
vsaq.loadAnswers = function() {
  if (vsaq.qpageObject_.getReadonly()) {
    vsaq.showToastbar();
    return;
  }
  var searchTerm =  goog.dom.getElement('search_qid').value;
  if (vsaq.qpageObject_ && searchTerm.trim() !== '') {
      vsaq.qpageObject_.loadAnswersFromServer_(
      searchTerm,
      '/loadone',
      goog.dom.getElement("_csrf_token").value,
      'POST');
  }
};

/**
 * Loads the modifications in current answers based on comparison from a 
 * previously saved answers from server into the current questionnaire.
 */
vsaq.loadDiffs = function() {
  if (vsaq.qpageObject_) {
    if (vsaq.qpageObject_.getReadonly()) {
        vsaq.showToastbar();
        return;
    }
    vsaq.qpageObject_.loadLastSubmittedAnswerFromServer_(
    goog.dom.getElement('q_id').innerText,
    '/diff',
    goog.dom.getElement("_csrf_token").value);
  }
};

/**
 * Sends a login request to the server for a given user.
 */
vsaq.login = function() {
  if (vsaq.qpageObject_) {
    var loginBtn = goog.dom.getElement('pk-signin-btn');
    var username = goog.dom.getElement('signin-username').value;
    var password = goog.dom.getElement('signin-password').value;
    if (username.trim() !== '' && password.trim() !== '') {
      loginBtn.value = 'Logging in...';
      vsaq.qpageObject_.login_(
      username,
      password,
      '/login',
      goog.dom.getElement("_csrf_token").value);
    }
  }
};

/**
 * Log the currently logged in user out.
 */
vsaq.logout = function() {
  if (vsaq.qpageObject_) {
      vsaq.qpageObject_.logout_(
      '/logout',
      goog.dom.getElement("_csrf_token").value);
  }
  goog.dom.getElement('q_id').innerText = "";
  var reviewBtn = goog.dom.getElement('_vsaq_review_questionnaire');
  reviewBtn.className = 'maia-button eh-review maia-button-disabled';
  var approveBtn = goog.dom.getElement('_vsaq_approve_questionnaire');
  approveBtn.className = 'maia-button eh-approve maia-button-disabled';
  vsaq.showToastbar("You have been signed out.");
};

vsaq.checkRequiredFields = function() {
    var invalidInputs = document.querySelectorAll('html input:invalid');
    var invalidTexts = document.querySelectorAll('html textarea:invalid');
    if (invalidInputs.length > 0) {
      invalidInputs[0].focus();
      vsaq.showToastbar('Please fill in the required fields marked with red border.');
      return false;
    }
    if (invalidTexts.length > 0) {
      invalidTexts[0].focus();
      vsaq.showToastbar('Please fill in the required fields marked with red border.');
      return false;
    }
    vsaq.showToastbar("", true);
    return true;
};

/**
 * Sends a request that changes the form status to In Review.
 */
vsaq.submitReview = function() {
  if (confirm('Are you sure that you want to finish reviwing the answers ? This will send a notification to the submitter that you have finished reviewing.')) {
    if (vsaq.qpageObject_) {
        vsaq.qpageObject_.submitStatus_(
        goog.dom.getElement('q_id').innerText,
        '/status',
        goog.dom.getElement("_csrf_token").value,
        'r');
    }
  }
};

/**
 * Sends a request that approves the form.
 */
vsaq.approveForm = function() {
  if (confirm('Are you sure that you want to approve this form ?')) {
    if (vsaq.qpageObject_) {
        vsaq.qpageObject_.submitStatus_(
        goog.dom.getElement('q_id').innerText,
        '/status',
        goog.dom.getElement("_csrf_token").value,
        'a');
    }
  }
};

/**
 * Displays the submissions page and sends a request to fetch 
 * all submissions.
 */
vsaq.fetchAllSubmissions = function(clickable, event) {
  if (vsaq.qpageObject_.getReadonly()) {
    vsaq.showToastbar();
    return;
  }
  if (!submissionsModal) {
    submissionsModal = document.getElementsByClassName("js-submissions-modal")[0];
    if( submissionsModal && !submissionsModalHandler) {
      submissionsModalHandler = new ModalSubmissions(submissionsModal);
    }
  }
  goog.dom.getElement('_submissions_mode_').value = "submissions";
  submissionsModalHandler.showSubmissionsForm(event.target.getAttribute('data-submissions'));
  var chkSubmitted = goog.dom.getElement('pk-checkbox-submitted');
  chkSubmitted.checked = true;
  chkSubmitted.disabled = false;
  var chkReview = goog.dom.getElement('pk-checkbox-in-review');
  chkReview.checked = false;
  chkReview.disabled = false;
  var chkApproved = goog.dom.getElement('pk-checkbox-approved');
  chkApproved.checked = false;
  chkApproved.disabled = false;
  var draft = goog.dom.getElement('pk-checkbox-draft');
  draft.checked = false;
  draft.disabled = false;
  vsaq.loadSubmissions();
};

/**
 * Sends a request to fetch all submissions.
 * searchTypes:
 * s = submitted only
 * rs = submitted and in-review
 * ars = submitted, in-review and approved ones.
 */
vsaq.loadSubmissions = function() {
  var mode = goog.dom.getElement('_submissions_mode_').value;
  if (mode != "submissions") {
    return;
  }
  goog.dom.getElement('pk-inline-item-container').className = "show";
  if (vsaq.qpageObject_) {
    vsaq.qpageObject_.loadSubmissionsFromServer_(
    vsaq.updateCheckStates(true),
    '/submissions',
    goog.dom.getElement("_csrf_token").value,
    "",
    submissionsModalHandler,
    submissionsModalHandler.loadMetadataResults);
  }
};

vsaq.updateCheckStates = function(shouldDisable) {
  var submitted = goog.dom.getElement('pk-checkbox-submitted');
  var inReview = goog.dom.getElement('pk-checkbox-in-review');
  var approved = goog.dom.getElement('pk-checkbox-approved');
  var draft = goog.dom.getElement('pk-checkbox-draft');
  submitted.disabled = shouldDisable;
  inReview.disabled = shouldDisable;
  approved.disabled = shouldDisable;
  draft.disabled = shouldDisable;
  return (approved.checked ? "a" : "") + (draft.checked ? "d" : "") + (inReview.checked ? "r" : "") + (submitted.checked ? "s" : "");
};

/**
 * Loads the current and all previous revisions of the given questionnaire answers
 */
vsaq.loadRevisions = function(clickable, event) {
  if (vsaq.qpageObject_.getReadonly()) {
    vsaq.showToastbar();
    return;
  }
  if (!submissionsModal) {
    submissionsModal = document.getElementsByClassName("js-submissions-modal")[0];
    if( submissionsModal && !submissionsModalHandler) {
      submissionsModalHandler = new ModalSubmissions(submissionsModal);
    }
  }
  if (vsaq.qpageObject_) {
    goog.dom.getElement('_submissions_mode_').value = "revisions";
    var chkSubmitted = goog.dom.getElement('pk-checkbox-submitted');
    chkSubmitted.checked = true;
    chkSubmitted.disabled = true;
    var chkReview = goog.dom.getElement('pk-checkbox-in-review');
    chkReview.checked = true;
    chkReview.disabled = true;
    var chkApproved = goog.dom.getElement('pk-checkbox-approved');
    chkApproved.checked = true;
    chkApproved.disabled = true;
    var draft = goog.dom.getElement('pk-checkbox-draft');
    draft.checked = true;
    draft.disabled = true;
    submissionsModalHandler.showSubmissionsForm(event.target.getAttribute('data-submissions'));
    goog.dom.getElement('pk-inline-item-container').className = "hide";
    vsaq.qpageObject_.loadSubmissionsFromServer_(
    "ars",
    '/submissions',
    goog.dom.getElement("_csrf_token").value,
    goog.dom.getElement('q_id').innerText,
    submissionsModalHandler,
    submissionsModalHandler.loadMetadataResults);
  }
};

if (!goog.getObjectByName('goog.testing.TestRunner')) {
  vsaq.initQuestionnaire();
  new vsaq.QuestionnaireEditor();

  vsaq.utils.initClickables({
    'eh-clear': vsaq.clearAnswers,
    'eh-submit': vsaq.submitAnswers,
    'eh-save': vsaq.saveAnswersAsDraft,
    'eh-load': vsaq.loadAnswers,
    'eh-diff': vsaq.loadDiffs,
    'eh-login': vsaq.login,
    'eh-signout': vsaq.logout,
    'eh-review': vsaq.submitReview,
    'eh-approve': vsaq.approveForm,
    'eh-submissions': vsaq.fetchAllSubmissions,
    'eh-submissionCheckChanged': vsaq.loadSubmissions,
    'eh-revisions': vsaq.loadRevisions
  });
}

  /**
  * @constructor
  */
  function ModalSubmissions(element) {
    this.element = element;
    this.blocks = this.element.getElementsByClassName('js-submissions-modal-block');
    this.triggers = document.getElementsByClassName('js-submissions-modal-trigger');
    this.metadataInput = this.element.getElementsByClassName('js-submissions-modal-block')[0];
    this.init();
  };

  ModalSubmissions.prototype.init = function() {
    var self = this;
    //open modal/switch form
    for(var i =0; i < this.triggers.length; i++) {
      (function(i){
        self.triggers[i].addEventListener('click', function(event){
          if( event.target.hasAttribute('data-submissions') ) {
            event.preventDefault();
            self.showSubmissionsForm(event.target.getAttribute('data-submissions'));
          }
        });
      })(i);
    }

    //close modal
    this.element.addEventListener('click', function(event){
      if( hasClass(event.target, 'js-submissions-modal') ) {
        event.preventDefault();
        removeClass(self.element, 'pk-submissions-modal--is-visible');
      }
    });

    this.metadataInput.addEventListener('keyup', function(event){
      self.searchMetadata();
    });

    //close modal when clicking the esc keyboard button
    document.addEventListener('keydown', function(event){
      (event.which=='27') && removeClass(self.element, 'pk-submissions-modal--is-visible');
    });

    this.blocks[0].getElementsByTagName('form')[0].addEventListener('submit', function(event){
      event.preventDefault();
    });
  };

  ModalSubmissions.prototype.showSubmissionsForm = function(type) {
    // show modal if not visible
    !hasClass(this.element, 'pk-submissions-modal--is-visible') && addClass(this.element, 'pk-submissions-modal--is-visible');
    // show selected form
    for( var i=0; i < this.blocks.length; i++ ) {
      this.blocks[i].getAttribute('data-type') == type ? addClass(this.blocks[i], 'pk-submissions-modal__block--is-selected') : removeClass(this.blocks[i], 'pk-submissions-modal__block--is-selected');
    }
  };

  ModalSubmissions.prototype.searchMetadata = function() {
    var input, filter, table, tr, tds, td, i, j;
    input = document.getElementById("pk-metadataSearchInput");
    filter = input.value.toUpperCase();
    table = document.getElementById("pk-metadataTable");
    tr = table.getElementsByTagName("tr");
    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < tr.length; i++) {
      tds = tr[i].getElementsByTagName("td");
      for (j = 0; j < tds.length; j++) {
        td = tds[j];
        if (td) {
          if (td.innerHTML.toUpperCase().indexOf(filter) > -1) {
            tr[i].style.display = "";
            break;
          } else {
            tr[i].style.display = "none";
          }
        }
      }
    }
  };

  ModalSubmissions.prototype.loadMetadataResults = function(self, response) {
    var table = document.getElementById("pk-metadataTable");
    var rowCount = table.rows.length;
    for (var i = rowCount - 1; i > 0; i--) {
        table.deleteRow(i);
    }
    var rows = response['rows'];
    for( var i=0; i < rows.length; i++ ) {
      self.addMetadataRow(self, table, rows[i]);
    }
  };

  ModalSubmissions.prototype.addMetadataRow = function(self, table, rowData) {
    var tr = document.createElement("tr");
    var sortedRowData = Object.keys(rowData).sort().reduce(function (result, key) {
        result[key] = rowData[key];
        return result;
    }, {});
    var index = 0;
    var length = Object.keys(sortedRowData).length;
    Object.keys(sortedRowData).forEach(function(key) {
      index++;
      self.addMetadataColumnCell(tr, rowData[key], index, length);
    });
    table.appendChild(tr);
  };

  ModalSubmissions.prototype.addMetadataColumnCell = function(tr, cellData, index, length) {
    var td = document.createElement("td");
    if (index == 1) {
      var anchorElement = document.createElement("a");
      anchorElement.href = '[QUESTIONNAIRE_PATH_PARAMETER]' + cellData;
      anchorElement.innerText = cellData;
      td.appendChild(anchorElement)
    } else if (index == length && cellData != null){
      var issueArray = cellData.split(',');
      for(var i = 0; i < issueArray.length; i++) {
        var anchorAction = document.createElement("a");
        anchorAction.href = '[BUG_TRACKER_URL]' + issueArray[i];
        anchorAction.innerText = issueArray[i];
        td.appendChild(anchorAction)
        td.appendChild(document.createElement("br"));
      }
    } else {
      td.innerText = cellData;
    }
    tr.appendChild(td);
  };

  //class manipulations - needed if classList is not supported
  function hasClass(el, className) {
      if (el.classList) return el.classList.contains(className);
      else return !!el.className.match(new RegExp('(\\s|^)' + className + '(\\s|$)'));
  }
  function addClass(el, className) {
    var classList = className.split(' ');
    if (el.classList) el.classList.add(classList[0]);
    else if (!hasClass(el, classList[0])) el.className += " " + classList[0];
    if (classList.length > 1) addClass(el, classList.slice(1).join(' '));
  }
  function removeClass(el, className) {
    var classList = className.split(' ');
      if (el.classList) el.classList.remove(classList[0]);  
      else if(hasClass(el, classList[0])) {
        var reg = new RegExp('(\\s|^)' + classList[0] + '(\\s|$)');
        el.className=el.className.replace(reg, ' ');
      }
      if (classList.length > 1) removeClass(el, classList.slice(1).join(' '));
  }

var submissionsModal;
var submissionsModalHandler;
