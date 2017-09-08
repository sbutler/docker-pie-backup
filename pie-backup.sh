#!/bin/bash
# Copyright (c) 2017 University of Illinois Board of Trustees
# All rights reserved.
#
# Developed by: 		Technology Services
#                      	University of Illinois at Urbana-Champaign
#                       https://techservices.illinois.edu/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# with the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#	* Redistributions of source code must retain the above copyright notice,
#	  this list of conditions and the following disclaimers.
#	* Redistributions in binary form must reproduce the above copyright notice,
#	  this list of conditions and the following disclaimers in the
#	  documentation and/or other materials provided with the distribution.
#	* Neither the names of Technology Services, University of Illinois at
#	  Urbana-Champaign, nor the names of its contributors may be used to
#	  endorse or promote products derived from this Software without specific
#	  prior written permission.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH
# THE SOFTWARE.

# Based off of https://github.com/awslabs/data-pipeline-samples/blob/master/samples/EFSBackup/efs-backup.sh

# Example would be to run this script as follows:
# Every 6 hours; retain last 4 backups
# pie-backup.sh hourly 4 efs-12345
# Once a day; retain last 31 days
# efs-backup.sh $src $dst daily 31 efs-12345
# Once a week; retain 4 weeks of backup
# efs-backup.sh $src $dst weekly 7 efs-12345
# Once a month; retain 3 months of backups
# efs-backup.sh $src $dst monthly 3 efs-12345
#
# Snapshots will look like:
# $dst/hourly.0-3; daily.0-30; weekly.0-3; monthly.0-2

set -xe

echo "PIE_BACKUP_SOURCE = ${PIE_BACKUP_SOURCE:=/data-src}"
echo "PIE_BACKUP_DESTINATION = ${PIE_BACKUP_DESTINATION:=/data-dst}"
echo "PIE_BACKUP_INTERVAL = ${PIE_BACKUP_INTERVAL:=daily}"
echo "PIE_BACKUP_RETAIN = ${PIE_BACKUP_RETAIN:=7}"

# we need to decrement retain because we start counting with 0 and we need to remove the oldest backup
let "retain=$PIE_BACKUP_RETAIN-1"
if [[ -d $PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.$retain ]]; then
    rm -rf "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.$retain"
fi


# Rotate all previous backups (except the first one), up one level
for x in $(seq $retain -1 2); do
    if [[ -d $PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.$[$x-1] ]]; then
        mv "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.$[$x-1]" "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.$x"
    fi
done

# Copy first backup with hard links, then replace first backup with new backup
if [[ -d $PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.0 ]]; then
    cp -al "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.0" "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.1"
fi
rsync -ahv --stats --delete --numeric-ids "$PIE_BACKUP_SOURCE/" "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.0/"
rsyncStatus=$?

touch "$PIE_BACKUP_DESTINATION/$PIE_BACKUP_INTERVAL.0/"

exit $rsyncStatus
