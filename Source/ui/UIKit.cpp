#include "UIKit.h"
#include <cmath>
#include <cstdarg>

using namespace gd;

namespace UIKit
{
// `X = Col(...)` form: TEXT(...) would hit the Windows TEXT() macro
const Col TEXT = Col("#f4ecdc"), MUTED = Col("#a8a0b0"), GOLD = Col("#ffd35a"), EMBER = Col("#ff9a4a"),
          DANGER = Col("#ff5a4a"), GOOD = Col("#8ae05a"), SKY = Col("#8ad8ff"), SHADOW = Col(0.04f, 0.02f, 0.05f, 0.95f);

std::string fmt(const char* f, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, f);
    vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

std::string button_style(const std::string& kind)
{
    static const std::map<std::string, std::string> K{{"primary", "ember"}, {"confirm", "ember"}, {"secondary", "steel"},
                                                      {"quiet", "stone"},   {"reward", "gold"},   {"danger", "crimson"},
                                                      {"blue", "steel"},    {"red", "ember"}};
    auto it = K.find(kind);
    return it == K.end() ? kind : it->second;
}

StyleBox tex_style(const std::string& file, float margin, float content) { return StyleBox::tex(UI_DIR + file, margin, content); }
StyleBox flat(const Col& c, const Col& border, float bw) { return StyleBox::flat(c, border, bw); }

static float extra_margin() { return float(I(GM.settings, "safe_area", 0) * 30); }
static Vec2 insets()
{
    float extra = extra_margin();
#if AX_TARGET_PLATFORM == AX_PLATFORM_ANDROID || AX_TARGET_PLATFORM == AX_PLATFORM_IOS
    auto d = ax::Director::getInstance();
    auto safe = d->getSafeAreaRect();
    auto vo = d->getVisibleOrigin();
    auto vs = d->getVisibleSize();
    float top = (vo.y + vs.height) - (safe.origin.y + safe.size.height);
    float bottom = safe.origin.y - vo.y;
    return Vec2(std::max(0.0f, top) + extra, std::max(0.0f, bottom) + extra);
#else
    return Vec2(extra, extra);
#endif
}
float safe_top() { return insets().x; }
float safe_bottom() { return insets().y; }

int snap_text(int size) { return std::max(20, (int)std::lround(size / 10.0) * 10); }

Label* label(const std::string& text, int size, const Col& color, HAlign align, int outline)
{
    size = snap_text(size);
    auto l = Label::create(text, size);
    l->set_color(color);
    l->set_shadow(SHADOW, float(size / 10));
    if (outline > 0) l->set_outline(outline, Col("#140806"));
    l->h_align = align;
    l->set_mouse_filter(MOUSE_IGNORE);
    return l;
}

Label* heading(const std::string& text, int size, const Col& color)
{
    return label(text, size, color, ALIGN_CENTER, std::max(8, snap_text(size) / 6));
}

Label* wrap_label(const std::string& text, int size, const Col& color)
{
    auto l = label(text, size, color);
    l->set_autowrap(true);
    l->set_min_w(100);
    return l;
}

Control* title_plate(const std::string& text, int size)
{
    auto p = PanelFrame::make("plank", 10);
    p->set_h_flags(SIZE_SHRINK_CENTER);
    p->set_min_w(520);
    p->add(label(text, size, Col("#fff0c0"), ALIGN_CENTER, 10));
    return p;
}

TextureRect* separator()
{
    auto r = TextureRect::create(UI_DIR + "v2_separator.png");
    r->stretch = STRETCH_SCALE;
    r->ignore_size = true;
    r->set_custom_min(Vec2(0, 15));
    r->set_mouse_filter(MOUSE_IGNORE);
    return r;
}

PanelContainer* tag(const std::string& text, const Col& color)
{
    auto p = PanelContainer::create(flat(color, Col("#ffd35a"), 3).content(10, 2, 10, 2));
    p->add(label(text, T_SMALL, Col::WHITE, ALIGN_CENTER, 6));
    p->set_mouse_filter(MOUSE_IGNORE);
    return p;
}

FantasyButton* btn(const std::string& text, const std::string& kind, Vec2 min_size, const std::string& icon_path)
{
    auto b = FantasyButton::make(text, button_style(kind), min_size, icon_path);
    b->kind = kind;
    if (min_size.y < 100) b->set_font_size(T_BUTTON_S);
    return b;
}

FantasyButton* button(const std::string& text, const std::string& icon_path, Vec2 min_size, const std::string& style)
{
    return FantasyButton::make(text, button_style(style), min_size, icon_path);
}

void hook_sounds(BaseButton* b)
{
    b->mouse_entered.connect([b] {
        if (!b->disabled()) AudioManager::play_sfx("hover", 0.02f, -12.0f);
    });
    b->pressed.connect([] { AudioManager::play_sfx("click", 0.03f); });
}

PanelFrame* panel(const std::string& style)
{
    static const std::map<std::string, std::string> V{{"frame", "panel"}, {"dark", "panel"}, {"red", "boss"}, {"ember", "boss"},
                                                      {"tile", "inset"},  {"card", "card_neutral"}, {"plate", "plank"}};
    auto it = V.find(style);
    return PanelFrame::make(it == V.end() ? style : it->second);
}

int snap_icon(int size) { return std::max(16, (int)std::lround(size / 16.0) * 16); }

TextureRect* icon(const std::string& path, int size)
{
    auto r = TextureRect::create(path);
    size = snap_icon(size);
    r->set_custom_min(Vec2((float)size, (float)size));
    r->ignore_size = true;
    r->stretch = STRETCH_KEEP_ASPECT_CENTERED;
    r->set_mouse_filter(MOUSE_IGNORE);
    return r;
}

TextureRect* tex_rect(ax::Texture2D* tex, Vec2 size)
{
    auto r = TextureRect::create();
    r->set_texture(tex);
    r->set_custom_min(size);
    r->ignore_size = true;
    r->stretch = STRETCH_KEEP_ASPECT_CENTERED;
    r->set_mouse_filter(MOUSE_IGNORE);
    return r;
}

TextureRect* orb(const std::string& element, int size) { return icon("assets/icons/orb_" + element + ".png", size); }

BoxContainer* stars(int count, int size)
{
    auto h = hbox(0);
    h->set_mouse_filter(MOUSE_IGNORE);
    for (int i = 0; i < count; ++i) h->add(icon("assets/icons/star.png", size));
    return h;
}

BoxContainer* element_badge(const std::string& element, int size)
{
    auto h = hbox(8);
    h->add(orb(element, 48));
    h->add(label(DB.element_name(element), size, Col(DB.element_color(element)).lightened(0.25f), ALIGN_LEFT, 6));
    return h;
}

Control* portrait_art(const Json& def, Vec2 box)
{
    auto holder = Control::create();
    holder->set_custom_min(box);
    holder->set_clip(true);
    holder->set_mouse_filter(MOUSE_IGNORE);
    Col col(DB.element_color(S(def, "element")));
    auto bg = TextureRect::create();
    bg->set_texture(gradient_texture({{0.0f, col.darkened(0.15f)}, {1.0f, col.darkened(0.82f)}}, 4, 64));
    bg->ignore_size = true;
    bg->set_anchors_preset(PRESET_FULL_RECT);
    holder->add(bg);
    if (auto tex = texture(S(def, "portrait")))
    {
        Vec2 ts = tex->getContentSize();
        float k = std::max(1.0f, std::round(std::max(box.x / ts.x, box.y / ts.y) - 0.1f));
        auto r = tex_rect(tex, ts * k);
        r->set_size(ts * k);
        r->set_position(Vec2((box.x - ts.x * k) / 2, box.y - ts.y * k));
        holder->add(r);
    }
    return holder;
}

Control* portrait_frame(const Json& def, int size, bool show_orb)
{
    std::string el = S(def, "element", "neutral");
    auto frame = PanelFrame::make("card_" + el, 9);
    frame->set_mouse_filter(MOUSE_IGNORE);
    auto stack = Control::create();
    stack->set_custom_min(Vec2((float)size, (float)size));
    stack->set_mouse_filter(MOUSE_IGNORE);
    frame->add(stack);
    stack->add(portrait_art(def, Vec2((float)size, (float)size)));
    if (show_orb)
    {
        auto o = orb(el, size < 160 ? 32 : 48);
        Vec2 m = o->custom_min();
        o->set_position(Vec2(-4, size - m.y + 4));
        o->set_size(m);
        stack->add(o);
    }
    return frame;
}

Particles* sparkle(Control* parent, Rect2 area, const Col& color, int amount)
{
    ParticleCfg c;
    c.amount = amount;
    c.lifetime = 1.4f;
    c.emission_rect = area.size / 2;
    c.gravity = Vec2(0, -20);
    c.vel_min = 0;
    c.vel_max = 10;
    c.direction = Vec2(0, -1);
    c.spread = 180;
    c.scale_min = 3;
    c.scale_max = 6;
    c.ramp = {color, color.with_alpha(0)};
    auto p = Particles::create(c);
    p->set_position(area.center());
    parent->add(p);
    return p;
}

Control* spacer(bool h_expand, bool v_expand)
{
    auto c = Control::create();
    if (h_expand) c->set_h_flags(SIZE_EXPAND_FILL);
    if (v_expand) c->set_v_flags(SIZE_EXPAND_FILL);
    c->set_mouse_filter(MOUSE_IGNORE);
    return c;
}

BoxContainer* stat_row(const std::string& name, const std::string& value, int size, const Col& value_color)
{
    auto h = hbox(8);
    auto n = label(name, size, SKY);
    n->set_min_w(float(size * 4));
    h->add(n);
    h->add(label(value, size, value_color));
    return h;
}

PanelContainer* strip(const std::string& title, const std::string& value, const Col& color)
{
    auto p = PanelContainer::create(flat(color.darkened(0.35f), color.lightened(0.2f), 3).content(18, 6, 18, 6));
    auto h = hbox(20);
    h->add(label(title, T_BODY, Col::WHITE, ALIGN_LEFT, 6));
    auto v = label(value, T_BODY, GOLD, ALIGN_LEFT, 6);
    v->set_h_flags(SIZE_EXPAND_FILL);
    h->add(v);
    p->add(h);
    return p;
}

TextureRect* stone_rect()
{
    auto stone = TextureRect::create(UI_DIR + "m_stone.png");
    stone->stretch = STRETCH_TILE;
    stone->ignore_size = true;
    stone->set_modulate(Col(0.5f, 0.46f, 0.56f));
    stone->set_mouse_filter(MOUSE_IGNORE);
    return stone;
}

TextureRect* screen_background(Control* parent, const std::string& bg_name, float dim)
{
    auto stone = TextureRect::create(UI_DIR + "m_stone.png");
    stone->stretch = STRETCH_TILE;
    stone->ignore_size = true;
    stone->set_anchors_preset(PRESET_FULL_RECT);
    stone->set_modulate(Col(0.55f, 0.5f, 0.6f));
    stone->set_mouse_filter(MOUSE_IGNORE);
    parent->add(stone);
    auto bg = TextureRect::create("assets/environments/" + bg_name + ".png");
    bg->set_anchors_preset(PRESET_FULL_RECT);
    bg->ignore_size = true;
    bg->stretch = STRETCH_KEEP_ASPECT_COVERED;
    bg->set_mouse_filter(MOUSE_IGNORE);
    parent->add(bg);
    if (dim > 0)
    {
        auto d = ColorRect::create(Col(0.05f, 0.03f, 0.07f, dim));
        d->set_anchors_preset(PRESET_FULL_RECT);
        d->set_mouse_filter(MOUSE_IGNORE);
        parent->add(d);
    }
    return bg;
}

StatusBar* status_bar(Control* parent)
{
    auto bar = StatusBar::create();
    bar->set_anchors_preset(PRESET_TOP_WIDE);
    bar->set_offsets(8, 6 + safe_top(), -8, TOP_BAR_H - 4 + safe_top());
    parent->add(bar);
    bar->build();
    return bar;
}

Control* badge(Control* c, const std::string& text)
{
    if (auto old = c->find("Badge")) old->removeFromParent();
    auto p = PanelContainer::create(flat(Col("#d8281e"), Col("#ffe08a"), 3).content(10, 2, 10, 2));
    p->set_name("Badge");
    p->set_mouse_filter(MOUSE_IGNORE);
    p->set_custom_min(Vec2(46, 46));
    auto l = label(text, 28, Col::WHITE, ALIGN_CENTER, 6);
    l->v_align = VALIGN_CENTER;
    p->add(l);
    p->set_z(5);
    c->add(p);
    auto place = [p, c] {
        Vec2 s = p->combined_min();
        p->set_size(s);
        p->set_position(Vec2(c->size().x - s.x + 6, -12));
        p->set_pivot(s / 2);
    };
    place();
    c->resized.connect(place);
    auto tw = tween(p);
    tw->loops();
    tw->scale(p, Vec2(1.1f, 1.1f), 0.5f);
    tw->scale(p, Vec2(1, 1), 0.5f);
    return p;
}

NavBar* nav_bar(Control* parent, const std::string& current) { return NavBar::attach(parent, current); }

FantasyPopup* modal(Control* parent, const std::string& title, int min_width) { return FantasyPopup::open(parent, title, min_width); }

FantasyPopup* confirm(Control* parent, const std::string& text, std::function<void()> on_yes, const std::string& yes,
                      const std::string& no, std::function<void()> on_no, bool danger)
{
    ConfirmOpts o;
    o.cancel_text = no;
    o.on_cancel = std::move(on_no);
    o.parent = parent;
    o.danger = danger;
    return UIManager::confirm("", text, yes, std::move(on_yes), o);
}

FantasyPopup* message(Control* parent, const std::string& title, const std::string& text, const std::string& ok)
{
    return UIManager::message(title, text, ok, parent);
}

void toast(Control*, const std::string& text, const Col& color)
{
    std::string kind = "info";
    if (color == DANGER) kind = "error";
    else if (color == GOOD || color == GOLD) kind = "success";
    UIManager::toast(text, kind);
}

void on_tap(Control* c, std::function<void()> cb)
{
    c->set_mouse_filter(MOUSE_STOP);
    c->gui_input.connect([c, cb](InputEvent& e) {
        if (e.type == Ev::PRESS)
        {
            c->meta["tap_start"] = {e.global.x, e.global.y};
            c->set_pivot(c->size() / 2);
            c->setScale(0.97f);
            e.accept();
        }
        else if (e.type == Ev::CANCEL)
        {
            c->meta.erase("tap_start");
            c->setScale(1.0f);
        }
        else if (e.type == Ev::RELEASE && c->meta.contains("tap_start"))
        {
            Vec2 start((float)F(c->meta["tap_start"][0]), (float)F(c->meta["tap_start"][1]));
            c->meta.erase("tap_start");
            c->setScale(1.0f);
            if (e.global.distance(start) < 30.0f)
            {
                AudioManager::play_sfx("click");
                c->retain();
                cb();
                c->release();
            }
            e.accept();
        }
    });
}

static std::string trim_dec(double v)
{
    if (v >= 100.0) return std::to_string((long long)std::floor(v));
    double t = std::floor(v * 10.0) / 10.0;
    if (t == std::floor(t)) return std::to_string((long long)t);
    return fmt("%.1f", t);
}

std::string format_number(long long n) { return fmt_number(n); }

std::string format_compact(long long n)
{
    long long a = std::llabs(n);
    std::string sign = n < 0 ? "-" : "";
    if (a < 10000) return sign + format_number(a);
    if (a < 1000000) return sign + trim_dec(a / 1000.0) + "K";
    if (a < 1000000000) return sign + trim_dec(a / 1000000.0) + "M";
    return sign + trim_dec(a / 1000000000.0) + "B";
}

std::string format_time(int s)
{
    s = std::max(s, 0);
    int h = s / 3600, m = (s % 3600) / 60, sec = s % 60;
    return h > 0 ? fmt("%d:%02d:%02d", h, m, sec) : fmt("%d:%02d", m, sec);
}

Label* fit_label(Label* l, float max_width, int min_size)
{
    if (!l->meta.contains("fit_base")) l->meta["fit_base"] = l->font_size();
    int size = I(l->meta, "fit_base", l->font_size());
    l->set_clip_text(false);
    l->tooltip_text.clear();
    while (size > min_size && text_size(l->text(), size, 0, l->outline()).x > max_width) size -= 10;
    l->set_font_size(size);
    if (text_size(l->text(), size, 0, l->outline()).x > max_width)
    {
        l->set_clip_text(true);
        l->tooltip_text = l->text();
    }
    return l;
}
}  // namespace UIKit

