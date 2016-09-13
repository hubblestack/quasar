# -*- encoding: utf-8 -*-
'''
HubbleStack Pulsar-to-Splunk returner

:maintainer: HubbleStack
:maturity: 2016.7.0
:platform: All
:requires: SaltStack

Deliver HubbleStack Pulsar event data into Splunk using the HTTP
event collector. Required config/pillar settings:

.. code-block:: yaml

    hubblestack:
      pulsar:
        returner:
          splunk:
            token: <splunk_http_forwarder_token>
            indexer: <hostname/IP of Splunk indexer>
            sourcetype: <Destination sourcetype for data>
            index: <Destination index for data>
'''

import socket

# Imports for http event forwarder
import requests
import json
import time
import os.path
from collections import defaultdict

import logging

_max_content_bytes = 100000
http_event_collector_SSL_verify = False
http_event_collector_debug = True

log = logging.getLogger(__name__)

hec = None


def returner(ret):
    # Customized to split up the change events and send to Splunk.
    opts = _get_options()
    logging.info("Options: %s" % json.dumps(opts))
    http_event_collector_key = opts['token']
    http_event_collector_host = opts['indexer']
    hec_ssl = opts['http_event_server_ssl']
    # Set up the collector
    hec = http_event_collector(http_event_collector_key, http_event_collector_host, http_event_server_ssl=hec_ssl)
    # Check whether or not data is batched:
    if isinstance(ret, dict):  # Batching is disabled
        data = [ret]
    else:
        data = ret
    # Sometimes there are duplicate events in the list. Dedup them:
    data = _dedupList(data)
    fqdn = __grains__['fqdn']
    master = __grains__['master']
    fqdn_ip4 = __grains__['fqdn_ip4'][0]

    for item in data:
        alert = item['return']
        # The second half of the change will be "|IN_ISDIR" for directories
        change = alert['change'].split("|")[0]
        # Skip the IN_IGNORED events
        if change == "IN_IGNORED":
            continue
        if len(alert['change'].split("|")) == 2:
            object_type = 'directory'
        else:
            object_type = 'file'

        actions = defaultdict(lambda: 'unknown')
        actions['IN_ACCESS'] = 'read'
        actions['IN_ATTRIB'] = 'acl_modified'
        actions['IN_CLOSE_NOWRITE'] = 'read'
        actions['IN_CLOSE_WRITE'] = 'read'
        actions['IN_CREATE'] = 'created'
        actions['IN_DELETE'] = 'deleted'
        actions['IN_DELETE_SELF'] = 'deleted'
        actions['IN_MODIFY'] = 'modified'
        actions['IN_MOVE_SELF'] = 'modified'
        actions['IN_MOVED_FROM'] = 'modified'
        actions['IN_MOVED_TO'] = 'modified'
        actions['IN_OPEN'] = 'read'
        actions['IN_MOVE'] = 'modified'
        actions['IN_CLOSE'] = 'read'
        expected_cim_values = {'action': actions}

        event = {}
        payload = {}
        event["action"] = expected_cim_values['action'][change]
        event["change_type"] = 'filesystem'
        event["object_category"] = object_type
        event["object_path"] = alert['path']
        event['file_name'] = alert['name']
        event['file_path'] = alert['tag']

        if alert['stats']:  # Gather more data if the change wasn't a delete
            stats = alert['stats']
            event['object_id'] = stats['inode']
            event['file_acl'] = stats['mode']
            event['file_create_time'] = stats['ctime']
            event['file_modify_time'] = stats['mtime']
            event['file_size'] = stats['size'] / 1024.0  # Convert bytes to kilobytes
            event['user'] = stats['user']
            event['group'] = stats['group']
            if object_type == 'file':
                event['file_hash'] = alert['checksum']
                event['file_hash_type'] = alert['checksum_type']

        event.update({"master": master})
        event.update({"dest_host": fqdn})
        event.update({"dest_ip": fqdn_ip4})
        payload.update({"host": fqdn})
        payload.update({"index": opts['index']})
        payload.update({"sourcetype": opts['sourcetype']})
        payload.update({'event': event})
        hec.batchEvent(payload)

    hec.flushBatch()
    return


