#pragma once
// Battle presentation (ports of scripts/combat/battle_*.gd, effects_layer.gd,
// skill_executor.gd, scripts/ui/battle_hud.gd, party_card.gd, battle_result.gd and
// the enemy_plate / cutin_decor components). Rules stay in logic/Battle (BattleModel).
//
// The Godot world (Node2D + Camera2D) is a gd::Node2D "world" whose children are
// raw nodes / Node2D-like Controls in Godot world coordinates. Godot z_index values
// are flattened onto the world's children as localZOrder = z * ZK (+ y for y-sorted units).
#include "screens/Screens.h"
#include <set>

using Next = std::function<void()>;
using Step = std::function<void(Next)>;

// Runs async steps in order (a Godot await chain). Each step calls `next` when done.
struct Chain : std::enable_shared_from_this<Chain>
{
    std::vector<Step> q;
    Next done;
    size_t i = 0;
    static void run(std::vector<Step> steps, Next done = nullptr)
    {
        auto c = std::make_shared<Chain>();
        c->q = std::move(steps);
        c->done = std::move(done);
        c->next();
    }
    void next()
    {
        if (i >= q.size()) { if (done) done(); return; }
        auto self = shared_from_this();
        q[i++]([self] { self->next(); });
    }
};

namespace BattleFx
{
constexpr int ZK = 4096;                       // world z step (room for y-sorting inside one z level)
float randf_range(float a, float b);           // presentation-only randomness (never the model rng)
bool fx_enabled();                              // Battle Effects setting
void wait(ax::Node* owner, float t, Next f);   // _wait(): immediate when t <= 0
void free_later(ax::Node* n);                  // queue_free for raw nodes

// Tween::kill() is unsafe once a tween has finished (it keeps the freed action), so tweens that get
// replaced run on a throwaway child node: dropping that node cancels them at any time.
struct TweenSlot
{
    ax::Node* node = nullptr;
    gd::TweenRef start(ax::Node* parent)
    {
        cancel();
        node = ax::Node::create();
        parent->addChild(node);
        return gd::tween(node);
    }
    void cancel()
    {
        if (node) node->removeFromParent();
        node = nullptr;
    }
};
}  // namespace BattleFx

// ------------------------------------------------------------------ battle_camera.gd
struct BattleCamera
{
    static constexpr float MAX_ZOOM = 1.22f, MAX_OFFSET = 220.0f;
    ax::Node* owner = nullptr;   // tweens run on this node
    Vec2 base_position{540, 960}, position{540, 960}, offset;
    float zoom = 1.0f;
    void process(float dt);
    void shake(float strength = 10.0f, float duration = 0.18f);
    gd::TweenRef focus(Vec2 point, float zoom_amount, float time = 0.25f);
    gd::TweenRef reset(float time = 0.3f);
private:
    float _shake_strength = 0, _shake_time = 0, _shake_duration = 0;
    BattleFx::TweenSlot _move_tween;
    gd::TweenRef move(Vec2 to, float z, float time);
};

// ------------------------------------------------------------------ battle_stage.gd
class BattleStage
{
public:
    static constexpr float PX = 6.0f, IMG_H = 270.0f, HORIZON = 150.0f;
    std::string env = "forest";
    bool boss = false;
    float bottom_y = 0;
    void setup(gd::Node2D* world, const std::string& bg_name, bool is_boss, BattleCamera* cam);
    void fit(Vec2 view_size, float field_bottom);
    float horizon_y() const { return bottom_y - (IMG_H - HORIZON) * PX; }
    void process(float dt);
private:
    struct Ambient { gd::ParticleCfg cfg; std::string kind; gd::Particles* node = nullptr; };
    gd::Node2D* _world = nullptr;
    BattleCamera* _camera = nullptr;
    Vec2 _base_cam, _view;
    std::vector<ax::Sprite*> _sprites;
    std::vector<Vec2> _homes;
    std::vector<float> _factors;
    std::vector<ax::Node*> _rays;
    std::vector<Ambient> _ambient;
    ax::Sprite* _fog = nullptr;
    ax::DrawNode* _sky = nullptr;
    float _t = 0;
    void add_ambient();
    gd::ParticleCfg particles(int amount, const Col& c0, const Col& c1, Vec2 gravity, float life, float smin, float smax);
    void add_rays(const Col& col);
    void add_fog(const Col& col);
    void place_ambient(Vec2 view_size);
};