// ================================================================== PanelFrame
PanelFrame* PanelFrame::make(const std::string& v, int pad)
{
    auto p = gd::make<PanelFrame>();
    p->set_variant(v, pad);
    return p;
}

void PanelFrame::set_variant(const std::string& v, int pad)
{
    variant = v;
    static const std::map<std::string, std::pair<int, int>> M{{"panel", {30, 30}}, {"inset", {15, 20}}, {"plank", {15, 16}},
                                                              {"boss", {30, 26}},  {"enemy", {18, 18}}, {"slot", {12, 10}}};
    int tm = 12, content = 18;
    auto it = M.find(v);
    if (it != M.end()) { tm = it->second.first; content = it->second.second; }
    else if (v.rfind("card", 0) == 0) { tm = 21; content = 18; }
    else if (v.rfind("rarity", 0) == 0) { tm = 21; content = 12; }
    if (pad >= 0) content = pad;
    set_style(UIKit::tex_style("v2_" + v + ".png", (float)tm, (float)content));
}

// ================================================================== FantasyButton
FantasyButton* FantasyButton::make(const std::string& text, const std::string& style, Vec2 min_size, const std::string& icon_path)
{
    auto b = gd::make<FantasyButton>();
    b->set_text(text);
    b->apply_style(style);
    b->set_custom_min(min_size);
    if (!icon_path.empty())
    {
        b->set_icon(icon_path);
        b->icon_max_width = 48;
    }
    return b;
}

