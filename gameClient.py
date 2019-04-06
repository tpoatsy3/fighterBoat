# Battleship client


import socket
import selectors
import types
import sys
import signal
import fcntl
import os

from functools import partial
from time import sleep
import random

import models

import kivy
kivy.require('1.10.1')
from kivy.app import App
from kivy.core.window import Window
from kivy.properties import NumericProperty, ListProperty, ObjectProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanelItem

DEFAULT_PORT = "2136"

class BoatButton(Button):
	"""Used to select boat to be placed"""

	boatId = NumericProperty(0)
	boatLen = NumericProperty(0)
	placed = BooleanProperty(False)

	def __init__(self, **kwargs):
		super(Button, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.start_up, 0)

	def start_up(self, *args):
		self.placementScr = self.fboatApp.root.ids.placementScr

	def register_click(self, *args):
		""" Change values of boatSpan and boatId on PlacementScreen"""
		self.placementScr.boatSpan = self.boatLen
		self.placementScr.boatId = self.boatId


class FbBoard(BoxLayout):
	""" Board object, appears on both play and placement screens"""

	# 2D List of references to individual squares
	spaces = []

	def __init__(self, **kwargs):
		super(FbBoard, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		self.spaces = [[None] * 8 for i in range(8)]		# 	self.spaces.append([None] * 8)
		Clock.schedule_once(self.start_up, 0)

	def start_up(self, *args):
		for key, val in self.ids.items():
			x = int(key[-2])
			y = int(key[-1])
			self.spaces[x][y] = val

	def register_shot(self, x, y, result):
		color = []
		if result == 0:
			color = 1
		elif result == 1:
			color = 2
		elif result > 20:
			color = 3

		self.spaces[x][y].status = color

		# Handle elimination and victory


class FbBoardSpace(Button):
	boatSpan = NumericProperty(0)
	hor = BooleanProperty(True)
	placementScr = ObjectProperty(None)
	available = BooleanProperty(True)
	status = NumericProperty(0)

	client = ObjectProperty(None)


	def __init__(self, **kwargs):
		super(FbBoardSpace, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.start_up, 0)


	def start_up(self, *args):
		self.placementScr = self.fboatApp.root.ids.placementScr
		self.playScr = self.fboatApp.root.ids.playScr
		self.client = self.playScr.client


	def on_mouse_pos_play(self, *args):
		pos = args[1]
		(x, y) = pos

		if self.status == 0:
			self.background_color = [.7, .7, .7, 1]
		elif self.status == 1:
			self.background_color = [1, 1, 1, 1]
		elif self.status == 2:
			self.background_color = self.fboatApp.colorAccent1 + [1]
		elif self.status == 3:
			self.background_color = self.fboatApp.colorDarkGray + [1]


	def on_mouse_pos_placement(self, *args):
		pos = args[1]
		(x, y) = pos

		if self.available:
			self.unhover_color()

			for i in range(self.boatSpan):
				if self.hor:
					x = pos[0] + (i * self.width) + ((i-1) * 2)
				else:
					y = pos[1] - (i * self.height) - ((i-1) * 2)

				if self.collide_point(*self.to_widget(x, y)):
					self.hover_color()


	def shoot(self, *args):
		targetName = self.playScr.ids['panelFrame'].current_tab.text
		if targetName == "You":
			return False

		targetPort = self.playScr.oppPorts[targetName]


		print("NAME: {}, PORT: {}, LOC: {}".format(targetName, targetPort, self.text))

		self.client.take_shot(targetPort, self.text[0], self.text[1])



	def place(self, *args):

		if self.placementScr.boatSpan == 0:
			return False

		coords = [0] * (self.boatSpan)
		base = int(self.text)


		if self.hor:
			if int(self.text[0]) + self.boatSpan > 8:
				return False

			for i in range(len(coords)):
				coords[i] = "{:0>2}".format(base + (i*10))
				tag = "space" + coords[i]
				if self.placementScr.ids.board.ids[tag].available == False:
					return False


			for i in coords:
				tag = "space" + i
				self.placementScr.ids.board.ids[tag].background_color = (0,0,1,1)
				self.placementScr.ids.board.ids[tag].available = False

		elif not self.hor:
			if int(self.text[1]) + self.boatSpan > 8:
				return False

			for i in range(len(coords)):
				coords[i] = "{:0>2}".format(base + (i*1))
				tag = "space" + coords[i]
				if self.placementScr.ids.board.ids[tag].available == False:
					return False

			for i in coords:
				tag = "space" + i
				self.placementScr.ids.board.ids[tag].background_color = (0,0,1,1)
				self.placementScr.ids.board.ids[tag].available = False

		boatId = self.placementScr.boatId

		self.placementScr.boatButtons[boatId - 1].placed = True
		self.placementScr.boatButtons[boatId - 1].disabled = True

		self.placementScr.boatSpan = 0

		self.fboatApp.client.set_boat(boatId, coords)


	def hover_color(self, *args):
		self.background_color = (1, 0, 0, 1)


	def unhover_color(self, *args):
		self.background_color = (.7, .7, .7, 1)



class ConnectScreen(Screen):
	address = StringProperty("localhost")
	port = StringProperty(DEFAULT_PORT)
	manager = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(ConnectScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def create_connection(self, *args):
		self.fboatApp.client = self.fboatApp.start_connection(self.address, int(self.port))
		self.manager.to_join_scr()
		Clock.schedule_interval(self.fboatApp.service_connection, .5)



class PlacementScreen(Screen):
	manager = ObjectProperty(None)
	boatSpan = NumericProperty(0)
	hor = BooleanProperty(True)
	boatButtons = ListProperty()
	boatId = NumericProperty(0)

	def __init__(self, **kwargs):
		super(PlacementScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.start_up, 0)

	def start_up(self, *args):
		for key, val in self.ids["board"].ids.items():
			val.bind(on_press=val.place)
			Window.bind(mouse_pos = val.on_mouse_pos_placement)

	def on_boatSpan(self, *args):
		for i in self.ids['board'].spaces:
			for j in i:
				j.boatSpan = self.boatSpan

	def on_hor(self, *args):
		for i in range(len(self.ids['board'].spaces)):
			for j in self.ids['board'].spaces[i]:
				j.hor = self.hor

	def go_to_play(self, *args):

		for boat in self.boatButtons:
			if not boat.placed:
				return False

		self.manager.to_play_scr()



class JoinScreen(Screen):
	opps = NumericProperty()
	join_buttons = ListProperty()
	waitText = ObjectProperty(None)
	waitPlayer = NumericProperty(0)

	def __init__(self, **kwargs):
		super(JoinScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def send_join_msg(self, opps):
		self.fboatApp.client.send_join_msg(opps)
		for b in self.join_buttons:
			b.disabled = True
		self.waitText.color = self.fboatApp.colorDarkGray + [1]

	def set_wait_text(self, have, want):
		self.waitText.text = "Your game currently has {0} of {1} players. Please wait...".format(have, want)

	def set_play_text(self):
		self.waitText.text = "Found all players, setting up game"

	def on_waitPlayer(self):
		self.waitText(self.fboatApp.client.playerCount, self.fboatApp.client.playerGoal)



class PlayScreen(Screen):
	manager = ObjectProperty(None)
	client = ObjectProperty(None)
	port = StringProperty("")

	# Key: Opp Port; Value: Opponent Object
	opps = None

	# Key: Opp Name; Value: Opp Port
	oppPorts = {}

	def __init__(self, **kwargs):
		super(PlayScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def start_up(self, *args):
		self.client = self.fboatApp.client
		self.port = self.client.get_port()
		self.opps = self.client.get_opponents()
		self.panelFrame = self.ids["panelFrame"]
		self.panelFrame.tab_width = self.width/(len(self.opps) + 1)
		self.ids['tab_0'].ids['namePlate'].text = "Your board"

		for key, value in self.opps.items():
			tab = PlayTab()
			tab.text = value.name
			tab.id = "tab" + key
			self.panelFrame.add_widget(tab)
			self.oppPorts[value.name] = key
			tab.ids['namePlate'].text = "{}'s board".format(value.name)

		for tab in self.panelFrame.tab_list:
			for spot_id, spot in tab.ids['board'].ids.items():
				if spot_id[:5] == "space":
					spot.bind(on_press=spot.shoot)
					Window.bind(mouse_pos = spot.on_mouse_pos_play)

	def register_shot(self,shooter, target, x, y, result, *args):
		ind = 0
		print(target, self.port)
		if target != self.port:
			targetName = self.opps[target].name
			ind = list(map(lambda x: x.text, self.panelFrame.tab_list)).index(targetName)
			self.panelFrame.tab_list[ind].ids['board'].register_shot(x, y, result)
		else:
			self.ids['tab_0'].ids['board'].register_shot(x, y, result)

		# announce game event







class PlayTab(TabbedPanelItem):

	def __init__(self, **kwargs):
		super(PlayTab, self).__init__(**kwargs)





class Manager(ScreenManager):
	playScr = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(Manager, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def to_conn_scr(self, *args):
		self.current = "connectScr"

	def to_join_scr(self, *args):
		self.current = "joinScr"

	def to_placement_scr(self, *args):
		self.current = "placementScr"

	def to_play_scr(self, *args):
		self.playScr.start_up()
		self.current = "playScr"



class FboatApp(App):

	# Colors for Kivy Lang File
	colorMain = ListProperty([0.13671875, 0.53515625, 0.93359375])
	colorAccent1 = ListProperty([1.0, 0.8313725490196079, 0.28627450980392155])
	colorAccent2 = ListProperty([1.0, 0.6745098039215687, 0.5176470588235295])
	colorWhite = ListProperty([1, 1, 1])
	colorDarkGray = ListProperty([0.3254901960784314, 0.41568627450980394, 0.5098039215686274])
	colorLightGray = ListProperty([0.87109375, 0.90625, 0.921875])
	colorBlack = ListProperty([0, 0, 0])

	client = ObjectProperty(None)


	def __init__(self, **kwargs):
		super(FboatApp, self).__init__(**kwargs)
		self.sel = selectors.DefaultSelector()


	def service_connection(self, *args):
		events = self.sel.select(timeout=0)
		for key, mask in events:
			if mask & selectors.EVENT_READ:
				self.process_server_msg(key)


	def start_connection(self, host, port):

		# Connection to server
		addr = (host, port)
		print('starting connection to', addr)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setblocking(False)
		sock.connect_ex(addr)

		# Create Client datatype
		events = selectors.EVENT_READ | selectors.EVENT_WRITE
		myHost, myPort = sock.getsockname()
		data = models.Client(sock, myPort)

		# Add socket to selectors
		self.sel.register(sock, events, data=data)

		return data


	def process_server_msg(self, key):
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
			have, want = client.parse_wait_msg()
			self.root.ids.joinScr.set_wait_text(have, want)

		elif msg == "PLAY":
			self.root.ids.joinScr.set_play_text()
			client.parse_play_msg()

		elif msg == "SAIL":
			boatArr = client.parse_sail_msg()
			for i in range(1, len(boatArr)):
				length = boatArr[i]
				self.root.ids.placementScr.boatButtons[i-1].boatLen = int(length)
				self.root.ids.placementScr.boatButtons[i-1].text = "Place {} Boat".format(length)
				self.root.ids.placementScr.boatButtons[i-1].boatId = i

			self.root.to_placement_scr()

		elif msg == "SHOT":
			shooter, target, loc, result = client.parse_shot_msg()
			self.root.ids.playScr.register_shot(shooter, target, *loc, result)



	def on_stop(self):
		map = self.sel.get_map()
		keys = list(map.keys())
		for conn in keys:
			socket = self.sel.get_key(conn).fileobj
			socket.close()
			self.sel.unregister(conn)
		self.sel.close()


if __name__ == '__main__':
	FboatApp().run()
