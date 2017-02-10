# pie-backup
Do a simple tar.gz backup of a data directory to S3. Supports level-0 (full) and
level-1 (incremental) backups and S3 encryption through KMS.

# Volumes

## /data
This is the location that will be backed up. The tar.gz file will be relative
from this path. To backup your data, mount it inside the container as `/data`.

# Environment

## AWS_ACCESS_KEY_ID (optional)
Access Key ID for the AWS IAM user. You should only use this option if you are
in an environment that doesn't support EC2 Instance or Task roles.

## AWS_SECRET_ACCESS_KEY (optional)
Secret Access Key for the AWS IAM user specified by `AWS_ACCESS_KEY_ID`. You
should only use this option is you are in an environment that doesn't support
EC2 Instance or Task roles.

## AWS_DEFAULT_REGION
AWS Region name the S3 bucket is in.

## PIE_BACKUP_FULL_WINDOW (default: 30)
When searching for the last full (level-0) backup, how many days back to look.
If it cannot find a full backup within this many days then it will create a new
full backup instead of an incremental one.

When searching, it uses the most recent full backup found.

## PIE_BACKUP_KMS_KEY_ID (optional)
ID for the KMS Key, not the alias. If present then the backup will be encrypted
in S3 using this key.

## ENV PIE_BACKUP_S3_BUCKET
Name of the S3 bucket to backup to.

## ENV PIE_BACKUP_S3_PREFIX (optional)
Bucket prefix (aka, subdirectory) to use when storing backups. Names for backup
files will follow this pattern:

 > (prefix)/(year)/(month)/(full timestamp).(tar.gz|snar)
 > (prefix)/(year)/(month)/(full timestamp)-(incremental timestamp).(tar.gz|snar)

 If no prefix is specified then the backups are stored in the root of the
 bucket.

## PIE_BACKUP_TZ (default: America/Chicago)
Timezone to use when generating timestamps for file names. Please be careful
changing this when you have existing backups in the bucket; incremental backups
might not operate properly in this case.

## PIE_TAR_OPTIONS
Extra options to pass to tar when creating the archives. For example:

* `--ignore-failed-read`: useful if a backup is failing on a corrupted drive,
but you'd like the backup to be as successful as possible.
* `--no-check-device`: useful for backing up files on NFS mounts.
* `--acls --selinux --xattrs`: save extra metadata about the files to the
archive.
* `--exclude`: exclude some files from the archive.

Be careful to not change the compression method or incremental options or your
archives might not work as expected.

# Running
For simple cases, in automatic mode, you can just run the container. If you
would like to pass options to the backup script then you can run it as:

    pie-backup.py [--full] [--dry-run] [--debug]

Using the `--full` option will force a full backup to be done.
