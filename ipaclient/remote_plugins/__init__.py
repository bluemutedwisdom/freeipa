#
# Copyright (C) 2016  FreeIPA Contributors see COPYING for license
#

import collections
import errno
import json
import locale
import os
import time

from . import compat
from . import schema
from ipaclient.plugins.rpcclient import rpcclient
from ipaplatform.paths import paths
from ipapython.dnsutil import DNSName
from ipapython.ipa_log_manager import log_mgr

logger = log_mgr.get_logger(__name__)


class ServerInfo(collections.MutableMapping):
    _DIR = os.path.join(paths.USER_CACHE_PATH, 'ipa', 'servers')

    def __init__(self, api):
        hostname = DNSName(api.env.server).ToASCII()
        self._path = os.path.join(self._DIR, hostname)
        self._force_check = api.env.force_schema_check
        self._dict = {}

        # copy-paste from ipalib/rpc.py
        try:
            self._language = (
                 locale.setlocale(locale.LC_ALL, '').split('.')[0].lower()
            )
        except locale.Error:
            self._language = 'en_us'

        self._read()

    def _read(self):
        try:
            with open(self._path, 'r') as sc:
                self._dict = json.load(sc)
        except EnvironmentError as e:
            if e.errno != errno.ENOENT:
                logger.warning('Failed to read server info: {}'.format(e))

    def _write(self):
        try:
            try:
                os.makedirs(self._DIR)
            except EnvironmentError as e:
                if e.errno != errno.EEXIST:
                    raise
            with open(self._path, 'w') as sc:
                json.dump(self._dict, sc)
        except EnvironmentError as e:
            logger.warning('Failed to write server info: {}'.format(e))

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def update_validity(self, ttl=None):
        if ttl is None:
            ttl = 3600
        self['expiration'] = time.time() + ttl
        self['language'] = self._language
        self._write()

    def is_valid(self):
        if self._force_check:
            return False

        try:
            expiration = self._dict['expiration']
            language = self._dict['language']
        except KeyError:
            # if any of these is missing consider the entry expired
            return False

        if expiration < time.time():
            # validity passed
            return False

        if language != self._language:
            # language changed since last check
            return False

        return True


def get_package(api):
    if api.env.in_tree:
        from ipaserver import plugins
    else:
        try:
            plugins = api._remote_plugins
        except AttributeError:
            server_info = ServerInfo(api)

            client = rpcclient(api)
            client.finalize()

            try:
                plugins = schema.get_package(server_info, client)
            except schema.NotAvailable:
                plugins = compat.get_package(server_info, client)
            finally:
                if client.isconnected():
                    client.disconnect()

            object.__setattr__(api, '_remote_plugins', plugins)

    return plugins
