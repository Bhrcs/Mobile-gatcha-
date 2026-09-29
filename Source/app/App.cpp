#include "App.h"
#include "ui/UIKit.h"
#include "audio/AudioEngine.h"
#include <cmath>
#include <cstdarg>

using namespace ax;
using gd::Col;

// ================================================================== AudioManager
namespace AudioManager
{
static float g_master = 0.8f, g_music = 0.6f, g_sfx = 0.8f;
struct Track
{
    AUDIO_ID id = AudioEngine::INVALID_AUDIO_ID;
    float gain = 0, target = 0, rate = 0;   // linear fade gain
    bool stop_at_zero = false;
};
static Track g_tracks[2];
static int g_active = 0;
static std::string g_current;
static std::map<std::string, double> g_last;
static bool g_scheduled = false;

static float db2lin(float db) { return std::pow(10.0f, db / 20.0f); }
static bool has(const std::string& p)
{
    static std::map<std::string, bool> cache;
    auto it = cache.find(p);
    if (it != cache.end()) return it->second;
    return cache[p] = FileUtils::getInstance()->isFileExist(p);
}

static void apply(Track& t)
{
    if (t.id != AudioEngine::INVALID_AUDIO_ID) AudioEngine::setVolume(t.id, t.gain * g_master * g_music);
}

static void tick(float dt)
{
    for (auto& t : g_tracks)
    {
        if (t.id == AudioEngine::INVALID_AUDIO_ID || t.rate <= 0) continue;
        if (t.gain < t.target) t.gain = std::min(t.target, t.gain + t.rate * dt);
        else t.gain = std::max(t.target, t.gain - t.rate * dt);
        apply(t);
        if (t.gain == t.target)
        {
            t.rate = 0;
            if (t.stop_at_zero && t.target <= 0)
            {
                AudioEngine::stop(t.id);
                t.id = AudioEngine::INVALID_AUDIO_ID;
            }
        }
    }
}

static void ensure_tick()
{
    if (g_scheduled) return;
    g_scheduled = true;
    Director::getInstance()->getScheduler()->schedule([](float dt) { tick(dt); }, &g_tracks, 0, false, "audio_fades");
}

static void fade(Track& t, float to, float secs, bool stop)
{
    ensure_tick();
    t.target = to;
    t.stop_at_zero = stop;
    t.rate = secs > 0 ? std::max(0.001f, std::abs(to - t.gain) / secs) : 1000.0f;
}

void set_volumes(float master, float music, float sfx)
{
    g_master = master;
    g_music = music;
    g_sfx = sfx;
    for (auto& t : g_tracks) apply(t);
}

void play_sfx(const std::string& name, float /*pitch_var: no pitch control in AudioEngine*/, float volume_db)
{
    double now = gd::ticks();
    auto it = g_last.find(name);
    if (it != g_last.end() && now - it->second < 0.03) return;
    g_last[name] = now;
    std::string p = "assets/audio/sfx/" + name + ".wav";
    if (!has(p) || g_master * g_sfx <= 0.001f) return;
    AudioEngine::play2d(p, false, std::min(1.0f, db2lin(volume_db) * g_master * g_sfx));
}

void play_music(const std::string& track, float fade_s)
{
    if (track == g_current && g_tracks[g_active].id != AudioEngine::INVALID_AUDIO_ID) return;
    std::string p = "assets/audio/music/" + track + ".ogg";
    if (!has(p)) return;
    g_current = track;
    Track& old = g_tracks[g_active];
    if (old.id != AudioEngine::INVALID_AUDIO_ID) fade(old, 0, fade_s, true);
    g_active = 1 - g_active;
    Track& t = g_tracks[g_active];
    if (t.id != AudioEngine::INVALID_AUDIO_ID) AudioEngine::stop(t.id);
    t.gain = 0.01f;
    t.id = AudioEngine::play2d(p, true, t.gain * g_master * g_music);
    fade(t, 1.0f, fade_s, false);
}

void play_sting(const std::string& track)
{
    stop_music(0.3f);
    std::string p = "assets/audio/music/" + track + ".ogg";
    if (has(p)) AudioEngine::play2d(p, false, g_master * g_music);
}

void stop_music(float fade_s)
{
    g_current.clear();
    for (auto& t : g_tracks)
        if (t.id != AudioEngine::INVALID_AUDIO_ID) fade(t, 0, fade_s, true);
}

void shutdown()
{
    AudioEngine::stopAll();
    for (auto& t : g_tracks) t = Track();
    g_current.clear();
}
}  // namespace AudioManager