bool FantasyButton::init()
{
    if (!gd::Button::init()) return false;
    set_font_size(40);
    button_down.connect([this] {
        if (_disabled) return;
        if (_tw) _tw->kill();
        set_pivot(size() / 2);
        _tw = tween(this);
        _tw->scale(this, Vec2(0.96f, 0.94f), 0.05f);
    });
    button_up.connect([this] {
        if (_tw) _tw->kill();
        set_pivot(size() / 2);
        _tw = tween(this);
        _tw->scale(this, Vec2(1.03f, 1.03f), 0.06f);
        _tw->scale(this, Vec2(1, 1), 0.08f);
    });
    mouse_entered.connect([this] {
        if (!_disabled) AudioManager::play_sfx("hover", 0.02f, -12.0f);
    });
    pressed.connect([] { AudioManager::play_sfx("click", 0.03f); });
    return true;
}

void FantasyButton::apply_style(const std::string& style)
{
    style_name = style;
    auto sb = [](const std::string& file, float top, float bottom) {
        StyleBox s = StyleBox::tex("assets/ui/" + file, 12, 30);
        s.tex_margin[3] = 18;
        s.content_margin[1] = top;
        s.content_margin[3] = bottom;
        return s;
    };
    StyleBox normal = sb("v2_btn_" + style + ".png", 24, 13);
    set_style(NORMAL, normal);
    set_style(HOVER, selected ? normal : normal);
    set_style(PRESSED, sb("v2_btn_" + style + "_p.png", 30, 7));
    set_style(DISABLED, sb("v2_btn_off.png", 24, 13));
}

