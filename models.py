from random import uniform, shuffle # used by Game
from kivy.event import EventDispatcher
from copy import deepcopy
import math

MISS = 0
HIT = 1
SINK = 2
ELIMINATED = 3
WON = 4

LEN_GAME = 3
LEN_NAME = 20
LEN_PORT = 5
LEN_BOARD_SIZE = 2


class Transmitter:
	""" Contians methods that help with socket transactions

		Parameters:
			socket - from socket library """

	def __init__(self, socket):
		self.socket = socket


	def send_msg(self, msg):
		"""sends encoded message(msg) over socket connection"""
		self.socket.send(msg.encode())

	def str_with_buffer(self, content, length, fill):
		"""Returns inputted content to a string of a certain length
		Any additional space in the returned string is filled by 'fill' character"""
		return "{:{fill}>{length}}".format(content, fill=fill, length=length)

	def recv_int(self, byteLen):
		"""Reads from socket and returns the integer value"""
		return int(self.socket.recv(byteLen).decode())

	def recv_str(self, byteLen):
		"""Reads from socket and returns a decoded string"""
		return self.socket.recv(byteLen).decode().lstrip(' ')


class GameManager:
	""" Organizes instances of game class for server """

	def __init__(self):
		self.gameCounter = 0
		self.minPlayers = 2
		self.maxPlayers = 5

		self.waitingGames = [None] * (self.maxPlayers - self.minPlayers)
		self.gameDict = {}

	def join_open_game(self, desPlayers, player):
		""" Adds 'player' to a game with 'desPlayers' number of players
		returns the game instance that the player was added to

		Params:
		desPlayer-int- number of desired players wanted in the game
		player-Player- data structure associated with requesting user"""

		game = None

		# return game of X players
		if self.waitingGames[desPlayers - self.minPlayers] == None:
			# if one doesnt exist, create and return it
			game = self.create_new_game(desPlayers)

		else:
			# Otherwise,
			game = self.waitingGames[desPlayers - self.minPlayers]

		# Add player to game
		game.add_player(player)

		# Start game if it has enough players to play
		if len(game.players) == game.numPlayers:
			self.waitingGames[desPlayers - self.minPlayers] = None
			game.start_game()

		# Else, update waiting information
		else:
			# Set player status to waiting
			player.set_status("waiting")

			# Send waiting update to all waiting players in this game
			for i in game.players:
				# Get reference to player
				waiting_player = game.players[i]

				# Send waiting message
				waiting_player.send_waiting_message(len(game.players), desPlayers)

		return game



	def create_new_game(self, numPlayers):
		"""Returns a new Game instance with 'numPlayers' players"""

		# Create new gameId and increment for next use (gamecounter must remain a )
		newId = self.gameCounter
		self.gameCounter = (self.gameCounter + 1) % 1000

		# Create new game
		game = Game(newId, numPlayers)

		# Add game to dictionary and array for lookup and origanization
		self.gameDict[newId] = game
		self.waitingGames[numPlayers - self.maxPlayers] = game

		return game

	# Getter methods
	def get_game(self, gameId):
		return self.gameDict.get(gameId)


