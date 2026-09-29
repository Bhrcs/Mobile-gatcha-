// Shared widgets: CinderTabs, CinderSwitch, ElementChart, SettingsPanel
// (scripts/ui/components/cinder_tabs.gd, cinder_switch.gd, element_chart.gd, scripts/ui/settings_panel.gd).
#include "screens/Screens.h"

using namespace gd;

// ================================================================== CinderTabs
static void style_tabs(CinderTabs* t)
{
    for (size_t i = 0; i < t->tabs.size(); ++i)
    {
        FantasyButton* b = t->tabs[i];
        bool on = (int)i == t->selected;
        StyleBox sb = UIKit::tex_style(on ? "p5_tab_on.png" : "p5_tab.png", 12, 10);
        sb.content_margin[1] = on ? 6 : 12;
        for (auto st : {Button::NORMAL, Button::HOVER, Button::PRESSED, Button::DISABLED}) b->set_style(st, sb);
        b->set_font_color(Button::NORMAL, on ? UIKit::GOLD : UIKit::MUTED);
        b->set_font_color(Button::HOVER, on ? UIKit::GOLD : Col::WHITE);
        b->set_font_color(Button::PRESSED, UIKit::GOLD);
    }
}

CinderTabs* CinderTabs::make(const std::vector<std::string>& tab_labels, int current, std::function<void(int)> on_change, int height)
{
    auto t = gd::make<CinderTabs>();
    t->vertical = false;
    t->set_name("Tabs");
    t->labels = tab_labels;
    t->selected = current;
    t->separation = UIKit::SP_S;
    for (size_t i = 0; i < tab_labels.size(); ++i)
    {
        auto b = gd::make<FantasyButton>();   // FantasyButton already plays the hover/click sounds (hook_sounds)
        std::string n = upper(tab_labels[i]);
        std::replace(n.begin(), n.end(), ' ', '_');
        b->set_name("Tab_" + n);
        b->set_text(tab_labels[i]);
        b->set_custom_min(Vec2(0, (float)height));
        b->set_h_flags(SIZE_EXPAND_FILL);
        if (b->label()) b->label()->set_clip_text(true);
        b->set_font_size(height >= 80 ? UIKit::T_BODY : UIKit::T_SMALL);
        b->set_outline(8, Col("#140806"));
        int idx = (int)i;
        b->pressed.connect([t, idx] { t->select(idx); });
        t->add(b);
        t->tabs.push_back(b);
    }
    if (on_change) t->tab_changed.connect(on_change);
    style_tabs(t);
    return t;
}

void CinderTabs::select(int i, bool emit)
{
    if (i == selected && emit) return;
    selected = i;
    style_tabs(this);
    FantasyButton* b = tabs[i];
    b->set_pivot(b->size() / 2);
    b->setScale(0.95f);
    gd::tween(this)->scale(b, Vec2(1, 1), 0.12f).trans(TRANS_QUAD);
    if (emit) tab_changed.emit(i);
}

void CinderTabs::set_badge(int i, const std::string& text)
{
    FantasyButton* b = tabs[i];
    if (auto old = b->find("Badge")) old->removeFromParent();
    if (!text.empty()) UIKit::badge(b, text);
}

// ================================================================== CinderSwitch
static void refresh_switch(CinderSwitch* s)
{
    auto art = static_cast<TextureRect*>(s->find("Art"));
    auto text = static_cast<Label*>(s->find("Text"));
    art->set_texture(s->on ? "assets/ui/p5_switch_on.png" : "assets/ui/p5_switch_off.png");
    text->set_text(s->on ? "ON" : "OFF");
    text->set_color(s->on ? UIKit::GOOD : s->hovered() ? UIKit::TEXT : UIKit::MUTED);
}

CinderSwitch* CinderSwitch::make(bool start_on, std::function<void(bool)> on_toggle)
{
    auto s = gd::make<CinderSwitch>();
    s->on = start_on;
    s->set_custom_min(Vec2(250, UIKit::TOUCH_MIN));
    auto row = UIKit::hbox(UIKit::SP_M);
    row->set_anchors_preset(PRESET_FULL_RECT);
    row->set_mouse_filter(MOUSE_IGNORE);
    s->add(row);
    auto text = UIKit::label("", UIKit::T_BODY, UIKit::MUTED, ALIGN_LEFT, 8);
    text->set_name("Text");
    text->v_align = VALIGN_CENTER;
    text->set_h_flags(SIZE_EXPAND_FILL);
    row->add(text);
    auto art = TextureRect::create();   // switch art at 2x
    art->set_name("Art");
    art->ignore_size = true;
    art->set_custom_min(Vec2(144, 72));
    art->set_v_flags(SIZE_SHRINK_CENTER);
    art->set_mouse_filter(MOUSE_IGNORE);
    row->add(art);
    if (on_toggle) s->toggled_to.connect(on_toggle);
    s->pressed.connect([s] {
        s->set_on(!s->on);
        UIManager::sfx("toggle", -4.0f);
        s->toggled_to.emit(s->on);
    });
    s->mouse_entered.connect([s] { refresh_switch(s); });
    s->mouse_exited.connect([s] { refresh_switch(s); });
    refresh_switch(s);
    return s;
}