// ================================================================== App layers
namespace App
{
static gd::Control* g_screens = nullptr;
static gd::Control* g_ui = nullptr;
static gd::ColorRect* g_fade = nullptr;
gd::Control* screen_layer() { return g_screens; }
gd::ColorRect* fade_rect() { return g_fade; }
}  // namespace App

// ================================================================== SceneRouter
namespace SceneRouter
{
Json params = Json::object();
std::string current;
bool transitioning = false;
bool reduce_motion = false;
float fade_time = 0.22f;
Signal<std::string> scene_changed;
static Json history = Json::array();
static ScreenBase* g_screen = nullptr;
static const std::vector<std::string> TABS{"home", "world_select", "units", "summon", "menu"};
static const std::vector<std::string> RESETS{"main_menu", "starter_select", "intro"};

static std::map<std::string, Factory>& registry()
{
    static std::map<std::string, Factory> r;
    return r;
}
bool register_screen(const std::string& name, Factory f)
{
    registry()[name] = std::move(f);
    return true;
}
ScreenBase* current_screen() { return g_screen; }
bool has_history() { return !history.empty(); }
std::string previous_scene() { return history.empty() ? "" : S(history.back(), "scene"); }
void push_entry(const std::string& scene, const Json& p) { history.push_back({{"scene", scene}, {"params", p}}); }
void remember(const Json& values)
{
    if (!params.is_object()) params = Json::object();
    for (auto& [k, v] : values.items()) params[k] = v;
}

static bool in(const std::vector<std::string>& v, const std::string& s) { return std::find(v.begin(), v.end(), s) != v.end(); }

static std::string resolve_mode(const std::string& scene, const std::string& nav)
{
    if (!nav.empty()) return nav;
    if (in(RESETS, scene)) return "reset";
    if (in(TABS, scene)) return "tab";
    if (scene == current || scene == "battle") return "replace";
    return "push";
}

static void trim_loop(const std::string& scene)
{
    for (int i = (int)history.size() - 1; i >= 0; --i)
        if (S(history[i], "scene") == scene)
        {
            history.erase(history.begin() + i, history.end());
            return;
        }
}

static void finish()
{
    gd::Root::get()->input_blocked = false;
    transitioning = false;
    scene_changed.emit(current);
}

static void switch_to(const std::string& scene, const Json& new_params, const std::string& mode)
{
    auto it = registry().find(scene);
    if (it == registry().end())
    {
        Platform::log("Unknown screen: " + scene);
        return;
    }
    transitioning = true;
    gd::Root::get()->input_blocked = true;
    UIManager::hide_tooltip();
    bool ember = scene == "battle" || current == "battle";
    auto fade = App::fade_rect();
    fade->set_color(ember ? Col("#1a0806") : Col("#0d0810"));
    float to = ember || mode == "tab" || mode == "replace" || mode == "reset" ? 1.0f : 0.55f;
    auto tw = gd::tween(fade);
    tw->alpha(fade, to, ember ? fade_time : 0.12f);
    tw->callback([scene, new_params, mode, ember, fade] {
        if (g_screen) g_screen->removeFromParent();
        params = new_params.is_object() ? new_params : Json::object();
        current = scene;
        g_screen = registry()[scene]();
        g_screen->set_anchors_preset(gd::PRESET_FULL_RECT);
        App::screen_layer()->add(g_screen);
        g_screen->ready();
        gd::defer([mode, ember, fade] {
            auto t2 = gd::tween(fade);
            if (!ember && (mode == "push" || mode == "back") && !reduce_motion && g_screen)
            {
                float dir = mode == "push" ? 1.0f : -1.0f;
                g_screen->set_shift(Vec2(120 * dir, 0));
                g_screen->set_alpha(0);
                t2->set_parallel();
                t2->shift(g_screen, Vec2::ZERO, 0.18f).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
                t2->alpha(g_screen, 1.0f, 0.14f);
                t2->alpha(fade, 0.0f, 0.14f);
            }
            else
                t2->alpha(fade, 0.0f, ember ? fade_time : 0.14f);
            t2->on_finished(finish);
        });
    });
}

void go(const std::string& scene, const Json& new_params, const std::string& nav)
{
    if (transitioning) return;
    std::string mode = resolve_mode(scene, nav);
    if (mode == "tab")
        history = scene == "home" ? Json::array() : Json::array({{{"scene", "home"}, {"params", Json::object()}}});
    else if (mode == "reset")
        history = Json::array();
    else if (mode == "push")
    {
        if (current != "battle" && !current.empty() && current != scene) history.push_back({{"scene", current}, {"params", params}});
        trim_loop(scene);
    }
    switch_to(scene, new_params, mode);
}

void back(const std::string& fallback, const Json& fallback_params)
{
    if (transitioning) return;
    UIManager::sfx("back");
    if (history.empty())
    {
        if (current == fallback) return;
        switch_to(fallback, fallback_params, fallback != "home" ? "back" : "tab");
        return;
    }
    Json e = history.back();
    history.erase(history.end() - 1);
    Json p = O(e, "params");
    p["returning"] = true;
    switch_to(S(e, "scene"), p, "back");
}

void leave_battle(const std::string& map_scene, const Json& extra) { go(map_scene, extra, "replace"); }
}  // namespace SceneRouter