class Game:
	"""Class that provides the framework and structure for play"""

	def __init__(self, id, numPlayers, boardSize=8):
		"""Params:
		id - integer - the unique id number for the game, registered in game manager's dictionary
		numPlayers -  integer - total number of players at the game's start
		boardSize - integer - number of spaces in both the x and y directions
		 """

		# Game information
		self.numPlayers = numPlayers
		self.origPlayers = numPlayers
		self.id = id
		self.status = "waiting"

		# holds player and board objects, respectively, as values in dict keyed by thier port numbers
		self.players = {}
		self.boards = {}

		# Stores boat lengths indexed at their id numbers
		self.boatLengths = [0,2,3,3,4,5]
		self.boardSize = 8

		# Number of digits that coordinates are given in
		self.coordLen = int(math.log(self.boardSize, 10)) + 1

		# Turn indicators
		self.turn = 0
		self.turnList = None


	def add_player(self, player):
		"""Add player to game"""
		self.players[player.get_port()] = player
		player.set_game_id(self.id)
		player.send_game_notification()


	def player_quit(self, port):
		"""Process a user's request to quit in a game"""

		player = self.players.pop(port)
		board = self.boards.pop(port)

		# Protect turn indicator from quit consequences
		i = self.turnList.index(port)
		if i > self.turn:
			self.turn -= 1

		# Remove player from game list
		self.turnList.remove(port)

		if len(self.players) == 1:
			for oppPort, oppPlayer in self.players.items():
				oppPlayer.send_quit_notificaiton(port)

		else:
			for oppPort, oppPlayer in self.players.items():
				oppPlayer.send_quit_notificaiton(port)

				if len(self.players) == 1:
					oppPlayer.send_victory_notification()


	def start_game(self):
		"""Set up game environment/variables needed for play"""

		self.status = "active"

		self.turnArray = shuffle(list(self.players))

		for curPort in self.players:

			# Get player
			player = self.players[curPort]

			# Create shot board
			board = Board(self.boardSize)
			self.boards[curPort] = board

			# Initialize game for player
			player.set_up_game(self.boardSize, self.boatLengths)

			# Create opponent array for PLAY message
			opps = []
			for oppPort in self.players:
				opp = self.players[oppPort]
				if oppPort != curPort:
					opps.append((oppPort, opp.get_name()))

			# Send PLAY message to each player
			player.send_play_msg(self.boardSize, opps)

			# Send SAIL message to each player
			player.send_sail_msg(self.coordLen, self.boatLengths)

			# Set player statuses
			player.set_status("settingBoard")


	def process_shot(self, shooterId, targetId, loc):
		"""Process a shot taken in a game and return outcome"""

		#TODO: Add logic to check turn first
		target = self.players[targetId]
		boatId = None
		outcome = target.recieve_shot(loc)

		if outcome == SINK:
			boatId = target.get_boat_id(loc)

		elif outcome == ELIMINATED:
			self.numPlayers -= 1
			if self.numPlayers == 1:
				outcome = WON

		for i in self.players:
			cur_player = self.players[i]
			cur_player.send_shot_msg(shooterId, targetId, loc, outcome, boatId)

	def remove_player(self):
		# TODO: Define from player_quit then add to process shot
		pass

	def advance_turn(self):
		"""Advance turn to next active player"""
		while True:
			self.turn = (self.turn + 1) % self.origPlayers
			player = self.turnArray[self.turn]
			if player.get_status() != "eliminated":
				break

		player.send_turn_notification()


	# Getters
	def get_boat_length(self, id):
		return self.boatLengths[int(id)]


