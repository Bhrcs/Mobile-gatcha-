extends Node
## Visual smoke test: plays Stage 1 automatically and saves screenshots.
## xvfb-run godot --resolution 1920x1080 res://tests/shot_driver.tscn

var out_dir := "user://shots/"


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	var driver := Node.new()
	driver.set_script(load("res://tests/shot_driver_runner.gd"))
	get_tree().root.add_child.call_deferred(driver)
