import socket, os, random, pickle, vlc, threading, time, yaml


with open("client_conf.yml", "r") as f:
	config_data = yaml.safe_load(f)

location = ""
accepted_exts = config_data['accepted_extentions']
play_order = [0, 1]
play_files = ["None", "None"]
play_location = ""
index = 0
listPlayer = ""
media_play_command = 0
retries = 3

player_running = False
start_playing = False

CC = config_data['CC']
Fullscreen = config_data['fullscreen']


def save_data(l1,l2,l3,l4,b1,b2):
	with open("data_state.txt", 'wb') as tmp:
		pickle.dump([l1,l2,l3,l4,b1,b2],tmp)
	print("Data Saved")


def load_data():
	global play_order
	global play_files
	global play_location
	global index
	global listPlayer
	global start_playing
	global Fullscreen
	global CC

	with open("data_state.txt", 'rb') as data:
		tmp = pickle.load(data)
		play_order = tmp[0]
		play_files = tmp[1]
		play_location = tmp[2]
		index = tmp[3]
		if tmp[4] == 'True':
			Fullscreen = True
		if tmp[4] == 'False':
			Fullscreen = False
		if tmp[5] == 'True':
			CC = True
		if tmp[5] == 'False':
			CC = False
		CC = (tmp[5])
	start_playing = True



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((config_data['server_ip'],config_data['port']))
if os.path.exists("data_state.txt"):
	load_data()
msg = s.recv(1024)
print(msg)
send_msg = pickle.dumps([play_files[play_order[index]],play_files[play_order[index+1]]])
s.sendall(send_msg)
print("Done")

print(repr(Fullscreen))
media_player = vlc.MediaPlayer()
media_player.set_fullscreen(Fullscreen)

def play_handler():
	global media_player
	global index
	global play_location
	global play_files
	global play_order
	for attempt in range(0, retries):
		try:
			media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
			media_player.set_media(media)
			if CC == 'False':
				media_player.video_set_spu(0)
			if Fullscreen == 'True':
				media_player.set_fullscreen(True)
			else:
				media_player.set_fullscreen(False)
			media_player.play()
		except:
			print("Couldn't Play")
			index += 1
			pass



while True:
	if start_playing:
		if not media_player.is_playing():
			if player_running:
				index +=1
			else:
				player_running = True
			if index >= len(play_files):
				index = 0
			print(media_player.is_playing())
			media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
			print(os.path.join(play_location,play_files[play_order[index]]))
			media_player.set_media(media)
			if CC == False:
				media_player.video_set_spu(0)
			media_player.set_fullscreen(Fullscreen)
			media_player.play()
			start_playing = False
	
	print(start_playing, player_running)
	incomming_data = pickle.loads(s.recv(1024))
	msg = incomming_data[0]
	if msg != b'':
		print(repr(msg))
		if msg == '>':
			tmp_data = []
			if player_running:
				media_player.stop()
				index +=1
				if index >= len(play_files):
					index = 0
				play_handler()
				tmp_data = [play_files[play_order[index]],play_files[play_order[index+1]]]
			else:
				tmp_data = ["None", "None"]

			send_msg = pickle.dumps(tmp_data)
			s.sendall(send_msg)
			save_data(play_order, play_files, play_location, index, Fullscreen, CC)
		

		elif msg == '<':
			tmp_data = []
			if player_running:
				media_player.stop()
				if index > 0:
					index -= 1
				play_handler()
				tmp_data = [play_files[play_order[index]],play_files[play_order[index+1]]]
			else:
				tmp_data = ["None", "None"]
			send_msg = pickle.dumps(tmp_data)
			s.sendall(send_msg)
			save_data(play_order, play_files, play_location, index, Fullscreen, CC)

		elif msg == '?':
			send_msg = pickle.dumps([play_files[play_order[index]],play_files[play_order[index+1]]])
			s.sendall(send_msg)
			save_data(play_order, play_files, play_location, index, Fullscreen, CC)

		elif os.path.exists(msg):
			files = []
			files = os.listdir(msg)
			large_files = 0
			send_msg = []
			holder = play_files
			play_files.clear()
			for f in files:
				names = os.path.splitext(msg +"\\"+f) 
				if names[1].lower() in accepted_exts:
					play_files.append(f)
					large_files += 1
			if large_files > 0:
				play_order = random.sample(range(large_files), large_files)
				print(f"Location Found! Total files and Total Large Files: {len(files)} {large_files}")
				print(play_order, play_files)
				send_msg = pickle.dumps([play_files[play_order[index]],play_files[play_order[index+1]]])
				Fullscreen = incomming_data[1]
				CC = incomming_data[2]

				play_location = msg
				if player_running:
					media_player.stop()
					index = 0
					play_handler()
				else:
					start_playing = True
				
			else:
				print("Error No Files")
				send_msg = pickle.dumps(["None", "None"])
				play_files = holder

			s.sendall(send_msg)



	#except:
	#	pass