class Player(Transmitter):

	def __init__(self, socket, port:int):

		Transmitter.__init__(self, socket)

		# For UI purposes
		self.name = "Anonymous" + str(port)[-2:]
		self.status = None

		# ID and contact information, assigned at creation
		self.socket = socket
		self.id = port

		# Assigned when joining a game
		self.gameId = None

		# For in game use
		self.boatHealth = []
		self.board = None

		# Game Information
		self.boardSize = 8

	def place_boat(self, boatId, coords):
		""" Sets the location of one of the player's boats)
		boatId - which boat is being set
		coords - array of location data in [x1, y1, x2, y2, ...] format"""

		# Verify boat length and set boat on player's board
		if len(coords)/2 == self.boatArray[boatId]:
			self.board.place_boat(boatId, coords)

			# Add boat's health so we can track which boats are set
			self.boatHealth[boatId] = len(coords)/2

		# else:
			# Send error message to player. Should include boat array/ boat format (similar to play)

		# Determine if the player has placed all of thier boats
		for i in range(1, len(self.boatArray)):
			if self.boatArray[i] != self.boatHealth[i]:
				break
		else:
			self.boatHealth[0] = 0
			self.status = "ready"

	def recieve_shot(self, loc):
		"""Process shot targeted at player and return the outcome"""

		print("Recieve Shot: {}, port: {}".format(loc, self.id))
		result = self.board.check_space(*loc)
		self.board.register_hit(*loc)


		# Shooter Missed
		if result == 0:
			return MISS

		# Shooter already hit that spot
		elif result > 10:
			return HIT

		# Shooter hit a boat
		else:
			self.boatHealth[result] -= 1
			print(self.boatHealth)


			# Shooter only damaged a boat
			if self.boatHealth[result] != 0:
				return HIT

			# Shooter sank a boat
			else:
				self.liveBoats -= 1
				if self.liveBoats != 0:
					return SINK

				# Shooter sank player's last boat
				else:
					self.status = "eliminated"
					self.send_elim_msg()
					return ELIMINATED

	def send_play_msg(self, boardSize, opps):
		""" Sends a 'PLAY' message to players containing game and opponent information"""

		msg = "PLAY"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		boardSize = self.str_with_buffer(boardSize, 2, 0)
		oppCount = self.str_with_buffer(len(opps), 1, 0)

		oppIdStr = ""
		for i in range(len(opps)):
			port, name = opps[i]
			oppIdStr += self.str_with_buffer(port, 5, 0) + self.str_with_buffer(name, 20, " ")

		outMsg = msg + gameId + boardSize + oppCount + oppIdStr
		self.send_msg(outMsg)



	def send_sail_msg(self, coordLen, boats):
		"""Send SAIL message to each player indicating that they should place their
		boats on the board"""


		msg = "SAIL"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		coordLen = self.str_with_buffer(coordLen, 1, 0)
		boatCount = self.str_with_buffer(len(boats) - 1, 1, 0)
		boatLens = ""
		for i in range(1, len(boats)):
			boatLens += str(boats[i])

		outMsg = msg + gameId + coordLen + boatCount + boatLens
		self.send_msg(outMsg)

	def send_shot_msg(self, shooter, target, loc, outcome, boatId):
		"""Send SHOT message indiciating who shot whom and the result to each of
		the players in the game"""

		msg = "SHOT"
		gameId = self.str_with_buffer(self.gameId, 3, 0)
		shootr = self.str_with_buffer(shooter, 5, 0)
		tar = self.str_with_buffer(target, 5, 0)
		x = self.str_with_buffer(loc[0], 1, 0)
		y = self.str_with_buffer(loc[1], 1, 0)
		result = self.str_with_buffer(outcome, 1, 0)

		outMsg = msg + gameId + shootr + tar + x + y + result

		if int(outcome) == 2:
			boatId = self.str_with_buffer(boatId, 1, 0)
			outMsg += boatId

		self.send_msg(outMsg)


	def send_elim_msg(self):
		"""Send LOSE message indicating that the receiving player has been eliminated"""
		msg = "LOSE"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId
		self.send_msg(outMsg)

	def send_game_notification(self):
		"""Send GAME message indiciating the gameId for the game they joined"""
		msg = "GAME"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId
		self.send_msg(outMsg)

	def send_turn_notification(self):
		"""Send URMV message indiciating that it's the recieving player's move"""
		msg = "URMV"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId

		self.send_msg(outMsg)

	def send_waiting_message(self, curPlayerCount, tarPlayerCount):
		"""Send WAIT message indicating that a game is building and has 'curPlayerCount'
		 of the required 'tarPlayerCount' players needed to begin"""

		msg = "WAIT"
		gameId = self.str_with_buffer(self.gameId, LEN_GAME, 0)
		cur = self.str_with_buffer(curPlayerCount, 1, 0)
		tar = self.str_with_buffer(tarPlayerCount, 1, 0)

		outMsg = msg + gameId + cur + tar

		self.send_msg(outMsg)

	def send_quit_notification(self, port):
		"""Send LEFT message indiciating that another player has quit the game"""

		msg = "LEFT"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		quitPort = self.str_with_buffer(port, 5, 0)

		outMsg = msg + gameId + quitPort

		self.send_msg(outMsg)

	def send_victory_notification(self):
		"""Anncounce that the receiving player has won"""
		msg = "WIN!"
		gameId = self.str_with_buffer(self.gameId, 3,0)

		outMsg = msg + gameId

		self.send_msg(outMsg)

	def set_up_game(self, dim, ships):
		"""Sets up the game information for the game
		dim-int- how wide a the board is
		ships-int array- how many and what style of boats are in the game"""

		self.boardSize = dim
		self.board = Board(dim)
		self.boatArray = deepcopy(ships)
		self.boatHealth = [None] * len(self.boatArray)
		self.liveBoats = len(ships) - 1


	def quit_game(self):
		"""Reset game information after player has quit"""
		self.status = None
		self.board = None
		self.gameId = None
		self.boatHealth = None
		self.boardSize = None

	# Getters and setters
	def set_name(self, name):
		self.name = name

	def set_status(self, status):
		self.status = status

	def set_game_id(self, gameId):
		self.gameId = gameId

	def get_name(self):
		return self.name

	def get_game_id(self):
		return self.gameId

	def get_port(self):
		return self.id

	def get_boat_id(self, loc):
		return self.board.check_space(*loc)%10

	def get_status(self):
		return self.status