// ================================================================== UIManager
namespace UIManager
{
static std::vector<FantasyPopup*> g_popups;
static gd::BoxContainer* g_toasts = nullptr;
static gd::PanelContainer* g_tip = nullptr;
static gd::Control* g_tip_owner = nullptr;
static int g_tip_token = 0;

gd::Control* ui_root() { return App::g_ui; }

void sfx(const std::string& kind, float db)
{
    static const std::map<std::string, std::string> SOUNDS{
        {"press", "click"}, {"back", "ui_back"}, {"cancel", "ui_back"}, {"confirm", "ui_confirm"}, {"error", "ui_error"},
        {"coin", "coin"}, {"claim", "claim"}, {"mission", "mission"}, {"level_up", "level_up"}, {"evolve", "evolve"},
        {"summon", "summon_reveal"}, {"open", "menu_open"}, {"close", "menu_close"}, {"select", "unit_select"},
        {"stage", "stage_select"}, {"toggle", "click"}, {"reward", "reward"}};
    auto it = SOUNDS.find(kind);
    AudioManager::play_sfx(it == SOUNDS.end() ? kind : it->second, 0.03f, db);
}

void haptic(const std::string& kind)
{
#if AX_TARGET_PLATFORM == AX_PLATFORM_ANDROID || AX_TARGET_PLATFORM == AX_PLATFORM_IOS
    if (!B(GM.settings, "haptics", true)) return;
    static const std::map<std::string, int> MS{{"light", 12}, {"confirm", 20}, {"burst", 30}, {"reveal", 45}, {"evolve", 60}};
    auto it = MS.find(kind);
    Device::vibrate((it == MS.end() ? 15 : it->second) / 1000.0f);
#else
    (void)kind;
#endif
}

void toast(const std::string& text, const std::string& kind)
{
    if (!g_toasts) return;
    for (auto t : g_toasts->children())
        if (S(t->meta, "text") == text)
        {
            t->meta["ttl"] = 1.6;
            return;
        }
    auto kids = g_toasts->children();
    for (size_t i = 0; i + 2 < kids.size(); ++i) kids[i]->removeFromParent();
    static const std::map<std::string, std::string> COLORS{{"info", "#f4ecdc"}, {"success", "#8ae05a"}, {"error", "#ff7a5a"},
                                                           {"warning", "#ffd35a"}, {"reward", "#ffd35a"}};
    static const std::map<std::string, std::string> ICONS{{"info", "info"}, {"success", "check"}, {"error", "warning"},
                                                          {"warning", "warning"}, {"reward", "chest_open"}};
    auto p = PanelFrame::make("inset", 14);
    p->set_name("Toast");
    p->meta["text"] = text;
    p->meta["ttl"] = 1.6;
    p->set_mouse_filter(gd::MOUSE_IGNORE);
    p->set_h_flags(gd::SIZE_SHRINK_CENTER);
    auto h = UIKit::hbox(UIKit::SP_M);
    h->set_mouse_filter(gd::MOUSE_IGNORE);
    p->add(h);
    auto ic = ICONS.count(kind) ? ICONS.at(kind) : "info";
    h->add(UIKit::icon("assets/icons/" + ic + ".png", 32));
    auto l = UIKit::label(text, UIKit::T_BODY, Col(COLORS.count(kind) ? COLORS.at(kind) : "#f4ecdc"), gd::ALIGN_LEFT, 6);
    l->set_autowrap(true);
    l->set_min_w(std::min(820.0f, gd::text_size(text, UIKit::T_BODY).x + 8));
    h->add(l);
    g_toasts->add(p);
    if (kind == "error") sfx("error", -4.0f);
    p->set_alpha(0);
    gd::tween(p)->alpha(p, 1.0f, 0.12f);
    p->schedule(
        [p](float dt) {
            double ttl = F(p->meta, "ttl", 0) - dt;
            p->meta["ttl"] = ttl;
            if (ttl <= 0 && !B(p->meta, "gone", false))
            {
                p->meta["gone"] = true;
                auto tw = gd::tween(p);
                tw->alpha(p, 0.0f, 0.2f);
                tw->callback([p] { p->queue_free(); });
            }
        },
        0.0f, "toast_ttl");
}

void not_enough(const std::string& resource, int need, int have, const std::string& hint)
{
    std::string msg = "Not enough " + resource + ". Need " + UIKit::format_number(need) + " - you have " + UIKit::format_number(have) + ".";
    if (!hint.empty()) msg += " " + hint;
    toast(msg, "error");
}

void attach_tooltip(gd::Control* c, const std::string& title, const std::string& body, const std::string& icon)
{
    c->meta["tip"] = {title, body, icon};
    if (B(c->meta, "tip_hooked", false)) return;
    c->meta["tip_hooked"] = true;
    if (c->mouse_filter == gd::MOUSE_IGNORE) c->mouse_filter = gd::MOUSE_PASS;
    auto show_for = [c] {
        const Json& d = at(c->meta, "tip");
        show_tooltip(c, S(at(d, 0)), S(at(d, 1)), S(at(d, 2)));
    };
    c->mouse_entered.connect([c, show_for] {
        int token = ++g_tip_token;
        gd::after(c, 0.35f, [c, token, show_for] {
            if (token == g_tip_token && c->is_visible_in_tree() && gd::Root::get()->hovered() == c) show_for();
        });
    });
    c->mouse_exited.connect([c] {
        ++g_tip_token;
        if (g_tip_owner == c) hide_tooltip();
    });
    bool is_button = dynamic_cast<gd::BaseButton*>(c) != nullptr;
    c->gui_input.connect([c, is_button, show_for](gd::InputEvent& e) {
        if (e.type == gd::Ev::PRESS)
        {
            if (is_button)
            {
                int token = ++g_tip_token;
                gd::after(c, 0.45f, [c, token, show_for] {
                    if (token == g_tip_token && c->is_visible_in_tree()) show_for();
                });
            }
            else if (g_tip_owner == c)
                hide_tooltip();
            else
                show_for();
        }
        else if (e.type == gd::Ev::RELEASE || e.type == gd::Ev::CANCEL)
            ++g_tip_token;
    });
    c->tree_exiting.connect([c] {
        if (g_tip_owner == c) hide_tooltip();
    });
}

void show_tooltip(gd::Control* anchor, const std::string& title, const std::string& body, const std::string& icon)
{
    hide_tooltip();
    g_tip_owner = anchor;
    g_tip = gd::PanelContainer::create(UIKit::tex_style("p5_tip.png", 9, 16));
    g_tip->set_name("Tooltip");
    g_tip->set_mouse_filter(gd::MOUSE_IGNORE);
    g_tip->set_z(20);
    auto v = UIKit::vbox(UIKit::SP_XS);
    v->set_mouse_filter(gd::MOUSE_IGNORE);
    g_tip->add(v);
    auto h = UIKit::hbox(UIKit::SP_S);
    if (!icon.empty()) h->add(UIKit::icon(icon, 32));
    h->add(UIKit::label(title, UIKit::T_BODY, UIKit::GOLD, gd::ALIGN_LEFT, 6));
    v->add(h);
    if (!body.empty())
    {
        auto b = UIKit::label(body, UIKit::T_SMALL, UIKit::TEXT);
        b->set_autowrap(true);
        b->set_min_w(std::min(640.0f, std::max(300.0f, gd::text_size(body, UIKit::T_SMALL).x + 8)));
        v->add(b);
    }
    ui_root()->add(g_tip);
    g_tip->set_alpha(0);
    auto tip = g_tip;
    gd::defer([tip, anchor] {
        if (tip != g_tip || g_tip_owner != anchor) return;
        Vec2 sz = tip->combined_min();
        Vec2 vp = ui_root()->size();
        gd::Rect2 r = anchor->global_rect();
        Vec2 pos(r.center().x - sz.x / 2, r.position.y - sz.y - UIKit::SP_S);
        if (pos.y < UIKit::safe_top() + UIKit::SP_L) pos.y = r.end().y + UIKit::SP_S;
        pos.x = std::clamp(pos.x, (float)UIKit::MARGIN, std::max((float)UIKit::MARGIN, vp.x - sz.x - UIKit::MARGIN));
        pos.y = std::clamp(pos.y, UIKit::MARGIN + UIKit::safe_top(),
                           std::max(UIKit::MARGIN + UIKit::safe_top(), vp.y - sz.y - UIKit::MARGIN - UIKit::safe_bottom()));
        tip->set_position(pos);
        tip->set_size(sz);
        gd::tween(tip)->alpha(tip, 1.0f, 0.1f);
    });
}

void hide_tooltip()
{
    if (g_tip) g_tip->removeFromParent();
    g_tip = nullptr;
    g_tip_owner = nullptr;
}
bool tooltip_visible() { return g_tip != nullptr; }

void register_popup(FantasyPopup* p)
{
    g_popups.push_back(p);
    p->tree_exiting.connect([p] { g_popups.erase(std::remove(g_popups.begin(), g_popups.end(), p), g_popups.end()); });
    hide_tooltip();
}

FantasyPopup* top_popup()
{
    for (auto it = g_popups.rbegin(); it != g_popups.rend(); ++it)
        if ((*it)->is_inside_tree() && !(*it)->closing()) return *it;
    return nullptr;
}

bool has_popup(const std::string& name)
{
    for (auto p : g_popups)
        if (p->name() == name && !p->closing()) return true;
    return false;
}

FantasyPopup* confirm(const std::string& title, const std::string& body, const std::string& confirm_text,
                      std::function<void()> on_confirm, const ConfirmOpts& opts)
{
    if (has_popup("ConfirmDialog")) return nullptr;
    gd::Control* parent = opts.parent ? opts.parent : (gd::Control*)SceneRouter::current_screen();
    if (!parent) parent = ui_root();
    auto p = FantasyPopup::open(parent, title, 900);
    p->set_name(opts.name);
    if (!body.empty())
    {
        auto msg = UIKit::wrap_label(body, title.empty() ? UIKit::T_NAME : UIKit::T_BODY);
        msg->h_align = gd::ALIGN_CENTER;
        msg->set_min_w(820);
        p->content->add(msg);
    }
    for (auto& line : opts.lines)
    {
        auto h = UIKit::hbox(UIKit::SP_M);
        h->alignment = gd::ALIGNMENT_CENTER;
        if (!line.icon.empty()) h->add(UIKit::icon(line.icon, 48));
        h->add(UIKit::label(line.text, UIKit::T_BODY, line.color, gd::ALIGN_LEFT, 6));
        p->content->add(h);
    }
    auto row = UIKit::hbox(UIKit::SP_XL);
    row->alignment = gd::ALIGNMENT_CENTER;
    auto no = UIKit::btn(opts.cancel_text, "quiet", Vec2(340, 116));
    no->set_name("DialogCancel");
    auto yes = UIKit::btn(confirm_text, opts.danger ? "danger" : "primary", Vec2(380, 116));
    yes->set_name("DialogConfirm");
    row->add(no);
    row->add(yes);
    p->content->add(row);
    auto on_cancel = opts.on_cancel;
    yes->pressed.connect([p, on_confirm] {
        if (p->closing()) return;
        sfx("confirm");
        haptic("confirm");
        p->close();
        if (on_confirm) on_confirm();
    });
    no->pressed.connect([p, on_cancel] {
        p->close();
        if (on_cancel) on_cancel();
    });
    p->cancel_action = [p, on_cancel] {
        p->close();
        if (on_cancel) on_cancel();
    };
    p->default_action = [yes] { yes->pressed.emit(); };
    return p;
}

FantasyPopup* message(const std::string& title, const std::string& body, const std::string& ok_text, gd::Control* parent)
{
    if (!parent) parent = SceneRouter::current_screen() ? (gd::Control*)SceneRouter::current_screen() : ui_root();
    auto p = FantasyPopup::open(parent, title, 900);
    p->set_name("MessageDialog");
    auto msg = UIKit::wrap_label(body, UIKit::T_BODY);
    msg->h_align = gd::ALIGN_CENTER;
    msg->set_min_w(820);
    p->content->add(msg);
    auto ok = UIKit::btn(ok_text, "primary", Vec2(320, 110));
    ok->set_name("DialogOK");
    ok->set_h_flags(gd::SIZE_SHRINK_CENTER);
    p->content->add(ok);
    ok->pressed.connect([p] { p->close(); });
    p->default_action = [p] { p->close(); };
    return p;
}

CoachMark* guide(const std::string& step, gd::Control* target, const std::string& text, const std::string& gesture)
{
    if (!target || !GM.has_profile() || GM.coach_done(step)) return nullptr;
    auto scene = SceneRouter::current_screen();
    if (!scene) return nullptr;
    auto c = CoachMark::show_on(scene, target, text, gesture, false);
    c->set_name("Guide_" + step);
    auto done = std::make_shared<bool>(false);
    auto finish = [step, c, done] {
        if (*done) return;
        *done = true;
        GM.mark_coach_done(step);
        c->finish();
    };
    c->retain();
    c->finished.connect([c] { gd::defer([c] { c->release(); }); });
    if (auto b = dynamic_cast<gd::BaseButton*>(target))
        b->pressed.connect(finish);
    else
        target->gui_input.connect([finish](gd::InputEvent& e) {
            if (e.type == gd::Ev::RELEASE) finish();
        });
    return c;
}

void handle_key(int key)
{
    using K = EventKeyboard::KeyCode;
    auto screen = SceneRouter::current_screen();
    if (screen && !SceneRouter::transitioning && screen->on_key(key)) return;
    if (key == (int)K::KEY_ESCAPE || key == (int)K::KEY_BACK)
    {
        if (tooltip_visible())
        {
            hide_tooltip();
            return;
        }
        if (auto p = top_popup())
        {
            p->cancel();
            return;
        }
        if (SceneRouter::transitioning) return;
        if (screen) screen->on_back();
    }
    else if (key == (int)K::KEY_ENTER || key == (int)K::KEY_KP_ENTER)
    {
        if (auto p = top_popup()) p->confirm_default();
    }
}
}  // namespace UIManager

