#!/bin/bash

# Copyright 2016 The Fuchsia Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Mirror one git repo to another.

# Exit this script if one command fails.
set -e

# Print all commands for debug.
set -x

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 [source git host] [destination git host] [repo name]"
  echo "Example: $0 https://fuchsia.googlesource.com https://github.com/fuchsia-mirror magenta"
  exit 1
fi

SRC_HOST="$1"; DST_HOST="$2"; REPO_NAME="$3"
TEMP_DIR="$(mktemp -d fuchsia-gitsync.XXX)"

# Make sure we clean up our temp directory no matter what.
TEMP_DIR_ABS="$(cd $TEMP_DIR && pwd)"
trap "rm -rf \"${TEMP_DIR_ABS}\"" INT TERM EXIT

# Replace slashes in $REPO_NAME with dashes since GitHub won't allow slashes in repo names.
DST_REPO_NAME="${REPO_NAME//\//-}"

# Pull down the source host.
cd "${TEMP_DIR}"
mkdir "${DST_REPO_NAME}"
cd "${DST_REPO_NAME}"
git init .
git config core.bare true
git remote add origin "${SRC_HOST}/${REPO_NAME}"
git config remote.origin.mirror true
# We want to fetch all remote heads and tags, but not everything.
# In particular, we don't want to mirror refs/changes/*
git config remote.origin.fetch '+refs/heads/*:refs/heads/*'
git config --add remote.origin.fetch '+refs/tags/*:refs/tags/*'

# Add a git remote to the destination host.
REMOTE_URL="${DST_HOST}/${DST_REPO_NAME}"
git remote add gitsync "${REMOTE_URL}"
git config remote.gitsync.mirror true
git remote update

# Check that the gitsync remote exists. If not attempt to create it.
curl -s -f >/dev/null $REMOTE_URL

if [ $? -ne 0 ] ; then
  curl -f -i -n -X POST --data '{"name":"'$REPO_NAME'","has_issues":false,"team_id": 2058456}' https://api.github.com/orgs/fuchsia-mirror/repos
fi

# Push to the destination.
git push gitsync
