# Figherboat Testing


import unittest
from unittest.mock import Mock
from random import shuffle
import models
import socket
import selectors
from gameServer import *

SERVER_SOCKET = 1738

# class TestClientMethods(unittest.TestCase):


# Helper Functions
def encode_msg(array):
	return list(map(lambda x: x.encode(), array))


class TestServerMethods(unittest.TestCase):

	def setUp(self):

		# Create fake socket
		self.mock_sock = Mock()


		# Create fake player
		self.player = models.Player(self.mock_sock, 12345)
		self.out_msgs = []

		def mock_send(*args, **kwargs):
			self.out_msgs.append(args[0])

		self.player.send_msg = mock_send


		# Create fake connection
		self.conn = Mock()
		self.conn.fileobj = self.mock_sock
		self.conn.data = self.player


		# Create game manager
		self.manager = models.GameManager()

	def test_name_msg(self):
		msg_parts = ["NAME", "{: >20}".format("Ted")]

		self.mock_sock.recv.side_effect = encode_msg(msg_parts)

		process_read_request(self.manager, self.conn)

		self.assertEqual(self.player.get_name(), "Ted")


	def test_join_wait(self):
		"""tests the wait response that a player gets on joining an empty game"""
		msg_parts = ["JOIN", "2"]

		self.mock_sock.recv.side_effect = encode_msg(msg_parts)

		# Start actual test
		process_read_request(self.manager, self.conn)

		# Check variables
		self.assertIsNotNone(self.manager.waitingGames[0])
		self.assertEqual(self.player.status.lower(), "waiting")

		# Check response messages
		game_msg = self.out_msgs[0]
		self.assertEqual(game_msg[:4], "GAME")
		game_number = game_msg[4:]

		wait_msg = self.out_msgs[1]
		self.assertEqual(wait_msg[:4], "WAIT")
		self.assertEqual(wait_msg[4:7], game_number)
		self.assertLess(int(wait_msg[7]), int(wait_msg[8]))


	def test_join_update(self):

		# Set up
		msg_parts = ["JOIN", "3"]

		# Create second player
		mock_sock_2 = Mock()

		player_2 = models.Player(mock_sock_2, 18958)
		conn_2 = Mock()
		conn_2.fileobj = mock_sock_2
		conn_2.data = player_2

		self.mock_sock.recv.side_effect = encode_msg(msg_parts)
		mock_sock_2.recv.side_effect = encode_msg(msg_parts)


		# Test methods
		process_read_request(self.manager, self.conn)
		process_read_request(self.manager, conn_2)


		# Check variables
		self.assertIsNotNone(self.manager.waitingGames[1])
		self.assertEqual(self.player.status, "waiting")


		# Check response messages
		game_msg = self.out_msgs[0]
		game_number = game_msg[4:]
		wait_msg = self.out_msgs[1]
		wait_update_msg = self.out_msgs[2]

		self.assertEqual(wait_update_msg[:4], "WAIT")
		self.assertEqual(wait_update_msg[4:7], game_number)
		self.assertEqual(wait_update_msg[7], "2")
		self.assertEqual(wait_update_msg[8], "3")


	def test_join_play_sail(self):
		# Set up
		msg_parts = ["JOIN", "2"]

		# Create second player
		mock_sock_2 = Mock()

		player_2 = models.Player(mock_sock_2, 18958)
		conn_2 = Mock()
		conn_2.fileobj = mock_sock_2
		conn_2.data = player_2

		# Load Messages
		self.mock_sock.recv.side_effect = encode_msg(msg_parts)
		mock_sock_2.recv.side_effect = encode_msg(msg_parts)

		# Test method
		process_read_request(self.manager, self.conn)
		process_read_request(self.manager, conn_2)

		# Get message responses
		game_msg = self.out_msgs[0]
		wait_msg = self.out_msgs[1]
		play_msg = self.out_msgs[2]
		sail_msg = self.out_msgs[3]
		game_number = game_msg[4:]

		# Check play message
		self.assertEqual(play_msg[:4], "PLAY")
		self.assertEqual(play_msg[4:7], game_number)
		self.assertEqual(int(play_msg[7:9]), self.player.boardSize) # Boardsize
		self.assertEqual(play_msg[9], "1") # Number of opponents
		self.assertEqual(play_msg[10:15], "18958") # Opp 1 Port
		self.assertEqual(play_msg[15:35].lstrip(" "), "Anonymous58") #Opp 1 Name

		# Check sail message
		self.assertEqual(sail_msg[:4], "SAIL")
		self.assertEqual(sail_msg[4:7], game_number)
		self.assertEqual(sail_msg[7], "1") # Coord Size
		self.assertEqual(sail_msg[8], "5") # Boat Count
		self.assertEqual(sail_msg[9:14], "23345") # Boat Layout

		# Check Variables
		self.assertEqual(self.player.status, "settingBoard")
		self.assertEqual(self.player.boatHealth, [None] * 6)
		self.assertIsInstance(self.player.board, models.Board)


	def test_setb_msg(self):

		# Create message
		msg_parts = []
		msg_parts += ("SETB|123|1|8|7|8|8".split("|"))
		msg_parts += ("SETB|123|2|8|1|8|2|8|3".split("|"))
		msg_parts += ("SETB|123|3|2|3|3|3|4|3".split("|"))
		msg_parts += ("SETB|123|4|5|5|6|5|7|5|8|5".split("|"))
		msg_parts += ("SETB|123|5|1|7|2|7|3|7|4|7|5|7".split("|"))


		# Create game
		game = models.Game(123, 2)

		# Associate game with game manager
		self.manager.gameDict[123] = game

		# Prepare player for game
		self.player.set_up_game(8, [0,2,3,3,4,5])

		# load messages
		self.mock_sock.recv.side_effect = encode_msg(msg_parts)

		# Test method
		for i in range(5):
			self.assertNotEqual(self.player.get_status(), "ready")
			process_read_request(self.manager, self.conn)

		# Check Board
		exp_board = [[0, 0, 0, 0, 0, 0, 5, 0],
					[0, 0, 3, 0, 0, 0, 5, 0],
					[0, 0, 3, 0, 0, 0, 5, 0],
					[0, 0, 3, 0, 0, 0, 5, 0],
					[0, 0, 0, 0, 4, 0, 5, 0],
					[0, 0, 0, 0, 4, 0, 0, 0],
					[0, 0, 0, 0, 4, 0, 0, 0],
					[2, 2, 2, 0, 4, 0, 1, 1]]

		self.assertEqual(exp_board, self.player.board.plot)
		self.assertEqual(self.player.boatHealth, self.player.boatArray)
		self.assertEqual(self.player.get_status(), "ready")


	def test_shot_msg(self):

		# Create second player
		mock_sock_2 = Mock()

		player_2 = models.Player(mock_sock_2, "18958")
		player_2.gameId = 234
		conn_2 = Mock()
		conn_2.fileobj = mock_sock_2
		conn_2.data = player_2

		shot_1 = ["SHOT", "234", "12345", "5", "2"] # Miss
		shot_2 = ["SHOT", "234", "12345", "8", "8"] # Hit boat
		shot_3 = ["SHOT", "234", "12345", "8", "7"] # Sink boat
		shot_4 = ["SHOT", "234", "12345", "5", "7"] # Sink last boat

		msg_parts = shot_1 + shot_2 + shot_3 + shot_4

		mock_sock_2.recv.side_effect = encode_msg(msg_parts)

		# Set up game
		game = models.Game(234, 2)
		self.manager.gameDict[234] = game

		# Add players to game
		game.players["12345"] = self.player
		game.players["18958"] = player_2
		game.turnArray = list(game.players.values())
		# shuffle(game.turnArray)
		game.turn = 0

		# Set up player's board
		exp_board = [[0, 0, 0, 0, 0, 0, 15, 0],
					[0, 0, 13, 0, 0, 0, 15, 0],
					[0, 0, 13, 0, 0, 0, 15, 0],
					[0, 0, 13, 0, 0, 0, 15, 0],
					[0, 0, 0, 0, 14, 0, 5, 0],
					[0, 0, 0, 0, 14, 0, 0, 0],
					[0, 0, 0, 0, 14, 0, 0, 0],
					[12, 12, 12, 0, 14, 0, 1, 1]]

		self.player.set_up_game(8, [0,2,3,3,4,5])
		self.player.gameId = 234
		self.player.board.plot = exp_board
		self.player.liveBoats = 2
		self.player.boatHealth = [0, 2, 0, 0, 0, 1]
		self.player.set_status = "ready"





		# Test method
		for i in range(4):
			process_read_request(self.manager, conn_2)

		for i in self.out_msgs:
			print(i)

		print(self.player.board.plot)






	# def test_quit_msg(self):




	# def test_dropped_conn(self):




	# def tearDown(self):
		# self.conn.close()


# class TestCommunication(unittest.TestCase):

		# def mock_recv(*args, **kwargs):
		# 	if args[0] == 4:
		# 		return "NAME".encode()
		# 	elif args[0] == 20:
		# 		return "{: >20}".format("Ted").encode()
		# self.mock_sock.recv.side_effect = mock_recv


if __name__ == "__main__":
	unittest.main()