void FantasyButton::set_selected(bool on)
{
    selected = on;
    apply_style(style_name);
    set_font_color(NORMAL, on ? UIKit::GOLD : Col::WHITE);
}

void FantasyButton::add_shine(float period)
{
    set_clip(true);
    auto band = ax::DrawNode::create();
    ax::Vec2 poly[4] = {gd::p2(0, 0), gd::p2(36, 0), gd::p2(-24, 400), gd::p2(-60, 400)};
    band->drawSolidPoly(poly, 4, Col(1, 0.95f, 0.8f, 0.28f).c4f());
    band->setBlendFunc(ax::BlendFunc::ADDITIVE);
    auto holder = gd::Node2D::create();
    holder->set_position(Vec2(-120, -40));
    holder->addChild(band);
    add(holder);
    auto tw = tween(holder);
    tw->loops();
    tw->interval(period);
    tw->callback([holder] { holder->set_position_x(-120); });
    tw->position_x(holder, 1400, 0.7f).trans(gd::TRANS_SINE);
}

// ================================================================== FantasyPopup
FantasyPopup* FantasyPopup::open(Control* parent, const std::string& title, int width, const std::string& variant)
{
    auto p = gd::make<FantasyPopup>();
    p->set_name("Popup");
    p->set_anchors_preset(PRESET_FULL_RECT);
    p->set_mouse_filter(MOUSE_STOP);
    p->set_z(50);
    p->dim = ColorRect::create(Col(0.02f, 0.01f, 0.04f, 0.78f));
    p->dim->set_name("Dim");
    p->dim->set_anchors_preset(PRESET_FULL_RECT);
    p->dim->gui_input.connect([p](InputEvent& e) {
        if (p->tap_outside_closes && e.type == Ev::PRESS) p->cancel();
    });
    p->add(p->dim);
    auto center = CenterContainer::create();
    center->set_anchors_preset(PRESET_FULL_RECT);
    center->set_mouse_filter(MOUSE_PASS);
    p->add(center);
    p->panel = PanelFrame::make(variant);
    p->panel->set_min_w((float)width);
    center->add(p->panel);
    p->content = UIKit::vbox(24);
    p->panel->add(p->content);
    if (!title.empty()) p->content->add(UIKit::title_plate(title));
    parent->add(p);
    UIManager::register_popup(p);
    AudioManager::play_sfx("menu_open", 0.02f, -3.0f);
    auto panel = p->panel;
    panel->setScale(0.94f);
    panel->set_alpha(0);
    p->dim->set_alpha(0);
    panel->resized.connect([panel] { panel->set_pivot(panel->size() / 2); });
    auto tw = tween(p);
    tw->set_parallel();
    tw->scale(panel, Vec2(1, 1), 0.16f).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
    tw->alpha(panel, 1.0f, 0.12f);
    tw->alpha(p->dim, 1.0f, 0.12f);
    return p;
}

void FantasyPopup::cancel()
{
    if (_closing) return;
    if (cancel_action) cancel_action();
    else close();
}

void FantasyPopup::confirm_default()
{
    if (_closing) return;
    if (default_action) default_action();
}

void FantasyPopup::close()
{
    if (_closing) return;
    _closing = true;
    AudioManager::play_sfx("menu_close", 0.02f, -6.0f);
    auto tw = tween(this);
    tw->alpha(this, 0.0f, 0.1f);
    tw->callback([this] {
        retain();
        closed.emit();
        removeFromParent();
        release();
    });
}

// ================================================================== ScreenBase
bool ScreenBase::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    return true;
}

Control* ScreenBase::build_frame(const std::string& bg, const std::string& title, const std::string& nav_tab,
                                 std::function<void()> on_back_cb, float dim, bool with_status, const Json& opts)
{
    _back_override = std::move(on_back_cb);
    UIKit::screen_background(this, bg, dim);
    float top = UIKit::safe_top();
    if (with_status)
    {
        status_bar_node = UIKit::status_bar(this);
        top += UIKit::TOP_BAR_H;
    }
    if (!title.empty())
    {
        std::function<void()> cb;
        if (!B(opts, "no_back", false)) cb = [this] { on_back(); };
        header = ScreenHeader::attach(this, title, cb, top + 4, S(opts, "help"));
        top += ScreenHeader::HEIGHT + 12;
    }
    content = Control::create();
    content->set_name("Content");
    content->set_anchors_preset(PRESET_FULL_RECT);
    float bottom = !nav_tab.empty() ? -(NavBar::HEIGHT + UIKit::safe_bottom() + 10) : -(UIKit::safe_bottom() + 14);
    content->set_offsets(14, top, -14, bottom);
    content->set_mouse_filter(MOUSE_IGNORE);
    add(content);
    if (!nav_tab.empty()) nav_bar = NavBar::attach(this, nav_tab);
    return content;
}

void ScreenBase::on_back()
{
    if (SceneRouter::transitioning) return;
    if (_back_override)
    {
        UIManager::sfx("back");
        _back_override();
    }
    else
        SceneRouter::back(back_fallback);
}

bool ScreenBase::require_profile()
{
    if (GM.has_profile() || GM.continue_game()) return true;
    gd::defer([] { SceneRouter::go("main_menu"); });
    return false;
}