// ------------------------------------------------------------------ battle_unit_view.gd
class BattleUnitView : public gd::Node2D
{
public:
    static constexpr float BAR_W = 150.0f;
    static BattleUnitView* make(const CombatantPtr& c, Vec2 pos, float scale_mult = 1.0f);
    CombatantPtr combatant;
    Json sprite_def = Json::object();
    Vec2 home_pos;
    float unit_scale = 5.0f;
    Vec2 frame_size{48, 48};
    int z_index = 0;
    gd::AnimatedSprite* sprite = nullptr;

    float visual_height() const { return frame_size.y * 0.62f * unit_scale; }
    Vec2 impact_point() const { return position() + Vec2(0, -visual_height() * 0.5f); }
    gd::Rect2 hit_rect() const;
    Vec2 melee_anchor(bool attacker_is_player) const;
    void play_idle();
    float play_anim(const std::string& anim, float speed = 1.0f);
    std::string resolve_anim(const std::string& anim) const;
    void hit_react(float knock = 14.0f);
    void play_guard();
    void set_silhouette(bool on, float time = 0.0f);
    void set_guarding(bool on);
    void anticipate(const Col& color, float time = 0.3f);
    void flash(const Col& color, float time = 0.12f);
    void play_defeat();
    void play_victory();
    bool is_dead_visual() const { return _dead_visual; }
    gd::TweenRef move_to(Vec2 target, float time);
    gd::TweenRef return_home(float time) { return move_to(home_pos, time); }
    void set_targeted(bool on);
    void set_selected(bool on);
    void update(float dt) override;

private:
    ax::Sprite *_overlay = nullptr, *_shadow = nullptr, *_select_ring = nullptr, *_target_ring = nullptr, *_guard_icon = nullptr,
               *_cursor = nullptr;
    gd::Particles *_aura = nullptr, *_charge_fx = nullptr;
    BattleFx::TweenSlot _flash_tween;
    gd::TweenRef _charge_tw;   // loops: kill() is safe
    Col _tint = Col::WHITE, _mod = Col::WHITE, _flash_col = Col::WHITE;
    float _flash_amt = 0, _cursor_time = 0, _ring_t = 0;
    bool _dead_visual = false;
    void build();
    bool is_boss() const { return B(combatant->def, "boss", false); }
    void add_boss_aura(const Col& c0 = Col("#c8ff9a"), const Col& c1 = Col("#ffb04a"), int amount = 16);
    void play(const std::string& anim, float speed = 1.0f);
    void set_flash(const Col& c, float amount);
    void apply_color();
    void set_charging(bool on);
    void refresh_statuses();
};

