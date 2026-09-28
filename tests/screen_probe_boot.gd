extends Node
## Boots the screen probe driver on the root so it survives scene changes.
func _ready() -> void:
	var driver := Node.new()
	driver.set_script(load("res://tests/screen_probe.gd"))
	get_tree().root.add_child.call_deferred(driver)