// ================================================================== ScreenHeader
ScreenHeader* ScreenHeader::attach(Control* parent, const std::string& title, std::function<void()> on_back, float top,
                                   const std::string& help_topic)
{
    auto h = gd::make<ScreenHeader>();
    h->set_name("Header");
    h->set_mouse_filter(MOUSE_IGNORE);
    h->set_anchors_preset(PRESET_TOP_WIDE);
    h->set_offsets(UIKit::MARGIN - 4, top, -(UIKit::MARGIN - 4), top + HEIGHT);
    parent->add(h);
    auto plank = PanelFrame::make("plank", 10);
    plank->set_anchors_preset(PRESET_FULL_RECT);
    plank->set_mouse_filter(MOUSE_IGNORE);
    h->add(plank);
    auto row = UIKit::hbox(UIKit::SP_L);
    plank->add(row);
    auto left = Control::create();
    left->set_custom_min(Vec2(200, 96));
    left->set_mouse_filter(MOUSE_IGNORE);
    row->add(left);
    if (on_back)
    {
        h->back_button = UIKit::btn("BACK", "quiet", Vec2(200, 96), "assets/icons/back.png");
        h->back_button->set_name("BackButton");
        h->back_button->set_font_size(UIKit::T_BODY);
        h->back_button->h_separation = 6;
        h->back_button->pressed.connect(on_back);
        h->back_button->set_size(Vec2(200, 96));
        left->add(h->back_button);
    }
    h->title_label = UIKit::label(title, UIKit::T_SCREEN, Col("#fff0c0"), gd::ALIGN_CENTER, 10);
    h->title_label->set_name("Title");
    h->title_label->set_h_flags(SIZE_EXPAND_FILL);
    h->title_label->v_align = VALIGN_CENTER;
    h->title_label->set_clip_text(true);
    row->add(h->title_label);
    h->right_slot = UIKit::hbox(UIKit::SP_S);
    h->right_slot->set_custom_min(Vec2(200, 96));
    h->right_slot->alignment = ALIGNMENT_END;
    row->add(h->right_slot);
    if (!help_topic.empty()) h->add_help(help_topic);
    h->resized.connect([h] { UIKit::fit_label(h->title_label, std::max(120.0f, h->size().x - 460.0f), UIKit::T_BODY); });
    return h;
}

void ScreenHeader::add_help(const std::string& topic)
{
    auto b = UIKit::btn("", "quiet", Vec2(96, 96), "assets/icons/help.png");
    b->set_name("HelpButton");
    b->tooltip_text = "Help & Guide";
    b->pressed.connect([topic] { SceneRouter::go("help", {{"topic", topic}}); });
    right_slot->add(b);
}

void ScreenHeader::set_title(const std::string& t)
{
    title_label->set_text(t);
    UIKit::fit_label(title_label, std::max(120.0f, size().x - 460.0f), UIKit::T_BODY);
}

// ================================================================== NavBar
static int g_nav_last_index = -1;

std::string NavBar::tab_of(const std::string& s)
{
    static const std::map<std::string, std::string> T{
        {"home", "home"},   {"world_select", "world_select"}, {"stage_select", "world_select"}, {"tower", "world_select"},
        {"units", "units"}, {"unit_detail", "units"},         {"codex", "units"},               {"squad", "units"},
        {"train", "units"}, {"evolve", "units"},              {"summon", "summon"},             {"menu", "menu"},
        {"inventory", "menu"}, {"missions", "menu"},          {"profile", "menu"},              {"settings", "menu"},
        {"help", "menu"}};
    auto it = T.find(s);
    return it == T.end() ? s : it->second;
}

NavBar* NavBar::attach(Control* parent, const std::string& current_tab)
{
    auto n = gd::make<NavBar>();
    n->set_name("NavBar");
    n->current = tab_of(current_tab);
    n->set_variant("plank", 8);
    n->set_anchors_preset(PRESET_BOTTOM_WIDE);
    n->set_offsets(0, -HEIGHT - UIKit::safe_bottom(), 0, -UIKit::safe_bottom());
    parent->add(n);
    n->build();
    return n;
}

void NavBar::build()
{
    struct Item { const char *text, *icon, *target, *feature; };
    static const Item ITEMS[] = {{"HOME", "home", "home", ""}, {"QUEST", "quest", "world_select", ""},
                                 {"UNITS", "units", "units", "units"}, {"SUMMON", "summon", "summon", "summon"},
                                 {"MENU", "menu", "menu", ""}};
    auto row = UIKit::hbox(8);
    add(row);
    int active_index = -1;
    for (int i = 0; i < 5; ++i)
    {
        const Item& it = ITEMS[i];
        auto b = gd::Button::create(it.text);
        b->set_name(std::string("Nav_") + it.text);
        b->set_icon(std::string("assets/icons/nav_") + it.icon + ".png");
        b->icon_top = true;
        b->icon_max_width = 80;
        b->set_h_flags(SIZE_EXPAND_FILL);
        b->set_custom_min(Vec2(0, 176));
        b->set_font_size(UIKit::T_BODY);
        b->set_outline(8, Col("#120a0c"));
        std::string target = it.target, feature = it.feature;
        bool active = target == current;
        if (active) active_index = i;
        StyleBox sb = UIKit::tex_style(active ? "v2_nav_on.png" : "v2_nav.png", 12, 10);
        sb.content_margin[1] = active ? 8.0f : 16.0f;
        StyleBox pressed_sb = sb;
        pressed_sb.modulate = Col(0.8f, 0.8f, 0.8f);
        pressed_sb.content_margin[1] += 6;
        b->set_style(gd::Button::NORMAL, sb);
        b->set_style(gd::Button::DISABLED, sb);
        b->set_style(gd::Button::HOVER, sb);
        b->set_style(gd::Button::PRESSED, pressed_sb);
        b->set_font_color(gd::Button::NORMAL, active ? UIKit::GOLD : UIKit::MUTED);
        b->set_font_color(gd::Button::HOVER, Col::WHITE);
        b->set_font_color(gd::Button::PRESSED, UIKit::GOLD);
        if (!active) b->set_modulate(Col(0.82f, 0.8f, 0.84f));
        UIKit::hook_sounds(b);
        bool locked = !feature.empty() && !GM.feature_unlocked(feature);
        if (locked)
        {
            b->set_modulate(Col(0.55f, 0.53f, 0.58f));
            auto lk = UIKit::icon("assets/icons/lock.png", 40);
            lk->set_position(Vec2(8, 8));
            b->add(lk);
            std::string text = it.text;
            b->pressed.connect([text, feature] {
                UIManager::toast(capitalize(text == "UNITS" ? "units" : "summon") + " unlocks after clearing " +
                                     GM.feature_unlock_label(feature) + ".",
                                 "info");
            });
        }
        else if (!active)
            b->pressed.connect([target] { SceneRouter::go(target, Json::object(), "tab"); });
        else
            b->pressed.connect([target] {
                if (SceneRouter::current != target) SceneRouter::go(target, Json::object(), "tab");
            });
        row->add(b);
        buttons.push_back(b);
        if (!locked)
        {
            bool show = false;
            if (target == "units") show = GM.units_badge();
            else if (target == "summon") show = GM.summon_badge();
            else if (target == "menu") show = GM.missions_claimable() > 0;
            if (show) UIKit::badge(b);
        }
    }
    if (active_index >= 0) gd::defer([this, active_index] { animate_selection(active_index); });
}