// ================================================================== App
namespace App
{
static void update_resolution()
{
    auto view = Director::getInstance()->getRenderView();
    if (!view) return;
    auto fs = view->getFrameSize();
    // keep_width: taller screens show more height; wider ones get side bars
    auto policy = fs.height / std::max(1.0f, fs.width) >= 1920.0f / 1080.0f ? ResolutionPolicy::FIXED_WIDTH : ResolutionPolicy::SHOW_ALL;
    view->setDesignResolutionSize(1080, 1920, policy);
}

void apply_settings()
{
    const Json& s = GM.settings;
    SceneRouter::reduce_motion = B(s, "reduce_motion", false);
    AudioManager::set_volumes((float)F(s, "master_volume", 0.8), (float)F(s, "music_volume", 0.6), (float)F(s, "sfx_volume", 0.8));
#if AX_TARGET_PLATFORM == AX_PLATFORM_WIN32 || AX_TARGET_PLATFORM == AX_PLATFORM_LINUX || AX_TARGET_PLATFORM == AX_PLATFORM_MAC
    if (auto view = dynamic_cast<RenderViewImpl*>(Director::getInstance()->getRenderView()))
    {
        bool want = B(s, "fullscreen", false);
        if (want != view->isFullscreen())
        {
            if (want) view->setFullscreen();
            else view->setWindowed(576, 1024);
            update_resolution();
        }
    }
#endif
}

void quit_game(int /*code*/)
{
    static bool quitting = false;
    if (quitting) return;
    quitting = true;
    if (GM.has_profile()) GM.save();
    AudioManager::shutdown();
    Director::getInstance()->end();
}

// CI screenshot probe: CB_SHOTS="main_menu,home,..." CB_SHOT_DIR=/abs/dir/ -> one PNG per screen, then quit.
static void run_shots(std::shared_ptr<std::vector<std::string>> list, size_t i, std::string dir)
{
    if (i >= list->size())
    {
        quit_game(0);
        return;
    }
    std::string name = (*list)[i];
    if (name != "main_menu" && !GM.has_profile() && !GM.continue_game()) GM.new_game("kael_emberclaw");
    if (name == "battle" && GM.current_stage_id.empty()) GM.current_stage_id = "ashroot_01";
    SceneRouter::transitioning = false;
    SceneRouter::go(name, name == "battle" ? Json{{"skip_hints", true}} : Json::object(), "reset");
    gd::after(gd::Root::get(), name == "battle" ? 5.0f : 2.5f, [list, i, dir, name] {
        ax::utils::captureScreen([list, i, dir](bool, std::string_view) { run_shots(list, i + 1, dir); }, dir + name + ".png");
    });
}

void start()
{
    update_resolution();
    Director::getInstance()->getEventDispatcher()->addCustomEventListener(RenderViewImpl::EVENT_WINDOW_RESIZED,
                                                                         [](EventCustom*) { update_resolution(); });
    DB.reload();
    GM.init();
    auto scene = Scene::create();
    auto root = gd::Root::create();
    scene->addChild(root);
    g_screens = gd::Control::create();
    g_screens->set_name("Screens");
    g_screens->set_mouse_filter(gd::MOUSE_IGNORE);
    g_screens->set_anchors_preset(gd::PRESET_FULL_RECT);
    root->add(g_screens);
    g_ui = gd::Control::create();
    g_ui->set_name("UIRoot");
    g_ui->set_mouse_filter(gd::MOUSE_IGNORE);
    g_ui->set_anchors_preset(gd::PRESET_FULL_RECT);
    g_ui->set_z(90);
    root->add(g_ui);
    UIManager::g_toasts = UIKit::vbox(UIKit::SP_S);
    UIManager::g_toasts->set_name("Toasts");
    UIManager::g_toasts->set_mouse_filter(gd::MOUSE_IGNORE);
    UIManager::g_toasts->set_anchors_preset(gd::PRESET_TOP_WIDE);
    UIManager::g_toasts->set_offsets(60, UIKit::TOP_BAR_H + 150, -60, UIKit::TOP_BAR_H + 150);
    g_ui->add(UIManager::g_toasts);
    g_fade = gd::ColorRect::create(Col("#0d0810"));
    g_fade->set_name("Fade");
    g_fade->set_mouse_filter(gd::MOUSE_IGNORE);
    g_fade->set_anchors_preset(gd::PRESET_FULL_RECT);
    g_fade->set_z(100);
    g_fade->set_alpha(0);
    root->add(g_fade);
    root->key_pressed.connect([](int k) { UIManager::handle_key(k); });
    root->schedule([](float dt) { GM.tick(dt); }, 0.0f, "gm_tick");
    apply_settings();
    GM.settings_changed.connect([] { apply_settings(); });
    Director::getInstance()->runWithScene(scene);
    const char* shots = std::getenv("CB_SHOTS");
    if (shots && *shots)
    {
        auto list = std::make_shared<std::vector<std::string>>();
        std::string cur;
        for (const char* c = shots;; ++c)
        {
            if (*c == ',' || *c == 0)
            {
                if (!cur.empty()) list->push_back(cur);
                cur.clear();
                if (!*c) break;
            }
            else
                cur += *c;
        }
        const char* d = std::getenv("CB_SHOT_DIR");
        std::string dir = d && *d ? d : Platform::writablePath();
        if (dir.back() != '/') dir += '/';
        gd::defer([list, dir] { run_shots(list, 0, dir); });
        return;
    }
    SceneRouter::go("main_menu", Json::object(), "reset");
}
}  // namespace App
