# -*- encoding: utf-8 -*-
'''
HubbleStack Nova-to-Splunk returner

:maintainer: HubbleStack
:maturity: 2016.7.0
:platform: All
:requires: SaltStack

Deliver HubbleStack Nova result data into Splunk using the HTTP
event collector. Required config/pillar settings:

.. code-block:: yaml

    hubblestack:
      nova:
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

import logging

_max_content_bytes = 100000
http_event_collector_SSL_verify = False
http_event_collector_debug = True

log = logging.getLogger(__name__)

hec = None


def returner(ret):
    # Customized to split up the queries and extract the correct sourcetype
    opts = _get_options()
    logging.info("Options: %s" % json.dumps(opts))
    http_event_collector_key = opts['token']
    http_event_collector_host = opts['indexer']
    # Set up the collector
    hec = http_event_collector(http_event_collector_key, http_event_collector_host)
    # st = "salt:hubble:nova"
    data = ret['return']
    minion_id = ret['id']
    jid = ret['jid']

    if __grains__['master']:
        master=__grains__['master']
    else:
        master= socket.gethostname() # We *are* the master, so use our hostname
  
    for fai in data.get('Failure', []):
        check_id = fai.keys()[0]
        payload = {}
        event = {}
        event.update({"minion_id": minion_id})
        event.update({"check_result": "Failure"})
        event.update({"check_id": check_id})
        event.update({"job_id": jid})
        event.update({"master": master})
        if not isinstance(fai[check_id], dict):
            event.update({"check_desc": fai[check_id]})
        elif 'description' in fai[check_id]:
            event.update({"check_desc": fai[check_id]['description']})
        payload.update({"host": minion_id})
        payload.update({"index": opts['index']})
        payload.update({"sourcetype": opts['sourcetype']})
        payload.update({'event': event})
        hec.batchEvent(payload)

    for suc in data.get('Success', []):
        check_id = suc.keys()[0]
        payload = {}
        event = {}
        event.update({"minion_id": minion_id})
        event.update({"check_result": "Success"})
        event.update({"check_id": check_id})
        event.update({"job_id": jid})
        event.update({"master": master})
        if not isinstance(suc[check_id], dict):
            event.update({"check_desc": suc[check_id]})
        elif 'description' in suc[check_id]:
            event.update({"check_desc": suc[check_id]['description']})
        payload.update({"host": minion_id})
        payload.update({"sourcetype": opts['sourcetype']})
        payload.update({"index": opts['index']})
        payload.update({"event": event})
        hec.batchEvent(payload)

    if data.get('Compliance', None):
        payload = {}
        event = {}
        event.update({"minion_id": minion_id})
        event.update({"job_id": jid})
        event.update({"master": master})
        event.update({"compliance_percentage": data['Compliance']})
        payload.update({"host": minion_id})
        payload.update({"sourcetype": opts['sourcetype']})
        payload.update({"index": opts['index']})
        payload.update({"event": event})
        hec.batchEvent(payload)

    hec.flushBatch()
    return


def event_return(event):
    # When called from the master via event_return.
    # 
    # Note that presently the master won't see returners in file_roots/_returners 
    # so you need to put it in a returners/ subdirectory and configure
    # custom_modules in your master config.
    for e in event:
        if not("salt/job/" in e['tag']):
            continue # not a salt job event. Not relevant to hubble
        elif(e['data']['fun'] != "hubble.audit"):
            continue # not a call to hubble.audit, so not relevant
        else:
            logging.debug("Logging event: %s" % str(e))
            returner(e['data']) # Call the standard returner
    return 


def _get_options():
    try:
        token = __salt__['config.get']('hubblestack:nova:returner:splunk:token')
        indexer = __salt__['config.get']('hubblestack:nova:returner:splunk:indexer')
        sourcetype = __salt__['config.get']('hubblestack:nova:returner:splunk:sourcetype')
        index = __salt__['config.get']('hubblestack:nova:returner:splunk:index')
    except:
        return None
    splunk_opts = {"token": token, "indexer": indexer, "sourcetype": sourcetype, "index": index}
    return splunk_opts


def send_splunk(event, index_override=None, sourcetype_override=None):
    # Get Splunk Options
    # init the payload
    payload = {}

    # Set up the event metadata
    if index_override is None:
        payload.update({"index": opts['index']})
    else:
        payload.update({"index": index_override})

    if sourcetype_override is None:
        payload.update({"sourcetype": opts['sourcetype']})
    else:
        payload.update({"sourcetype": sourcetype_override})

    # Add the event
    payload.update({"event": event})
    logging.info("Payload: %s" % json.dumps(payload))

    # fire it off
    hec.batchEvent(payload)
    return True


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

        payloadLength = len(json.dumps(payload))

        if (self.currentByteLength + payloadLength) > self.maxByteLength:
            self.flushBatch()
            # Print debug info if flag set
            if http_event_collector_debug:
                print "auto flushing"
        else:
            self.currentByteLength = self.currentByteLength + payloadLength

        # If eventtime in epoch not passed as optional argument use current system time in epoch
        if not eventtime:
            eventtime = str(int(time.time()))

        # Update time value on payload if need to use system time
        data = {"time": eventtime}
        data.update(payload)

        self.batchEvents.append(json.dumps(data))

    def flushBatch(self):
        # Method to flush the batch list of events

        if len(self.batchEvents) > 0:
            headers = {'Authorization': 'Splunk ' + self.token}
            r = requests.post(self.server_uri, data=" ".join(self.batchEvents), headers=headers, verify=http_event_collector_SSL_verify)
            self.batchEvents = []
            self.currentByteLength = 0