def _dedupList(l):
    deduped = []
    for i, x in enumerate(l):
        if x not in l[i + 1:]:
            deduped.append(x)
    return deduped


def _get_options():
    try:
        token = __salt__['config.get']('hubblestack:pulsar:returner:splunk:token')
        indexer = __salt__['config.get']('hubblestack:pulsar:returner:splunk:indexer')
        sourcetype = __salt__['config.get']('hubblestack:pulsar:returner:splunk:sourcetype')
        index = __salt__['config.get']('hubblestack:pulsar:returner:splunk:index')
    except:
        return None
    splunk_opts = {"token": token, "indexer": indexer, "sourcetype": sourcetype, "index": index}

    try:
        hec_ssl = __salt__['config.get']('hubblestack:pulsar:returner:splunk:hec_ssl')
    except:
        hec_ssl = True
    splunk_opts["http_event_server_ssl"]=hec_ssl

    return splunk_opts


# Thanks to George Starcher for the http_event_collector class (https://github.com/georgestarcher/)
# Default batch max size to match splunk's default limits for max byte
# See http_input stanza in limits.conf; note in testing I had to limit to 100,000 to avoid http event collector breaking connection
# Auto flush will occur if next event payload will exceed limit

class http_event_collector:

    def __init__(self, token, http_event_server, host="", http_event_port='8088', http_event_server_ssl=True, max_bytes=_max_content_bytes):
        self.token = token
        self.batchEvents = []
        self.maxByteLength = max_bytes
        self.currentByteLength = 0

        # Set host to specified value or default to localhostname if no value provided
        if host:
            self.host = host
        else:
            self.host = socket.gethostname()

        # Build and set server_uri for http event collector
        # Defaults to SSL if flag not passed
        # Defaults to port 8088 if port not passed

        if http_event_server_ssl:
            buildURI = ['https://']
        else:
            buildURI = ['http://']
        for i in [http_event_server, ':', http_event_port, '/services/collector/event']:
            buildURI.append(i)
        self.server_uri = "".join(buildURI)

        if http_event_collector_debug:
            print self.token
            print self.server_uri

    def sendEvent(self, payload, eventtime=""):
        # Method to immediately send an event to the http event collector

        headers = {'Authorization': 'Splunk ' + self.token}

        # If eventtime in epoch not passed as optional argument use current system time in epoch
        if not eventtime:
            eventtime = str(int(time.time()))

        # Fill in local hostname if not manually populated
        if 'host' not in payload:
            payload.update({"host": self.host})

        # Update time value on payload if need to use system time
        data = {"time": eventtime}
        data.update(payload)

        # send event to http event collector
        r = requests.post(self.server_uri, data=json.dumps(data), headers=headers, verify=http_event_collector_SSL_verify)

        # Print debug info if flag set
        if http_event_collector_debug:
            logger.debug(r.text)
            logger.debug(data)

    def batchEvent(self, payload, eventtime=""):
        # Method to store the event in a batch to flush later

        # Fill in local hostname if not manually populated
        if 'host' not in payload:
            payload.update({"host": self.host})

        # If eventtime in epoch not passed as optional argument and not in payload, use current system time in epoch
        if not eventtime and 'time' not in payload:
            eventtime = time.time()
            payload.update({"time": eventtime})

        payloadString = json.dumps(payload)
        payloadLength = len(payloadString)

        if (self.currentByteLength + payloadLength) > self.maxByteLength:
            self.flushBatch()
            # Print debug info if flag set
            if http_event_collector_debug:
                print "auto flushing"
        else:
            self.currentByteLength = self.currentByteLength + payloadLength


        self.batchEvents.append(payloadString)

    def flushBatch(self):
        # Method to flush the batch list of events

        if len(self.batchEvents) > 0:
            headers = {'Authorization': 'Splunk ' + self.token}
            r = requests.post(self.server_uri, data=" ".join(self.batchEvents), headers=headers, verify=http_event_collector_SSL_verify)
            self.batchEvents = []
            self.currentByteLength = 0
