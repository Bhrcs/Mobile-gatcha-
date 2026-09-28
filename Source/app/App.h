#pragma once
// App services (the Godot autoloads that touch the engine): AudioManager,
// SceneRouter and UIManager. Game rules live in logic/ (GM, DB).
#include "ui/Gui.h"
#include "logic/GameManager.h"

class ScreenBase;
class FantasyPopup;
class CoachMark;

// ------------------------------------------------------------------ audio
namespace AudioManager
{
void set_volumes(float master, float music, float sfx);
void play_sfx(const std::string& name, float pitch_var = 0.05f, float volume_db = 0.0f);
void play_music(const std::string& track, float fade = 0.8f);
void play_sting(const std::string& track);
void stop_music(float fade = 0.5f);
void shutdown();
}  // namespace AudioManager

// ------------------------------------------------------------------ scenes
namespace SceneRouter
{
using Factory = std::function<ScreenBase*()>;
bool register_screen(const std::string& name, Factory f);
// nav: "" auto | push | tab | replace | reset  (see scripts/core/scene_router.gd)
void go(const std::string& scene, const Json& params = Json::object(), const std::string& nav = "");
void back(const std::string& fallback = "home", const Json& fallback_params = Json::object());
void leave_battle(const std::string& map_scene, const Json& extra = Json::object());
void push_entry(const std::string& scene, const Json& params = Json::object());
void remember(const Json& values);   // merged into params, restored on Back
bool has_history();
std::string previous_scene();
ScreenBase* current_screen();
extern Json params;                  // arguments of the current screen
extern std::string current;          // current screen key
extern bool transitioning;
extern bool reduce_motion;
extern float fade_time;
extern Signal<std::string> scene_changed;
}  // namespace SceneRouter

// Self-registration: REGISTER_SCREEN("home", HomeScreen) in the screen's .cpp
#define REGISTER_SCREEN(key, T) \
    static bool _registered_##T = SceneRouter::register_screen(key, []() -> ScreenBase* { return gd::make<T>(); });

// ------------------------------------------------------------------ interface services
struct ConfirmOpts
{
    bool danger = false;
    std::string cancel_text = "CANCEL";
    std::function<void()> on_cancel;
    struct Line { std::string icon, text; gd::Col color = gd::Col("#f4ecdc"); };
    std::vector<Line> lines;
    std::string name = "ConfirmDialog";
    gd::Control* parent = nullptr;
};

namespace UIManager
{
gd::Control* ui_root();              // layer above screens (toasts, tooltips)
void sfx(const std::string& kind, float volume_db = -2.0f);
void haptic(const std::string& kind = "light");
void toast(const std::string& text, const std::string& kind = "info");   // info|success|error|warning|reward
void not_enough(const std::string& resource, int need, int have, const std::string& hint = "");
void attach_tooltip(gd::Control* c, const std::string& title, const std::string& body = "", const std::string& icon = "");
void show_tooltip(gd::Control* anchor, const std::string& title, const std::string& body = "", const std::string& icon = "");
void hide_tooltip();
bool tooltip_visible();
void register_popup(FantasyPopup* p);
FantasyPopup* top_popup();
bool has_popup(const std::string& name);
FantasyPopup* confirm(const std::string& title, const std::string& body, const std::string& confirm_text,
                      std::function<void()> on_confirm, const ConfirmOpts& opts = ConfirmOpts());
FantasyPopup* message(const std::string& title, const std::string& body, const std::string& ok_text = "OK",
                      gd::Control* parent = nullptr);
CoachMark* guide(const std::string& step, gd::Control* target, const std::string& text, const std::string& gesture = "tap");
void handle_key(int key);            // Esc / Enter (called by App)
}  // namespace UIManager

// ------------------------------------------------------------------ app
namespace App
{
void start();                         // builds the root layers, loads data, opens the first screen
void apply_settings();                // volumes, fullscreen, reduce motion
void quit_game(int code = 0);
gd::Control* screen_layer();
gd::ColorRect* fade_rect();
}  // namespace App
