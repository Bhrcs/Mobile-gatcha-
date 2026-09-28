extends Node
## Compiles every script in the project and reports parse errors.
func _ready() -> void:
	var failed := 0
	for path in _walk("res://scripts") + _walk("res://tests"):
		var s = load(path)
		if s == null or (s is GDScript and not s.can_instantiate()):
			print("FAILED: ", path)
			failed += 1
	print("checked, failures: ", failed)
	get_tree().quit(1 if failed else 0)

func _walk(dir: String) -> Array:
	var out: Array = []
	var d := DirAccess.open(dir)
	for f in d.get_files():
		if f.ends_with(".gd"):
			out.append(dir + "/" + f)
	for sub in d.get_directories():
		out += _walk(dir + "/" + sub)
	return out
