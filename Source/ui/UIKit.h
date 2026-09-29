#pragma once
// Cinderbound UI kit: ports of scripts/ui/ui_kit.gd and the shared components
// (PanelFrame, FantasyButton, FantasyPopup, ScreenBase, ScreenHeader, NavBar,
// StatusBar, ResourceBar, CoachMark). Names and defaults follow the Godot code.
#include "app/App.h"

using gd::Col;
using gd::Vec2;
class FantasyButton;
class PanelFrame;
class FantasyPopup;
class StatusBar;
class NavBar;

namespace UIKit
{
// palette & type scale
extern const Col TEXT, MUTED, GOLD, EMBER, DANGER, GOOD, SKY, SHADOW;
constexpr int T_DISPLAY = 120, T_TITLE = 80, T_HEAD = 50, T_NAME = 40, T_BODY = 30, T_SMALL = 20;
constexpr int T_SCREEN = T_HEAD, T_PANEL = T_BODY, T_UNIT = T_NAME, T_BUTTON = T_NAME, T_BUTTON_S = T_BODY,
              T_CURRENCY = T_BODY, T_META = T_SMALL;
constexpr int SP_XS = 4, SP_S = 8, SP_M = 12, SP_L = 16, SP_XL = 24, SP_XXL = 32, MARGIN = 16, TOUCH_MIN = 88;
constexpr int TOP_BAR_H = 150, NAV_H = 200;
const std::string UI_DIR = "assets/ui/";

std::string button_style(const std::string& kind);   // primary->ember, secondary->steel, quiet->stone, reward->gold, danger->crimson
gd::StyleBox tex_style(const std::string& file, float margin, float content);   // file under assets/ui/
gd::StyleBox flat(const Col& c, const Col& border = Col::CLEAR, float border_w = 0);

float safe_top();
float safe_bottom();

int snap_text(int size);
gd::Label* label(const std::string& text, int size = T_BODY, const Col& color = TEXT, gd::HAlign align = gd::ALIGN_LEFT, int outline = 0);
gd::Label* heading(const std::string& text, int size = T_HEAD, const Col& color = GOLD);
gd::Label* wrap_label(const std::string& text, int size = T_BODY, const Col& color = TEXT);
gd::Control* title_plate(const std::string& text, int size = T_HEAD);
gd::TextureRect* separator();
gd::PanelContainer* tag(const std::string& text, const Col& color);

FantasyButton* btn(const std::string& text, const std::string& kind = "primary", Vec2 min_size = Vec2(320, 110),
                         const std::string& icon_path = "");
FantasyButton* button(const std::string& text, const std::string& icon_path = "", Vec2 min_size = Vec2(320, 110),
                            const std::string& style = "steel");
void hook_sounds(gd::BaseButton* b);
PanelFrame* panel(const std::string& style = "panel");

int snap_icon(int size);
gd::TextureRect* icon(const std::string& path, int size = 48);
gd::TextureRect* tex_rect(ax::Texture2D* tex, Vec2 size);
gd::TextureRect* orb(const std::string& element, int size = 48);
gd::BoxContainer* stars(int count, int size = 32);
gd::BoxContainer* element_badge(const std::string& element, int size = T_BODY);
gd::Control* portrait_art(const Json& char_def, Vec2 box);
gd::Control* portrait_frame(const Json& char_def, int size = 192, bool show_orb = true);
gd::Particles* sparkle(gd::Control* parent, gd::Rect2 area, const Col& color = Col("#fff0b0"), int amount = 6);

inline gd::BoxContainer* hbox(int sep = 12) { return gd::hbox(sep); }
inline gd::BoxContainer* vbox(int sep = 12) { return gd::vbox(sep); }
gd::Control* spacer(bool h_expand = true, bool v_expand = false);
gd::BoxContainer* stat_row(const std::string& name, const std::string& value, int size = T_BODY, const Col& value_color = TEXT);
gd::PanelContainer* strip(const std::string& title, const std::string& value, const Col& color);

gd::TextureRect* screen_background(gd::Control* parent, const std::string& bg_name, float dim = 0.35f);
gd::TextureRect* stone_rect();
StatusBar* status_bar(gd::Control* parent);
gd::Control* badge(gd::Control* c, const std::string& text = "!");
NavBar* nav_bar(gd::Control* parent, const std::string& current);

// legacy popup helpers
FantasyPopup* modal(gd::Control* parent, const std::string& title, int min_width = 940);
FantasyPopup* confirm(gd::Control* parent, const std::string& text, std::function<void()> on_yes,
                            const std::string& yes = "CONFIRM", const std::string& no = "CANCEL",
                            std::function<void()> on_no = nullptr, bool danger = false);
FantasyPopup* message(gd::Control* parent, const std::string& title, const std::string& text, const std::string& ok = "OK");
void toast(gd::Control* parent, const std::string& text, const Col& color = TEXT);

void on_tap(gd::Control* c, std::function<void()> cb);   // tap on a non-button control
std::string format_compact(long long n);                 // 999 / 9,999 / 12.4K / 1.3M
std::string format_number(long long n);                  // 1,234,567
std::string format_time(int seconds);                    // 2:05 / 1:06:40
gd::Label* fit_label(gd::Label* l, float max_width, int min_size = T_SMALL);
std::string fmt(const char* f, ...);                     // printf-style helper ("%d/%d")
}  // namespace UIKit

