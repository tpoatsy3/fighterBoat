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
	boat_id = NumericProperty(0)
	boat_len = NumericProperty(0)
	placed = BooleanProperty(False)

	def __init__(self, **kwargs):
		super(Button, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.get_placement_screen, 0)

	def get_placement_screen(self, *args):
		self.placement_scr = self.fboatApp.root.ids.placement_scr

	def register_click(self, *args):
		self.placement_scr.boat_span = self.boat_len
		self.placement_scr.boat_id = self.boat_id


class FbBoard(BoxLayout):
	spaces = []

	def __init__(self, **kwargs):
		super(FbBoard, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		self.spaces = [[None] * 8 for i in range(8)]		# 	self.spaces.append([None] * 8)
		Clock.schedule_once(self.create_refs, 0)

	def create_refs(self, *args):
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
	boat_span = NumericProperty(0)
	hor = BooleanProperty(True)
	placement_scr = ObjectProperty(None)
	available = BooleanProperty(True)
	status = NumericProperty(0)

	client = ObjectProperty(None)


	def __init__(self, **kwargs):
		super(FbBoardSpace, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.get_connection, 0)


	def get_connection(self, *args):
		self.placement_scr = self.fboatApp.root.ids.placement_scr
		self.play_scr = self.fboatApp.root.ids.play_scr
		self.client = self.play_scr.client


	def on_mouse_pos_play(self, *args):
		pos = args[1]
		(x, y) = pos

		if self.status == 0:
			self.background_color = [.7,.7,.7,1]
		elif self.status == 1:
			self.background_color = [1,1,1,1]
		elif self.status == 2:
			self.background_color = self.fboatApp.color_accent_1 + [1]
		elif self.status == 3:
			self.background_color = self.fboatApp.color_dark_gray + [1]


	def on_mouse_pos_placement(self, *args):
		pos = args[1]
		(x, y) = pos

		if self.available:
			self.unhover_color()

			for i in range(self.boat_span):
				if self.hor:
					x = pos[0] + (i * self.width) + ((i-1) * 2)
				else:
					y = pos[1] - (i * self.height) - ((i-1) * 2)

				if self.collide_point(*self.to_widget(x, y)):
					self.hover_color()


	def shoot(self, *args):
		tar_name = self.play_scr.ids['panel_frame'].current_tab.text
		if tar_name == "You":
			return False

		tar_port = self.play_scr.opps_port[tar_name]


		print("NAME: {}, PORT: {}, LOC: {}".format(tar_name, tar_port, self.text))

		self.client.take_shot(tar_port, self.text[0], self.text[1])


	def do_nothing(self, *args):
		pass


	def place(self, *args):

		if self.placement_scr.boat_span == 0:
			return False

		coords = [0] * (self.boat_span)
		base = int(self.text)


		if self.hor:
			if int(self.text[0]) + self.boat_span > 8:
				return False

			for i in range(len(coords)):
				coords[i] = "{:0>2}".format(base + (i*10))
				tag = "space" + coords[i]
				if self.placement_scr.ids.board.ids[tag].available == False:
					return False


			for i in coords:
				tag = "space" + i
				self.placement_scr.ids.board.ids[tag].background_color = (0,0,1,1)
				self.placement_scr.ids.board.ids[tag].available = False

		elif not self.hor:
			if int(self.text[1]) + self.boat_span > 8:
				return False

			for i in range(len(coords)):
				coords[i] = "{:0>2}".format(base + (i*1))
				tag = "space" + coords[i]
				if self.placement_scr.ids.board.ids[tag].available == False:
					return False

			for i in coords:
				tag = "space" + i
				self.placement_scr.ids.board.ids[tag].background_color = (0,0,1,1)
				self.placement_scr.ids.board.ids[tag].available = False

		boat_id = self.placement_scr.boat_id

		self.placement_scr.boatButtons[boat_id - 1].placed = True
		self.placement_scr.boatButtons[boat_id - 1].disabled = True

		self.placement_scr.boat_span = 0

		self.fboatApp.client.set_boat(boat_id, coords)


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
	boat_span = NumericProperty(0)
	hor = BooleanProperty(True)
	boatButtons = ListProperty()
	boat_id = NumericProperty(0)

	def __init__(self, **kwargs):
		super(PlacementScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		Clock.schedule_once(self.set_up_board, 0)

	def set_up_board(self, *args):
		for key, val in self.ids["board"].ids.items():
			val.bind(on_press=val.place)
			Window.bind(mouse_pos = val.on_mouse_pos_placement)

	def on_boat_span(self, *args):
		for i in self.ids['board'].spaces:
			for j in i:
				j.boat_span = self.boat_span

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
	wait_text = ObjectProperty(None)
	wait_player = NumericProperty(0)
	# client = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(JoinScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		# self.client = self.fboatApp.client

	def send_join_msg(self, opps):
		self.fboatApp.client.send_join_msg(opps)
		for b in self.join_buttons:
			b.disabled = True
		self.wait_text.color = self.fboatApp.color_dark_gray + [1]
		# self.fboatApp.client.bind(player_count = self.on_wait_player)

	def set_wait_text(self, have, want):
		self.wait_text.text = "Your game currently has {0} of {1} players. Please wait...".format(have, want)

	def set_play_text(self):
		self.wait_text.text = "Found all players, setting up game"

	def on_wait_player(self):
		self.wait_text(self.fboatApp.client.player_count, self.fboatApp.client.player_goal)



class PlayScreen(Screen):
	manager = ObjectProperty(None)
	client = ObjectProperty(None)
	port = StringProperty("")

	# Key: Opp Port; Value: Opponent Object
	opps = None

	# Key: Opp Name; Value: Opp Port
	opps_port = {}

	def __init__(self, **kwargs):
		super(PlayScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def start_up(self, *args):
		self.client = self.fboatApp.client
		self.port = self.client.get_port()
		self.opps = self.client.get_opponents()
		self.panelFrame = self.ids["panel_frame"]
		self.panelFrame.tab_width = self.width/(len(self.opps) + 1)
		self.ids['tab_0'].ids['name_plate'].text = "Your board"

		for key, value in self.opps.items():
			tab = PlayTab()
			tab.text = value.name
			tab.id = "tab" + key
			self.panelFrame.add_widget(tab)
			self.opps_port[value.name] = key
			tab.ids['name_plate'].text = "{}'s board".format(value.name)

		for tab in self.panelFrame.tab_list:
			for spot_id, spot in tab.ids['board'].ids.items():
				if spot_id[:5] == "space":
					spot.bind(on_press=spot.shoot)
					Window.bind(mouse_pos = spot.on_mouse_pos_play)

	def register_shot(self,shooter, target, x, y, result, *args):
		ind = 0
		print(target, self.port)
		if target != self.port:
			tar_name = self.opps[target].name
			ind = list(map(lambda x: x.text, self.panelFrame.tab_list)).index(tar_name)
			self.panelFrame.tab_list[ind].ids['board'].register_shot(x, y, result)
		else:
			self.ids['tab_0'].ids['board'].register_shot(x, y, result)

		# announce game event







class PlayTab(TabbedPanelItem):

	def __init__(self, **kwargs):
		super(PlayTab, self).__init__(**kwargs)





class Manager(ScreenManager):
	play_scr = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(Manager, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def to_conn_scr(self, *args):
		self.current = "connect_scr"

	def to_join_scr(self, *args):
		self.current = "join_scr"

	def to_placement_scr(self, *args):
		self.current = "placement_scr"

	def to_play_scr(self, *args):
		self.play_scr.start_up()
		self.current = "play_scr"



class FboatApp(App):

	# Colors for Kivy Lang File
	color_main = ListProperty([0.13671875, 0.53515625, 0.93359375])
	color_accent_1 = ListProperty([1.0, 0.8313725490196079, 0.28627450980392155])
	color_accent_2 = ListProperty([1.0, 0.6745098039215687, 0.5176470588235295])
	color_white = ListProperty([1, 1, 1])
	color_dark_gray = ListProperty([0.3254901960784314, 0.41568627450980394, 0.5098039215686274])
	color_light_gray = ListProperty([0.87109375, 0.90625, 0.921875])
	color_black = ListProperty([0, 0, 0])

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
			self.root.ids.join_scr.set_wait_text(have, want)

		elif msg == "PLAY":
			self.root.ids.join_scr.set_play_text()
			client.parse_play_msg()

		elif msg == "SAIL":
			boat_arr = client.parse_sail_msg()
			for i in range(1, len(boat_arr)):
				length = boat_arr[i]
				self.root.ids.placement_scr.boatButtons[i-1].boat_len = int(length)
				self.root.ids.placement_scr.boatButtons[i-1].text = "Place {} Boat".format(length)
				self.root.ids.placement_scr.boatButtons[i-1].boat_id = i

			self.root.to_placement_scr()

		elif msg == "SHOT":
			shooter, target, loc, result = client.parse_shot_msg()
			self.root.ids.play_scr.register_shot(shooter, target, *loc, result)



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
