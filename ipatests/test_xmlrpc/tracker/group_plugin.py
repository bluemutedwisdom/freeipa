#
# Copyright (C) 2015  FreeIPA Contributors see COPYING for license
#

from ipatests.test_xmlrpc import objectclasses
from ipatests.test_xmlrpc.xmlrpc_test import fuzzy_digits, fuzzy_uuid

from ipatests.test_xmlrpc.tracker.base import Tracker
from ipatests.util import assert_deepequal, get_group_dn


class GroupTracker(Tracker):
    """ Class for host plugin like tests """
    retrieve_keys = {u'dn', u'cn', u'gidnumber', u'member_user',
                     u'member_group'}
    retrieve_all_keys = retrieve_keys | {u'ipauniqueid', u'objectclass'}

    create_keys = retrieve_all_keys
    update_keys = retrieve_keys - {u'dn'}

    add_member_keys = retrieve_keys | {u'description'}

    def __init__(self, name):
        super(GroupTracker, self).__init__(default_version=None)
        self.cn = name
        self.dn = get_group_dn(name)

    def make_create_command(self, nonposix=False, external=False,
                            force=True):
        """ Make function that creates a group using 'group-add' """
        return self.make_command('group_add', self.cn,
                                 nonposix=nonposix, external=external)

    def make_delete_command(self):
        """ Make function that deletes a group using 'group-del' """
        return self.make_command('group_del', self.cn)

    def make_retrieve_command(self, all=False, raw=False):
        """ Make function that retrieves a group using 'group-show' """
        return self.make_command('group_show', self.cn, all=all)

    def make_find_command(self, *args, **kwargs):
        """ Make function that searches for a group using 'group-find' """
        return self.make_command('group_find', *args, **kwargs)

    def make_update_command(self, updates):
        """ Make function that updates a group using 'group-mod' """
        return self.make_command('group_mod', self.cn, **updates)

    def make_add_member_command(self, options={}):
        """ Make function that adds a member to a group
        Attention: only works for one user OR group! """
        if u'user' in options:
            self.attrs[u'member_user'] = [options[u'user']]
        elif u'group' in options:
            self.attrs[u'member_group'] = [options[u'group']]
        self.adds = options

        return self.make_command('group_add_member', self.cn, **options)

    def make_remove_member_command(self, options={}):
        """ Make function that removes a member from a group
        Attention: only works for one user OR group! """
        if u'user' in options:
            del self.attrs[u'member_user']
        elif u'group' in options:
            del self.attrs[u'member_group']
        return self.make_command('group_remove_member', self.cn, **options)

    def make_detach_command(self):
        """ Make function that detaches a managed group using
        'group-detach' """
        self.exists = True
        return self.make_command('group_detach', self.cn)

    def track_create(self):
        """ Updates expected state for group creation"""
        self.attrs = dict(
            dn=get_group_dn(self.cn),
            cn=[self.cn],
            gidnumber=[fuzzy_digits],
            ipauniqueid=[fuzzy_uuid],
            objectclass=objectclasses.posixgroup,
            )
        self.exists = True

    def check_create(self, result):
        """ Checks 'group_add' command result """
        assert_deepequal(dict(
            value=self.cn,
            summary=u'Added group "%s"' % self.cn,
            result=self.filter_attrs(self.create_keys)
            ), result)

    def check_delete(self, result):
        """ Checks 'group_del' command result """
        assert_deepequal(dict(
            value=[self.cn],
            summary=u'Deleted group "%s"' % self.cn,
            result=dict(failed=[]),
            ), result)

    def check_retrieve(self, result, all=False, raw=False):
        """ Checks 'group_show' command result """
        if all:
            expected = self.filter_attrs(self.retrieve_all_keys)
        else:
            expected = self.filter_attrs(self.retrieve_keys)

        assert_deepequal(dict(
            value=self.cn,
            summary=None,
            result=expected
            ), result)

    def check_find(self, result, all=False, raw=False):
        """ Checks 'group_find' command result """
        if all:
            expected = self.filter_attrs(self.retrieve_all_keys)
        else:
            expected = self.filter_attrs(self.retrieve_keys)

        assert_deepequal(dict(
            count=1,
            truncated=False,
            summary=u'1 group matched',
            result=[expected],
        ), result)

    def check_update(self, result, extra_keys={}):
        """ Checks 'group_mod' command result """
        assert_deepequal(dict(
            value=self.cn,
            summary=u'Modified group "%s"' % self.cn,
            result=self.filter_attrs(self.update_keys | set(extra_keys))
        ), result)

    def check_add_member(self, result):
        """ Checks 'group_add_member' command result """
        assert_deepequal(dict(
            completed=1,
            failed={u'member': {u'group': (), u'user': ()}},
            result=self.filter_attrs(self.add_member_keys)
        ), result)

    def check_add_member_negative(self, result):
        """ Checks 'group_add_member' command result when expected result
        is failure of the operation"""
        if u'member_user' in self.attrs:
            del self.attrs[u'member_user']
        elif u'member_group' in self.attrs:
            del self.attrs[u'member_group']

        expected = dict(
            completed=0,
            failed={u'member': {u'group': (), u'user': ()}},
            result=self.filter_attrs(self.add_member_keys)
        )
        if u'user' in self.adds:
            expected[u'failed'][u'member'][u'user'] = [(
                self.adds[u'user'], u'no such entry')]
        elif u'group' in self.adds:
            expected[u'failed'][u'member'][u'group'] = [(
                self.adds[u'group'], u'no such entry')]

        assert_deepequal(expected, result)

    def check_remove_member(self, result):
        """ Checks 'group_remove_member' command result """
        assert_deepequal(dict(
            completed=1,
            failed={u'member': {u'group': (), u'user': ()}},
            result=self.filter_attrs(self.add_member_keys)
        ), result)

    def check_detach(self, result):
        """ Checks 'group_detach' command result """
        assert_deepequal(dict(
            value=self.cn,
            summary=u'Detached group "%s" from user "%s"' % (
                self.cn, self.cn),
            result=True
        ), result)

    def make_fixture_detach(self, request):
        """Make a pytest fixture for this tracker

        The fixture ensures the plugin entry does not exist before
        and after the tests that use itself.
        """
        def cleanup():
            pass

        request.addfinalizer(cleanup)

        return self