void NavBar::animate_selection(int index)
{
    if (!is_inside_tree()) return;
    auto b = buttons[index];
    if (b->size().x <= 0) return;
    auto marker = ColorRect::create(UIKit::GOLD);
    marker->set_name("NavMarker");
    marker->set_mouse_filter(MOUSE_IGNORE);
    marker->set_size(Vec2(b->size().x * 0.5f, 6));
    b->add(marker);
    float target_x = b->size().x * 0.25f, y = b->size().y - 18, from_x = target_x;
    if (g_nav_last_index >= 0 && g_nav_last_index != index && g_nav_last_index < (int)buttons.size())
    {
        auto pb = buttons[g_nav_last_index];
        from_x = pb->global_position().x - b->global_position().x + pb->size().x * 0.25f;
    }
    marker->set_position(Vec2(from_x, y));
    g_nav_last_index = index;
    auto tw = tween(this);
    tw->set_parallel();
    tw->position_x(marker, target_x, 0.22f).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
    b->set_pivot(b->size() / 2);
    b->setScale(0.94f);
    tw->scale(b, Vec2(1, 1), 0.18f).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
}

// ================================================================== ResourceBar
ResourceBar* ResourceBar::make(const std::string& k, int height)
{
    auto b = gd::make<ResourceBar>();
    b->kind = k;
    b->set_custom_min(Vec2(80, (float)height));
    b->build();
    return b;
}

bool ResourceBar::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    resized.connect([this] { layout_bars(); });
    return true;
}

void ResourceBar::build()
{
    StyleBox fr = StyleBox::tex(kind == "boss" ? "assets/ui/v2_bar_boss.png" : "assets/ui/v2_bar.png", 6, 0);
    _frame = fr.build(size());
    addChild(_frame, -1);
    auto mk = [this](const std::string& n) {
        auto r = TextureRect::create("assets/ui/v2_fill_" + n + ".png");
        r->ignore_size = true;
        r->stretch = STRETCH_SCALE;
        r->set_mouse_filter(MOUSE_IGNORE);
        add(r);
        return r;
    };
    _lag_rect = mk("lag");
    _fill = mk(fill_name());
    layout_bars();
}

std::string ResourceBar::fill_name() const
{
    if (kind == "hp") return _shown > 0.5f ? "hp_high" : _shown > 0.25f ? "hp_mid" : "hp_low";
    if (kind == "burst") return _shown >= 0.999f ? "burst_ready" : "burst";
    return kind;
}

void ResourceBar::layout_bars()
{
    if (!_fill) return;
    if (_frame) _frame->setContentSize(size());
    Vec2 inner(size().x - 12, size().y - 12);
    _fill->set_position(Vec2(6, 6));
    _fill->set_size(Vec2(std::max(inner.x * _shown, 0.0f), std::max(0.0f, inner.y)));
    _lag_rect->set_position(Vec2(6, 6));
    _lag_rect->set_size(Vec2(std::max(inner.x * std::max(_lag, _shown), 0.0f), std::max(0.0f, inner.y)));
    _fill->setVisible(_shown > 0.001f);
    _lag_rect->setVisible(_lag > _shown + 0.001f);
}

void ResourceBar::refresh()
{
    if (_fill) _fill->set_texture("assets/ui/v2_fill_" + fill_name() + ".png");
    layout_bars();
}

void ResourceBar::set_values(float current, float maximum, bool animate)
{
    bool was_full = _shown >= 0.999f;
    max_value = std::max(maximum, 0.0001f);
    value = std::clamp(current, 0.0f, max_value);
    float target = value / max_value;
    if (!is_inside_tree() || !animate)
    {
        _shown = _lag = target;
        refresh();
        return;
    }
    if (_tw) _tw->kill();
    if (_lag_tw) _lag_tw->kill();
    if (target < _shown)
    {
        _lag = std::max(_lag, _shown);
        _shown = target;
        refresh();
        _lag_tw = tween(this);
        _lag_tw->interval(0.25f);
        float from = _lag;
        _lag_tw->method([this](float v) { _lag = v; layout_bars(); }, from, target, 0.3f);
    }
    else
    {
        _tw = tween(this);
        _tw->method([this](float v) { _shown = v; _lag = v; refresh(); }, _shown, target, 0.25f);
    }
    if (kind == "burst" && target >= 0.999f && !was_full) filled.emit();
}

// ================================================================== StatusBar
namespace
{
struct CurrencyInfo { const char *icon, *color, *name, *desc; };
const std::map<std::string, CurrencyInfo>& currencies()
{
    static const std::map<std::string, CurrencyInfo> C{
        {"gems", {"assets/icons/gem.png", "#9ae8ff", "Gems",
                  "Used to summon heroes and refill Energy.\nEarned from first clears, rank-ups, missions and login rewards."}},
        {"gold", {"assets/icons/gold.png", "#ffd35a", "Gold", "Used for training and evolution.\nEarned from every stage and tower floor."}},
        {"shards", {"assets/icons/soul_shard.png", "#d9a8ff", "Soul Shards",
                    "Made from duplicate summons.\nSpend them to raise a hero's Burst level."}}};
    return C;
}
}  // namespace

StatusBar* StatusBar::create()
{
    auto b = gd::make<StatusBar>();
    b->set_name("StatusBar");
    b->set_variant("panel", 12);
    return b;
}

