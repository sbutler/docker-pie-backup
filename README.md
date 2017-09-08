# pie-backup
Do a simple rsync between volumes, using hard links to preserve and manage
previous backups.

# Volumes

## /data-src
This is the location that will be backed up. To backup your data, mount it
inside the container as `/data-src`.

## /data-dst
This is the location that will be backed up to. Backups are stored in a
subdirectory called `$interval.$x` where `interval` is "daily", "hourly", etc
and `x` is a number. The most recent backup is "0" and higher `x` are older
backups.

To specify your destination, mount it inside the container as `/data-dst`.

# Environment

## AWS_ACCESS_KEY_ID (optional)
Access Key ID for the AWS IAM user. You should only use this option if you are
in an environment that doesn't support EC2 Instance or Task roles.

## AWS_SECRET_ACCESS_KEY (optional)
Secret Access Key for the AWS IAM user specified by `AWS_ACCESS_KEY_ID`. You
should only use this option is you are in an environment that doesn't support
EC2 Instance or Task roles.

## PIE_BACKUP_RETAIN (default: 7)
How many backups of your data to retain. As new backups are taken the old ones
are renamed, with the oldest in the retention period deleted.

## PIE_BACKUP_INTERVAL (default: daily)
The interval to use when storing backups. This only affects the name of the
backup copy directory, and doesn't impact the logic of the script.


# Running
For simple cases, in automatic mode, you can just run the container. If you
would like to pass options to the backup script then you can run it as:

    pie-backup.py [--full] [--dry-run] [--debug]

Using the `--full` option will force a full backup to be done.