// ------------------------------------------------------------------ effects_layer.gd
class EffectsLayer
{
public:
    static constexpr int MAX_PER_EFFECT = 10, MAX_NUMBERS = 24, MAX_BURSTS = 8;
    static constexpr float EFFECT_SCALE = 6.0f;
    gd::Node2D* world = nullptr;
    gd::AnimatedSprite* spawn(const std::string& effect_name, Vec2 pos, bool flip = false, float scale_mult = 1.0f, int z = 20);
    gd::TweenRef projectile(const std::string& effect_name, Vec2 from, Vec2 to, float time, bool flip = false);
    void particles(const std::string& kind, Vec2 pos, int amount = 14, float spread_deg = 180.0f);
    void ring(Vec2 pos, const Col& color, float radius = 180.0f, float time = 0.45f, float thickness = 10.0f, float squash = 0.45f);
    void shield_dome(Vec2 pos, const Col& color, float radius = 130.0f, float hold = 0.6f);
    void streaks(Vec2 pos, const Col& color, int count = 5, float length = 260.0f);
    void damage_number(Vec2 pos, int value, const std::string& kind = "normal", const std::string& tag = "", const std::string& icon_path = "");
    void floating_text(Vec2 pos, const std::string& text, const Col& color, int size = 40);
private:
    struct Number { gd::Node2D* n; gd::BoxContainer* row; gd::TextureRect* ic; gd::Label* main; gd::Label* sub; BattleFx::TweenSlot tw; };
    std::map<std::string, std::vector<gd::AnimatedSprite*>> _effect_pools;
    std::set<std::string> _looping;   // projectiles loop their effect from then on (like Godot's shared SpriteFrames)
    std::vector<Number> _number_pool;
    int _number_index = 0;
    std::vector<gd::Particles*> _bursts;
    int _burst_index = 0;
    std::vector<std::pair<Vec2, double>> _recent;
    gd::AnimatedSprite* take_effect(const std::string& effect_name);
    Number& take_number();
    void launch(Number& n, Vec2 pos, float pop, bool soft);
};

// ------------------------------------------------------------------ party_card.gd
class PartyCard : public gd::Control
{
public:
    static constexpr float SWIPE_DIST = 60.0f;
    static constexpr int H = 210;
    static PartyCard* make(const CombatantPtr& c);
    Signal<CombatantPtr, std::string> action;
    Signal<CombatantPtr> pressed_unit;
    CombatantPtr combatant;
    PanelFrame* frame = nullptr;
    void set_enabled(bool on);
    void set_selected(bool on);
    void refresh_state();
private:
    gd::Control *content = nullptr, *portrait = nullptr, *gesture = nullptr;
    ResourceBar *hp_bar = nullptr, *burst_bar = nullptr;
    gd::Label *hp_text = nullptr, *burst_label = nullptr, *burst_pct = nullptr, *ko_stamp = nullptr, *gesture_label = nullptr;
    gd::BoxContainer* status_row = nullptr;
    gd::TextureRect* gesture_icon = nullptr;
    gd::Particles* _sparkle = nullptr;
    Vec2 _press_pos;
    bool _pressing = false, _enabled = true, _ready_state = false, _selected = false;
    gd::TweenRef _glow_tween;
    std::string _el = "neutral";
    void setup(const CombatantPtr& c);
    void build_gesture_overlay();
    void on_input(gd::InputEvent& e);
    void update_gesture(float dy);
    void release(Vec2 delta);
    void on_hp(int current, int maximum);
    void on_burst(double current, double maximum);
    void on_burst_filled();
    void set_sparkle(bool on);
    void on_statuses();
};

// ------------------------------------------------------------------ enemy_plate.gd
class EnemyPlate : public PanelFrame
{
public:
    static EnemyPlate* create(const CombatantPtr& c);
    Signal<CombatantPtr> tapped;
    CombatantPtr combatant;
    bool is_boss = false;
    void set_targeted(bool on);
    void refresh_phase();
private:
    ResourceBar* bar = nullptr;
    gd::Label *pct = nullptr, *name_label = nullptr;
    gd::BoxContainer* status_row = nullptr;
    gd::TextureRect* marker = nullptr;
    gd::PanelContainer *phase_tag = nullptr, *_danger = nullptr;
    gd::ColorRect* _tick = nullptr;
    bool _targeted = false;
    int _last_hp = 0;
    gd::TweenRef _pulse;
    void build();
    void on_hp(int current, int maximum);
    void on_statuses();
    std::string phase_text() const;
    void add_phase_tick();
    void set_danger(bool on);
};

namespace CutinDecor   // cutin_decor.gd
{
void add(gd::Control* band, const std::string& element);
}

