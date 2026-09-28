extends Node
## Boots the real main menu with a persistent test driver attached to the root.
## Usage (see tests/run_all.sh):
##   godot res://tests/ui_flow.tscn -- --phase=1 --starter=kael_emberclaw
func _ready() -> void:
	var driver := Node.new()
	driver.set_script(load("res://tests/ui_flow_runner.gd"))
	get_tree().root.add_child.call_deferred(driver)
	get_tree().change_scene_to_file.call_deferred("res://scenes/ui/main_menu.tscn")
