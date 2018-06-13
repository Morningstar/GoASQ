![logo](logo/GoASQ_logo.png "GoASQ logo")

# GoASQ: General Open Architecture Security Questionnaire

[![Build Status](https://travis-ci.org/Morningstar/GoASQ.svg?branch=master)](https://travis-ci.org/Morningstar/GoASQ)

## Introduction
----
GoASQ is intended to be used as a part of an AppSec (Application Security) review process for applications before they are deployed to production. GoASQ is implemented in Javascript and Python and makes use of the Flask microservice engine.

GoASQ is a framework for building security questionnaires using a simple JSON format. This project is derived from the VSAQ (https://github.com/google/vsaq) project which Google graciously open sourced in March, 2016 (https://opensource.googleblog.com/2016/03/scalable-vendor-security-reviews.html). GoASQ differs from VSAQ in that it is not specifically focused on vendor assessments, but is instead open to any security-focused questionnaire contributions.

We are excited to work with the open source community to further enhance GoASQ so it becomes a widely useful AppSec tool. Please join us and help to make GoASQ more functional, comprehensive and complete.

## Table of Contents
- [How do we use GoASQ](#how-do-we-use-goasq)
- [Example Security Review Workflow](#example-security-review-workflow)
- [How has Morningstar benefited by using GoASQ?](#how-has-morningstar-benefited-by-using-goasq)
- [How does GoASQ differ from VSAQ?](#how-does-goasq-differ-from-vsaq)
- [Project Structure](#project-structure)
- [Build Prerequisites](#build-prerequisites)
  - [Caveats](#caveats)
  - [Troubleshooting](#troubleshooting)
  - [Installing python-ldap](#installing-python-ldap-300)
    - [Debian/Ubuntu](#debianubuntu)
    - [RedHat/CentOS](#redhatcentos)
- [Code Setup](#code-setup)
  - [Build](#build)
  - [Local Development Server](#local-development-server)
  - [Deployment](#deployment)
    - [Manual deployment](#manual-deployment)
- [Login](#login)
- [Session Management](#session-management)
- [Logging](#logging)
- [Exception handling](#exception-handling)
- [Questionnaires](#questionnaires)
- [E-mail notifications](#e-mail-notifications)
- [Security Headers](#security-headers)
- [Runtime Application Self Protection](#runtime-application-self-protection)
  - [User session termination](#user-session-termination)
  - [Alerting administrators](#alerting-administrators)
  - [Rate limiting and user warning](#rate-limiting-and-user-warning)
- [Notes](#notes)
- [Features](#features)
- [TODO](#todo)
- [Contributions](#todo)
  - [Code reviews](#code-reviews)
- [License](#license)
--------

### How do we use GoASQ?

Project teams use the GoASQ questionnaire(s) to describe the architecture and security posture of their code. When answers indicate a bad security practice, the questionnaire automatically highlights this, provides best practice advice, and asks if there is any justification for deviating from best practice.

The AppSec team can review and approve the resulting answers typically engaging with the team to clarify questions and discuss issues and concerns through the approval process. Typically the project team will go through a few rounds of updating answers before getting approval and from these discussions issues are identified, bugs are filed, prioritized and addressed.

### Example Security Review Workflow
1. *Security champion* or another member of the development team fills out and completes the *GoASQ* questionnaire hosted at your server.
(e.g., https://vsaq-demo.withgoogle.com/vsaq.html?qpath=questionnaires/webapp.json).
1. The answers are saved using the "Download" button at the bottom and *Security champion* shares that in an email with *Reviewers* for review or submits the answers using "Save and Submit" which automatically sends out a notification to *Reviewers* including a project summary and the answers file.
1. *Reviewers* either load the answers they received in the email as attachment or just click on the link in the email that auto-loads the answers.
1. *Reviewers* finish the review which sends an automated email to *Security champion* and the development team. *Reviewers* also provide review comments in an email, request for more information or ask to file follow-up tickets (in JIRA or your favorite bug tracker tool) to address security concerns and then re-submit the answers. When satisfied, *Reviewers* approve the project.

### How has Morningstar benefited by using GoASQ?

GoASQ helps to enable AppSec teams to get involved with projects early in the software development lifecycle when it is easier and more practical to make changes and adjustments. Having each team engage with security-focused discussion for each release ensures that security gets the attention it deserves. 

It is common for projects to tell the AppSec team that they had not considered particular security expectations before going through this process. The review process allows the AppSec team to engage and consult, so all projects develop a common understanding of good security practices.

Improvements are not just one-directional as the review process frequently highlights ways to improve the questionnaire itself. As every project is unique, it is common for particular projects to have issues or difficulty answering certain questions, or to feel that questions do not apply. It is also not unusual to encounter a project that has unique security issues that are not well covered by the questionnaire. So, after each review, the Morningstar AppSec team considers these issues and we regularly update/reorganize the questionnaire to make questions and advice more clear and to enhance it with questions to cover missing topics. This process of continual improvement feeds into less cumbersome and higher quality reviews.

GoASQ has become a critical part of Morningstar process providing oversight and an ability to provide consistent quality in terms of architecture and security controls. GoASQ AppSec has helped to develop a stronger company-wide understanding and consensus of good security policy, expectations and best practices. For sure, we notice teams taking their improved understanding of security with security more effectively built-in when they return with new projects.

### How does GoASQ differ from VSAQ?

While the Google's VSAQ project does provide an excellent foundation for security-focused questionnaires, it has not been active and the code is missing many key features needed to make for a workable process. GoASQ fleshes out many of these missing pieces.

The best features of VSAQ are preserved in GoASQ, including its ability to create dynamic questionnaires. How questions are answered can cause additional questions, advice, alerts, or even additional sections of questions and advice to be presented. This provides an ability to build questionnaires that ask a few simple questions, but grow to the right amount of complexity as based on how answers describe the threat landscape specific to the application under review.

By itself, the VSAQ project only provides non-functional stubs for backend storage and provides no easy mechanism for questionnaires to be submitted by one group of people and reviewed by another. Unless you implement these stubs, the sharing of the JSON data between the author and reviewer is a manual process. VSAQ also provides no mechanisms for keeping track of submitted forms, like which forms are awaiting review or already approved.

GoASQ improves upon VSAQ and addresses these issues by reworking the code so it uses the Flask Python microframework, through integration with a SQLite database, and by providing an interface that allows users to submit, view or review questionnaire answers. GoASQ has also been enhanced to integrate with LDAP to control access and ensure that users can only modify questionnaires that they previously created and to allow reviewers to have the access they need to review and mark forms as approved.

### Project Structure

* / : top-level directory for common files and most of the server python source files as well as application configuration files and placeholder configuration files.
* /build : the directory where the build outputs will be placed. It's this directory from where the content is eventually served to the browser clients
* /client_side_only_impl : directory for the client-side implementation.
* /db : contains the database table schema and database related other python source files
* /login : all source files relevant to client side login functionality
* /Logs : hosts the server log file. These log files are rotated. More on this later.
* /questionnaires : directory for questionnaire templates.
* /vsaq : directory for the questionnaire rendering engine library.
* /scripts : test script to check the validity if the JSON questionnaire. However, the same is also validated at the time of build itself.
* /third_party : has all the third party dependencies
* /uploads : directory for keeping the submitted answers in a JSON format in a text file
* /vsaq : directory for the questionnaire rendering engine library.


## Build Prerequisites
----
These instructions have been tested with the following software:

* Linux/OpenBSD/UNIX/Macintosh (the build is not yet supported on Microsoft Windows cygwin environment)
* java >= 1.7 : for running the Closure Compiler
* ant : for building VSAQ dependencies
* git
* curl
* a web server (an optional Python development server is provided)
* a browser with HTML5 support
* apache-maven
* Python 2.7.x
* flask (install it under <ProjectRoot>/flask/). See http://flask.pocoo.org/docs/1.0/installation/
* jq : For checking validity of json file (use "brew install jq" to install on OSX)
* running over https: openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
  https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
* Update settings in app.config file
* python-ldap-3.0.0 (You can try installing using pip install python-ldap. If that doesn't work, see the alternatives below)
* pycrypto : Get the latest version from https://pypi.org/simple/pycrypto/. We used pycrypto 2.6.1. Run `python setup.py install`
  or `yum install gcc` then `yum install gcc-c++` then `yum install python-devel` then `pip install pycrypto`
* uglify-js : `npm install uglify-js -g`
* Facebook buck: If you'd like to build documentations as well. See https://buckbuild.com/setup/getting_started.html
* Closure-linter: https://developers.google.com/closure/utilities/docs/linter_howto
* bash > 4

You could also use requirements.txt file to install requirements. Use requirements-dev.txt to install additional dependencies for
development needs.

### Caveats
    When using openSSL, the self signed certificates may not be trusted.
    A CA file may have been bootstrapped using certificates from the SystemRoots
    keychain. To add additional certificates (e.g. the certificates added in
    the System keychain), place .pem files in
      `/usr/local/etc/openssl/certs`

    and run
      `/usr/local/opt/openssl/bin/c_rehash`

### Troubleshooting
  When using `pip` to try to install any package, you receive the error : `There was a problem confirming the ssl certificate: [SSL: TLSV1_ALERT_PROTOCOL_VERSION] tlsv1 alert protocol version`, you need to upgrade your pip.
  Do this: `curl https://bootstrap.pypa.io/get-pip.py | python` (Use sudo, if required)

### Installing python-ldap-3.0.0

If installing python-ldap using pip doesn't work, see the alternatives below

#### Debian/Ubuntu:
  `sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev`

#### RedHat/CentOS:
  `sudo yum install python-devel openldap-devel`

* Download the package python-ldap-3.0.0 from https://pypi.python.org/pypi/python-ldap/3.0.0 (v3.0.0.tar.gz)
* Download the dependencies
* * pyasn1 from https://pypi.python.org/pypi/pyasn1 (v0.4.2.tar.gz)
* * pyasn1-modules from https://pypi.python.org/pypi/pyasn1-modules (v0.2.1.tar.gz)
* Extract pyasn1 tar package, `cd <folder where you extracted>` and then run `python setup.py install`
* Extract pyasn1-modules tar package, `cd <folder where you extracted>` and then run `python setup.py install`
* Extract python-ldap-3.0.0 tar package, `cd <folder where you extracted>` and then run `python setup.py install`

## Code Setup
----
These instructions assume a working directory of the repository root.

The root directory includes an easy-to-use setup script called `do.sh`. It supports the following commands:

 * Setup:   `./do.sh {install_deps|check_deps|setup_db}`
 * Build:   `./do.sh {build|build_prod|build_templates|build_docs} [debug]`
 * Run:     `./do.sh {run} [-v|-vvvvv] [-d|--debug]`
 * Data:    `./do.sh {backup_db|bulkinsert_db|restore_db} [/path/to/DB/file.db] [/directory/path/for/input or output]`
 * Cleanup: `./do.sh {clean|clean_deps}`
 * Deploy:  `./do.sh {deploy} [--debug] [--test]`
 * Other:   `./do.sh {lint}`

### Build

To build GoASQ, run the following commands:

1. `./do.sh install_deps`
1. `./do.sh build debug`

To setup database for the first time, run the following command from the project root directory:
1. `./do.sh setup_db`

Please note that you should be running this command in the capacity of the same user that you'd run the server with.
Alternatively, use `chown` to own the database file - EGS.db - created under `build\db\`.

### Local Development Server
To run the GoASQ development server locally, use the `run` command:

1. `./do.sh run`
1. `./do.sh run -vvvvv`

Note that the development app server uses a snapshot of the code, taken
at the time you run it. If you make changes to the code, be sure to run the
appropriate build command again and restart the dev server:

 * Run `./do.sh build`  to refresh the source code, static files, and templates.
 * Run `./do.sh build_templates` to rebuild only the Closure Templates. Then
 run `./do.sh run` to restart the dev server.
 * Run `sudo ./do.sh run -vvvvv --debug` to run the server in debug mode (loading the `app.config.debug`)
   instead of `app.config` and with verbose logging enabled.
 * Run `sudo ./do.sh run -vvvvv --debug --test` to run the server in debug mode as well as enabling `Test` mode. Enabling test mode allows you to skip LDAP authentication and instead accepts any credential you supply. Please note that Test mode is designed to work only from a local development server. Though, this setting can be controlled by ENABLE_TEST_MODE_LOCAL_ONLY in app.config (or app.config.debug).
 * Run `sudo lsof -i tcp:80 | grep LISTEN | awk '{ print $2 }' | sudo xargs kill -9` to kill any existing
   server instance.

### Deployment
The open source version of VSAQ does not require a dedicated back end. This means
VSAQ can be hosted as a static application on any web server. However, if you'd
like to have deployment with backend integration, you will need to have additional
deployments done.
  `http://flask.pocoo.org/docs/0.12/deploying/#deployment`
  1. Remember to turn off the DEBUG configuration parameters and update the host in app.config file.
  1. Run `sudo ./do.sh deploy` to deploy it to a remote SSH HOST. It assumes that you have SSH access 
    to the remote host and that you have saved the private/public key pair in the ~/.ssh directory.

Alternatively, you can also follow the instructions below for manual deployment.

#### Manual deployment

##### To deploy GoASQ (with a backend), complete the following steps:

1. To setup database for the first time, run the following command from the project root directory:
  `./do.sh setup_db`
  If the database already exists, you will need to copy that to the target directory under 
  `[server root directory]/build/db/EGS.db`
1. `./do.sh build_prod` : This will run a normal build, but will also remove test files. This will also replace all placeholder strings from various files as defined in placeholders.compile.cfg
1. Copy the `build` directory into the target directory hosted on your web server.
1. Run the command from target root directory to generate a self signed certificate and key
   `openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365`
1. Make chanegs to app.config file to remove any reference to `DEBUG` logging settings and 
  updating the server address, cookie domain etc.
1. Copy all the python (`.py`), bash shell (`.sh`) and `app.config` files from the project root 
  directory to the target directory hosted on your web server. Also copy the python files from [project root directory]\db
  directory that contains the `dbUtils.py` and `__init__.py` to the `[target directory]\db`. You do not need to copy the rest of the files from db directory.

  The target root directory should look like this:

  `[root directory]`
  `[root directory]\app.config` or `app.config.debug` if you build for debug environment.
  `[root directory]\build\* [contents after building (build_prod)]`
  `[root directory]\build\db\EGS.db (This gets here after running the DB setup for the first time or you copying an existing DB.)`
  `[root directory]\cert.pem`
  `[root directory]\compiler.flags`
  `[root directory]\cryptoUtils.py`
  `[root directory]\db`
  `[root directory]\db\dbUtils.py`
  `[root directory]\db\__init__.py`
  `[root directory]\do.sh`
  `[root directory]\flask\* (if you have installed and enabled it only locally for this application)`
  `[root directory]\flask_sslify.py`
  `[root directory]\globals.py`
  `[root directory]\key.pem`
  `[root directory]\ldapUtils.py`
  `[root directory]\Logs\`
  `[root directory]\postHandler.py`
  `[root directory]\randomizer.py`
  `[root directory]\rename_files.sh`
  `[root directory]\renderer.py`
  `[root directory]\requirements.txt`
  `[root directory]\smtp_handler.py`
  `[root directory]\translator.py`
  `[root directory]\uploads\`
  `[root directory]\goasq_server.py`

1. Run the server from target root directory:
  `cd [root directory]`
  `sudo ./do.sh run` (You can pass -v, -vv or -vvvvv for enabling additional logging output)
  This will start the python server. You can also pass -d or --debug to run the server in
  debug mode.

1. The questionnaire should now be available under
https://[yourserver]/vsaq.html?qpath=questionnaires/mstar_0_1.json

## Login
The application identifies the users via their network username and authenticates using LDAP. The user is expected to provide their network username (without domain) and password. The application attempts to authenticate with the selected DC from the app.config file and returns the full name  and authorization status of the user. If the user is one of the members of the team (identified by REVIEWERS_AD_GROUP in app.config), it grants the user additional authorization to change the review status to "In Review" and "Approved". The checks are implemented at the backend as well as front end. See the LDAP section in app.config for details on other configuration parameters.

The questionnaire is by default loaded in the readonly mode until the user signs-in. This is controlled by the method call `readonly` in globals.py. Also see `setup_Defaults` in the same file.

## Session Management
When the user successfully logs into the application, a session cookie is created with a default expiry (configurable by PERMANENT_SESSION_LIFETIME in app.config). The application uses Flask. Flask sessions (http://flask.pocoo.org/docs/1.0/api/?highlight=session#flask.session) expire once you close the browser unless you have a permanent session. We use setting the session to Permanent which defaults the expiry of session cookie to 31 days. To overcome that, you could use permanent_session_lifetime and set it to expire in 5 minutes in the Live environment and 24 hours for debug environment. Please see PERMANENT_SESSION_LIFETIME and other relevant configuration parameters in the app.config file.

## Logging
We use the logging (https://docs.python.org/2/library/logging.html) library from Python. When the application is initialized at runtime, the logger is set with the configuration parameters as per definition in app.config file. See LOG_FILE_NAME, LOG_FILE_MAX_SIZE and LOG_FILE_BACKUP_COUNT in the configuration. When running the server, you might want to set the loglevel to verbose/debug by specifying -vvvvv as the 2nd parameter (sudo ./do.sh run -vvvvv). This sets the log level to Debug and flushes out all logs as desired. See `setup_Logging` in globals.py.

## Exception handling
The application uses try catch blocks as a standard practice to catch and log exceptions. At the same time, it also registers for an error handler so that all errors raised by the application are routed through and bubbled up to a single method. Please see `handle_error` in goasq_server.py. Any application specific stack trace or sensitive error details are removed for Live environment so that those are not sent back to the user. In the debug environment, nothing gets removed from the exception logs or trace. Before sending out the exception in the response, it's jsonified. The application also sends out an email digest to the server admins (configurable by SERVER_ADMINS in app.config) when the number of errors reaches 10 (configurable by ERROR_DIGEST_CAPACITY).

## Questionnaires
Application makes use of multiple questionnaires. The base questionnaire is mstar_0_1.json. Which questionnaires should be served by the application is determined by the app.config parameter QUESTIONNAIRES_SERVED which contains a list of json questionnaire file names that the application is allowed to serve.

## E-mail notifications
The application sends out email notifications in the following cases:

* When a questionnaire is submitted for review.
* When a reviewer updates the review status to "In Review" by clicking on "Finish Review" or approves it by clicking on "Approve" button. See `setup_Notification_For_Reviews` in globals.py.
* When application has encountered a total of 10 (or ERROR_DIGEST_CAPACITY in app.config) errors/exceptions since the last time an email for exceptions was sent or when the server was restarted. So if the error buffer is filled with 10 logs, the exception email is sent to the SERVER_ADMINS as specified in the app.config file. This is to make sure that the site administrator fixes a problem that might be causing the exceptions or is alerted if someone is trying to do something malicious that's been causing exceptions. See setup_Notification_For_Errors in globals.py.

## Security Headers
The project makes extensive use of the recommended web application security headers. 

* Server response header is set to a non-empty, non-revealing value.
* X-Frame-Options is set to deny.
* X-XSS-Protection is set to 1; mode=block.
* X-Content-Type-Options is set to nosniff
* Content-Security-Policy is set to allow downloading js script files or css or image only from the origin source. A couple of css and js files are also allowed from google.com. In-line execution of scripts is prevented.
* Expires is set to SEND_FILE_MAX_AGE_DEFAULT seconds as defined by app.config for all GET responses and to -1 for all POST responses or when error is encountered for GET requests..
* Last-Modified is set to the date timestamp of the modified date-time of the (static) resources being requested. For POST requests, it's set to now.
* Cache-Control is set to "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0" for all POST responses or when error is encountered for GET requests.
* Content-Type is set based on the content being served.

## Runtime Application Self Protection
The project makes use of several techniques to apply runtime application self protection (RASP). Some of these are listed below:

### User session termination
The application terminates a session if the csrf token for a POST request does not match the expected token. Similarly, if the user value in the cookie for an authenticated API request is not decrypted or is found to be messed up with, the session is cleared and logged out. See csrf_protect in goasq_server.py for details. The session is also terminated when the user logs out. 

### Alerting administrators
When a number of errors are encountered by the application and it fills the buffer for which the limit is set by the config value ERROR_DIGEST_CAPACITY in app.config file, an email with a digest of all exceptions/errors is sent out to the site administrators as defined by SERVER_ADMINS in app.config file. This makes sure that site administrators can look at what might be causing these many abrupt exceptions that have not been handled in the application. there may be two reasons for such exceptions. First, that the application really got into an execution path that's currently not handling an exception case and second, that someone is trying to mess with the web application that's causing the exceptions to occur. In either of the cases, it helps to either improve the code or bring the application into a fail-secure-failure status. See setup_Notification_For_Errors in globals.py.

### Rate limiting and user warning
The project limits the number of requests that can be made by a unique client by defining RATE_LIMITING_DEFAULTS in app.config. By default, in the Live environment, it's set to 200 per day or 50 per hour whichever ie met first. If the user makes more requests than this limit, the user would start receiving HTTP error code 429 Too many requests. It's assumed that a user does not need to send these many requests to be able to complete a simple questionnaire. For debug environments, the values are set to be 20000 per day or 500 per hour. Restarting the server resets the counters, just in case, you happened to make these many requests and started receiving 429. Please note that restarting the server does not reset your session unless the secret key is also changed which will trigger all sessions to be marked as invalid.

## Notes
----
JS-Files in `static/` are compiled by the Closure Compiler and placed in
`build/vsaq_binary.js`.

Closure Templates are compiled by the Closure Template Compiler
and placed in `build/templates/vsaq/static/questionnaire/templates.soy.js`.

The `/questionnaires` directory and parts of the `/static` directories are
replicated in `build/`.

Changes to the JSON `/questionnaires` do not require redeployment of the
application code, and can be done on the server if required.

## Features

Here's a brief feature list you might want to be aware of:

* Loading the base questionnaire as dictated by QUESTIONNAIRES_SERVED configuration value in app.config (or app.config.debug for debug mode)
* Loading the extension questionnaire via an extension parameter if the same can be served as dictated by QUESTIONNAIRES_SERVED configuration value in app.config (or app.config.debug for debug mode). However, we do not have any extension questionnaire under the open source version. You should also know that to be able to load extensions, the version and namespace in the questionnaire should be the same as in those the base questionnaire.
* Database setup to create various tables, triggers and constraints from the command line
* Login using network credentials (LDAP)
* Test mode for skipping network login (works only in debug mode when debugging locally)
* Password strength indicator as per the organization policy
* Saving and retrieving answers and application metadata into/from the SQLite database.
* Saving and retrieving answers to/from file system
* Highlighting required fields and restricting text input field lengths
* Reading and updating various files with placeholders at build time based on keys-values in placeholders.compile.config
* AES 256 encrypted session data
* Recommended security headers to protect web application from common vulnerabilities as well as CSRF protection. CSRF driven by configuration value CERF_STRICT in app.config.
* Built-in SSL support and SSL redirection
* Read-only mode for viewing and post-sign in editing capabilities for the questionnaire
* Segregation of edit right between approver/reviewer and normal users based on AD group membership thus enforcing vertical access control. Horizontal access control using user verification.
* Unique questionnaireID for every new project
* Runtime application self protection using session termination, log alerts and rate limiting for abuse cases
* Email notifications for new submissions, review updates, approvals and exception alerts
* URL handling driven by configuration
* Exception details suppression in non-debug (production) mode
* Diff between the currently loaded answers and the last saved answers along with a table of changes (ToC) that helps navigate through the edits
* Searching and loading of answers based on simple keywords and application metadata
* Submission lifecycle management from "Submitted" > "In Review" to "Approved"
* Viewing all submissions based on submissions status, filtering and searching within submissions
* Viewing all revisions of a submission
* Content-length and content-type validations at server end aside from other abuse case restrictions
* Handling 304 NOT MODIFIED at server end for reuse of caches at the client
* Bulk import of all answers along with their revisions in database without losing the original timestamps
* File system Logging and log rotation driven by configuration parameters in app.config.

## TODO

Following features may be in the To-Do list (not necessarily in the same order)
1. Restore database from the backup file generated using ./do.sh backup_db
1. Better integration of the action items and listing them under TODO items at the end of the questionnaire that acts as automated recommendations even before the questionnaire is submitted.
1. Allowing online comments for each section
1. Using the `unroll` mode and `extension` feature to better present the questionnaire section-wise (for example in a step-by-step setup wizard format)
1. Integration with bug tracking system (for example JIRA) so that a ticket/bug can be created in one-click with reviewer comments online. The person filling out the questionnaire may be required to provide the tracking project code (for example JIRA project name)
1. Automatic tracking of tickets/bugs that got created as part of the review. Such tracking should remind the team (via email notifications?) to close the unresolved tickets. The status of the submission should change to `Closed` from `Approved` when all tickets are closed. Such `Closed` submissions should not longer appear during the search results.
1. Integrate with bug tracking system (for example JIRA) to auto-populate the number of open/unresolved security issues when the person filling out the questionnaire enters the project information.
1. Optionally allow auto-commit of backup files in a repository (possibly via a Jenkins job that runs every day?)
1. CI build for the open source (travis-ci?)
1. Enable direct remote logging (Splunk?)

## Contributions

### Code reviews
All submissions, including submissions by project members, require review. We use Github pull requests for this purpose.

## License
GoASQ is licensed under the Apache License 2.0. Details can be found in the LICENSE file.