// ------------------------------------------------------------------ battle_hud.gd
class BattleHUD : public gd::Control
{
public:
    static constexpr int CARD_H = PartyCard::H, LOG_LINES = 2, TOP_H = 124, LOG_H = 100;
    static BattleHUD* create();
    Signal<CombatantPtr> unit_selected, target_requested;
    Signal<CombatantPtr, std::string> card_action;
    Signal<> menu_requested;
    Signal<bool> auto_toggled;
    Signal<float> speed_toggled;
    float bottom_block = 560.0f;
    bool auto_on = false, auto_available = true;
    float speed = 1.0f;
    gd::BoxContainer* enemy_row = nullptr;
    std::map<Combatant*, EnemyPlate*> plates;
    std::map<Combatant*, PartyCard*> cards;

    float field_bottom() const;
    float field_top() const;
    void set_auto(bool on, bool emit = false);
    void set_auto_available(bool on);
    void set_speed(float v, bool emit = false);
    void show_warning(const std::string& text, const std::string& sub, Next done = nullptr);
    void set_enemies(const Units& enemies);
    void set_party(const Units& players);
    void set_header(const Json& stage, int wave, int wave_total, int turn);
    void set_loot(int gold, int drops);
    void set_target_text(const CombatantPtr& target);
    void refresh(bool can_input, const CombatantPtr& selected);
    void add_log(const std::string& text, const Col& color = UIKit::TEXT);
    void flash_screen(const Col& color, float strength = 0.35f, float time = 0.12f);
    void show_banner(const std::string& text, const Col& color = UIKit::GOLD, float hold = 0.7f, const std::string& style = "wave",
                     const std::string& sub = "", Next done = nullptr);
    void play_burst_cutin(const CombatantPtr& c, const Json& skill, Next done);
    void play_boss_title(const std::string& boss_name);
    void show_hint(const Json& hint, Next done);
    void show_menu(std::function<void()> on_retreat);

private:
    gd::Control *_block = nullptr, *banner_layer = nullptr, *cutin = nullptr;
    gd::Label *stage_label = nullptr, *stage_num = nullptr, *wave_label = nullptr, *gold_label = nullptr, *drops_label = nullptr;
    gd::BoxContainer *wave_pips = nullptr, *log_box = nullptr;
    FantasyButton *btn_menu = nullptr, *btn_auto = nullptr, *btn_speed = nullptr;
    gd::GridContainer* cards_grid = nullptr;
    gd::ColorRect* flash_rect = nullptr;
    PanelFrame* _auto_band = nullptr;
    CombatantPtr _target;
    void build_top();
    void build_enemy_row();
    void build_bottom();
    void update_auto_band();
};

// ------------------------------------------------------------------ battle_result.gd
class BattleResult : public gd::Control
{
public:
    static BattleResult* create();
    Signal<> next_pressed, retry_pressed, home_pressed, party_pressed, stage_select_pressed;
    bool sequence_done = false;
    void show_victory(const Json& summary, bool has_next);
    void show_defeat();
    bool handle_enter();   // Enter on PC: skip, then the default button
    static std::string defeat_tip();
private:
    struct Row { gd::Control* node; Json data; ResourceBar* bar; gd::Label *level, *gains, *stamp; };
    gd::BoxContainer* _content = nullptr;
    PanelFrame* _panel = nullptr;
    bool _fast = false;
    FantasyButton *_skip = nullptr, *_default = nullptr;
    void skip_now();
    void add_skip();
    Step step(float t);
    void frame(const std::string& title, const Col& color, const std::string& variant = "panel");
    gd::Label* counter(gd::Control* parent, const std::string& icon_path, const Col& color);
    void count(gd::Label* l, int total, const std::string& fmt, Next done);
    Row unit_row(const Json& u, bool compact);
    void animate_xp(const Row& row);
    void pop(gd::Control* c);
};
