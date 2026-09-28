#pragma once
// gd:: — a small Godot-style Control toolkit on top of Axmol, so the Godot UI code
// ports almost line by line.
//
// Coordinates: every Control has a Godot rect — position() is the top-left corner
// relative to the parent Control, y grows DOWN, in design pixels (1080 wide).
// Layout works like Godot: containers (VBox/HBox/Grid/Flow/Center/Margin/Panel/
// Scroll) place their children from minimum sizes and size flags; plain Controls
// place anchored children (set_anchors_preset + offsets) and leave free children
// where they are. Layout runs once per frame when something changed.
//
// Raw Axmol nodes (sprites, particles, DrawNode...) inside a Control: a Control's
// Axmol-space origin is its bottom-left corner. Put raw nodes under a Node2D
// (a zero-size Control) and position them with gd::p2(x, y) (== Vec2(x, -y)),
// i.e. Godot Node2D coordinates. Raw nodes nested in raw nodes also use p2().
#include "axmol.h"
#include "logic/Json.h"
#include "logic/Platform.h"
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace gd
{
using ax::Vec2;

// ------------------------------------------------------------------ colour
struct Col
{
    float r = 1, g = 1, b = 1, a = 1;
    Col() = default;
    Col(float r_, float g_, float b_, float a_ = 1.0f) : r(r_), g(g_), b(b_), a(a_) {}
    Col(const char* hex);   // "#rrggbb" / "#rrggbbaa" / "rrggbb"
    Col(const std::string& hex) : Col(hex.c_str()) {}
    Col darkened(float k) const { return {r * (1 - k), g * (1 - k), b * (1 - k), a}; }
    Col lightened(float k) const { return {r + (1 - r) * k, g + (1 - g) * k, b + (1 - b) * k, a}; }
    Col lerp(const Col& o, float t) const { return {r + (o.r - r) * t, g + (o.g - g) * t, b + (o.b - b) * t, a + (o.a - a) * t}; }
    Col with_alpha(float na) const { return {r, g, b, na}; }
    Col operator*(const Col& o) const { return {r * o.r, g * o.g, b * o.b, a * o.a}; }
    bool operator==(const Col& o) const { return r == o.r && g == o.g && b == o.b && a == o.a; }
    bool operator!=(const Col& o) const { return !(*this == o); }
    ax::Color4B c4b() const;
    ax::Color3B c3b() const;
    ax::Color4F c4f() const { return ax::Color4F(r, g, b, a); }
    static const Col WHITE, BLACK, TRANSPARENT;
};

// ------------------------------------------------------------------ enums (Godot names)
enum SizeFlags { SIZE_SHRINK_BEGIN = 0, SIZE_FILL = 1, SIZE_EXPAND = 2, SIZE_EXPAND_FILL = 3, SIZE_SHRINK_CENTER = 4, SIZE_SHRINK_END = 8 };
enum MouseFilter { MOUSE_STOP, MOUSE_PASS, MOUSE_IGNORE };
enum Preset
{
    PRESET_TOP_LEFT, PRESET_TOP_RIGHT, PRESET_BOTTOM_LEFT, PRESET_BOTTOM_RIGHT, PRESET_CENTER_LEFT, PRESET_CENTER_TOP,
    PRESET_CENTER_RIGHT, PRESET_CENTER_BOTTOM, PRESET_CENTER, PRESET_LEFT_WIDE, PRESET_TOP_WIDE, PRESET_RIGHT_WIDE,
    PRESET_BOTTOM_WIDE, PRESET_VCENTER_WIDE, PRESET_HCENTER_WIDE, PRESET_FULL_RECT
};
enum Side { SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM };
enum Grow { GROW_BEGIN, GROW_END, GROW_BOTH };
enum HAlign { ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT };
enum VAlign { VALIGN_TOP, VALIGN_CENTER, VALIGN_BOTTOM };
enum BoxAlign { ALIGNMENT_BEGIN, ALIGNMENT_CENTER, ALIGNMENT_END };
enum Stretch { STRETCH_SCALE, STRETCH_TILE, STRETCH_KEEP, STRETCH_KEEP_CENTERED, STRETCH_KEEP_ASPECT, STRETCH_KEEP_ASPECT_CENTERED, STRETCH_KEEP_ASPECT_COVERED };

// gd::make<T>() — create + init + autorelease for any Control subclass (Godot T.new()).
template <class T>
T* make()
{
    T* t = new T();
    if (!t->init()) { delete t; return nullptr; }
    t->autorelease();
    return t;
}

inline Vec2 p2(float x, float y) { return Vec2(x, -y); }   // Godot Node2D position -> raw Axmol position
inline Vec2 p2(const Vec2& v) { return Vec2(v.x, -v.y); }

struct Rect2   // Godot Rect2 (top-left origin)
{
    Vec2 position, size;
    Vec2 end() const { return position + size; }
    Vec2 center() const { return position + size / 2; }
    bool has_point(const Vec2& p) const { return p.x >= position.x && p.y >= position.y && p.x < position.x + size.x && p.y < position.y + size.y; }
};

// ------------------------------------------------------------------ input
enum class Ev { PRESS, RELEASE, MOVE, CANCEL, WHEEL };
struct InputEvent
{
    Ev type = Ev::PRESS;
    Vec2 global;          // screen position (top-left origin)
    Vec2 local;           // relative to the receiving control
    float wheel = 0;      // WHEEL: +1 up / -1 down
    bool accepted = false;
    void accept() { accepted = true; }
    bool pressed() const { return type == Ev::PRESS; }
    bool released() const { return type == Ev::RELEASE; }
};

// ------------------------------------------------------------------ Control
class Control : public ax::Node
{
public:
    static Control* create();
    bool init() override;

    // tree ----------------------------------------------------------------
    using ax::Node::addChild;
    void addChild(ax::Node* child, int localZOrder, int tag) override;
    void addChild(ax::Node* child, int localZOrder, std::string_view name) override;
    void removeChild(ax::Node* child, bool cleanup = true) override;
    Control* add(Control* c) { addChild(c); return c; }   // add_child, returns the child
    template <class T> T* add(T* c) { addChild(c); return c; }
    std::vector<Control*> children() const;   // child Controls in tree order
    Control* parent_control() const { return dynamic_cast<Control*>(const_cast<ax::Node*>(getParent())); }
    Control* find(const std::string& name) const;   // find_child(name, recursive)
    void move_child(Control* c, int index);   // 0 = first, -1 = last
    void remove_child(Control* c) { removeChild(c, true); }
    void clear_children();                    // frees every child Control now
    void queue_free();                        // removed at the end of the frame
    bool is_inside_tree() const { return _running; }
    void set_name(const std::string& n) { setName(n); }
    std::string name() const { return std::string(getName()); }

    // geometry ------------------------------------------------------------
    Vec2 position() const { return _pos; }
    Vec2 size() const { return _size; }
    void set_position(const Vec2& p);
    void set_size(const Vec2& s);
    void set_position_x(float x) { set_position(Vec2(x, _pos.y)); }
    void set_position_y(float y) { set_position(Vec2(_pos.x, y)); }
    Vec2 custom_min() const { return _custom_min; }
    void set_custom_min(const Vec2& s);
    void set_min_w(float w) { set_custom_min(Vec2(w, _custom_min.y)); }
    void set_min_h(float h) { set_custom_min(Vec2(_custom_min.x, h)); }
    int h_flags() const { return _hflags; }
    int v_flags() const { return _vflags; }
    void set_h_flags(int f);
    void set_v_flags(int f);
    float stretch_ratio = 1.0f;
    void set_anchors_preset(Preset p);
    void set_anchors_and_offsets_preset(Preset p) { set_anchors_preset(p); }
    void set_anchor(Side s, float v);
    void set_offset(Side s, float v);
    void set_offsets(float l, float t, float r, float b);
    float offset(Side s) const { return _offset[s]; }
    void set_grow(Grow h, Grow v);
    bool anchored() const { return _anchored; }
    Vec2 pivot() const { return _pivot; }
    void set_pivot(const Vec2& p);            // pivot_offset (scale / rotation centre)
    Vec2 shift() const { return _shift; }     // extra render offset that layout never touches (slides, shakes)
    void set_shift(const Vec2& s);
    Rect2 rect() const { return {_pos, _size}; }
    Rect2 global_rect() const;
    Vec2 global_position() const { return global_rect().position; }
    Vec2 to_local(const Vec2& global) const { return global - global_position(); }

    // minimum size: custom minimum combined with the content (Godot get_combined_minimum_size)
    float min_w();
    float min_h(float width);
    Vec2 combined_min() { float w = min_w(); return Vec2(w, min_h(w)); }
    virtual float content_min_w() { return 0; }
    virtual float content_min_h(float /*width*/) { return 0; }

    // look ------------------------------------------------------------------
    Col modulate() const { return _modulate; }
    void set_modulate(const Col& c);
    float alpha() const { return _modulate.a; }
    void set_alpha(float a) { set_modulate(_modulate.with_alpha(a)); }
    void set_z(int z) { setLocalZOrder(z); }
    int z() const { return getLocalZOrder(); }
    bool clip_contents() const { return _clip; }
    void set_clip(bool c) { _clip = c; }
    void setVisible(bool v) override;
    bool visible() const { return isVisible(); }
    void set_visible(bool v) { setVisible(v); }
    bool is_visible_in_tree() const;

    // input -------------------------------------------------------------------
    MouseFilter mouse_filter = MOUSE_STOP;
    void set_mouse_filter(MouseFilter m) { mouse_filter = m; }
    Signal<InputEvent&> gui_input;
    Signal<> mouse_entered, mouse_exited;
    virtual void on_gui_event(InputEvent& /*e*/) {}   // built-in handling (buttons, scroll...)
    virtual void on_hover(bool /*inside*/) {}

    // signals & data ----------------------------------------------------------
    Signal<> resized;
    Signal<> tree_exiting;
    Json meta = Json::object();   // Godot set_meta / get_meta
    std::string tooltip_text;

    // layout (called by the framework) ----------------------------------------
    void fit(const Vec2& pos, const Vec2& size);   // place + size + lay out children
    virtual void layout_children();
    void onExit() override;
    void visit(ax::Renderer* r, const ax::Mat4& t, uint32_t flags) override;
    int seq() const { return _seq; }

protected:
    void apply_transform();
    virtual void size_changed() {}    // update drawing after a resize
    void fit_child_in(Control* c, const Rect2& r);   // container helper: honours size flags

    Vec2 _pos, _size, _custom_min, _pivot, _shift;
    int _hflags = SIZE_FILL, _vflags = SIZE_FILL;
    bool _anchored = false;
    float _anchor[4] = {0, 0, 0, 0};
    float _offset[4] = {0, 0, 0, 0};
    Grow _grow_h = GROW_END, _grow_v = GROW_END;
    Col _modulate;
    bool _clip = false;
    int _seq = 0;
    ax::Rect _scissor_saved;
    bool _scissor_was_on = false;
    void before_clip();
    void after_clip();
};

// A zero-size Control that holds raw nodes in Godot Node2D coordinates.
class Node2D : public Control
{
public:
    static Node2D* create();
    bool init() override;
    ax::Node* add2d(ax::Node* n, const Vec2& godot_pos, int z = 0);
};

// ------------------------------------------------------------------ containers
class BoxContainer : public Control
{
public:
    bool vertical = true;
    int separation = 12;
    BoxAlign alignment = ALIGNMENT_BEGIN;
    static BoxContainer* create(bool vertical, int sep = 12);
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
private:
    std::vector<float> distribute(const std::vector<Control*>& kids, float total, float* start);
};
using VBox = BoxContainer;
using HBox = BoxContainer;
inline BoxContainer* vbox(int sep = 12) { return BoxContainer::create(true, sep); }
inline BoxContainer* hbox(int sep = 12) { return BoxContainer::create(false, sep); }

class GridContainer : public Control
{
public:
    int columns = 1, h_separation = 4, v_separation = 4;
    static GridContainer* create(int columns = 1);
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
private:
    void measure(float width, std::vector<float>& cols, std::vector<float>& rows);
};

class FlowContainer : public Control   // HFlowContainer
{
public:
    int h_separation = 4, v_separation = 4;
    BoxAlign alignment = ALIGNMENT_BEGIN;
    static FlowContainer* create();
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
private:
    float flow(float width, bool apply);
};

class CenterContainer : public Control
{
public:
    static CenterContainer* create();
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
};

class MarginContainer : public Control
{
public:
    float margin[4] = {0, 0, 0, 0};   // left, top, right, bottom
    static MarginContainer* create(float l = 0, float t = 0, float r = 0, float b = 0);
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
};

// ------------------------------------------------------------------ style boxes
struct StyleBox
{
    enum Kind { EMPTY, TEXTURE, FLAT } kind = EMPTY;
    std::string texture;                   // path under Content/ (e.g. "assets/ui/v2_panel.png")
    float tex_margin[4] = {0, 0, 0, 0};    // 9-slice margins in texture pixels (l, t, r, b)
    float content_margin[4] = {0, 0, 0, 0};
    Col modulate;                          // tint for textures
    Col bg, border;                        // flat
    float border_width = 0;
    static StyleBox empty() { return {}; }
    static StyleBox tex(const std::string& path, float margin, float content);
    static StyleBox flat(const Col& bg, const Col& border = Col::TRANSPARENT, float border_w = 0);
    StyleBox& content(float l, float t, float r, float b) { content_margin[0] = l; content_margin[1] = t; content_margin[2] = r; content_margin[3] = b; return *this; }
    StyleBox& content_all(float m) { return content(m, m, m, m); }
    float cw() const { return content_margin[0] + content_margin[2]; }
    float ch() const { return content_margin[1] + content_margin[3]; }
    ax::Node* build(const Vec2& size) const;        // node sized `size`, anchored bottom-left
    static void resize(ax::Node* n, const StyleBox& sb, const Vec2& size);
};

// Draws a StyleBox behind its children (Godot Panel; children are NOT laid out).
class Panel : public Control
{
public:
    static Panel* create(const StyleBox& sb = StyleBox());
    bool init() override;
    void set_style(const StyleBox& sb);
    const StyleBox& style() const { return _style; }
protected:
    void size_changed() override;
    StyleBox _style;
    ax::Node* _bg = nullptr;
};

// Godot PanelContainer: StyleBox + children filling the content rect.
class PanelContainer : public Panel
{
public:
    static PanelContainer* create(const StyleBox& sb = StyleBox());
    bool init() override;
    float content_min_w() override;
    float content_min_h(float w) override;
    void layout_children() override;
};

// ------------------------------------------------------------------ leaves
class Label : public Control
{
public:
    static Label* create(const std::string& text = "", int font_size = 30);
    bool init() override;
    const std::string& text() const { return _text; }
    void set_text(const std::string& t);
    int font_size() const { return _font_size; }
    void set_font_size(int s);
    void set_color(const Col& c);
    Col color() const { return _color; }
    void set_shadow(const Col& c, float offset);      // offset 0 = none
    void set_outline(int size, const Col& c = Col("#140806"));
    void set_outline_color(const Col& c) { set_outline(_outline, c); }
    int outline() const { return _outline; }
    HAlign h_align = ALIGN_LEFT;
    VAlign v_align = VALIGN_TOP;
    void set_align(HAlign h, VAlign v = VALIGN_TOP) { h_align = h; v_align = v; mark(); }
    void set_autowrap(bool w) { _wrap = w; mark(); }
    bool autowrap() const { return _wrap; }
    void set_clip_text(bool c) { _clip_text = c; mark(); }   // clip with an ellipsis
    void set_visible_ratio(float r);                       // typewriter reveal (0..1)
    int line_spacing = 6;
    float content_min_w() override;
    float content_min_h(float w) override;
    ax::Label* ax_label() { return _lbl; }
    Vec2 text_size() const;   // single-line size of the current text
protected:
    void size_changed() override;
    void rebuild();
    void mark();
    std::string _text;
    int _font_size = 30;
    Col _color = Col::WHITE, _shadow = Col(0, 0, 0, 0), _outline_col = Col("#140806");
    float _shadow_off = 0;
    int _outline = 0;
    bool _wrap = false, _clip_text = false;
    float _visible_ratio = 1;
    ax::Label* _lbl = nullptr;
    bool _dirty_font = true;
};

class TextureRect : public Control
{
public:
    static TextureRect* create(const std::string& path = "");
    bool init() override;
    void set_texture(const std::string& path);   // "" clears
    void set_texture(ax::Texture2D* t);
    ax::Texture2D* texture() const { return _tex; }
    const std::string& texture_path() const { return _path; }
    void set_region(const ax::Rect& r);          // AtlasTexture region (texture pixels, top-left origin)
    Stretch stretch = STRETCH_SCALE;
    bool ignore_size = false;                    // expand_mode = EXPAND_IGNORE_SIZE
    bool flip_h = false, flip_v = false;
    bool additive = false;
    void set_stretch(Stretch s) { stretch = s; size_changed(); }
    void set_flip_h(bool f) { flip_h = f; size_changed(); }
    float content_min_w() override;
    float content_min_h(float w) override;
    Vec2 texture_size() const;
    ax::Sprite* sprite() { return _spr; }
protected:
    void size_changed() override;
    ax::Texture2D* _tex = nullptr;
    std::string _path;
    ax::Rect _region;
    bool _has_region = false;
    ax::Sprite* _spr = nullptr;
};

class ColorRect : public Control
{
public:
    static ColorRect* create(const Col& c = Col::WHITE);
    bool init() override;
    void set_color(const Col& c);
    Col color() const { return _color; }
    bool additive = false;
protected:
    void size_changed() override;
    Col _color;
    ax::Sprite* _spr = nullptr;
};

// Base for clickable controls: press / release / cancel handling and signals.
class BaseButton : public Control
{
public:
    bool init() override;
    Signal<> pressed, button_down, button_up;
    bool disabled() const { return _disabled; }
    virtual void set_disabled(bool d);
    bool is_pressed_down() const { return _down; }
    bool hovered() const { return _hover; }
    float press_cooldown = 0.25f;   // seconds between accepted presses (0 = none)
    void on_gui_event(InputEvent& e) override;
    void on_hover(bool inside) override;
protected:
    virtual void update_look() {}
    bool _disabled = false, _down = false, _hover = false;
    double _last_press = -100;
};

// Godot Button: StyleBoxes per state, optional icon on the left, centred text.
class Button : public BaseButton
{
public:
    static Button* create(const std::string& text = "");
    bool init() override;
    void set_text(const std::string& t);
    const std::string& text() const { return _text; }
    void set_icon(const std::string& path);
    std::string icon_path() const { return _icon_path; }
    int icon_max_width = 0;       // 0 = natural size
    bool icon_top = false;        // icon above the text (nav buttons)
    int h_separation = 12;
    HAlign alignment = ALIGN_CENTER;
    void set_font_size(int s);
    int font_size() const { return _font_size; }
    enum State { NORMAL, HOVER, PRESSED, DISABLED, STATE_COUNT };
    void set_style(State s, const StyleBox& sb);
    const StyleBox& style(State s) const { return _styles[s]; }
    void set_font_color(State s, const Col& c);
    void set_outline(int size, const Col& c);
    float content_min_w() override;
    float content_min_h(float w) override;
    Label* label() { return _label; }
    TextureRect* icon_rect() { return _icon; }
protected:
    void size_changed() override;
    void update_look() override;
    State state() const;
    std::string _text, _icon_path;
    int _font_size = 40;
    StyleBox _styles[STATE_COUNT];
    Col _font_colors[STATE_COUNT];
    ax::Node* _bg = nullptr;
    State _bg_state = STATE_COUNT;
    Label* _label = nullptr;
    TextureRect* _icon = nullptr;
    Vec2 icon_draw_size(float avail_h);
};

// Vertical scroll area with one content child (touch drag, mouse wheel, inertia).
class ScrollContainer : public Control
{
public:
    static ScrollContainer* create();
    bool init() override;
    float scroll_vertical() const { return _scroll; }
    void set_scroll_vertical(float v);
    float max_scroll();
    bool show_bar = true;
    bool horizontal_disabled = true;
    float content_min_w() override;
    float content_min_h(float) override { return 0; }
    void layout_children() override;
    void on_gui_event(InputEvent& e) override;
    void ensure_visible(Control* c);
    void update(float dt) override;
    bool can_scroll() { return max_scroll() > 1; }
    void begin_drag(const Vec2& global);
    Signal<> scrolled;
private:
    float _scroll = 0, _vel = 0, _drag_y = 0;
    bool _dragging = false;
    double _last_move_t = 0;
    ax::Node* _bar = nullptr;
    ax::Node* _grab = nullptr;
    void place_bar();
};

class HSlider : public Control
{
public:
    static HSlider* create(float min = 0, float max = 1, float step = 0.01f);
    bool init() override;
    float min_value = 0, max_value = 1, step = 0.01f;
    float value() const { return _value; }
    void set_value(float v, bool emit = true);
    Signal<float> value_changed;
    float content_min_w() override { return 100; }
    float content_min_h(float) override { return 60; }
    void on_gui_event(InputEvent& e) override;
protected:
    void size_changed() override;
    float _value = 0;
    ax::Node *_track = nullptr, *_fill = nullptr;
    ax::Sprite* _knob = nullptr;
};

class LineEdit : public Control
{
public:
    static LineEdit* create(const std::string& text = "");
    bool init() override;
    std::string text() const;
    void set_text(const std::string& t);
    void set_placeholder(const std::string& p);
    int max_length = 0;
    int font_size = 30;
    Signal<std::string> text_changed, text_submitted;
    void grab_focus();
    void release_focus();
    float content_min_w() override { return 200; }
    float content_min_h(float) override;
    void on_gui_event(InputEvent& e) override;
    void onExit() override;
protected:
    void size_changed() override;
    ax::TextFieldTTF* _field = nullptr;
    ax::Node* _bg = nullptr;
    ax::EventListenerKeyboard* _keys = nullptr;
    StyleBox _style;
    bool _focused = false;
};

// ------------------------------------------------------------------ tweens
enum Trans { TRANS_LINEAR, TRANS_SINE, TRANS_QUAD, TRANS_CUBIC, TRANS_QUART, TRANS_QUINT, TRANS_EXPO, TRANS_CIRC, TRANS_BACK, TRANS_ELASTIC, TRANS_BOUNCE };
enum Ease { EASE_IN, EASE_OUT, EASE_IN_OUT, EASE_OUT_IN };
float ease_value(float t, Trans tr, Ease e);

// Godot-style tween bound to an owner node (stops when the owner is removed).
// Steps run in sequence unless set_parallel()/parallel(). Starts on the next frame.
class Tween : public std::enable_shared_from_this<Tween>
{
public:
    explicit Tween(ax::Node* owner);
    ~Tween();
    Tween& prop(std::function<float()> get, std::function<void(float)> set, float to, float dur);
    Tween& prop2(std::function<Vec2()> get, std::function<void(Vec2)> set, Vec2 to, float dur);
    Tween& method(std::function<void(float)> f, float from, float to, float dur);
    Tween& alpha(Control* c, float to, float dur);
    Tween& modulate(Control* c, const Col& to, float dur);
    Tween& position(Control* c, const Vec2& to, float dur);
    Tween& position_x(Control* c, float to, float dur);
    Tween& position_y(Control* c, float to, float dur);
    Tween& shift(Control* c, const Vec2& to, float dur);
    Tween& scale(ax::Node* n, const Vec2& to, float dur);
    Tween& rotation(ax::Node* n, float degrees, float dur);
    Tween& node_pos(ax::Node* n, const Vec2& godot_to, float dur);   // raw node, Godot coords (p2)
    Tween& opacity(ax::Node* n, float to01, float dur);              // raw node opacity
    Tween& interval(float dur);
    Tween& callback(std::function<void()> f);
    Tween& set_parallel(bool on = true) { _parallel_all = on; return *this; }
    Tween& parallel() { _next_parallel = true; return *this; }
    Tween& chain() { _force_new_group = true; return *this; }
    Tween& trans(Trans t);
    Tween& ease(Ease e);
    Tween& loops(int n = 0);   // 0 = forever
    Tween& on_finished(std::function<void()> f) { _finished = std::move(f); return *this; }
    void kill();
    bool is_running() const { return !_killed && (_action != nullptr || !_started); }
    struct Step;
    void start();
private:
    void add(std::shared_ptr<Step> s);
    ax::Node* _owner;
    std::vector<std::vector<std::shared_ptr<Step>>> _groups;
    bool _parallel_all = false, _next_parallel = false, _force_new_group = false;
    int _loops = 1;
    bool _started = false, _killed = false;
    ax::Action* _action = nullptr;
    std::function<void()> _finished;
    Trans _default_trans = TRANS_LINEAR;
};
using TweenRef = std::shared_ptr<Tween>;
TweenRef tween(ax::Node* owner);   // create_tween()

// ------------------------------------------------------------------ helpers
ax::Texture2D* texture(const std::string& path);   // cached, nearest filtering; nullptr if missing
bool exists(const std::string& path);
ax::Texture2D* white_texture();
// Gradient texture: stops (offset, colour). radial: centre at `from`, radius |to-from| (UV space).
ax::Texture2D* gradient_texture(const std::vector<std::pair<float, Col>>& stops, int w, int h, bool radial = false,
                                Vec2 from = Vec2(0.5f, 0), Vec2 to = Vec2(0.5f, 1));
ax::Size text_size(const std::string& text, int font_size, float wrap_width = 0, int outline = 0);
std::string font_path();
double ticks();   // seconds since start (Time.get_ticks_msec() / 1000)

void after(ax::Node* owner, float seconds, std::function<void()> f);   // get_tree().create_timer bound to a node
void defer(std::function<void()> f);                                  // call_deferred (after the next layout)
template <class... A, class F>
void listen(Control* owner, Signal<A...>& sig, F f)   // auto-disconnect on exit
{
    int id = sig.connect(std::function<void(A...)>(std::move(f)));
    owner->tree_exiting.connect([&sig, id] { sig.disconnect(id); });
}

// CPUParticles2D stand-in (GRAVITY emitter, square pixels).
struct ParticleCfg
{
    int amount = 8;
    float lifetime = 1.0f;
    bool one_shot = false;
    float explosiveness = 0;
    float preprocess = 0;
    Vec2 emission_rect;          // extents (half size); zero = point
    float emission_radius = 0;   // sphere/ring emission (uses both axes)
    Vec2 direction{1, 0};        // Godot direction (y down)
    float spread = 45;           // degrees
    Vec2 gravity{0, 98};         // Godot gravity (y down)
    float vel_min = 0, vel_max = 0;
    float scale_min = 1, scale_max = 1;
    float scale_end = -1;        // end size multiplier (-1 = same as start)
    Col color = Col::WHITE;      // used when no ramp
    std::vector<Col> ramp;       // colour over lifetime (first / last used)
    bool additive = false;
    std::string texture;         // default: a square pixel
    bool local_coords = true;
};
class Particles : public Node2D
{
public:
    static Particles* create(const ParticleCfg& cfg);
    bool emitting() const;
    void set_emitting(bool on);
    void restart();
    ax::ParticleSystemQuad* system() { return _ps; }
private:
    ax::ParticleSystemQuad* _ps = nullptr;
    ParticleCfg _cfg;
};

// ------------------------------------------------------------------ root & input router
// One per app: sized to the visible screen, owns input dispatch and the layout pass.
class Root : public Control
{
public:
    static Root* get();
    static Root* create();
    bool init() override;
    void update(float dt) override;
    void layout_now();
    Signal<int> key_pressed;     // ax::EventKeyboard::KeyCode as int
    Signal<int> key_released;
    Control* hovered() const { return _hover.get(); }
    Vec2 mouse_position() const { return _mouse; }
    Control* hit_test(const Vec2& global);
    bool input_blocked = false;  // e.g. during screen transitions
    static void mark_dirty();
private:
    Control* hit(Control* c, const Vec2& g, const Vec2& origin);
    void dispatch(Control* target, InputEvent& e);
    void press(const Vec2& g);
    void move(const Vec2& g);
    void release(const Vec2& g, bool cancel);
    Vec2 to_gd(const Vec2& gl) const;
    ax::RefPtr<Control> _capture;
    ax::RefPtr<Control> _hover;
    Vec2 _press_at, _mouse;
    bool _pressing = false, _scroll_taken = false;
};

// ------------------------------------------------------------------ animated sprites
// SpriteFrames stand-in: named animations of texture regions.
struct SpriteAnim
{
    std::vector<ax::SpriteFrame*> frames;   // retained
    float fps = 8;
    bool loop = true;
};
class AnimatedSprite : public ax::Sprite
{
public:
    static AnimatedSprite* create();
    ~AnimatedSprite() override;
    void add_animation(const std::string& name, const std::vector<ax::Rect>& regions, ax::Texture2D* tex, float fps, bool loop);
    bool has_animation(const std::string& name) const { return _anims.count(name) > 0; }
    void play(const std::string& name);
    void stop();
    const std::string& animation() const { return _current; }
    int frame() const { return _frame; }
    void set_frame(int f);
    int frame_count(const std::string& name) const;
    bool is_playing() const { return _playing; }
    float speed_scale = 1.0f;
    Signal<> animation_finished;
    Signal<> frame_changed;
    void update(float dt) override;
    void set_flip_h(bool f) { setFlippedX(f); }
private:
    std::map<std::string, SpriteAnim> _anims;
    std::string _current;
    int _frame = 0;
    float _t = 0;
    bool _playing = false;
};

}  // namespace gd
