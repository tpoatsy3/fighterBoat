# Battleship client

# import socket
# import thread

# def on_connect(client, addr):
# 	msg = client.recv(1024)
# 	print("{0}: {1}".format(addr, msg))
# 	msg = raw_input("To {0}:".format(addr))
# 	client.send(msg)


# cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# cli.connect(('', 2136))
# cli.send("hello".encode())

# while True:
# 	print(cli.recv(1024))
# 	inpt = raw_input("type anything and click enter... ")
# 	cli.send(inpt)


import socket
import selectors
import types
import sys
import signal
import fcntl
import os

from time import sleep

import models





sel = selectors.DefaultSelector()

def main():
	if len(sys.argv) != 3:
		print("usage:", sys.argv[0], "<host> <port>")
		sys.exit(1)

	host, port = sys.argv[1:3] # checkArguments()
	start_connection(host, int(port))

	try:
		while True:

			sleep(1)
			events = sel.select(timeout=0)
			for key, mask in events:
				if type(key.data) == models.Client:

					if mask & selectors.EVENT_READ:
						process_server_msg(key)
				else:
					got_keyboard_data(key.fileobj, key.data)

			# Check for a socket being monitored to continue.
			if not sel.get_map():
				break
	except KeyboardInterrupt:
		print("caught keyboard interrupt, exiting")

	finally:
		sel.unregister(sys.stdin)
		sel.close()

def process_server_msg(key):
	conn = key.fileobj
	client = key.data

	msg = conn.recv(4).decode()
	print("msg:" + msg)

	if msg == "GAME":
		client.parse_game_msg()
		return

	gameId = conn.recv(3).decode()

	# Check for correct game number
	if client.get_game_id() != gameId:
		# IGNORE MESSAGE, ERROR HAS OCCURED
		wrongMsg = conn.recv(1024).decode()
		print("THE WRONG GAME NUMBER WAS SENT TO {}, YOU HAVE SOME WORK TO DO".format(client.get_port()))
		print("Wrong Message: {}".format(wrongMsg))
		return None

	if msg == "WAIT":
		client.parse_wait_msg()

	elif msg == "PLAY":
		client.parse_play_msg()

	elif msg == "SAIL":
		client.parse_sail_msg()


def got_keyboard_data(stdin, data):
	msg = stdin.read()
	send_message(data, msg)


def set_nonblocking_stdin():
	# Set sys.stdin non-blocking
	orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
	fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)


def start_connection(host, port):

	# Connection to server
	addr = (host, port)
	print('starting connection to', addr)
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setblocking(False)
	sock.connect_ex(addr)

	events = selectors.EVENT_READ | selectors.EVENT_WRITE

	myHost, myPort = sock.getsockname()

	data = models.Client(sock, myPort)

	set_nonblocking_stdin()

	sel.register(sock, events, data=data)
	sel.register(sys.stdin, selectors.EVENT_READ, data=sock)






def send_message(socket, input):

	socket.send(input.encode())
	# msgType = input[:4]

	# if msgType == "JOIN":
		# players = input("Number of players:")






	# elif msgType == "NAME":


	# elif msgType == "SETB":


	# elif msgType == "SHOT":


	# elif msgType == "QUIT":






def process_event(key):
	# print(key)
	return None
	# sock =

def service_connection(key, mask):
	sock = key.fileobj
	data = key.data

	if mask & selectors.EVENT_READ:
		recv_data = sock.recv(1024).decode()
		if recv_data:
			print('recieved', repr(recv_data), 'from connection')

		if not recv_data:
			print('closing connection', data.connid)
			sel.unregister(sock)
			sock.close()

	if mask & selectors.EVENT_WRITE:
		if not data.outb:
			data.outb = input("Send to server: ")
		if data.outb:
			print('sending', repr(data.outb), 'to connection')
			sent = sock.send(data.outb.encode())
			data.outb = None

if __name__ == '__main__':
	main()
