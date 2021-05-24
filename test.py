import logging
import sys

from huawei_connector import HuaweiTelnet
import yaml

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

with open('test_model.yaml') as stream:
    model = yaml.unsafe_load(stream)
huawei_telnet = HuaweiTelnet(host=model['host'],
                             port=model['port'],
                             user=model['user'],
                             pwd=model['pwd'],
                             time_delta=model['time_delta'],
                             pre_cmd=model['pre_cmd'],
                             post_cmd=model['post_cmd'])
huawei_telnet.login(network_element='MSC')
huawei_telnet.logout()