void StatusBar::build()
{
    auto row = UIKit::hbox(UIKit::SP_M);
    add(row);
    auto rank_box = UIKit::hbox(UIKit::SP_S);
    rank_box->set_name("RankBox");
    rank_box->set_h_flags(SIZE_EXPAND_FILL);
    rank_box->add(UIKit::icon("assets/icons/rank.png", 56));
    auto left = UIKit::vbox(2);
    left->set_h_flags(SIZE_EXPAND_FILL);
    left->set_mouse_filter(MOUSE_IGNORE);
    auto r = UIKit::hbox(UIKit::SP_S);
    r->set_mouse_filter(MOUSE_IGNORE);
    r->add(UIKit::label("RANK", UIKit::T_SMALL, UIKit::SKY, gd::ALIGN_LEFT, 5));
    auto rank_l = UIKit::label(std::to_string(GM.rank()), UIKit::T_NAME, UIKit::TEXT, gd::ALIGN_LEFT, 7);
    rank_l->set_name("RankValue");
    r->add(rank_l);
    left->add(r);
    auto xb = ResourceBar::make("xp", 20);
    xb->set_h_flags(SIZE_EXPAND_FILL);
    int rank_xp = I(O(GM.profile, "player"), "rank_xp", 0);
    int need = Progression::rank_xp_to_next(GM.rank());
    xb->set_values((float)rank_xp, (float)need, false);
    left->add(xb);
    rank_box->add(left);
    row->add(rank_box);
    UIKit::on_tap(rank_box, [] { SceneRouter::go("profile"); });
    UIManager::attach_tooltip(rank_box, "Rank " + std::to_string(GM.rank()),
                              "EXP " + UIKit::format_number(rank_xp) + " / " + UIKit::format_number(need) +
                                  "\nRank up to refill Energy and raise its maximum.");
    auto en = chip("assets/icons/energy.png", "EnergyChip", 250);
    auto ev = UIKit::vbox(0);
    ev->set_mouse_filter(MOUSE_IGNORE);
    _energy_l = UIKit::label("", UIKit::T_BODY, Col("#ffe07a"), gd::ALIGN_LEFT, 6);
    _energy_l->set_name("EnergyValue");
    _timer_l = UIKit::label("", UIKit::T_SMALL, UIKit::MUTED, gd::ALIGN_LEFT, 4);
    ev->add(_energy_l);
    ev->add(_timer_l);
    en->children()[0]->add(ev);
    row->add(en);
    UIKit::on_tap(en, [this] { energy_info(); });
    row->add(currency_chip("gems", "GemsChip", 190));
    row->add(currency_chip("gold", "GoldChip", 230));
    refresh();
    schedule([this](float) { refresh_energy(); }, 1.0f, "energy_tick");
    gd::listen(this, GM.gold_changed, [this](int) { refresh(); });
    gd::listen(this, GM.gems_changed, [this](int) { refresh(); });
    gd::listen(this, GM.energy_changed, [this](int, int) { refresh_energy(); });
    gd::listen(this, GM.profile_changed, [this]() { refresh(); });
}

void StatusBar::show_currency(const std::string& key)
{
    if (!currencies().count(key) || !_chips.count(_third)) return;
    Chip c = _chips[_third];
    _chips.erase(_third);
    _third = key;
    const auto& info = currencies().at(key);
    std::string nm = key == "gems" ? "GemsChip" : key == "shards" ? "ShardsChip" : "GoldChip";
    c.chip->set_name(nm);
    if (auto ic = dynamic_cast<gd::TextureRect*>(c.chip->children()[0]->children()[0])) ic->set_texture(info.icon);
    c.label->set_name(nm.substr(0, nm.size() - 4) + "Value");
    c.label->set_color(Col(info.color));
    c.shown = value_of(key);
    _chips[key] = c;
    UIManager::attach_tooltip(c.chip, info.name, info.desc, info.icon);
    refresh();
}

PanelFrame* StatusBar::chip(const std::string& icon_path, const std::string& name, int w)
{
    auto p = PanelFrame::make("inset", 8);
    p->set_name(name);
    p->set_min_w((float)w);
    auto h = UIKit::hbox(6);
    h->set_mouse_filter(MOUSE_IGNORE);
    p->add(h);
    h->add(UIKit::icon(icon_path, 48));
    return p;
}

PanelFrame* StatusBar::currency_chip(const std::string& key, const std::string& name, int w)
{
    const auto& info = currencies().at(key);
    auto c = chip(info.icon, name, w);
    auto l = UIKit::label("", UIKit::T_CURRENCY, Col(info.color), gd::ALIGN_RIGHT, 6);
    l->set_name(name.substr(0, name.size() - 4) + "Value");
    l->set_h_flags(SIZE_EXPAND_FILL);
    c->children()[0]->add(l);
    c->set_pivot(Vec2(w / 2.0f, 50));
    _chips[key] = {c, l, value_of(key), nullptr};
    UIManager::attach_tooltip(c, info.name, info.desc, info.icon);
    return c;
}

long long StatusBar::value_of(const std::string& key) const
{
    if (key == "gems") return GM.gems();
    if (key == "gold") return GM.gold();
    if (key == "shards") return GM.soul_shards();
    return 0;
}

void StatusBar::refresh()
{
    if (!GM.has_profile()) return;
    refresh_energy();
    for (auto& [k, c] : _chips) update_chip(k);
}

void StatusBar::refresh_energy()
{
    if (!GM.has_profile()) return;
    int cur = GM.energy(), mx = GM.max_energy();
    _energy_l->set_text(std::to_string(cur) + "/" + std::to_string(mx));
    _timer_l->set_text(cur >= mx ? "FULL" : "+1 in " + UIKit::format_time(GM.energy_seconds_to_next()));
}