# Board
class Board:
	"""The actual plot that records boat positions, shots, and outcomes"""

	def __init__(self, dim):
		self.plot = [[0] * dim for i in range(dim)]

	def place_boat(self, id, locs):
		for i in range(int(len(locs)/2)):
			x = locs[i * 2]
			y = locs[i * 2 + 1]
			self.plot[x][y] = id

	def check_space(self, x, y):
		return self.plot[x][y]

	def register_hit(self, x, y):
		loc = self.plot[x][y]
		if loc < 10:
			self.plot[x][y] += 10

	def register_data(self, x, y, result):
		self.plot[x][y] = result


class Client(Transmitter, EventDispatcher):
	"""A client side data-structure to store game, socket, and user information"""

	def __init__(self, socket, port):
		Transmitter.__init__(self, socket)

		self.socket = socket
		self.port = str(port)

		self.status = None

		self.myBoard = None

		self.player_count = 0
		self.player_goal = 0

		self.gameId = None
		self.boardSize = None
		self.coordLen = None
		self.shipFormat = []
		self.turn = None

		self.opponents = {}

	def send_msg(self, msg):
		self.socket.send(msg.encode())
		print("OUT: {}".format(msg))


	def send_join_msg(self, opps):
		msg = "JOIN"
		player_count = self.str_with_buffer(int(opps) +1, 1, 0)

		outMsg = msg + player_count

		self.send_msg(outMsg)


	def send_setb_msg(self, boatId, coords):
		msg = "SETB"
		gameId = self.str_with_buffer(self.gameId, 3, 0)
		boatId = self.str_with_buffer(boatId, 1, 0)
		coords = self.str_with_buffer(''.join(map(str, coords)), len(coords), 0)

		outMsg = msg + gameId + boatId + coords

		self.send_msg(outMsg)


	def send_shot_msg(self, target, x, y):
		msg = "SHOT"
		gameId = self.str_with_buffer(self.gameId, 3, 0)
		tar_port = self.str_with_buffer(target, 5, 0)
		x_coord = self.str_with_buffer(x, 1, 0)
		y_coord = self.str_with_buffer(y, 1, 0)

		outMsg = msg + gameId + tar_port + x_coord + y_coord

		self.send_msg(outMsg)

	def set_boat(self, boatId, coords):
		locs = []
		for i in coords:
			for x in i:
				locs.append(int(x))

		self.myBoard.place_boat(boatId, locs)

		self.send_setb_msg(boatId, coords)

	def take_shot(self, target, x, y):

		self.send_shot_msg(target, x, y)


	def get_port(self):
		return self.port

	def get_game_id(self):
		return self.gameId

	def get_opponents(self):
		return self.opponents

	def parse_game_msg(self):
		self.gameId = self.recv_str(3)

	def parse_wait_msg(self):
		self.player_count = self.recv_int(1)
		self.player_goal = self.recv_int(1)

		print("Game #{} currently has {} of {} players".format(self.gameId, self.player_count, self.player_goal))
		print("Please continue waiting")
		return(self.player_count, self.player_goal)

	def parse_play_msg(self):
		self.boardSize = self.recv_int(2)

		self.myBoard = Board(self.boardSize)

		opps = self.recv_int(1)

		for i in range(opps):
			oppPort = self.recv_str(LEN_PORT)
			oppName = self.recv_str(LEN_NAME)
			opp = Opponent(oppPort, oppName, self.boardSize)
			self.opponents[oppPort] = opp

	def parse_sail_msg(self):
		self.coordLen = self.recv_int(1)
		boats = self.recv_int(1)

		self.shipFormat = [0]

		for i in range(boats):
			self.shipFormat.append(self.recv_int(1))

		print("SAIL")
		print("Game#: {}\nBoat Count: {}\nBoat Format: {}".format(self.gameId, boats, self.shipFormat))

		return self.shipFormat


	def parse_shot_msg(self):
		shooter = self.recv_str(LEN_PORT)
		target = self.recv_str(LEN_PORT)

		loc = [0,0]

		loc[0] = self.recv_int(self.coordLen)
		loc[1] = self.recv_int(self.coordLen)

		result = self.recv_int(1)

		if result == 2:
			boatId = self.recv_int(1)

			result = result*10 + boatId

		print("Models, parse_shot_msg--target: {}, self.port: {}".format(type(target), type(self.port)))
		if target != self.port:
			self.opponents[target].register_data(*loc, result)

		return (shooter, target, loc, result)


	# TODO: CHECK THIS THOROUGHLY
	def takeTurn(self, shooter, target, x, y):

		# Check if it's the player's turn
		if (shooter != self.players[self.turn].name):
			return False

		# Process shot
		result = self.players[self.turn].board.shootLocation(x, y)

		if result == 3:
			# if a player loses, decrement active players and change result if the game is won
			self.activePlayers -=1

			if self.activePlayers == 1:
				result = 4


		# Update non-afffected players' boards
		for p in self.players():
			if p != self.players[self.turn]:
				self.sendBoardUpdate(p, self.players[self.turn].name, self.players[self.turn].board)

			# Announce result to each player
			p.announce(shooter, target, result)

		# Advance Turn
		self.turn = (self.turn + 1)%len(self.players)

		# return success
		return True

	def announcement_msg(shooter, target, result):
		if self.name == shooter:
			shooter = "You"
			if result == 0:
				return "{0} missed {1}'s board".format(shooter, target)

			elif result == 1:
				return "{0} hit one of {1}'s boats".format(shooter, target)

			elif result == 2:
				return "{0} sank {1}'s {2}".format(shooter, target, boat)

			elif result == 3:
				return "{0} eliminated {1}".format(shooter, target)

			elif result == 4:
				return "{0} eliminated {1} and won the game".format(shooter, target)


		elif self.name == target:
			if result == 0:
				return "{0} missed your board".format(shooter)

			elif result == 1:
				return "{0} hit one of your boats".format(shooter)

			elif result == 2:
				return "{0} sank your {1}".format(shooter, boat)

			elif result == 3:
				return "{0} eliminated you".format(shooter)

			elif result == 4:
				return "{0} eliminated you and won the game".format(shooter)


		else:
			if result == 0:
				return "{0} missed {1}'s board".format(shooter, target)

			elif result == 1:
				return "{0} hit one of {1}'s boats".format(shooter, target)

			elif result == 2:
				return "{0} sank {1}'s {2}".format(shooter, target, boat)

			elif result == 3:
				return "{0} eliminated {1}".format(shooter, target)

			elif result == 4:
				return "{0} eliminated {1} and won the game".format(shooter, target)


class Opponent:
	"""Client-side data structure to organize information about their opponents"""

	def __init__(self, port, name, boardSize):
		self.port = port
		self.name = name
		self.board = Board(boardSize)

		# Fix this so that
		self.liveBoats = [False, True, True, True, True, True]

	def register_data(self, x, y, result):
		self.board.register_data(x, y, result)

		if result > 10:
			self.liveBoats[result%10] = False
			print("{}'s boats: {}".format(self.name, self.liveBoats))


