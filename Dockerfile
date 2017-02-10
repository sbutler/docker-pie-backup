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
FROM sbutler/pie-base:latest

COPY requirements.txt /tmp
COPY pie-backup.py /usr/local/bin

RUN set -xe \
    && apt-get update && apt-get install -y \
        curl \
        libyaml-0-2 \
        python3 \
        --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py \
    && python3 /tmp/get-pip.py && rm /tmp/get-pip.py \
    && pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt \
    && mkdir /data

ENV AWS_ACCESS_KEY_ID           ""
ENV AWS_SECRET_ACCESS_KEY       ""
ENV AWS_DEFAULT_REGION          ""

# How far back (in days) to search for a recent full backup
ENV PIE_BACKUP_FULL_WINDOW      30
# If present, will encrypt the backups using KMS
ENV PIE_BACKUP_KMS_KEY_ID       ""
# Which bucket to backup to
ENV PIE_BACKUP_S3_BUCKET        ""
# Bucket key prefix to use (aka, subdirectory)
ENV PIE_BACKUP_S3_PREFIX        ""
# Timezone to use for timestamps
ENV PIE_BACKUP_TZ               "America/Chicago"
# Options to pass to the tar command (raw, as is)
ENV PIE_TAR_OPTIONS             ""

CMD ["/usr/local/bin/pie-backup.py"]
