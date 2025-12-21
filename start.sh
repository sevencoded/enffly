#!/bin/sh
echo "Starting ENFFLY (upload + worker in same container)"
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
