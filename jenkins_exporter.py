#!/usr/bin/python

import re
import time
import requests
import argparse
from pprint import pprint

import os
from sys import exit
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY

DEBUG = int(os.environ.get('DEBUG', '0'))

COLLECTION_TIME = Summary('jenkins_collector_collect_seconds', 'Time spent to collect metrics from Jenkins')

class JenkinsCollector(object):
    currentBuildStatus = "currentBuild"
    offlineNodes = "offlineNodes"

    def __init__(self, target, user, password, insecure):
        if not os.environ.get('JENKINS_SERVER'):
            if os.environ.get('ENV_ID') == 'live':
                self._target = 'http://jenkins.pipedrive.tools'
            else:
                self._target = 'http://jenkins.pipedrivetest.tools'
        else:
            self._target = target
        self._target_computer = self._target + '/computer'
        self._user = user
        self._password = password
        self._insecure = insecure

    def collect(self):
        start = time.time()
        # Request data from Jenkins
        response = self._request_data_from_executors();

        self._setup_empty_prometheus_metrics()

        for offlineNode in response['offlineNodes']:
            if DEBUG:
                print("Found Offline Node: {}".format(offlineNode))
                pprint(offlineNode)
            self._get_offline_node_metrics(offlineNode)

        for currentBuild in response['currentBuilds']:
            if DEBUG:
                print("Found Current Build: {}".format(currentBuild))
                pprint(currentBuild)
            self._get_duration_for_current_builds(currentBuild)

        for metric in self._prometheus_metrics[self.currentBuildStatus].values():
            yield metric

        for metric in self._prometheus_metrics[self.offlineNodes].values():
            yield metric

        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _request_data_from_executors(self):
        url = '{0}/api/json'.format(self._target_computer)
        tree = 'computer[displayName,offline,offlineCause[timestamp],offlineCauseReason,executors[currentExecutable[url]],oneOffExecutors[currentExecutable[url]]]'
        params = {
            'tree': tree,
        }

        def parseExecutors(myurl):
            # params = tree: jobs[name,lastBuild[number,timestamp,duration,actions[queuingDurationMillis...
            if self._user and self._password:
                response = requests.get(myurl, params=params, auth=(self._user, self._password), verify=(not self._insecure))
            else:
                response = requests.get(myurl, params=params, verify=(not self._insecure))
            if DEBUG:
                pprint(response.text)
            if response.status_code != requests.codes.ok:
                raise Exception("Call to url %s failed with status: %s" % (myurl, response.status_code))
            result = response.json()
            if DEBUG:
                pprint(result)

            currentbuilds = []
            offlineNodes = []
            for node in result['computer']:
                # Check for offline nodes and collect timestamps
                if node['offline']:
                    offlineNodes.append(
                        {
                            'name': node['displayName'],
                            'timestamp': node['offlineCause']['timestamp']
                        }
                    )

                # Check for currentExecutables in executors
                for executable in node['executors']:
                    if executable['currentExecutable']:
                        currentbuilds.append(executable['currentExecutable']['url'])

                for executable in node['oneOffExecutors']:
                    if executable['currentExecutable']:
                        currentbuilds.append(executable['currentExecutable']['url'])
                
            return {
                'currentBuilds': currentbuilds,
                'offlineNodes': offlineNodes
            }

        return parseExecutors(url)

    def _get_duration_of_build(self, jobUrl):
        url = '{0}/api/json'.format(jobUrl)
        tree = 'timestamp'
        params = {
            'tree': tree,
        }

        def parseFields(myurl):
            # params = tree: jobs[name,lastBuild[number,timestamp,duration,actions[queuingDurationMillis...
            if self._user and self._password:
                response = requests.get(myurl, params=params, auth=(self._user, self._password), verify=(not self._insecure))
            else:
                response = requests.get(myurl, params=params, verify=(not self._insecure))
            if DEBUG:
                pprint(response.text)
            if response.status_code != requests.codes.ok:
                raise Exception("Call to url %s failed with status: %s" % (myurl, response.status_code))
            result = response.json()
            if DEBUG:
                pprint(result)

            return {
                'timestamp': result['timestamp']
            }

        return parseFields(url)

    def _setup_empty_prometheus_metrics(self):
        # The metrics we want to export.
        self._prometheus_metrics = {}

        current_builds = re.sub('([A-Z])', '_\\1', self.currentBuildStatus).lower()
        self._prometheus_metrics[self.currentBuildStatus] = {
            'timestamp':
                GaugeMetricFamily('jenkins_job_{0}'.format(current_builds),
                                    'Jenkins current build timestamp in unixtime for {0}'.format(self.currentBuildStatus), labels=["joburl"]),
        }


        offline_nodes = re.sub('([A-Z])', '_\\1', self.offlineNodes).lower()
        self._prometheus_metrics[self.offlineNodes] = {
            'timestamp':
                GaugeMetricFamily('jenkins_job_{0}'.format(offline_nodes),
                                    'Jenkins node offline timestamp in unixtime for {0}'.format(self.offlineNodes), labels=["name"]),
        }

    def _get_offline_node_metrics(self, node):
        self._add_offline_node_data_to_prometheus_structure(node, node['name'])

    def _get_duration_for_current_builds(self, url):
        result = self._get_duration_of_build(url)
        self._add_current_build_duration_data_to_prometheus_structure(result, url)

    def _add_offline_node_data_to_prometheus_structure(self, result, name):
        if result.get('timestamp', 0):
            self._prometheus_metrics[self.offlineNodes]['timestamp'].add_metric([name], result.get('timestamp'))
    
    def _add_current_build_duration_data_to_prometheus_structure(self, result, url):
        # If there's a null result, we want to pass.
        if result.get('timestamp', 0):
            self._prometheus_metrics[self.currentBuildStatus]['timestamp'].add_metric([url], result.get('timestamp'))

    

def parse_args():
    parser = argparse.ArgumentParser(
        description='jenkins exporter args jenkins address and port'
    )
    parser.add_argument(
        '-j', '--jenkins',
        metavar='jenkins',
        required=False,
        help='server url from the jenkins api',
        default=os.environ.get('JENKINS_SERVER', '')
    )
    parser.add_argument(
        '--user',
        metavar='user',
        required=False,
        help='jenkins api user',
        default=os.environ.get('JENKINS_USER')
    )
    parser.add_argument(
        '--password',
        metavar='password',
        required=False,
        help='jenkins api password',
        default=os.environ.get('JENKINS_PASSWORD')
    )
    parser.add_argument(
        '-p', '--port',
        metavar='port',
        required=False,
        type=int,
        help='Listen to this port',
        default=int(os.environ.get('VIRTUAL_PORT', '9118'))
    )
    parser.add_argument(
        '-k', '--insecure',
        dest='insecure',
        required=False,
        action='store_true',
        help='Allow connection to insecure Jenkins API',
        default=False
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(JenkinsCollector(args.jenkins, args.user, args.password, args.insecure))
        start_http_server(port)
        print("Polling every 30 sec. Serving at port: {}".format(args.jenkins, port))
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        print(" Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
