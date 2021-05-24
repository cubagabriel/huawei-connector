"""
Desc    : A wrapper class for python telnetlib.Telnet class that can send configuration commands directly to many Huawei core
network products (PGW, NBI) that uses plain text MML over TCP.
Author  : Gabriel Cuba
"""
import telnetlib
import re
from random import randint
import os
import time
import logging

DIR = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)


class HuaweiTelnet:
    """
    uses Telnet as protocol and implements login, registering NE and logout
    """
    DEFAULT_END_STRING = b' END\r\n'

    def __init__(self, host, port, user, pwd, pre_cmd, post_cmd, time_delta=0):
        """

        :param host:
        :param port:
        :param user:
        :param pwd:
        :param time_delta: use it to limit TPS
        :param pre_cmd: if no pre-commands, empty list
        :param post_cmd: if no post-commands, empty list
        """
        self.ne_name = None
        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.time_delta = time_delta
        self.pre_cmd_dict = pre_cmd
        self.post_cmd_dict = post_cmd
        time.sleep(randint(0, 3))  # add some random delay for multiprocessing case
        self.tn = telnetlib.Telnet(self.host, self.port)

    def login(self, network_element, sub_network_element=''):
        """

        :param network_element: will try to replace "network_element" on each pre-command text
        :param sub_network_element: will try to replace "subnetwork_element" on each pre-command text
        :return: 'OK' if success, otherwise 'error' or 'timeout'
        """
        user = self.user
        pwd = self.pwd
        self.ne_name = network_element
        for pre_cmd in self.pre_cmd_dict:
            # only replace values if text contains "format" method
            cmd = eval(pre_cmd['text']) if 'format' in pre_cmd['text'] else pre_cmd['text']
            output = self.__send_mml(cmd, self.time_delta)
            logger.info(output)
            if output == 'error':
                return 'error'
            retcode = parse_retcode(output)
            if not retcode.isdigit():
                return 'timeout'
            elif retcode != '0':
                # we return an error as we need to be logged in to send any command
                self.tn.close()
                return 'error'
        return 'OK'

    def logout(self):
        user = self.user
        for post_cmd in self.post_cmd_dict:
            cmd = eval(post_cmd['text']) if 'format' in post_cmd['text'] else post_cmd['text']
            output = self.__send_mml(cmd, self.time_delta)
            if output == 'error':
                return 'error'
        self.tn.close()

    def send_command(self, cmd, end_string=None, delay=True):
        """
        :param delay:
        :param end_string: string to be taken as the end of the telnet response, can be string or bytes
        :param cmd: command to be sent
        :return: result of command
        """
        # end_string adaptation
        end_string = end_string if end_string else self.DEFAULT_END_STRING
        end_string = end_string.encode('ascii') if type(end_string) == str else end_string
        # read any data left in buffer from previous commands
        self.tn.read_lazy()
        self.tn.write(cmd.encode('ascii') + b"\r\n")
        try:
            logger.debug(self.ne_name + ' - sending command: {}'.format(cmd))
            output = self.tn.read_until(end_string, 12)
            # when the response has many pages (with multiple "END") the caller might use a different string, however,
            # we always need to read the last "END" to <clean> the buffer. Another approach would be to read multiple
            # times with "END" but we would need a timeout for the last try
            if end_string != self.DEFAULT_END_STRING:
                self.tn.read_until(self.DEFAULT_END_STRING, 5)
        except ConnectionResetError as e:
            logger.error(str(e))
            return 'error'
        if delay:
            time.sleep(self.time_delta)
        return output

    def __send_mml(self, cmd, time_delta):
        """

        :param cmd: command to be sent
        :param time_delta: time to wait
        :return: result of command
        """
        self.tn.write(cmd.encode('ascii') + b"\r\n")
        try:
            logger.debug('sending command: {}'.format(cmd))
            output = self.tn.read_until(b" END", None)
        except ConnectionResetError as e:
            logger.error(str(e))
            return 'error'
        time.sleep(time_delta)
        return output


def parse_retcode(output):
    """ Receives response from telnet and will try to return the value as a string

    :param output: string containing the encoded telnet response
    :return: the last value of RETCODE found or None
    """
    dec_output = output.decode("utf-8").splitlines()
    retcode = None
    for line in dec_output:
        if line.count('RETCODE = ') > 0:
            retcode = re.search('[0-9]+', line).group()
    return retcode


def parse_number_of_results(output):
    """ Receives response from telnet and will try to return the number of results

    :param output: string containing the encoded telnet response
    :return: the number of results as a string or None
    """
    dec_output = output.decode("utf-8").splitlines()
    for line in dec_output:
        if line.count('Number of results = ') > 0:
            return re.search('[0-9]+', line).group()
        elif line.count('No matching result is found') > 0:
            return '0'
    return None


def send_cmd_get_result_number(connection, cmd):
    """ Sends commands to a telnet connection created somewhere else

    :param connection: connector in open state
    :param cmd: command to be executed via the telnet connection
    :return: error or the number of results if the result code is 0
    """
    logger.debug('Sending command: {}'.format(cmd))
    output = connection.send_command(cmd)
    if output == 'error':
        return 'error'
    retcode = parse_retcode(output)
    if retcode == '0':
        num_of_results = parse_number_of_results(output)
        logger.debug('Number of results is: {}'.format(num_of_results))
        return num_of_results
    elif retcode.isdigit():
        logger.debug('Received code {} from NE, assuming number of results is 0'.format(retcode))
        return '0'
    else:
        return 'error'


def send_cmd_return_raw(connection, cmd, end_string=None):
    """ Sends commands to a telnet connection created somewhere else

    :param end_string:
    :param connection: connector in open state
    :param cmd: command to be executed via the telnet connection
    :return: error or the raw result as a string if the result code is 0
    """
    logger.debug('Sending command: {}'.format(cmd))
    output = connection.send_command(cmd, end_string=end_string)
    if output == 'error':
        return 'error'
    retcode = parse_retcode(output)
    if retcode == '0':
        return output.decode("utf-8")
    else:
        return 'error'