void StatusBar::update_chip(const std::string& key)
{
    Chip& c = _chips[key];
    long long target = value_of(key);
    const auto& info = currencies().at(key);
    c.chip->meta["tip"] = {std::string(info.name) + "  " + UIKit::format_number(target), info.desc, info.icon};
    long long from = c.shown;
    if (from == target || !is_inside_tree() || !is_visible_in_tree())
    {
        c.shown = target;
        c.label->set_text(UIKit::format_compact(target));
        return;
    }
    if (c.tw) c.tw->kill();
    bool gain = target > from;
    auto l = c.label;
    c.tw = tween(this);
    c.tw->method([l](float x) { l->set_text(UIKit::format_compact((long long)std::llround(x))); }, (float)from, (float)target, 0.45f);
    c.shown = target;
    auto chip_c = c.chip;
    chip_c->set_modulate(gain ? Col(0.75f, 1.0f, 0.75f) : Col(1.0f, 0.7f, 0.65f));
    chip_c->setScale(1.06f);
    auto tw2 = tween(this);
    tw2->set_parallel();
    tw2->modulate(chip_c, Col::WHITE, 0.45f);
    tw2->scale(chip_c, Vec2(1, 1), 0.2f).trans(gd::TRANS_QUAD);
    if (gain && key == "gold") UIManager::sfx("coin", -8.0f);
}

void StatusBar::energy_info()
{
    auto p = FantasyPopup::open(parent_control(), "ENERGY", 860);
    p->set_name("EnergyInfo");
    std::vector<std::string> lines = {
        "Entering a stage or tower floor costs Energy.",
        "You recover 1 Energy every " + std::to_string(I(DB.balance("energy", "regen_seconds"), 180) / 60) +
            " minutes, even while the game is closed.",
        "Every Rank Up refills your Energy, and Max Energy grows as your Rank rises.",
        "Current: " + std::to_string(GM.energy()) + " / " + std::to_string(GM.max_energy())};
    for (auto& l : lines)
    {
        auto w = UIKit::wrap_label(l, UIKit::T_BODY);
        w->set_min_w(780);
        p->content->add(w);
    }
    auto ok = UIKit::btn("OK", "primary", Vec2(300, 110));
    ok->set_h_flags(SIZE_SHRINK_CENTER);
    ok->pressed.connect([p] { p->close(); });
    p->default_action = [p] { p->close(); };
    p->tap_outside_closes = true;
    p->content->add(ok);
}

// ================================================================== CoachMark
CoachMark* CoachMark::show_on(Control* parent, Control* target, const std::string& text, const std::string& gesture, bool block)
{
    auto c = gd::make<CoachMark>();
    c->_blocking = block;
    c->_target = target;
    c->_gesture = gesture;
    c->set_name("CoachMark");
    c->set_anchors_preset(PRESET_FULL_RECT);
    c->set_mouse_filter(MOUSE_IGNORE);
    c->set_z(60);
    target->tree_exiting.connect([c] { c->_target = nullptr; });
    for (int i = 0; i < 4; ++i)
    {
        auto d = ColorRect::create(Col(0.02f, 0.01f, 0.04f, block ? 0.72f : 0.45f));
        d->set_mouse_filter(block ? MOUSE_STOP : MOUSE_IGNORE);
        c->add(d);
        c->_dims.push_back(d);
    }
    c->_border = Panel::create(StyleBox::flat(Col::CLEAR, UIKit::GOLD, 6));
    c->_border->set_mouse_filter(MOUSE_IGNORE);
    c->add(c->_border);
    std::string hand = gesture == "up" ? "gesture_up" : gesture == "down" ? "gesture_down" : "hand";
    c->_hand = UIKit::icon("assets/icons/" + hand + ".png", 96);
    c->_hand->set_size(Vec2(96, 96));
    c->add(c->_hand);
    c->_plate = PanelFrame::make("plank", 16);
    c->_plate->set_mouse_filter(MOUSE_IGNORE);
    auto l = UIKit::label(text, UIKit::T_NAME, Col("#fff0c0"), gd::ALIGN_CENTER, 8);
    l->set_autowrap(true);
    l->set_min_w(820);
    c->_plate->add(l);
    c->add(c->_plate);
    parent->add(c);
    c->set_alpha(0);
    tween(c)->alpha(c, 1.0f, 0.2f);
    AudioManager::play_sfx("menu_open", 0.0f, -6.0f);
    c->scheduleUpdate();
    return c;
}

void CoachMark::update(float dt)
{
    if (_done) return;
    if (!_target || !_target->is_visible_in_tree())
    {
        finish();
        return;
    }
    _t += dt;
    Rect2 r = _target->global_rect();
    Vec2 origin = global_position();
    r.position = r.position - origin - Vec2(8, 8);
    r.size = r.size + Vec2(16, 16);
    Vec2 vp = size();
    _dims[0]->set_position(Vec2::ZERO);
    _dims[0]->set_size(Vec2(vp.x, std::max(r.position.y, 0.0f)));
    _dims[1]->set_position(Vec2(0, r.end().y));
    _dims[1]->set_size(Vec2(vp.x, std::max(vp.y - r.end().y, 0.0f)));
    _dims[2]->set_position(Vec2(0, r.position.y));
    _dims[2]->set_size(Vec2(std::max(r.position.x, 0.0f), r.size.y));
    _dims[3]->set_position(Vec2(r.end().x, r.position.y));
    _dims[3]->set_size(Vec2(std::max(vp.x - r.end().x, 0.0f), r.size.y));
    _border->set_position(r.position);
    _border->set_size(r.size);
    _border->set_alpha(0.6f + 0.4f * std::sin(_t * 6.0f));
    Vec2 ps = _plate->combined_min();
    _plate->set_size(ps);
    bool above = r.position.y - ps.y - 40 > 260.0f;
    _plate->set_position(Vec2((vp.x - ps.x) / 2, above ? r.position.y - ps.y - 30 : r.end().y + 30));
    Vec2 c = r.center();
    if (_gesture == "up" || _gesture == "down")
    {
        float k = std::fmod(_t, 1.0f);
        _hand->set_position(c + (_gesture == "up" ? Vec2(-48, 40 - k * 140) : Vec2(-48, -120 + k * 140)));
        _hand->set_alpha(1.0f - k * 0.7f);
    }
    else
        _hand->set_position(c + Vec2(10, 10 - std::abs(std::sin(_t * 5.0f)) * 24));
}

void CoachMark::finish()
{
    if (_done) return;
    _done = true;
    for (auto d : _dims) d->set_mouse_filter(MOUSE_IGNORE);
    auto tw = tween(this);
    tw->alpha(this, 0.0f, 0.15f);
    tw->callback([this] {
        retain();
        finished.emit();
        removeFromParent();
        release();
    });
}