void CinderSwitch::set_on(bool v)
{
    on = v;
    refresh_switch(this);
}

// ================================================================== ElementChart
namespace ElementChart
{
static const char* ORDER[] = {"fire", "nature", "water"};   // fire beats nature beats water beats fire
static const Vec2 SIZE(620, 520);

Control* make()
{
    auto c = Control::create();
    c->set_name("ElementChart");
    c->set_custom_min(SIZE);
    c->set_mouse_filter(MOUSE_IGNORE);
    Vec2 ctr = SIZE / 2 + Vec2(0, 20);
    float r = 190;
    std::map<std::string, Vec2> pos{{"fire", ctr + Vec2(0, -r)}, {"nature", ctr + Vec2(r * 0.87f, r * 0.5f)},
                                    {"water", ctr + Vec2(-r * 0.87f, r * 0.5f)}};
    // arrows (Godot _draw: behind the children)
    auto holder = Node2D::create();
    auto dn = ax::DrawNode::create();
    holder->add2d(dn, Vec2::ZERO);
    c->add(holder);
    for (int i = 0; i < 3; ++i)
    {
        Vec2 a = pos[ORDER[i]], b = pos[ORDER[(i + 1) % 3]];
        Vec2 dir = (b - a).getNormalized();
        Vec2 s = a + dir * 92, e = b - dir * 92;
        Col col = Col(DB.element_color(ORDER[i])).lightened(0.2f);
        dn->drawSegment(p2(s), p2(e), 7, Col(0, 0, 0, 0.6f).c4f());
        dn->drawSegment(p2(s), p2(e), 4, col.c4f());
        Vec2 n(-dir.y, dir.x);
        ax::Vec2 head[3] = {p2(e + dir * 18), p2(e - dir * 22 + n * 20), p2(e - dir * 22 - n * 20)};
        dn->drawSolidPoly(head, 3, col.c4f());
    }
    for (auto el : ORDER)
    {
        auto box = UIKit::vbox(2);
        box->set_mouse_filter(MOUSE_IGNORE);
        auto o = UIKit::orb(el, 96);
        o->set_h_flags(SIZE_SHRINK_CENTER);
        box->add(o);
        box->add(UIKit::label(upper(DB.element_name(el)), UIKit::T_BODY, Col(DB.element_color(el)).lightened(0.3f), ALIGN_CENTER, 6));
        c->add(box);
        box->set_size(box->combined_min());
        box->set_position(pos[el] - Vec2(box->size().x / 2, 52));
    }
    auto mid = UIKit::label("BEATS", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER, 5);
    c->add(mid);
    mid->set_size(mid->combined_min());
    mid->set_position(ctr - mid->size() / 2 + Vec2(0, 10));
    return c;
}

FantasyPopup* popup(Control* parent)
{
    auto p = FantasyPopup::open(parent, "ELEMENTS", 900);
    p->set_name("ElementPopup");
    auto chart = make();
    chart->set_h_flags(SIZE_SHRINK_CENTER);
    p->content->add(chart);
    for (auto& line : explanation())
    {
        auto l = UIKit::wrap_label(line, UIKit::T_BODY);
        l->h_align = ALIGN_CENTER;
        l->set_min_w(820);
        p->content->add(l);
    }
    auto ok = UIKit::btn("OK", "primary", Vec2(300, 110));
    ok->set_name("ElementOK");
    ok->set_h_flags(SIZE_SHRINK_CENTER);
    ok->pressed.connect([p] { p->close(); });
    p->content->add(ok);
    p->default_action = [p] { p->close(); };
    p->tap_outside_closes = true;
    return p;
}

std::vector<std::string> explanation()
{
    int strong = (int)std::lround((F(DB.element_config, "strong_multiplier", 1.25) - 1.0) * 100.0);
    int weak = (int)std::lround((1.0 - F(DB.element_config, "weak_multiplier", 0.75)) * 100.0);
    return {UIKit::fmt("Attacking the element you beat deals +%d%% damage.", strong),
            UIKit::fmt("Attacking the element that beats you deals -%d%% damage.", weak)};
}
}  // namespace ElementChart

