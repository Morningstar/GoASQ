#!/bin/sh
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

# Running this shell script will rename the json files containing the answers 
# in the following format:
# <Alpha-Numeric Unique ID>_<Application Name>_<Security Chanpion NAme>_<Team Contact Email>.json
# The script also removes any spaces from the subdirectories and replaces them with underscores.
# The renamed files will be copied into "GOASQ_Updated" directory along side the directory from
# where this script is run.
# CAUTION: In the re-run, it won't delete any previously generated files.
# Requires jq as dependency for parsing JSON files.

PARENT_DIRECTORY=$1
NEW_DIRECTORY_NAME="GOASQ_Updated"
# Make sure that files and folders do not have spaces and new lines
find ./${PARENT_DIRECTORY} -name "* *" -print0 | sort -rz | while read -d $'\0' f; do mv -v "$f" "$(dirname "$f")/$(basename "${f// /_}")"; done
# Get most recently modified files and rename them appropriately
DIRECTORIES=`find ./${PARENT_DIRECTORY} -type d -follow`
for dir in $DIRECTORIES
do
  FILE=`find $dir -type f -exec stat -f '%m%t%Sm %N' {} \; | sort -nr -u | cut -d . -f2- | head -1`
  FILE_NAME=$(basename $FILE)
  if [ "$FILE_NAME" != ".DS_Store" ]; then
    METADATA=`cat .${FILE} | jq '{name:.app_name,champion:.app_champion,email:.app_team_email}'`
    UNIQUE_ID=`cat /dev/urandom | env LC_CTYPE=C tr -dc 'A-Z0-9' | fold -w 12 | head -n 1`
    APP_NAME=`echo $METADATA | jq .name | sed 's/"//g' | sed 's/[\/]/ /g'`
    APP_CHAMPION=`echo $METADATA | jq .champion | sed 's/"//g' | sed 's/[;,\/<>]/ /g'`
    TEAM_CONTACT=`echo $METADATA | jq .email | sed 's/"//g' | sed 's/[;,\/<>]/ /g'`
    PADDED_FILENAME=`printf " %-60s%s" "$FILE_NAME"`
    echo "File will be renamed from: ${PADDED_FILENAME} to: ${UNIQUE_ID}_${APP_NAME}_${APP_CHAMPION}_${TEAM_CONTACT}.json"
    mkdir -p "./$NEW_DIRECTORY_NAME/$dir"
    yes | \cp ".${FILE}" "./${NEW_DIRECTORY_NAME}/$dir/${UNIQUE_ID}_${APP_NAME}_${APP_CHAMPION}_${TEAM_CONTACT}.json"
  fi
done
