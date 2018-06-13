#!/usr/bin/env bash
# Copyright 2016 Google Inc. All rights reserved.
#
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
#
# @fileoverview Shell script to facilitate build-related tasks for VSAQ.
#

PYTHON_CMD="python"
JSCOMPILE_CMD="java -jar third_party/closure-compiler/build/compiler.jar --flagfile=compiler.flags"
CKSUM_CMD="cksum" # chosen because it's available on most Linux/OS X installations
MD5_CMD="md5"
JS_UGLIFY_CMD="uglifyjs"
SFTP_CMD="lftp"
BUILD_DIR="build"
LOCAL_LAUNCH_DIR="LocalLaunchPad"
BUILD_TPL_DIR="$BUILD_DIR/templates"
ROOT_DIR=`pwd`
cd "${VSAQ_REFERENCE_DIR}"
WORKING_DIR=`pwd`

if [[ "${PLACEHOLDER_CONFIG_PATH}" == "" ]]; then
  PLACEHOLDER_CONFIG_PATH="${WORKING_DIR}/placeholders.compile.cfg"
fi
cd ${0%/*}

vsaq_assert_dependencies() {
  # Check if required binaries are present.
  type "$PYTHON_CMD" >/dev/null 2>&1 || { echo >&2 "Python is required to build GoASQ."; exit 1; }
  type ant >/dev/null 2>&1 || { echo >&2 "Ant is required to build GoASQ."; exit 1; }
  type java >/dev/null 2>&1 || { echo >&2 "Java is required to build GoASQ."; exit 1; }
  jversion=$(java -version 2>&1 | grep version | awk -F '"' '{print $2}')
  if [[ $jversion < "1.7" ]]; then
    echo "Java 1.7 or higher is required to build GoASQ."
    exit 1
  fi
  # Check if required files are present.
  files=(third_party/closure-library \
    third_party/closure-templates-compiler \
    third_party/closure-stylesheets/target/closure-stylesheets.jar \
    third_party/closure-compiler/build/compiler.jar \
    third_party/closure-compiler/contrib/externs/chrome_extensions.js \
  )
  for var in "${files[@]}"
  do
    if [ ! -e $var ]; then
      echo $var "not found"
      echo >&2 "Download libraries needed to build first. Use $0 install_deps."
      exit 1
    fi
  done
  echo "All dependencies met."
}

vsaq_get_file_cksum() {
  # creates a checksum of a given file spec
  # no-op if $CKSUM_CMD is not available
  type $CKSUM_CMD >/dev/null 2>&1 && (find "vsaq" -name $1 | sort | xargs $CKSUM_CMD | $CKSUM_CMD) || true
}

vsaq_build_templates() {
  vsaq_assert_dependencies
  set -e
  mkdir -p "$BUILD_TPL_DIR"
  rm -rf "$BUILD_TPL_DIR/*"
  # Compile soy templates
  echo "Compiling Soy templates..."
  rm -f "$BUILD_TPL_DIR/cksum"
  vsaq_get_file_cksum '*.soy' > "$BUILD_TPL_DIR/cksum"
  find "vsaq" -name '*.soy' -exec java -jar third_party/closure-templates-compiler/SoyToJsSrcCompiler.jar \
  --shouldProvideRequireSoyNamespaces --shouldGenerateJsdoc --shouldDeclareTopLevelNamespaces --srcs {} \
  --outputPathFormat "$BUILD_TPL_DIR/{INPUT_DIRECTORY}{INPUT_FILE_NAME}.js" \;
  echo "Done."
}

vsaq_assert_buildfiles() {
  if [ ! -d "$BUILD_DIR" ] || [ ! -f "$BUILD_DIR/vsaq.html" ]; then
    echo "Please build VSAQ first."
    exit 1
  fi
}

vsaq_assert_templates() {
  if [ ! -d $BUILD_TPL_DIR ]; then
    vsaq_build_templates
  else
    # If cmp is unavailable, just ignore the check, instead of exiting
    type cmp >/dev/null 2>&1 && (vsaq_get_file_cksum '*.soy' | cmp "$BUILD_TPL_DIR/cksum" - >/dev/null 2>&1) || true
    if [ -f "$BUILD_TPL_DIR/cksum" -a $? -eq 0 ] ; then
      echo "Using previous template build. Run ./do.sh clean if you want to rebuild the templates."
    else
      echo "Template files changed since last build. Rebuilding..."
      vsaq_build_templates
    fi
  fi
}

vsaq_assert_jsdeps() {
  if [ ! -f "$BUILD_DIR/deps.js" ]; then
    vsaq_generate_jsdeps
  fi
}

vsaq_build_closure_lib_() {
  # $1 - Closure entry point
  # $2 - Filename
  # $3 - Additional source dir
  # $4 - [debug|optimized]
  ENTRY_POINT=$1
  FNAME=$2
  SRC_DIRS=( \
    vsaq \
    client_side_only_impl \
    third_party/closure-library/closure/goog \
    third_party/closure-library/third_party/closure/goog \
    third_party/closure-templates-compiler )
  if [ -d "$3" ]; then
    SRC_DIRS+=("$3")
  fi
  jscompile_vsaq="$JSCOMPILE_CMD"
  for var in "${SRC_DIRS[@]}"
  do
    jscompile_vsaq+=" --js='$var/**.js' --js='!$var/**_test.js' --js='!$var/**_perf.js'"
  done
  jscompile_vsaq+=" --js='!third_party/closure-library/closure/goog/demos/**.js'"
  if [ "$4" == "debug" ]; then
     jscompile_vsaq+=" --debug --formatting=PRETTY_PRINT -O WHITESPACE_ONLY"
  elif [ "$4" == "optimized" ]; then
     jscompile_vsaq+=" -O ADVANCED"
  fi
  echo -n "."
  $jscompile_vsaq --closure_entry_point "$ENTRY_POINT" --js_output_file "$FNAME"
}

vsaq_build_jsmodule() {
  echo "Building JS module $1 into $BUILD_DIR/$1.js..."
  vsaq_assert_dependencies
  set -e
  vsaq_assert_jsdeps
  mkdir -p "$BUILD_DIR"
  if [ "$2" == "debug" ]; then
    echo "Debug mode enabled"
  fi
  vsaq_build_closure_lib_ $1 "$BUILD_DIR/$1.js" "" $2;
  echo ""
  echo "Done."
}

vsaq_build() {
  vsaq_assert_dependencies
  set -e
  vsaq_assert_jsdeps
  vsaq_assert_templates

  echo "Building VSAQ app to $BUILD_DIR"
  # compile javascript files
  if [ "$1" == "debug" ]; then
    echo "Debug mode enabled"
  fi
  if [ ! -f "${BUILD_DIR}/db/EGS.db" ]; then
    goasq_setup_db
  fi

  echo "Copying custom directories/files..."
  cp -R "login" "$BUILD_DIR"
  echo "Compiling JS files..."
  vsaq_build_closure_lib_ "vsaq" "$BUILD_DIR/vsaq_binary.js" "$BUILD_TPL_DIR" "$1"
  $JS_UGLIFY_CMD -h >/dev/null 2>&1 || { echo >&2 "It looks like uglifyjs is not installed.";}
  if hash $JS_UGLIFY_CMD 2>/dev/null; then
    $JS_UGLIFY_CMD "login/js/main.js" > "$BUILD_DIR/login/js/main.js"
  fi

  BUILD_DIR_STATIC="$BUILD_DIR/static"
  mkdir -p "$BUILD_DIR_STATIC"
  DIR_UPLOADS="uploads"
  DIR_LOGS="Logs"
  mkdir -p "$DIR_UPLOADS"
  mkdir -p "$DIR_LOGS"
  csscompile_vsaq="java -jar third_party/closure-stylesheets/target/closure-stylesheets.jar --allowed-non-standard-function color-stop"
  echo "Compiling CSS files..."
  $csscompile_vsaq "vsaq/static/vsaq_base.css" "vsaq/static/vsaq.css" > "$BUILD_DIR_STATIC/vsaq.css"
  $csscompile_vsaq "login/css/style.css" > "$BUILD_DIR/login/css/style.css"
  echo "Copying remaining static files..."
  find "vsaq" -regex '.*.\(gif\|png\|ico\|svg\)$' -exec cp -f "{}" "$BUILD_DIR_STATIC" \;
  if [ "${machine}" == "Mac" ]; then
    find -E "vsaq" -regex '.*\.(gif|png|ico|svg)' -exec cp -f "{}" "$BUILD_DIR_STATIC" \;
  fi
  echo "Copying main html files..."
  find "client_side_only_impl" -regex .*.html -not -regex .*_test_dom.html -exec cp -f "{}" "$BUILD_DIR" \;
  echo "Checking for valid JSON in questionnaire..."
  JSONError=`sed 's/\/\/ .*$//g' questionnaires/mstar_0_1.json | sed 's/\/\/\\n.*$//g' | grep '[^[:blank:]]' | jq '.'`
  echo "Copying questionnaire files..."
  cp -R "questionnaires" "$BUILD_DIR"
  if [[ "${ROOT_DIR}/${BUILD_DIR}" !=  "${WORKING_DIR}/${BUILD_DIR}" ]]; then
    cp -R "${ROOT_DIR}/questionnaires" "$BUILD_DIR"
  fi
  echo "Done."

  if [ "$2" == "auto" ]; then
    _DEBUG_=false
    _DEBUG_=true
    goasq_autoBuildDebugOnly
  fi
}

vsaq_build_prod() {
 vsaq_build
 rm -f "$BUILD_DIR/example.html"
 rm -f "$BUILD_DIR/all_tests.html"
}

goasq_setup_db() {
  set -e
  BUILD_DIR_DB="$BUILD_DIR/db"
  mkdir -p "$BUILD_DIR_DB"
  if [ -f "$BUILD_DIR_DB/EGS.db" ]; then
    read -p $'\e[31mEGS.db database file already exists in build/db. Do you want to remove it and create a new DB ? (y/n)\e[0m: '  removeDBFile
    if [ $removeDBFile == 'y' ] || [ $removeDBFile == 'Y' ]; then
      echo "Cleaning existing DB file..."
    elif [ $removeDBFile == 'n' ] || [ $removeDBFile == 'N' ]; then
      echo "Keeping the DB file as-is in $BUILD_DIR_DB."
      return
    else
      echo $'\e[31mERROR: A valid input (y/n) is required.\e[0m'
      exit 1
    fi
  fi
  rm -rf "$BUILD_DIR_DB"
  mkdir -p "$BUILD_DIR_DB"
  cd db
  echo "Setting up DB in $BUILD_DIR_DB"
  $PYTHON_CMD -c 'import db_setup; db_setup.first_time_setup()'
  RETVAL=$?
  cd ..
  echo "DB setup done."
}

goasq_backup_db() {
  set -e
  cd db
  DB_PATH="$1"
  OUTPUT_PATH="$2"
  PYTHON_FUNC="import db_setup; print db_setup.exportToJSON('"${DB_PATH}"','"${OUTPUT_PATH}"')"
  savedFile=`$PYTHON_CMD -c "${PYTHON_FUNC}"`
  RETVAL=$?
  echo "DB backup done. Please check:$savedFile"
}

goasq_bulkinsert_db() {
  set -e
  cd db
  DB_PATH="$1"
  INPUT_PATH="$2"
  PYTHON_FUNC="import db_setup; db_setup.importRecursivelyFromDirectory('"${DB_PATH}"','"${INPUT_PATH}"')"
  $PYTHON_CMD -c "${PYTHON_FUNC}"
  RETVAL=$?
  echo "DB bulk insert done. Please check DB."
}

goasq_restore_db() {
  echo "Not implemented yet! Check back later."
  goasq_applyKeyMappings $*
}

goasq_delete_submission() {
  set -e
  cd db
  DB_PATH="$1"
  QUESTIONNAIRE_ID="$2"
  PYTHON_FUNC="import db_setup; db_setup.deleteSubmission('"${DB_PATH}"','"${QUESTIONNAIRE_ID}"')"
  $PYTHON_CMD -c "${PYTHON_FUNC}"
  RETVAL=$?
  echo "Done."
}

goasq_prepare_local_launchpad() {
  set -e
  rm -rf "$LOCAL_LAUNCH_DIR"
  rm -rf "$BUILD_DIR/vsaq_editor.html"
  mkdir -p "$LOCAL_LAUNCH_DIR/db"
  mkdir -p "$LOCAL_LAUNCH_DIR/Logs"
  mkdir -p "$LOCAL_LAUNCH_DIR/uploads"
  cp -R "$BUILD_DIR" "$LOCAL_LAUNCH_DIR"
  rm -rf *.pyc /y
  rm -rf db/*.pyc /y
  echo "Copying config files"
  cp *.config* "$LOCAL_LAUNCH_DIR"
  echo "Copying python files"
  cp *.py "$LOCAL_LAUNCH_DIR"
  cp db/*.py "$LOCAL_LAUNCH_DIR/db"
  echo "Copying compiler flags"
  cp *.flags "$LOCAL_LAUNCH_DIR"
  echo "Copying bash script files"
  cp *.sh "$LOCAL_LAUNCH_DIR"
  echo "Updating build timestamp"
  JSON_QUESTIONNAIRE_PATH="${LOCAL_LAUNCH_DIR}/build/questionnaires/mstar_0_1.json"
  rm -rf "${JSON_QUESTIONNAIRE_PATH}"
  BUILD_TIMESTAMP=`date "+%Y-%m-%d %T %Z"`
  QUESTIONNAIRE_TITLE=`sed 's/\/\/ .*$//g' build/questionnaires/mstar_0_1.json | sed 's/\/\/\\n.*$//g' | grep '[^[:blank:]]' | jq '.questionnaire[0].text'`
  QUESTIONNAIRE_TITLE=`echo "${QUESTIONNAIRE_TITLE} (${BUILD_TIMESTAMP})" | sed 's/"//g'`
  sed 's/\/\/ .*$//g' build/questionnaires/mstar_0_1.json | sed 's/\/\/\\n.*$//g' | grep '[^[:blank:]]' | jq --arg title "${QUESTIONNAIRE_TITLE}" '.questionnaire[0].text |="\($title)"' >> ${JSON_QUESTIONNAIRE_PATH}
  echo "Copying requirements to be installed on target"
  cp *.txt "$LOCAL_LAUNCH_DIR"
  rm -rf "${LOCAL_LAUNCH_DIR}/app.config.original.bak"
  rm -rf "${LOCAL_LAUNCH_DIR}/app.config.debug.original.bak"
  RETVAL=$?
  echo "Local build done."
}

goasq_prepare_remote_launchpad() {
  set +e
  PWD=`pwd`
  echo "Preparing for remote deployment."
  read -p $'\e[31mIP or Hostname of target box (default 172.30.0.102)\e[0m: '  targetHost
  if [ "$targetHost" == "" ]; then
    targetHost="172.30.0.102"
  fi
  echo "${targetHost} will be used as target host."
  read -p $'\e[31mSSH Username of the user for deploying on target box (default ec2-user)\e[0m: '  targetUser
  if [ "$targetUser" == "" ]; then
    targetUser="ec2-user"
  fi
  echo "${targetUser} will be used as target user to login/SSH into ${targetHost}."
  result=`ssh ${targetUser}@${targetHost} true`
  read -p $'\e[31mPlease enter the remote deployment directory path (default /home/ec2-user/git/VSAQ)\e[0m: '  remoteHomeDirectory
  if [ "$remoteHomeDirectory" == "" ]; then
    remoteHomeDirectory="/home/ec2-user/git/VSAQ"
  fi
  echo "All the build outputs will be deployed under ${remoteHomeDirectory}"
  getRemoteDBFile=""
  read -p $'\e[31mWould you like to use the existing DB, if any, in the target deployment location ? (y/n)\e[0m: '  keepDBFile
  if [ "$keepDBFile" == "y" ] || [ "$keepDBFile" == "Y" ]; then
    getRemoteDBFile="get ${remoteHomeDirectory}/build/db/EGS.db ${PWD}/${LOCAL_LAUNCH_DIR}/build/db/EGS.db"
    echo "If a DB file exists at ${remoteHomeDirectory}/build/db/EGS.db, it will be kept as-is."
  elif [ "$keepDBFile" != "n" ] && [ "$keepDBFile" != "N" ]; then
    echo $'\e[31mERROR: A valid input (y/n) is required.\e[0m'
    exit 1
  else
    echo "If a DB file exists at ${remoteHomeDirectory}/build/db/EGS.db, it will be deleted and a new DB file will be created."
  fi
  read -p $'\e[31mWould you like to kill any server process running on port 80 and restart it with new deployment? (default No [n]) (y/n)\e[0m: '  killServer
  if [ "$killServer" == "y" ] || [ "$killServer" == "Y" ]; then
    killServer='Y'
    processesId="$"2
    forceKillServer="sudo lsof -i tcp:80 | grep LISTEN | awk '{ print $processesId }' | sudo xargs kill -9"
    echo "If a process is found running at port 80, it will be killed and the server will be restarted post-deployment."
  elif [ "$killServer" == "n" ] || [ "$killServer" == "N" ]; then
    echo $'\e[31m************* REMEMBER to restart the server manually! **************\e[0m'
  else
    echo $'\e[31mERROR: A valid input (y/n) is required.\e[0m'
    exit 1
  fi
  echo "Deploying to ${targetHost}..."
  putLocalDirectory="mirror -R ${PWD}/${LOCAL_LAUNCH_DIR}/ ${remoteHomeDirectory}/"
  SFTPExpression=${getRemoteDBFile}"; "${putLocalDirectory}"; bye"
  lftp -u ${targetUser}, sftp://${targetHost} -e "set xfer:clobber on ${SFTPExpression}"
  runServerinVerboseMode="sudo ./do.sh run -vvvvv $1 $2"
  if [ $killServer == 'Y' ]; then
    ssh ${targetUser}@${targetHost} "${forceKillServer} || true"
    ssh ${targetUser}@${targetHost} "cd ${remoteHomeDirectory} && ${runServerinVerboseMode} && true"
  fi
  RETVAL=$?
  rm -rf "${PWD}/${LOCAL_LAUNCH_DIR}"
  echo "Deployment finished."
}

vsaq_build_clean() {
  echo "Cleaning all builds..."
  rm -rfv "$BUILD_DIR"
  if [[ "${ROOT_DIR}/${BUILD_DIR}" !=  "${WORKING_DIR}/${BUILD_DIR}" ]]; then
    rm -rfv "${ROOT_DIR}/${BUILD_DIR}"
  fi
  echo "Done."
}

vsaq_clean_deps() {
  echo "Removing all build dependencies. Install them with ./do.sh install_deps."
  rm -rfv lib
  echo "Done."
}

vsaq_install_deps() {
  set -e
  echo "Installing build dependencies..."
  ./download-libs.sh
  echo "Done."
}

vsaq_generate_jsdeps() {
  vsaq_assert_templates
  $PYTHON_CMD third_party/closure-library/closure/bin/build/depswriter.py \
    --root_with_prefix="build/templates/ build/templates/" \
    --root_with_prefix="vsaq/ vsaq/" \
    --root_with_prefix="third_party/closure-templates-compiler/ third_party/closure-templates-compiler/" \
    > "$BUILD_DIR/deps.js"
}

vsaq_run() {
  vsaq_assert_buildfiles
  vsaq_assert_templates
  echo "Generating build/deps-runfiles.js file..."
  mkdir -p "$BUILD_DIR"
  $PYTHON_CMD third_party/closure-library/closure/bin/build/depswriter.py \
    --root_with_prefix="build/templates/ ../../../build/templates/" \
    --root_with_prefix="vsaq/ ../vsaq/" \
    --root_with_prefix="third_party/closure-templates-compiler/ ../../../../third_party/closure-templates-compiler/" \
    > "$BUILD_DIR/deps-runfiles.js"

  rm -f "$BUILD_DIR/all_tests.js"
  export FLASK_ENV='production'
  if [ "$2" == "-d"  ] || [ "$2" == "--debug"  ]; then
    export APP_SETTINGS='app.config.debug'
    echo "Starting the GOASQ server (Press Ctrl-C to stop)..."
    $PYTHON_CMD goasq_server.py $*
    if [ -f "${WORKING_DIR}/app.config.original.bak" ]; then
      \cp -rf "${WORKING_DIR}/app.config.original.bak" "${WORKING_DIR}/app.config"
      \cp -rf "${WORKING_DIR}/app.config.debug.original.bak" "${WORKING_DIR}/app.config.debug"
      rm -rf "${WORKING_DIR}/app.config.original.bak"
      rm -rf "${WORKING_DIR}/app.config.debug.original.bak"
    fi
  else
    export APP_SETTINGS='app.config'
    echo "Starting the GOASQ server as a background process..."
    $PYTHON_CMD goasq_server.py $* &>Logs/EGS.log &
    disown -h %1
  fi
  echo "Done."
  exit 0
}

vsaq_lint() {
  if [ -z `which gjslint` ]; then
    echo "Closure Linter is not installed."
    echo "Follow instructions at https://developers.google.com/closure/utilities/docs/linter_howto to install (root access is needed)."
    RETVAL=1
  else
    echo "Running Closure Linter..."
    if [ -z "$1" ]; then
      ADDITIONAL="-r vsaq"
    else
      ADDITIONAL=$*
    fi
    gjslint --strict --closurized_namespaces=goog,vsaq --limited_doc_files=_test.js --exclude_files=deps.js,externs.js $ADDITIONAL
    RETVAL=$?
  fi
}

vsaq_build_docs() {
  rm -rf docs/*
  if [ ! -f third_party/js-dossier/buck-out/gen/src/java/com/github/jsdossier/dossier.jar ]; then
    if [ -z `which buck` ]; then
      echo "Facebook Buck is not installed. Buck is needed by js-dossier to build the documentation."
      echo "Follow instructions at https://buckbuild.com/setup/getting_started.html to install."
      echo "Make sure 'buck' command line tool is available."
      RETVAL=1
      exit
    else
      cd third_party/js-dossier
      ./gendossier.sh -r
      cd ../..
    fi
  fi
  vsaq_build_templates
  java -jar third_party/js-dossier/buck-out/gen/src/java/com/github/jsdossier/dossier.jar -c third_party/docs-build/dossier-config.json
  RETVAL=$?
}

goasq_autoBuildDebugOnly() {
  echo 'DEBUG ONLY: Auto-build is turned on. To stop, press CTRL+C'
  chsum1=""
  trap "exit" INT
  while [[ _DEBUG_ ]]
  do
      chsum2=`find client_side_only_impl questionnaires vsaq \( -name "*.html" -or -name "*.js" -or -name "*.json" -or -name "*.css" \) -type f -mtime -5s -exec md5 {} \;`
      if [[ $chsum1 != $chsum2 ]] ; then
          chsum1=$chsum2
          if [[ $chsum2 != "" ]] ; then
            vsaq_build
          fi
      fi
      sleep 2
  done
  echo 'Exiting auto-build mode...'
}

goasq_copyConfigs() {
  if [[ "${ROOT_DIR}" !=  "${WORKING_DIR}" ]]; then
    if [ ! -f "${WORKING_DIR}/app.config.original.bak" ]; then
      \cp -rf "${WORKING_DIR}/app.config" "${WORKING_DIR}/app.config.original.bak"
      \cp -rf "${WORKING_DIR}/app.config.debug" "${WORKING_DIR}/app.config.debug.original.bak"
    fi
    \cp -rf "${ROOT_DIR}/app.config" "${WORKING_DIR}/app.config"
    \cp -rf "${ROOT_DIR}/app.config.debug" "${WORKING_DIR}/app.config.debug"
  else
    if [ -f "${WORKING_DIR}/app.config.original.bak" ]; then
      \cp -rf "${WORKING_DIR}/app.config.original.bak" "${WORKING_DIR}/app.config"
      \cp -rf "${WORKING_DIR}/app.config.debug.original.bak" "${WORKING_DIR}/app.config.debug"
    fi
  fi
  goasq_applyKeyMappings
}

goasq_applyKeyMappings() {
  CONFIG_PATH="${PLACEHOLDER_CONFIG_PATH}"
  PYTHON_FUNC_SECTIONS="import config_reader; print ' '.join(config_reader.getSections('"${CONFIG_PATH}"'))"
  sections=`$PYTHON_CMD -c "${PYTHON_FUNC_SECTIONS}"`
  index=0
  CMD_REPLACE="sed -i~ "
  for sec in ${sections}
  do
    sectionName="section"
    PYTHON_FUNC_DICT="import config_reader; config_reader.getKeyValueForSection('"${CONFIG_PATH}"', '"${sec}"', '"${sectionName}"')"
    dictionary=`$PYTHON_CMD -c "${PYTHON_FUNC_DICT}"`
    eval "${dictionary}"
    for i in "${!section[@]}"
    do
      key="\[${i^^}\]"
      value="${section[$i]}"
      echo ${CMD_REPLACE}"s|${key}|${value}|g" ${sec}
      ${CMD_REPLACE}"s|${key}|${value}|g" ${sec}
      rm -rf ${sec}~
    done
    unset section
    ((index=index+1))
  done
}

RETVAL=0
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac

CMD=$1
shift

case "$CMD" in
  check_deps)
    vsaq_assert_dependencies;
    ;;
  install_deps)
    vsaq_install_deps;
    ;;
  build)
    vsaq_build $1 $2;
    goasq_copyConfigs $*;
    ;;
  build_prod)
    vsaq_build_prod;
    goasq_copyConfigs
    ;;
  build_templates)
    vsaq_build_templates;
    goasq_copyConfigs
    ;;
  build_jsmodule)
    vsaq_build_jsmodule $*;
    goasq_copyConfigs
    ;;
  clean)
    vsaq_build_clean;
    ;;
  clean_deps)
    vsaq_clean_deps;
    ;;
  run)
    goasq_copyConfigs $*;
    vsaq_run $*;
    ;;
  lint)
    vsaq_lint $*;
    ;;
  build_docs)
    vsaq_build_docs;
    ;;
  deps)
    vsaq_generate_deps;
    ;;
  setup_db)
    goasq_setup_db;
    goasq_copyConfigs
    ;;
  backup_db)
    goasq_backup_db $*;
    ;;
  bulkinsert_db)
    goasq_bulkinsert_db $*;
    ;;
  restore_db)
    goasq_restore_db $*;
    ;;
  delete_submission)
    goasq_delete_submission $*;
    ;;
  deploy)
    vsaq_build_prod;
    goasq_copyConfigs;
    goasq_setup_db;
    goasq_prepare_local_launchpad;
    goasq_prepare_remote_launchpad $*;
    ;;
  *)
    echo "Usage:   $0 PARAMETER"
    echo "Setup:   $0 {install_deps|check_deps|setup_db}"
    echo ""
    echo "Cleanup: $0 {clean|clean_deps}"
    echo "         Removes the build directory | Deletes dependencies"
    echo ""
    echo "Build:   $0 {build|build_prod|build_templates|build_docs} [debug]"
    echo ""
    echo "Run:     $0 {run} [-v] [--debug or -d]"
    echo "         Not passing the -v or --verbose will default the log level to CRITICAL."
    echo "         More verbose levels in the same order can be set:"
    echo "          Error (-vv), "
    echo "          Warning (-vvv), "
    echo "          Info (-vvvv), "
    echo "          Debug (-vvvvv)"
    echo ""
    echo "Data:    $0 {backup_db|bulkinsert_db|restore_db} [/path/to/DB/file.db] [/directory/path/for/input or output]"
    echo "         creates a back up of the database | allows you to bulk insert from a specified directory | restores data"
    echo ""
    echo "Delete:  $0 {delete_submission} [/path/to/DB/file.db] [Questionnaire ID]"
    echo "         Deletes a row with specified questionnaire ID from the database."
    echo ""
    echo "Deploy:  $0 {deploy} [--debug][--test]"
    echo "         Builds the prod version of the application, creates DB"
    echo "         or leaves the existing DB as-is, if found, and attempts to deploy on a target box."
    echo "         optionally runs the server in debug and/or test mode"
    echo ""
    echo "Other:   $0 {lint}"
    RETVAL=1
esac

exit $RETVAL
