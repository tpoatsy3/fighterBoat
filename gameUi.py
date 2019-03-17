
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint


class PongBall(Widget):

    # velocity of the ball on x and y axis
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)

    # referencelist property so we can use ball.velocity as
    # a shorthand, just like e.g. w.pos for w.x and w.y
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    # ``move`` function will move the ball one step. This
    #  will be called in equal intervals to animate the ball
    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class PongGame(Widget):
	ball = ObjectProperty(None)

	def serve_ball(self):
		self.ball.center = self.center
		self.ball.velocity = Vector(4, 0).rotate(randint(0, 360))

	def update(self, dt):
		self.ball.move()


		if (self.ball.y < 0) or (self.ball.top > self.height):
			self.ball.velocity_y *= -1

		if (self.ball.x < 0) or (self.ball.right > self.width):
			self.ball.velocity_x *= -1

class PongApp(App):
	def build(self):
		game = PongGame()
		game.serve_ball()
		Clock.schedule_interval(game.update, 1.0/60.0)
		return game













if __name__ == '__main__':
	PongApp().run()











# import tkinter as tk
# from tk_models import *


# ###### COLORS ######
# MAIN = "#2389EF"
# ACCENT_1 = "#FFD449"
# ACCENT_2 = "#FFAC84"
# WHITE = "#FFFFFF"
# DARK_GRAY = "#536A82"
# LIGHT_GRAY = "#DFE8EC"
# BLACK = "#000000"

# def change_pages(appear, disappear):
# 	disappear.pack_forget()
# 	appear.pack()

# def clicked():
# 	val = txt.get()
# 	lbl.config(text=val)


# root = tk.Tk()
# root.config(bg=BLACK)
# root.title("Fighter Boat!")


# ##### ELEMENTS #####

# joinScreen = tk.Frame(root, bg=BLACK).pack()
# header = tk.Frame(joinScreen, bg=ACCENT_2, height=180, width=1080)
# lbl = tk.Label(header, text="FIGHTERBOAT!", font=("Rockwell", 50), fg=MAIN, bg=LIGHT_GRAY)

# body = tk.Frame(joinScreen, bg=ACCENT_1, height=440, width=1080)

# footer_left = tk.Frame(joinScreen, bg=MAIN, height=100, width=540)
# footer_right = tk.Frame(joinScreen, bg=LIGHT_GRAY, height=100, width=540)


# # CREATE RADIO BUTTONS
# OPPONENT_OPTIONS = [("Play with 2", 2),
# 					("Play with 3", 3),
# 					("Play with 4", 4),
# 					("Play with 5", 5)]

# opps = tk.IntVar()
# opps.set(2)
# opp_select = ButtonList(body, OPPONENT_OPTIONS, opps)

# ##### Placement #####
# header.pack(side=tk.TOP, fill=tk.BOTH)
# lbl.pack(side=tk.TOP, fill=tk.X)

# body.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=50)
# opp_select.pack(side=tk.TOP, fill=tk.X)

# footer_left.pack(side=tk.LEFT, fill=tk.BOTH)
# footer_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=0)
# ##### END COMMENTS #####



# # txt = tk.Entry(body, width=10)
# # txt.grid(column=0, row=1)

# # btn = tk.Button(body, text="Click Me!", command=clicked)
# # btn.grid(column=1, row=1)

# root.geometry("1080x720")

# # txt.focus()


# root.mainloop()

