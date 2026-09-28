class_name PanelFrame
extends PanelContainer
## Layered panel: outer metal frame -> inner stone panel -> content.
## Variants: panel (default), inset, plank, boss, enemy, slot,
##           card_fire / card_water / card_nature / card_neutral (+ "_lit"),
##           rarity_3 / rarity_4 / rarity_5 / rarity_6

const MARGINS := {
	"panel": [30, 30], "inset": [15, 20], "plank": [15, 16], "boss": [30, 26], "enemy": [18, 18], "slot": [12, 10],
}

var variant := "panel"


static func make(v := "panel", pad := -1) -> PanelFrame:
	var p := PanelFrame.new()
	p.set_variant(v, pad)
	return p


func set_variant(v: String, pad := -1) -> void:
	variant = v
	var file := "v2_%s.png" % v
	var tex_margin := 12
	var content := 18
	if MARGINS.has(v):
		tex_margin = MARGINS[v][0]
		content = MARGINS[v][1]
	elif v.begins_with("card"):
		tex_margin = 21
		content = 18
	elif v.begins_with("rarity"):
		tex_margin = 21
		content = 12
	if pad >= 0:
		content = pad
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/" + file)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		sb.set_texture_margin(side, tex_margin)
		sb.set_content_margin(side, content)
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE_FIT
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE_FIT
	add_theme_stylebox_override("panel", sb)
