

# Battleship server

import socket
import selectors
import types
# import sys
import argparse
from time import sleep
import models

MINIMUM_PLAYERS=2

sel = selectors.DefaultSelector()

gameManager = models.GameManager()

def main():

	host, port = check_arguments()

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((host, port))
	server.setblocking(False)
	server.listen()
	print("Listening on {0}".format((host, port)))

	sel.register(server, selectors.EVENT_READ, data=None)

	try:
		# Game loop
		while True:
			events = sel.select(timeout=None)

			# sleep(1)
			for key, mask in events:

				if key.data is None:
					accept_connection(key.fileobj)

				elif mask & selectors.EVENT_READ:
					process_read_request(gameManager, key)

	except KeyboardInterrupt:
		sel.close()
		server.close()
		print("caught keyboard interrupt, exiting")
	finally:
		sel.close()
		server.close()




def check_arguments():

	parser = argparse.ArgumentParser(description="<host> <port>")

	parser.add_argument(help="<host>", nargs=1, type=str, dest='host')
	parser.add_argument(help="<port>",nargs=1, type=int, dest='port')

	args = parser.parse_args()

	return (args.host[0], args.port[0])




def process_read_request(manager, conn):
	# parse connection
	sock = conn.fileobj
	player = conn.data


	# read message type
	msgType = read_socket(sock, 4)

	# Process incoming client message
	if msgType == "NAME":
		# Change player's name
		name = read_socket(sock, 20).lstrip(" ")
		player.set_name(name)



	elif msgType == "JOIN":
		# Allow player to join game
		desiredPlayers = read_socket(sock, 1)

		manager.join_open_game(int(desiredPlayers), player)


	elif msgType == "SETB":

		# parse incoming message
		gameId = int(read_socket(sock, 3))
		boatId = int(read_socket(sock, 1))

		# get game and boatLength
		game = manager.get_game(gameId)
		boatLength = game.get_boat_length(boatId)

		if game == None:
			pass

		# Package coordinates
		coords = [0] * (boatLength * 2)
		for loc in range(len(coords)):
			coords[loc] = int(read_socket(sock, game.coordLen))

		# set boat position
		player.place_boat(boatId, coords)



	elif msgType == "SHOT":

		# parse incoming message
		gameId = int(read_socket(sock, 3))
		target = read_socket(sock, 5)

		game = manager.get_game(gameId)

		if game == None:
			pass

		loc = [0] * 2
		for i in range(len(loc)):
			loc[i] = int(read_socket(sock, game.coordLen))

		game.process_shot(player.get_port(), target, loc)

		game.advance_turn()



	elif msgType == "QUIT":
		# parse incoming message
		gameId = read_socket(sock, 3)
		game = manager.get_game(gameId)

		if game==None:
			pass

		game.player_quit(player.get_port())
		player.quit_game()



def read_socket(connection, bytes):
	return connection.recv(bytes).decode()



def write_socket(connection, msg):
	connection.sendall(msg.encode())



def accept_connection(sock):
	conn, addr = sock.accept()
	host, port = addr

	conn.setblocking(False)
	print("accepting connection from {0}".format(addr))

	data = models.Player(conn, port)
	events = selectors.EVENT_READ | selectors.EVENT_WRITE

	sel.register(conn, events, data=data)


if __name__ == '__main__':
	main()