// ================================================================== SettingsPanel
namespace SettingsPanel
{
#if AX_TARGET_PLATFORM == AX_PLATFORM_ANDROID || AX_TARGET_PLATFORM == AX_PLATFORM_IOS
static const bool MOBILE = true;
#else
static const bool MOBILE = false;
#endif

// the account page only makes sense once a journey exists
static std::vector<std::string> categories()
{
    std::vector<std::string> c{"AUDIO", "GAMEPLAY", "GRAPHICS", "ACCOUNT"};
    if (!GM.has_profile()) c.pop_back();
    return c;
}

// {panel, row}
static std::pair<Control*, BoxContainer*> row(const std::string& title, const std::string& desc = "")
{
    auto panel = PanelFrame::make("inset", 14);
    auto r = UIKit::hbox(UIKit::SP_L);
    panel->add(r);
    auto col = UIKit::vbox(2);
    col->set_h_flags(SIZE_EXPAND_FILL);
    col->add(UIKit::label(title, UIKit::T_BODY, UIKit::TEXT, ALIGN_LEFT, 6));
    if (!desc.empty()) col->add(UIKit::wrap_label(desc, UIKit::T_SMALL, UIKit::MUTED));
    r->add(col);
    return {panel, r};
}

static Label* note(const std::string& text)
{
    auto l = UIKit::wrap_label(text, UIKit::T_SMALL, UIKit::MUTED);
    l->h_align = ALIGN_CENTER;
    return l;
}

static Control* slider_row(const std::string& title, const std::string& key)
{
    auto [panel, r] = row(title);
    auto s = HSlider::create(0.0f, 1.0f, 0.05f);
    s->set_name("Slider_" + key);
    s->set_value((float)F(GM.settings, key, 0.8), false);
    s->set_custom_min(Vec2(360, 56));
    s->set_v_flags(SIZE_SHRINK_CENTER);
    r->add(s);
    auto pct = UIKit::label(UIKit::fmt("%d%%", (int)(s->value() * 100)), UIKit::T_BODY, UIKit::GOLD, ALIGN_RIGHT, 6);
    pct->set_min_w(100);
    r->add(pct);
    s->value_changed.connect([pct, key](float v) {
        pct->set_text(UIKit::fmt("%d%%", (int)(v * 100)));
        GM.set_setting(key, v);
    });
    // one test sound when the player lets go (HSlider has no drag_ended: use the release event)
    s->gui_input.connect([](InputEvent& e) {
        if (e.released()) UIManager::sfx("press", -4.0f);
    });
    return panel;
}

static Control* toggle_row(const std::string& title, const std::string& key, const std::string& desc = "")
{
    auto [panel, r] = row(title, desc);
    bool on = B(GM.settings, key, key != "fullscreen" && key != "auto_battle" && key != "reduce_motion");
    auto sw = CinderSwitch::make(on, [key](bool now) { GM.set_setting(key, now); });
    sw->set_name("Toggle_" + key);
    r->add(sw);
    return panel;
}

static Control* speed_row()
{
    auto [panel, r] = row("Default Battle Speed", "Speed used when a battle starts.");
    bool fast = F(GM.settings, "battle_speed", 1.0) >= 1.5;
    auto seg = CinderTabs::make({"1x", "2x"}, fast ? 1 : 0, [](int i) { GM.set_setting("battle_speed", i == 1 ? 2.0 : 1.0); }, 80);
    seg->set_name("Toggle_battle_speed");
    seg->set_min_w(250);
    r->add(seg);
    return panel;
}

static Control* margin_row()
{
    auto [panel, r] = row("Screen Margins", "Extra space at the top and bottom for phones with a notch or rounded corners.");
    static const char* names[] = {"NONE", "SMALL", "MEDIUM", "LARGE"};
    int cur = std::clamp(I(GM.settings, "safe_area", 0), 0, 3);
    auto minus = UIKit::btn("", "quiet", Vec2(88, 88), "assets/icons/minus.png");
    minus->set_name("MarginMinus");
    auto val = UIKit::label(names[cur], UIKit::T_BODY, UIKit::GOLD, ALIGN_CENTER, 6);
    val->set_min_w(150);
    auto plus = UIKit::btn("", "quiet", Vec2(88, 88), "assets/icons/plus.png");
    plus->set_name("MarginPlus");
    auto change = [val](int d) {
        int n = std::clamp(I(GM.settings, "safe_area", 0) + d, 0, 3);
        GM.set_setting("safe_area", n);
        val->set_text(names[n]);
        UIManager::toast("Screen margins apply when a screen opens.", "info");
    };
    minus->pressed.connect([change] { change(-1); });
    plus->pressed.connect([change] { change(1); });
    r->add(minus);
    r->add(val);
    r->add(plus);
    return panel;
}

static Control* tutorial_row()
{
    auto [panel, r] = row("Tutorial Tips", "Show the first-time hints and guides again.");
    auto reset = UIKit::btn("RESET", "quiet", Vec2(220, 88));
    reset->set_name("ResetTutorial");
    reset->pressed.connect([reset] {
        GM.reset_tutorial();
        reset->set_disabled(true);
        reset->set_text("DONE");
        UIManager::toast("Tutorial tips will show again.", "success");
    });
    r->add(reset);
    return panel;
}

static void account(BoxContainer* v)
{
    auto [panel, r] = row(GM.player_name(), UIKit::fmt("Rank %d  -  %d heroes  -  %d stars", GM.rank(), (int)GM.units().size(), GM.all_stars()));
    auto prof = UIKit::btn("PROFILE", "secondary", Vec2(240, 88));
    prof->set_name("OpenProfile");
    prof->pressed.connect([] { SceneRouter::go("profile"); });
    r->add(prof);
    v->add(panel);
    auto s = row("Save Data", "Progress is saved automatically after every battle, summon and upgrade.");
    s.second->add(UIKit::icon("assets/icons/check.png", 48));
    v->add(s.first);
    auto t = row("Title Screen", "Return to the title screen. Your progress stays saved.");
    auto tb = UIKit::btn("TITLE", "quiet", Vec2(220, 88));
    tb->set_name("ToTitle");
    tb->pressed.connect([] { SceneRouter::go("main_menu"); });
    t.second->add(tb);
    v->add(t.first);
    v->add(note("Cinderbound  v0.6.0"));
}

// Popup version (title screen, battle). `category` picks the first tab.
FantasyPopup* open(Control* parent, int category)
{
    auto p = FantasyPopup::open(parent, "SETTINGS", 960);
    p->set_name("SettingsPopup");
    auto body = UIKit::vbox(UIKit::SP_L);
    body->set_custom_min(Vec2(900, 700));
    auto tabs = CinderTabs::make(categories(), category, [body, parent](int i) { fill(body, categories()[i], parent); }, 88);
    p->content->add(tabs);
    p->content->add(body);
    fill(body, categories()[category], parent);
    auto close = UIKit::btn("CLOSE", "primary", Vec2(320, 110));
    close->set_name("CloseSettings");
    close->set_h_flags(SIZE_SHRINK_CENTER);
    p->content->add(close);
    close->pressed.connect([p] { p->close(); });
    p->default_action = [p] { p->close(); };
    return p;
}

// Rebuilds `v` with the rows of one category.
void fill(BoxContainer* v, const std::string& category, Control* /*host*/)
{
    v->clear_children();
    if (category == "AUDIO")
    {
        v->add(slider_row("Master Volume", "master_volume"));
        v->add(slider_row("Music Volume", "music_volume"));
        v->add(slider_row("Effects Volume", "sfx_volume"));
        v->add(note("Effects include button sounds and battle impacts."));
    }
    else if (category == "GAMEPLAY")
    {
        v->add(speed_row());
        v->add(toggle_row("Start Battles on AUTO", "auto_battle", "Heroes act on their own until you turn AUTO off."));
        v->add(toggle_row("Damage Numbers", "damage_numbers", "Show damage and healing values in battle."));
        if (MOBILE) v->add(toggle_row("Vibration", "haptics", "Short vibrations for bursts, summons and evolutions."));
        if (GM.has_profile()) v->add(tutorial_row());
    }
    else if (category == "GRAPHICS")
    {
        if (!MOBILE) v->add(toggle_row("Fullscreen", "fullscreen", "F11 also toggles fullscreen."));
        v->add(toggle_row("Screen Shake", "screen_shake", "Camera shake on heavy hits and bursts."));
        v->add(toggle_row("Battle Effects", "battle_effects", "Particles, flashes and burst cut-ins."));
        v->add(toggle_row("Reduce Motion", "reduce_motion", "Menus switch without sliding."));
        v->add(margin_row());
    }
    else if (category == "ACCOUNT")
        account(v);
}
}  // namespace SettingsPanel
