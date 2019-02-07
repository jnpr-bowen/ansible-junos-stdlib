
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import collections
import os
import time
# import pprint
import json
from six import iteritems

from ansible.plugins.callback import CallbackBase
from ansible import constants as C

class CallbackModule(CallbackBase):
    """
    This callback add extra logging for the module junos_jsnapy .
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'jsnapy'

## useful links regarding Callback
## https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/callback/__init__.py

    def __init__(self):
        #self._pp = pprint.PrettyPrinter(indent=4)
        self._results = {}

        super(CallbackModule, self).__init__()

    def v2_runner_on_ok(self, result):
        """
        Collect test results for all tests executed if action is snapcheck or check
        """

        ## Extract module name
        module_name = ''
        module_args = {}
        if 'invocation' in result._result:
            if 'module_args' in result._result['invocation']:
                module_args = result._result['invocation']['module_args']
        module_name = result._task.action

        ## Check if dic return has all valid information
        ## Don't do anything if the name and args are empty or args is missing action
        if module_name == '' or module_args == {}:
            return None
        elif not module_args.has_key('action'):
            return None

        ## Make sure you are called for the jsnapy callback
        if (module_name in ['junos_jsnapy', 'juniper_junos_jsnapy'] and
            module_args['action'] in ['snapcheck', 'check']):

            ## Check if dict entry already exist for this host
            host = result._host.name
            if not host in self._results.keys():
                self._results[host] = []

            # self._pp.pprint(result.__dict__)
            self._results[host].append(result)

    def v2_playbook_on_stats(self, stats):

        ## Go over all results for all hosts
        for host, results in iteritems(self._results):
            has_printed_banner = False
            for result in results:
                # self._pp.pprint(result.__dict__)
                callback = None
                action = ''
                res = result._result
                if 'invocation' in res:
                    if 'module_args' in res['invocation']:
                        if 'callback' in res['invocation']['module_args']:
                            callback = res['invocation']['module_args']['callback']
                        if 'action' in res['invocation']['module_args']:
                            action = res['invocation']['module_args']['action']
                if action in ['check', 'snapcheck']:
                    if callback is None:
                        if res['final_result'] == "Failed":
                            for test_name, test_results in iteritems(res['test_results']):
                                for testlet in test_results:
                                    if testlet['count']['fail'] != 0:

                                        if not has_printed_banner:
                                            self._display.banner("JSNAPy Results for: " + str(host))
                                            has_printed_banner = True

                                        for test in testlet['failed']:

                                            # Check if POST exist in the response
                                            # data = ''
                                            if 'post' in test:
                                                data = test['post']
                                            else:
                                                data = test
                                            self._display.display(
                                                "Value of '{0}' not '{1}' at '{2}' with {3}".format(
                                                  str(testlet['node_name']),
                                                  str(testlet['testoperation']),
                                                  str(testlet['xpath']),
                                                  json.dumps(data)),
                                                color=C.COLOR_ERROR)
                    else:
                        self._display.banner("Results for: " + str(host), color=C.COLOR_VERBOSE)
                        self._display.display("Overall results: Passed: {}, Failed: {}".format(res['total_passed'],
                                                                                               res['total_failed']))
                        results_by_name = self._results_by_testname(res['test_results'])
                        for test_name, test_results in results_by_name.iteritems():
                            self._display.display(" -- Test: " + str(test_name))
                            for testlet in test_results:
                                if callback == 'info':
                                    if testlet['count']['pass'] > 0:
                                        self._display.display("\tResults for command/rpc: " + str(testlet['command']))
                                        for test in testlet['passed']:
                                            if test['message'] is not None:
                                                self._display.display("\t\t{}".format((test['message'])))
                                if callback == 'error' or callback == 'info':
                                    for test in testlet['failed']:
                                        self._display.display("\t Errors for command/rpc: " + str(testlet['command']))
                                        if 'message' in test:
                                            if test['message'] is not None:
                                                self._display.display("\t\t{}".format(test['message']),
                                                                      color=C.COLOR_ERROR)
                                            elif 'xpath_error' in test:
                                                if test['xpath_error'] is True:
                                                    self._display.display(
                                                      "\t\tTest failed, error in following XPath:\n\t\t{}".
                                                        format(testlet['xpath']), color=C.COLOR_ERROR)
                                                else:
                                                    self._display.display(
                                                      "\t\tTest Failed! Test may be invalid for device.",
                                                      color=C.COLOR_ERROR)
                                if testlet['result']:
                                    self._display.display("\tResult: Passed", color=C.COLOR_OK)
                                else:
                                    self._display.display("\tResult: Failed", color=C.COLOR_ERROR)

    def _results_by_testname(self, tests):
        testname_result_dict = collections.defaultdict(list)
        for cmd, data in tests.items():
            for test in data:
                test['command'] = cmd
                testname_result_dict[test['test_name']].append(test)
        return testname_result_dict