// ------------------------------------------------------------------ components
// Layered panel. Variants: panel, inset, plank, boss, enemy, slot, card_<element>[_lit], rarity_<n>.
class PanelFrame : public gd::PanelContainer
{
public:
    static PanelFrame* make(const std::string& variant = "panel", int pad = -1);
    void set_variant(const std::string& v, int pad = -1);
    std::string variant = "panel";
};

// Raised metal button. Styles: ember (primary), steel, gold, stone, crimson.
class FantasyButton : public gd::Button
{
public:
    static FantasyButton* make(const std::string& text, const std::string& style = "steel", Vec2 min_size = Vec2(320, 110),
                               const std::string& icon_path = "");
    bool init() override;
    void apply_style(const std::string& style);
    void set_selected(bool on);
    bool selected = false;
    std::string style_name = "steel";
    void add_shine(float period = 2.8f);
    std::string kind;   // semantic kind given to UIKit::btn
private:
    gd::TweenRef _tw;
};

// Modal popup: dim + framed panel; `content` is a VBox to fill.
class FantasyPopup : public gd::Control
{
public:
    static FantasyPopup* open(gd::Control* parent, const std::string& title = "", int width = 940, const std::string& variant = "panel");
    gd::BoxContainer* content = nullptr;
    PanelFrame* panel = nullptr;
    gd::ColorRect* dim = nullptr;
    std::function<void()> cancel_action;    // Esc / tap outside (default: close)
    std::function<void()> default_action;   // Enter
    bool tap_outside_closes = false;
    Signal<> closed;
    void cancel();
    void confirm_default();
    void close();
    bool closing() const { return _closing; }
private:
    bool _closing = false;
};

// Base for every menu screen (see scripts/ui/components/screen_base.gd).
class ScreenBase : public gd::Control
{
public:
    bool init() override;
    virtual void ready() {}                  // build the screen (Godot _ready); params in SceneRouter::params
    virtual void on_back();                  // Esc / header Back
    virtual bool on_key(int /*key*/) { return false; }   // screen-specific keys first (true = handled)
    gd::Control* build_frame(const std::string& bg, const std::string& title, const std::string& nav_tab,
                             std::function<void()> on_back = nullptr, float dim = 0.45f, bool with_status = true,
                             const Json& opts = Json::object());   // opts: help, no_back
    bool require_profile();
    gd::Control* content = nullptr;
    StatusBar* status_bar_node = nullptr;
    class ScreenHeader* header = nullptr;
    NavBar* nav_bar = nullptr;
    std::string back_fallback = "home";
    const Json& params() const { return SceneRouter::params; }
private:
    std::function<void()> _back_override;
};

class ScreenHeader : public gd::Control
{
public:
    static constexpr int HEIGHT = 120;
    static ScreenHeader* attach(gd::Control* parent, const std::string& title, std::function<void()> on_back, float top,
                                const std::string& help_topic = "");
    gd::Label* title_label = nullptr;
    FantasyButton* back_button = nullptr;
    gd::BoxContainer* right_slot = nullptr;
    void add_help(const std::string& topic);
    void set_title(const std::string& t);
};

class NavBar : public PanelFrame
{
public:
    static constexpr int HEIGHT = 200;
    static NavBar* attach(gd::Control* parent, const std::string& current_tab);
    static std::string tab_of(const std::string& screen);
    std::string current;
    std::vector<gd::Button*> buttons;
private:
    void build();
    void animate_selection(int index);
};

// Animated bar with a lingering "lost" section. kind: hp, burst, enemy, boss, xp, stat.
class ResourceBar : public gd::Control
{
public:
    static ResourceBar* make(const std::string& kind = "hp", int height = 30);
    bool init() override;
    void set_values(float current, float maximum, bool animate = true);
    float ratio() const { return value / max_value; }
    std::string kind = "hp";
    float max_value = 100, value = 100;
    Signal<> filled;
private:
    void build();
    void refresh();
    void layout_bars();
    std::string fill_name() const;
    float _shown = 1, _lag = 1;
    ax::Node* _frame = nullptr;
    gd::TextureRect *_lag_rect = nullptr, *_fill = nullptr;
    gd::TweenRef _tw, _lag_tw;
};

class StatusBar : public PanelFrame
{
public:
    static StatusBar* create();
    void show_currency(const std::string& key);   // gems | gold | shards
    void build();
private:
    gd::Label *_energy_l = nullptr, *_timer_l = nullptr;
    struct Chip { gd::Control* chip; gd::Label* label; long long shown; gd::TweenRef tw; };
    std::map<std::string, Chip> _chips;
    std::string _third = "gems";
    PanelFrame* chip(const std::string& icon, const std::string& name, int w);
    PanelFrame* currency_chip(const std::string& key, const std::string& name, int w);
    long long value_of(const std::string& key) const;
    void refresh();
    void refresh_energy();
    void update_chip(const std::string& key);
    void energy_info();
};

// Tutorial highlight: dims everything but `target`, shows text and a hand.
class CoachMark : public gd::Control
{
public:
    static CoachMark* show_on(gd::Control* parent, gd::Control* target, const std::string& text,
                              const std::string& gesture = "tap", bool block = true);
    void finish();
    Signal<> finished;
    void update(float dt) override;
private:
    gd::Control* _target = nullptr;
    std::string _gesture = "tap";
    bool _blocking = true, _done = false;
    float _t = 0;
    std::vector<gd::ColorRect*> _dims;
    gd::Panel* _border = nullptr;
    gd::TextureRect* _hand = nullptr;
    PanelFrame* _plate = nullptr;
};
