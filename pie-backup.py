#!/usr/bin/env python3
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

import argparse
import boto3
from datetime import datetime, timedelta
import logging
import os
from pytz import timezone
import re
import shlex
import subprocess
import sys
from tempfile import NamedTemporaryFile
import time

BACKUP_FULL_WINDOW = int(os.environ.get('PIE_BACKUP_FULL_WINDOW', '30'))
BACKUP_KMS_KEY_ID = os.environ.get('PIE_BACKUP_KMS_KEY_ID', None)
BACKUP_S3_BUCKET = os.environ['PIE_BACKUP_S3_BUCKET']
BACKUP_S3_PREFIX = os.environ.get('PIE_BACKUP_S3_PREFIX', '')
BACKUP_SOURCE = os.environ.get('PIE_BACKUP_SOURCE', '/data')
BACKUP_TZ = os.environ.get('PIE_BACKUP_TZ', 'UTC')

TAR_OPTIONS = os.environ.get('PIE_TAR_OPTIONS', '')

# Match our backup files in S3 and pull apart the details of the filename
BACKUP_FILE_REGEX = re.compile(r'/(?P<full_date>\d{14})(?:-(?P<incr_date>\d{14}))?\.(?P<file_type>(?:tar(?:\..+)?)|snar)$')

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

local_tz = timezone(BACKUP_TZ)
now = datetime.now()

rsrc_s3 = boto3.resource('s3')
bucket = rsrc_s3.Bucket(BACKUP_S3_BUCKET)

def daterange(begin, end, **kwargs):
    """
    Iterate between two dates. You can specify a "step" in the same format as
    the `datetime.timedelta()`` constructor. If not specified, `days=1` is used.
    """
    if not kwargs:
        kwargs['days'] = 1

    delta = timedelta(**kwargs)
    current = begin
    while current < end:
        yield current
        current = current + delta

def download_full_snar():
    """
    Find the last full backup in S3, looking only as far back as `window` days,
    and downloads it if one exists.

    This returns the name of the downloaded SNAR file, and a datetime object
    for the backup timestamp it contains.
    """
    period_begin = (now - timedelta(days=BACKUP_FULL_WINDOW))
    period_begin = local_tz.localize(datetime(
        period_begin.year,
        period_begin.month,
        period_begin.day,
    ))
    period_end = local_tz.localize(now)

    logger.debug("Period range: {0} to {1}".format(period_begin, period_end))

    bucket_prefixes = set()
    for period_date in daterange(period_begin, (period_end + timedelta(days=1))):
        bucket_prefixes.add(os.path.join(BACKUP_S3_PREFIX, period_date.strftime("%Y/%m")) + '/')

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Bucket prefixes: " + "; ".join(bucket_prefixes))

    snar_files = []
    for prefix in bucket_prefixes:
        for obj in bucket.objects.filter(Delimiter='/', Prefix=prefix):
            m = BACKUP_FILE_REGEX.search(obj.key)
            if m and not m.group('incr_date') and m.group('file_type') == 'snar':
                obj_dt = local_tz.localize(datetime.strptime(m.group('full_date'), "%Y%m%d%H%M%S"))

                if obj_dt >= period_begin:
                    logger.debug("Found SNAR file: {0} @ {1}".format(obj.key, obj_dt))
                    snar_files.append({
                        'key':          obj.key,
                        'full_date':    obj_dt,
                    })

    snar_files.sort(key=lambda o: o['full_date'], reverse=True)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Full backup SNAR files: " + "; ".join([f['key'] for f in snar_files]))

    if snar_files:
        obj = snar_files[0]

        f = NamedTemporaryFile(
            mode='w+b',
            prefix='pie-backup-{0:%Y%m%d%H%M%S}.'.format(obj['full_date']),
            suffix='.snar',
        )
        logger.debug("Full SNAR path: " + f.name)

        bucket.download_fileobj(obj['key'], f)
        f.flush()
        f.seek(0, os.SEEK_SET)

        return f, obj['full_date']
    else:
        return None, None

def parse_args():
    """ Parse the arguments to this script. Returns the argparse object. """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--full',
        action='store_true',
        help='Force the script to take a full backup',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help="Only output what would be done; don't execution the actions",
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help="Enable some debug output",
    )

    return parser.parse_args()

def upload_tar(full_snar_file, full_snar_dt, dry_run):
    """
    Build the tar + aws command that will upload to S3. If a `full_snar_file` is
    specified then this will be an incremental backup, otherwise a full backup
    is performed.
    """
    full_backup = not (full_snar_file and full_snar_dt)
    local_now = local_tz.localize(now)

    remote_prefix = "s3://" + BACKUP_S3_BUCKET + "/" + os.path.join(BACKUP_S3_PREFIX, local_now.strftime("%Y/%m"))
    if full_backup:
        prefix = "{0:%Y%m%d%H%M%S}".format(local_now)
        local_snar_file = NamedTemporaryFile(prefix='pie-backup-{0}.'.format(prefix), suffix='.snar')
    else:
        prefix = "{0:%Y%m%d%H%M%S}-{1:%Y%m%d%H%M%S}".format(full_snar_dt, local_now)
        local_snar_file = full_snar_file

    remote_prefix = os.path.join(remote_prefix, prefix)
    remote_tar_file = remote_prefix + ".tar.gz"
    remote_snar_file = remote_prefix + ".snar"

    kms_options = ''
    if BACKUP_KMS_KEY_ID:
        kms_options = '--sse aws:kms --sse-kms-key-id {0}'.format(
            shlex.quote(BACKUP_KMS_KEY_ID)
        )

    sh_cmd = "tar --create --gzip --verbose --file=- --listed-incremental={local_snar} --directory={source} {options} . | aws s3 cp {kms_options} - {remote_tar} && aws s3 cp {kms_options} {local_snar} {remote_snar}".format(
        local_snar=shlex.quote(local_snar_file.name),
        remote_tar=shlex.quote(remote_tar_file),
        remote_snar=shlex.quote(remote_snar_file),
        options=TAR_OPTIONS,
        source=shlex.quote(BACKUP_SOURCE),
        kms_options=kms_options,
    )

    logger.info("Executing: " + sh_cmd)
    ret = None
    if not dry_run:
        ret = subprocess.call(sh_cmd, shell=True)

    return ret

args = parse_args()
if args.debug:
    logging.getLogger().setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)

if args.full:
    full_snar_file, full_snar_dt = None, None
else:
    full_snar_file, full_snar_dt = download_full_snar()

upload_ret = upload_tar(full_snar_file, full_snar_dt, dry_run=args.dry_run)
sys.exit(1 if upload_ret is None else upload_ret)
