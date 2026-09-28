extends Node
## AudioManager (autoload)
## Plays music with cross-fades and pooled sound effects on dedicated buses.
## Sounds are looked up by name so audio files are trivial to replace:
##   assets/audio/sfx/<name>.wav   assets/audio/music/<name>.ogg

const SFX_DIR := "res://assets/audio/sfx/"
const MUSIC_DIR := "res://assets/audio/music/"
const SFX_POOL_SIZE := 10

var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _active_music: AudioStreamPlayer
var _current_music := ""
var _sfx_pool: Array[AudioStreamPlayer] = []
var _sfx_index := 0
var _cache: Dictionary = {}
var _last_play_time: Dictionary = {}   # throttles identical sfx fired in the same frame


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_bus("Music")
	_ensure_bus("SFX")
	_music_a = _make_player("Music")
	_music_b = _make_player("Music")
	_active_music = _music_a
	for i in SFX_POOL_SIZE:
		_sfx_pool.append(_make_player("SFX"))


func _ensure_bus(bus_name: String) -> void:
	if AudioServer.get_bus_index(bus_name) == -1:
		AudioServer.add_bus()
		var idx := AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, bus_name)
		AudioServer.set_bus_send(idx, "Master")


func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func set_volumes(master: float, music: float, sfx: float) -> void:
	_set_bus_volume("Master", master)
	_set_bus_volume("Music", music)
	_set_bus_volume("SFX", sfx)


func _set_bus_volume(bus_name: String, linear: float) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx >= 0:
		AudioServer.set_bus_volume_db(idx, linear_to_db(max(linear, 0.0001)))
		AudioServer.set_bus_mute(idx, linear <= 0.001)


## Plays a named sound effect. pitch_var adds slight random pitch variation.
func play_sfx(sfx_name: String, pitch_var: float = 0.05, volume_db: float = 0.0) -> void:
	var now := Time.get_ticks_msec()
	if now - int(_last_play_time.get(sfx_name, -1000)) < 30:
		return
	_last_play_time[sfx_name] = now
	var stream := _get_stream(SFX_DIR + sfx_name + ".wav")
	if stream == null:
		return
	var p := _sfx_pool[_sfx_index]
	_sfx_index = (_sfx_index + 1) % _sfx_pool.size()
	p.stream = stream
	p.pitch_scale = 1.0 + randf_range(-pitch_var, pitch_var)
	p.volume_db = volume_db
	p.play()


## Cross-fades to a named music track (looping). Same track = no restart.
func play_music(track: String, fade: float = 0.8) -> void:
	if track == _current_music and _active_music.playing:
		return
	var stream := _get_stream(MUSIC_DIR + track + ".ogg")
	if stream == null:
		return
	_current_music = track
	var old := _active_music
	var new_player := _music_b if _active_music == _music_a else _music_a
	_active_music = new_player
	new_player.stream = stream
	new_player.volume_db = -40.0
	new_player.play()
	var tw := create_tween().set_parallel(true)
	tw.tween_property(new_player, "volume_db", 0.0, fade)
	if old.playing:
		tw.tween_property(old, "volume_db", -40.0, fade)
		tw.chain().tween_callback(old.stop)


## One-shot musical sting (victory/defeat) that ducks the current track.
func play_sting(track: String) -> void:
	stop_music(0.3)
	var stream := _get_stream(MUSIC_DIR + track + ".ogg")
	if stream == null:
		return
	if stream is AudioStreamOggVorbis:
		stream = stream.duplicate()
		stream.loop = false
	var p := _sfx_pool[_sfx_index]
	_sfx_index = (_sfx_index + 1) % _sfx_pool.size()
	p.stream = stream
	p.pitch_scale = 1.0
	p.volume_db = 0.0
	p.play()


func stop_music(fade: float = 0.5) -> void:
	_current_music = ""
	for p in [_music_a, _music_b]:
		if p.playing:
			var tw := create_tween()
			tw.tween_property(p, "volume_db", -40.0, fade)
			tw.tween_callback(p.stop)


func _get_stream(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	var stream: AudioStream = null
	if ResourceLoader.exists(path):
		stream = load(path)
		if stream is AudioStreamOggVorbis and path.begins_with(MUSIC_DIR):
			stream.loop = true
	_cache[path] = stream
	return stream


## Stops every player and drops streams (called before quitting).
func shutdown() -> void:
	for p in [_music_a, _music_b] + _sfx_pool:
		if is_instance_valid(p):
			p.stop()
			p.stream = null
	_current_music = ""


func _exit_tree() -> void:
	# stop playback and drop cached streams so shutdown is clean
	for p in [_music_a, _music_b] + _sfx_pool:
		p.stop()
		p.stream = null
	_cache.clear()
