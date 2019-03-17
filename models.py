from random import uniform, shuffle # used by Game
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

	def __init__(self, socket):
		self.socket = socket

	def send_msg(self, msg):
		self.socket.send(msg.encode())

	def str_with_buffer(self, content, length, fill):
		return "{:{fill}>{length}}".format(content, fill=fill, length=length)

	def recv_int(self, byteLen):
		return int(self.socket.recv(byteLen).decode())

	def recv_str(self, byteLen):
		return self.socket.recv(byteLen).decode().lstrip(' ')


class GameManager:
	""" docstring """

	def __init__(self):
		self.gameCounter = 0
		self.minPlayers = 2
		self.maxPlayers = 5

		self.waitingGames = [None] * (self.maxPlayers - self.minPlayers)
		self.gameDict = {}

	def join_open_game(self, desPlayers, player):
		""" returns  """

		game = None

		if self.waitingGames[desPlayers - self.minPlayers] == None:
			game = self.create_new_game(desPlayers)

		else:
			game = self.waitingGames[desPlayers - self.minPlayers]

		game.add_player(player)

		# Does game has number of desired players?
		if len(game.players) == game.numPlayers:
			self.waitingGames[desPlayers - self.minPlayers] = None
			game.start_game()

		# Else, update waiting details
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


		# Create new gameId and increment for next use (gamecounter must remain a )
		newId = self.gameCounter
		self.gameCounter == (self.gameCounter + 1) % 1000

		# Create new game
		game = Game(newId, numPlayers)

		# Add game to dictionary and array for lookup and origanization
		self.gameDict[newId] = game
		self.waitingGames[numPlayers - self.maxPlayers] = game

		return game

	def get_game(self, gameId):
		return self.gameDict.get(gameId)


# Game
class Game:
	"""id - integer - the unique id number for the game, registered in game manager's dictionary
	numPlayers -  integer - total number of players at the game's start
	boardSize - integer - number of spaces in both the x and y directions
	 """

	def __init__(self, id, numPlayers, boardSize=8):
		# Create new game

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

		self.turn = 0
		self.turnList = None


	def add_player(self, player):
		self.players[player.get_port()] = player
		player.set_game_id(self.id)
		player.send_game_notification()


	def player_quit(self, port):
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

	def get_boat_length(self, id):
		return self.boatLengths[int(id)]


	def start_game(self):
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
		#TODO: Check turn first

		target = self.players[targetId]
		boatId = None
		outcome = target.recieve_shot(loc)

		if outcome == 2:
			boatId = target.get_boat_id(loc)

		elif outcome == 3:
			self.numPlayers -= 1
			if self.numPlayers == 1:
				outcome = 4

		for i in self.players:
			cur_player = self.players[i]
			cur_player.send_shot_msg(shooterId, targetId, loc, outcome, boatId)

	def remove_player(self):
		# Define from player_quit then add to process shot
		pass

	def advance_turn(self):
		while True:
			self.turn = (self.turn + 1) % self.origPlayers
			player = self.turnArray[self.turn]
			if player.get_status() != "eliminated":
				break

		player.send_turn_notification()


class Player(Transmitter):

	def __init__(self, socket, port):

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

	def set_name(self, name):
		self.name = name

	def set_status(self, status):
		self.status = status

	def set_up_game(self, dim, ships):
		self.boardSize = dim
		self.board = Board(dim)
		self.boatArray = deepcopy(ships)
		self.boatHealth = [None] * len(self.boatArray)
		self.liveBoats = len(ships) - 1

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
		print("Recieve Shot: {}, port: {}".format(loc, self.id))
		print(self.liveBoats)
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
		# FORMAT
		# msg - 4, game - 3
		# boardSize - 2, #ofOpps - 1
		# port - 5 and name - 20 of each opponent

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
		# Send SAIL message to each player
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
		msg = "LOSE"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId
		self.send_msg(outMsg)

	def send_game_notification(self):
		msg = "GAME"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId
		self.send_msg(outMsg)

	def send_turn_notification(self):
		msg = "URMV"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		outMsg = msg + gameId

		self.send_msg(outMsg)

	def send_waiting_message(self, curPlayerCount, tarPlayerCount):
		msg = "WAIT"
		gameId = self.str_with_buffer(self.gameId, LEN_GAME, 0)
		cur = self.str_with_buffer(curPlayerCount, 1, 0)
		tar = self.str_with_buffer(tarPlayerCount, 1, 0)

		outMsg = msg + gameId + cur + tar

		self.send_msg(outMsg)

	def send_quit_notification(self, port):
		msg = "LEFT"
		gameId = self.str_with_buffer(self.gameId, 3, 0)

		quitPort = self.str_with_buffer(port, 5, 0)

		outMsg = msg + gameId + quitPort

		self.send_msg(outMsg)

	def send_victory_notification(self):
		msg = "WIN!"
		gameId = self.str_with_buffer(self.gameId, 3,0)

		outMsg = msg + gameId

		self.send_msg(outMsg)


	def quit_game(self):
		self.status = None
		self.board = None
		self.gameId = None
		self.boatHealth = None
		self.boardSize = None




# Board
class Board:
	"""docstring"""

	def __init__(self, dim):
		self.plot = [[0] * dim for i in range(dim)]

	def place_boat(self, id, locs):
		for i in range(int(len(locs)/2)):
			x = locs[i * 2] - 1
			y = locs[i * 2 + 1] - 1
			self.plot[x][y] = id

	def check_space(self, x, y):
		return self.plot[x - 1][y - 1]

	def register_hit(self, x, y):
		loc = self.plot[x - 1][y - 1]
		if loc < 10:
			self.plot[x - 1][y - 1] += 10

class Client(Transmitter):

	def __init__(self, socket, port):
		Transmitter.__init__(self, socket)

		self.socket = socket
		self.port = port

		self.myBoard = None

		self.gameId = None
		self.boardSize = None
		self.coordLen = None
		self.shipFormat = []
		self.turn = None

		self.opponents = {}

	def send_msg(self, socket, msg):
		socket.send(msg.encode())

	def get_port(self):
		return self.port

	def get_game_id(self):
		return self.gameId

	def parse_game_msg(self):
		self.gameId = self.recv_str(3)

	def parse_wait_msg(self):
		count = self.recv_int(1)
		target = self.recv_int(1)

		print("Game #{} currently has {} of {} players".format(self.gameId, count, target))
		print("Please continue waiting")

	def parse_play_msg(self):
		self.boardSize = self.recv_int(2)

		opps = self.recv_int(1)

		print("Board Size: {}\n# Opponents: {}\n".format(self.boardSize, opps))


		for i in range(opps):
			oppPort = self.recv_str(LEN_PORT)
			oppName = self.recv_str(LEN_NAME)
			opp = Opponent(oppPort, oppName, self.boardSize)
			self.opponents[oppPort] = opp

			print("~~~Opponent #{}~~~\nPort: {}\nName: {}\n".format(i, oppPort, oppName))


	def parse_sail_msg(self):
		self.coordLen = self.recv_int(1)
		boats = self.recv_int(1)

		self.shipFormat = [0]

		for i in range(boats):
			self.shipFormat.append(self.recv_int(1))

		print("SAIL")
		print("Game#: {}\nBoat Count: {}\nBoat Format: {}".format(self.gameId, boats, self.shipFormat))


	# CHECK THIS THOROUGHLY
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

	def __init__(self, port, name, boardSize):
		self.port = port
		self.name = name
		self.board = Board(boardSize)


