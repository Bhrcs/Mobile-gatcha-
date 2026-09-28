shader_type canvas_item;
// Hit flash + tint for battle units. flash_amount 1 = solid flash_color silhouette.
// The node's modulate still applies (KO greying, fades).
uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;
uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	vec3 base = c.rgb * tint.rgb * COLOR.rgb;
	c.rgb = mix(base, flash_color.rgb, flash_amount);
	COLOR = vec4(c.rgb, c.a * COLOR.a);
}
