// The "battle" screen: battle_controller.gd (+ scenes/combat/battle.tscn) and skill_executor.gd.
// Rules live in BattleModel; SkillExecutor decides WHEN each hit is applied so damage lines up
// with the animation. Godot awaits are callback chains (Chain / Next).
#include "battle/BattleScene.h"
#include <cmath>

using namespace BattleFx;
using PlanPtr = std::shared_ptr<Plan>;
static std::string first_word(const std::string& s) { return s.substr(0, s.find(' ')); }
static Vec2 vp() { return gd::Root::get()->size(); }

// Formation slots as offsets from the battlefield's bottom edge (portrait layout). Leader in front.
static const Vec2 PLAYER_SLOTS[] = {{690, -170}, {905, -300}, {915, -50}, {660, -420}, {790, -10}};
static const Vec2 ENEMY_SLOTS[] = {{380, -140}, {175, -280}, {165, -30}, {380, -390}, {340, -10}};
static const Vec2 SINGLE_PLAYER_POS(790, -90), SINGLE_ENEMY_POS(290, -90);
static const Vec2 SUMMON_SLOTS[] = {{470, -300}, {480, -20}};   // minions called by a boss appear in front of it

class BattleScreen;

struct SkillExecutor
{
    static constexpr float DASH_TIME = 0.24f, RETURN_TIME = 0.22f, PROJECTILE_TIME = 0.26f, MULTI_HIT_GAP = 0.07f;
    BattleScreen* battle = nullptr;
    void execute(Plan plan, Next done);
private:
    BattleModel& model();
    BattleUnitView* view(const CombatantPtr& c);
    void wait(float t, Next f);
    void enemy_special_windup(const CombatantPtr& user, const Json& skill, Next done);
    void melee(PlanPtr p, BattleUnitView* uview, Next done);
    void run_hits(PlanPtr p, BattleUnitView* uview, const std::string& anim, std::function<void(float)> done);
    void ranged(PlanPtr p, BattleUnitView* uview, Next done);
    void self_cast(PlanPtr p, BattleUnitView* uview, Next done);
    void hit(const PlanPtr& p, int ti, int hi, bool is_final);
    void show_events(const std::vector<BattleEvent>& events, Next done);
    void burst_intro(const CombatantPtr& user, const Json& skill, Next done);
    void burst_outro(const CombatantPtr& user, Next done);
};

class BattleScreen : public ScreenBase
{
public:
    enum State { INTRO, PLAYER, BUSY, ENEMY, RESULT };
    Signal<std::string> state_changed;
    Signal<bool> battle_finished;
    float battle_speed = 1.0f;
    BattleModel model;
    SkillExecutor executor;
    std::vector<std::pair<CombatantPtr, BattleUnitView*>> views;   // insertion order, like the Godot Dictionary
    State state = INTRO;
    CombatantPtr selected, target;
    std::string stage_id;
    Json result_summary = Json::object();
    BattleCamera camera;
    BattleStage stage_view;
    EffectsLayer effects;
    gd::Node2D* world = nullptr;
    gd::ColorRect* dim = nullptr;
    BattleHUD* hud = nullptr;

    void ready() override
    {
        stage_id = S(params(), "stage_id", GM.current_stage_id);
        if ((stage_id.empty() || DB.stage(stage_id).empty()) && !DB.stage_order.empty()) stage_id = DB.stage_order[0];
        if (!GM.has_profile() && !GM.continue_game())
        {
            // launched without a profile: use a throwaway one
            GM.profile = SaveManager::get().default_profile();
            GM.profile["starter_id"] = "kael_emberclaw";
            GM.profile["units"] = Json::array({{{"uid", "u1"}, {"char_id", "kael_emberclaw"}, {"level", 1}, {"exp", 0}}});
            GM.profile["party"] = Json::array({"u1"});
        }
        GM.current_stage_id = stage_id;
        executor.battle = this;
        model.setup(stage_id, GM.party_units(), I(params(), "seed", -1));

        // battle.tscn: world (stage, units, dim, effects under a camera) + HUD layer
        world = gd::Node2D::create();
        world->set_name("World");
        add(world);
        camera.owner = world;
        effects.world = world;
        dim = gd::ColorRect::create(Col(0.02f, 0.01f, 0.03f, 0));
        dim->set_position(Vec2(-800, -800));
        dim->set_size(Vec2(2800, 4000));
        dim->set_mouse_filter(gd::MOUSE_IGNORE);
        world->addChild(dim, 5 * ZK);
        auto field = gd::Control::create();   // taps that no HUD control takes (Godot _unhandled_input)
        field->set_anchors_preset(gd::PRESET_FULL_RECT);
        field->gui_input.connect([this](gd::InputEvent& e) { on_field_input(e); });
        add(field);
        hud = BattleHUD::create();
        add(hud);

        stage_view.setup(world, S(model.stage, "background", "bg_forest"), B(model.stage, "boss", false), &camera);
        resized.connect([this] { fit_background(); });
        dim->setVisible(false);
        hud->unit_selected.connect([this](CombatantPtr c) { on_unit_selected(c); });
        hud->card_action.connect([this](CombatantPtr c, std::string a) {
            if (hud->auto_on) hud->set_auto(false, true);
            request_action(a, c);
        });
        hud->menu_requested.connect([this] { on_menu(); });
        hud->target_requested.connect([this](CombatantPtr c) {
            if (state == PLAYER && c->is_alive() && c != target)
            {
                set_target(c);
                AudioManager::play_sfx("target", 0.05f, -4.0f);
                coach_progress("target");
            }
        });
        hud->set_party(model.players);
        hud->set_auto_available(GM.feature_unlocked("auto"));
        hud->set_auto(B(GM.settings, "auto_battle", false));
        hud->auto_toggled.connect([this](bool on) {
            GM.set_setting("auto_battle", on);
            hud->add_log(std::string("Auto Battle ") + (on ? "ON" : "OFF") + ".", UIKit::SKY);
            if (on) auto_step();
        });
        set_battle_speed((float)F(GM.settings, "battle_speed", 1.0));
        hud->speed_toggled.connect([this](float v) {
            set_battle_speed(v);
            GM.set_setting("battle_speed", v);
        });
        fit_background();   // party size decides where the battlefield ends
        model.enemy_defeated.connect([this](CombatantPtr) { update_loot(); });
        update_loot();
        for (auto& p : model.players) spawn_view(p, slot_pos(PLAYER_SLOTS, 5, p->slot, (int)model.players.size(), true));
        AudioManager::play_music(B(model.stage, "boss", false) ? "boss" : "battle");
        scheduleUpdate();
        start_battle();
    }

    // Camera2D + y-sorted Units + hit-stop clock
    void update(float dt) override
    {
        camera.process(dt);
        stage_view.process(dt);
        if (!_stops.empty())
        {
            double now = gd::ticks();
            _stops.erase(std::remove_if(_stops.begin(), _stops.end(), [now](double t) { return t <= now; }), _stops.end());
            if (_stops.empty()) set_time_scale(battle_speed);
        }
        world->setScale(camera.zoom);
        world->set_position(vp() / 2 - (camera.position + camera.offset) * camera.zoom);
        for (auto& [c, v] : views) v->setLocalZOrder(v->z_index * ZK + (int)v->position().y);
    }

    void onExit() override
    {
        set_time_scale(1.0f);
        ScreenBase::onExit();
    }

    // Fits the layered stage to any window shape: the ground plane ends just under the unit cards.
    void fit_background()
    {
        Vec2 vs = vp();
        camera.base_position = vs / 2;
        camera.position = camera.base_position;
        stage_view.fit(vs, hud->field_bottom());
    }

    Vec2 enemy_pos(const CombatantPtr& e)
    {
        if (e->summoned)
        {
            Vec2 off = SUMMON_SLOTS[e->summon_index % 2];
            return Vec2(off.x, hud->field_bottom() + off.y);
        }
        int wave_size = 0;
        for (auto& x : model.enemies) wave_size += x->summoned ? 0 : 1;
        return slot_pos(ENEMY_SLOTS, 5, e->slot, wave_size, false);
    }

    Vec2 slot_pos(const Vec2* slots, int n, int slot, int count, bool is_player)
    {
        Vec2 off = slots[slot % n];
        if (count == 1) off = is_player ? SINGLE_PLAYER_POS : SINGLE_ENEMY_POS;
        return Vec2(off.x, hud->field_bottom() + off.y);
    }

    BattleUnitView* view_of(const CombatantPtr& c)
    {
        for (auto& [k, v] : views)
            if (k == c) return v;
        return nullptr;
    }

    BattleUnitView* spawn_view(const CombatantPtr& c, Vec2 pos)
    {
        // big squads / summoned minions are drawn a little smaller so the field stays readable
        float mult = 1.0f;
        if (c->is_player && model.players.size() >= 4) mult = 0.86f;
        else if (c->summoned) mult = 0.9f;
        auto v = BattleUnitView::make(c, pos, mult);
        world->addChild(v, (int)pos.y);
        views.push_back({c, v});
        return v;
    }

    // ------------------------------------------------------------------ flow
    void set_state(State s)
    {
        static const char* NAMES[] = {"INTRO", "PLAYER", "BUSY", "ENEMY", "RESULT"};
        state = s;
        state_changed.emit(NAMES[s]);
        refresh_hud();
    }

    bool skip_hints() const { return B(params(), "skip_hints", false); }

    void start_battle()
    {
        set_state(INTRO);
        spawn_wave_views([this] {
            std::string hint_id = S(model.stage, "hint");
            if (!hint_id.empty() && !GM.hint_seen(hint_id) && !skip_hints())
                hud->show_hint(O(DB.hints, hint_id), [this, hint_id] {
                    GM.mark_hint_seen(hint_id);
                    begin_player_phase();
                });
            else
                begin_player_phase();
        });
    }

    void spawn_wave_views(Next done)
    {
        hud->set_header(model.stage, model.wave_index, model.wave_count(), model.round_number);
        CombatantPtr boss;
        for (auto& e : model.enemies)
            if (B(e->def, "boss", false)) boss = e;
        auto spawn_rest = [this, boss, done] {
            for (auto& e : model.enemies)
            {
                if (e == boss) continue;
                Vec2 pos = enemy_pos(e);
                auto v = spawn_view(e, pos);
                v->set_position_x(v->position().x - 700);
                v->move_to(pos, 0.5f);
            }
            auto after = [this, done] {
                hud->set_enemies(model.enemies);
                wave_hints([this, done] {
                    std::string names;
                    for (auto& e : model.enemies) names += (names.empty() ? "" : ", ") + UIKit::fmt("%s Lv.%d", e->display_name.c_str(), e->level);
                    hud->add_log(UIKit::fmt("Wave %d: ", model.wave_index + 1) + names, UIKit::MUTED);
                    done();
                });
            };
            if (boss) boss_intro(boss, after);
            else gd::after(this, 0.55f, after);
        };
        if (!boss) hud->show_banner(UIKit::fmt("WAVE %d/%d", model.wave_index + 1, model.wave_count()), Col("#fff0c0"), 0.45f, "wave", "", spawn_rest);
        else spawn_rest();
    }

    void tween_dim(float to, float time, Next then = nullptr)
    {
        auto d = dim;
        auto tw = gd::tween(this);
        tw->prop([d] { return d->color().a; }, [d](float a) { d->set_color(d->color().with_alpha(a)); }, to, time);
        if (then) tw->callback(then);
    }

    // Ancient foe entrance: the field darkens, the boss stalks in as a silhouette with heavy steps,
    // its title appears, then the light returns.
    void boss_intro(const CombatantPtr& boss, Next done)
    {
        Vec2 pos = enemy_pos(boss);
        AudioManager::stop_music(0.3f);
        dim->setVisible(true);
        tween_dim(0.72f, 0.25f);
        auto v = spawn_view(boss, pos + Vec2(-520, 0));
        v->z_index = 8;
        v->set_silhouette(true);
        std::vector<Step> steps;
        steps.push_back([this](Next n) { gd::after(this, 0.25f, n); });
        steps.push_back([](Next n) { AudioManager::play_sfx("boss_sting"); n(); });
        for (int i = 0; i < 3; ++i)
            steps.push_back([this, v, pos, i](Next n) {
                auto tw = gd::tween(this);
                tw->position(v, pos + Vec2(-520.0f + 175.0f * (i + 1), 0), 0.24f).trans(gd::TRANS_QUAD);
                tw->on_finished([this, v, i, n] {
                    camera.shake(10.0f + i * 3.0f, 0.14f);
                    effects.particles("earth", v->position(), 10, 80.0f);
                    n();
                });
            });
        steps.push_back([this, boss](Next n) {
            hud->play_boss_title(boss->display_name);   // runs alongside the reveal (about 1.6 s)
            gd::after(this, 0.35f, n);
        });
        steps.push_back([this, v](Next n) {
            hud->flash_screen(Col("#c8ff9a"), 0.4f, 0.2f);
            tween_dim(0.0f, 0.35f);
            v->set_silhouette(false, 0.35f);
            camera.shake(16.0f, 0.3f);
            gd::after(this, 1.25f, n);
        });
        Chain::run(std::move(steps), [this, v, pos, done] {
            dim->setVisible(false);
            v->z_index = 0;
            v->home_pos = pos;
            AudioManager::play_music("boss");
            done();
        });
    }

    void begin_player_phase()
    {
        if (model.all_players_dead())
        {
            finish(false);
            return;
        }
        hud->set_header(model.stage, model.wave_index, model.wave_count(), model.round_number);
        for (auto& p : model.players)
            if (auto v = view_of(p); v && !p->guarding) v->set_guarding(false);
        selected = model.first_ready_player();
        if (!target || !target->is_alive()) auto_target();
        set_state(PLAYER);
        coach_check();
        auto_step();
    }

    // ------------------------------------------------------------------ coach marks (visual tutorial)
    CoachMark* _coach = nullptr;
    std::string _coach_step;

    // At most one coach mark at a time; each step is permanent once done.
    void coach_check()
    {
        if (state != PLAYER || skip_hints() || _coach || hud->auto_on) return;
        CombatantPtr ready_unit;
        for (auto& p : model.players)
            if (p->can_act() && p->burst_ready()) ready_unit = p;
        if (!GM.coach_done("tap_attack") && selected && hud->cards.count(selected.get()))
            show_coach("tap_attack", hud->cards[selected.get()], "Tap " + first_word(selected->display_name) + " to attack.", "tap");
        else if (ready_unit && !GM.coach_done("burst") && hud->cards.count(ready_unit.get()))
            show_coach("burst", hud->cards[ready_unit.get()], "Burst is full! Swipe up on " + first_word(ready_unit->display_name) + ".", "up");
        else if (model.alive(model.enemies).size() > 1 && !GM.coach_done("target") && GM.coach_done("tap_attack"))
            show_coach("target", hud->enemy_row, "Tap an enemy to choose your target.", "tap", false);
    }

    void show_coach(const std::string& step, gd::Control* ctrl, const std::string& text, const std::string& gesture, bool block = true)
    {
        _coach_step = step;
        auto c = CoachMark::show_on(hud, ctrl, text, gesture, block);
        _coach = c;
        c->finished.connect([this, c] {   // it also closes itself when its target disappears
            if (_coach == c) _coach = nullptr;
        });
    }

    // Completes the current coach step when the matching thing happened.
    void coach_progress(const std::string& event)
    {
        if (!_coach) return;
        bool any = event == "attack" || event == "burst" || event == "guard";
        bool done = (_coach_step == "tap_attack" && any) || (_coach_step == "burst" && event == "burst") ||
                    (_coach_step == "target" && (any || event == "target"));
        if (done)
        {
            GM.mark_coach_done(_coach_step);
            _coach->finish();
            _coach = nullptr;
            _coach_step.clear();
        }
    }

    void auto_target()
    {
        Units living = model.alive(model.enemies);
        set_target(living.empty() ? nullptr : living[0]);
    }

    // ------------------------------------------------------------------ input API (HUD, keyboard)
    void set_target(const CombatantPtr& e)
    {
        if (target)
            if (auto v = view_of(target)) v->set_targeted(false);
        target = e;
        if (target && target->is_alive())
            if (auto v = view_of(target)) v->set_targeted(true);
        hud->set_target_text(target);
    }

    void on_unit_selected(const CombatantPtr& c)
    {
        if (state != PLAYER || !c->can_act()) return;
        selected = c;
        refresh_hud();
    }

    // "attack" | "burst" | "guard" for `unit` (defaults to the next ready unit).
    // Ignored while anything is animating, so rapid taps can never double-act.
    void request_action(const std::string& action, CombatantPtr unit = nullptr)
    {
        if (unit) selected = unit;
        if (state != PLAYER || !selected || !selected->can_act()) return;
        if (action == "burst" && !selected->burst_ready())
        {
            hud->add_log(selected->display_name + "'s Burst gauge is not full yet.", UIKit::MUTED);
            return;
        }
        if (!target || !target->is_alive()) auto_target();
        CombatantPtr user = selected;
        coach_progress(action);
        if (_coach) _coach->setVisible(false);   // an unrelated coach step stays up; hide it while animating
        set_state(BUSY);
        Next after = [this] { after_player_action(); };
        if (action == "attack") executor.execute(model.plan_action(user, user->normal_skill, target), after);
        else if (action == "burst") executor.execute(model.plan_action(user, user->burst_skill, target, true), after);
        else if (action == "guard")
        {
            model.guard(*user);
            hud->add_log(user->display_name + " is guarding.", Col("#a8c4e0"));
            auto gv = view_of(user);
            gv->play_guard();
            effects.floating_text(gv->impact_point() + Vec2(0, -80), "GUARD", Col("#a8d0ff"), 40);
            effects.shield_dome(gv->position(), Col("#a8d0ff"), gv->visual_height() * 0.6f, 0.25f);
            AudioManager::play_sfx("guard");
            gd::after(this, 0.4f, after);
        }
    }

    void after_player_action()
    {
        check_wave_end([this](bool moved_on) {
            if (moved_on) return;
            if (model.players_can_act())
            {
                selected = model.first_ready_player();
                set_state(PLAYER);
                if (_coach) _coach->setVisible(true);
                coach_check();
                auto_step();
            }
            else
                enemy_phase();
        });
    }

    // cb(true) if the battle moved on (next wave or victory).
    void check_wave_end(std::function<void(bool)> cb)
    {
        if (!model.all_enemies_dead())
        {
            cb(false);
            return;
        }
        gd::after(this, 0.5f, [this, cb] {
            if (model.has_next_wave())
            {
                for (auto it = views.begin(); it != views.end();)
                {
                    if (it->first->is_player) { ++it; continue; }
                    it->second->queue_free();
                    it = views.erase(it);
                }
                target = nullptr;
                hud->set_enemies({});
                model.advance_wave();
                show_wave_recovery();
                spawn_wave_views([this, cb] {
                    begin_player_phase();
                    cb(true);
                });
            }
            else
            {
                finish(true);
                cb(true);
            }
        });
    }

    void show_wave_recovery()
    {
        if (DB.balancef("combat", "wave_recovery_percent", 0.0) <= 0.0) return;
        for (auto& p : model.alive(model.players))
        {
            auto v = view_of(p);
            effects.floating_text(v->impact_point() + Vec2(0, -60), "RECOVER", Col("#8ae05a"), 30);
            effects.particles("heal", v->impact_point(), 8, 360.0f);
            v->flash(Col("#8ae05a"), 0.3f);
            pulse_card(p, Col("#8ae05a"));
        }
    }

    void enemy_phase()
    {
        set_state(ENEMY);
        auto stop = std::make_shared<bool>(false);   // Godot `break`
        std::vector<Step> steps;
        for (auto& e : model.enemy_turn_order())
            steps.push_back([this, e, stop](Next next) {
                if (*stop || !e->is_alive()) return next();
                if (model.all_players_dead())
                {
                    *stop = true;
                    return next();
                }
                gd::after(this, 0.15f, [this, e, stop, next] {
                    check_phase2(e, [this, e, stop, next] {
                        Next post = [this, stop, next] {
                            if (model.all_players_dead() || model.all_enemies_dead()) *stop = true;
                            next();
                        };
                        EnemyDecision act = model.decide(e);
                        if (act.type == "charge") start_charge(e, act.skill_id, post);
                        else if (act.type == "summon") summon(e, post);
                        else
                        {
                            std::string t = S(DB.skill(act.skill_id), "target", "enemy_single");
                            if (!act.target && (t == "enemy_single" || t == "enemy_all"))
                            {
                                *stop = true;
                                return next();
                            }
                            executor.execute(model.plan_action(e, act.skill_id, act.target), post);
                        }
                    });
                });
            });
        Chain::run(std::move(steps), [this] {
            if (model.all_players_dead()) gd::after(this, 0.6f, [this] { finish(false); });
            else end_round();
        });
    }

    // Telegraph: the enemy glows and a WARNING band tells the player what is coming.
    void start_charge(const CombatantPtr& e, const std::string& skill_id, Next done)
    {
        model.begin_charge(*e, skill_id);
        auto v = view_of(e);
        std::string skill_name = S(DB.skill(skill_id), "name", "a powerful attack");
        hud->add_log(e->display_name + " is charging " + skill_name + "! Guard to halve the damage.", Col("#ffb04a"));
        if (v)
        {
            v->anticipate(Col("#ffcf4a"), 0.5f);
            effects.particles(e->element, v->impact_point(), 16, 360.0f);
        }
        hud->show_warning("WARNING", e->display_name + " is charging " + skill_name + "!", [this, done] {
            if (!_warned_charge && !GM.hint_seen("charge") && !skip_hints() && DB.hints.contains("charge"))
            {
                _warned_charge = true;
                hud->show_hint(DB.hints["charge"], [done] {
                    GM.mark_hint_seen("charge");
                    done();
                });
            }
            else
                done();
        });
    }

    // Boss phase 2: announcement, enrage flash and (optionally) a queued skill.
    void check_phase2(const CombatantPtr& e, Next done)
    {
        Json p2 = model.check_phase2(*e);
        if (p2.empty()) return done();
        auto v = view_of(e);
        AudioManager::play_sfx("boss_sting");
        if (v)
        {
            v->flash(Col("#ff5a3a"), 0.6f);
            effects.ring(v->position(), Col("#ff7a4a"), 320, 0.6f, 16, 0.5f);
            effects.particles(e->element, v->impact_point(), 30, 360.0f);
        }
        camera.shake(18.0f, 0.4f);
        hud->add_log(S(p2, "announce", e->display_name + " grows furious!"), Col("#ff7a5a"));
        if (hud->plates.count(e.get())) hud->plates[e.get()]->refresh_phase();
        hud->show_warning("PHASE 2", S(p2, "announce"), done);
    }

    // A boss calls minions: they rise in front of it.
    void summon(const CombatantPtr& boss, Next done)
    {
        auto bv = view_of(boss);
        if (bv)
        {
            bv->anticipate(Col(DB.element_color(boss->element)).lightened(0.3f), 0.4f);
            bv->play_anim(bv->resolve_anim("special"));
        }
        AudioManager::play_sfx("summon_charge", 0.05f, -4.0f);
        gd::after(this, 0.4f, [this, boss, bv, done] {
            Units spawned = model.summon_minions(*boss);
            std::string names;
            for (auto& m : spawned)
            {
                Vec2 pos = enemy_pos(m);
                auto v = spawn_view(m, pos);
                v->set_alpha(0.0f);
                gd::tween(v)->alpha(v, 1.0f, 0.35f);
                effects.particles(m->element, pos + Vec2(0, -40), 16, 360.0f);
                effects.ring(pos, Col(DB.element_color(m->element)), 180, 0.4f, 10, 0.35f);
                names += (names.empty() ? "" : ", ") + m->display_name;
            }
            if (!spawned.empty())
            {
                hud->add_log(boss->display_name + " calls for help! " + names + " appears.", Col("#ffb0a0"));
                hud->set_enemies(model.alive(model.enemies));
                set_target(target);
            }
            gd::after(this, 0.5f, [bv, done] {
                if (bv) bv->play_idle();
                done();
            });
        });
    }

    // One-time tips for new mechanics met in a wave (elites...).
    void wave_hints(Next done)
    {
        if (skip_hints()) return done();
        std::vector<Step> steps;
        for (auto& e : model.enemies)
            if (e->is_elite)
                steps.push_back([this](Next n) {
                    if (DB.hints.contains("elites") && !GM.hint_seen("elites"))
                        hud->show_hint(DB.hints["elites"], [n] {
                            GM.mark_hint_seen("elites");
                            n();
                        });
                    else
                        n();
                });
        Chain::run(std::move(steps), done);
    }

    void end_round()
    {
        std::vector<Step> steps;
        for (auto& ev : model.end_round())
            steps.push_back([this, ev](Next next) {
                const CombatantPtr& unit = ev.unit;
                if (!unit->is_alive()) return next();
                auto v = view_of(unit);
                if (ev.type == "hot")
                {
                    int healed = model.apply_hot(unit, ev.amount);
                    if (v && healed > 0)
                    {
                        effects.particles("heal", v->impact_point(), 6, 360.0f);
                        effects.damage_number(v->impact_point() + Vec2(0, -60), healed, "heal", "REGEN");
                        pulse_card(unit, Col("#8ae05a"));
                    }
                    return gd::after(this, 0.12f, next);
                }
                int dealt = model.apply_dot(unit, ev.amount);
                bool poison = ev.status == "poison";
                if (v)
                {
                    effects.spawn(poison ? "hit_nature" : "hit_fire", v->impact_point(), false, 0.7f);
                    effects.particles(poison ? "nature" : "fire", v->impact_point(), 6);
                    effects.damage_number(v->impact_point() + Vec2(0, -60), dealt, "dot", poison ? "POISON" : "BURN");
                    hud->add_log(UIKit::fmt("%s suffers %d %s damage.", unit->display_name.c_str(), dealt, poison ? "poison" : "burn"),
                                 poison ? Col("#c08aff") : Col("#ffa04a"));
                    if (unit->is_alive()) v->hit_react();
                    else
                    {
                        v->play_defeat();
                        on_unit_defeated(unit);
                    }
                }
                gd::after(this, 0.25f, next);
            });
        Chain::run(std::move(steps), [this] {
            if (model.all_players_dead()) return finish(false);
            check_wave_end([this](bool moved_on) {
                if (moved_on) return;
                model.start_player_phase();
                begin_player_phase();
            });
        });
    }

    void on_unit_defeated(const CombatantPtr& c)
    {
        if (c == target) auto_target();
        if (c == selected) selected = model.first_ready_player();
        refresh_hud();
    }

    BattleResult* _result = nullptr;

    void finish(bool victory)
    {
        if (state == RESULT) return;
        set_state(RESULT);
        if (_coach) _coach->finish();
        _coach = nullptr;
        set_target(nullptr);
        set_battle_speed(1.0f, false);
        auto show = [this, victory] {
            auto result = BattleResult::create();
            _result = result;
            hud->add(result);
            if (victory) result->show_victory(result_summary, !GM.next_stage_id(stage_id).empty());
            else result->show_defeat();
            result->next_pressed.connect([this] {
                std::string next_id = GM.next_stage_id(stage_id);
                SceneRouter::leave_battle(map_scene(), {{"highlight", next_id.empty() ? stage_id : next_id}});
            });
            result->retry_pressed.connect([this] {
                if (B(GM.try_start_stage(stage_id), "ok", false)) SceneRouter::go("battle", {{"stage_id", stage_id}});
                else EnergyPopup::open(hud, stage_id);
            });
            result->party_pressed.connect([this] {
                SceneRouter::push_entry(map_scene(), {{"highlight", stage_id}, {"prepare", true}});
                if (GM.feature_unlocked("squad")) SceneRouter::go("squad", {{"return_to", map_scene()}, {"stage_id", stage_id}}, "replace");
                else SceneRouter::go("unit_detail", {{"uid", GM.leader_uid()}}, "replace");
            });
            result->stage_select_pressed.connect([this] { SceneRouter::leave_battle(map_scene(), {{"highlight", stage_id}}); });
            battle_finished.emit(victory);
        };
        if (victory)
        {
            for (auto& p : model.players) view_of(p)->play_victory();
            AudioManager::play_sting("victory");
            model.roll_stage_drops();
            result_summary = GM.apply_battle_result(stage_id, model.victory_data());
            hud->show_banner("VICTORY", UIKit::GOLD, 0.7f, "victory", "", show);
        }
        else
        {
            AudioManager::play_sting("defeat");
            GM.record_defeat();
            show();
        }
    }

    // Esc on PC opens the pause menu (UIManager calls this when no popup is open).
    void on_back() override { on_menu(); }

    void on_menu()
    {
        if (state != PLAYER) return;
        hud->show_menu([this] { SceneRouter::leave_battle(map_scene(), {{"highlight", stage_id}}); });
    }

    std::string map_scene() const { return DB.is_tower_stage(stage_id) ? "tower" : "stage_select"; }

    // ------------------------------------------------------------------ helpers
    void update_loot()
    {
        int drops = 0;
        for (auto& [k, v] : model.items_earned.items()) drops += I(v);
        hud->set_loot(model.gold_earned, drops);
    }

    // Brief global freeze on heavy impacts (skipped when Battle Effects are off). Real-time clock.
    std::vector<double> _stops;

    static void set_time_scale(float s) { ax::Director::getInstance()->getScheduler()->setTimeScale(s); }

    void hit_stop(float duration)
    {
        if (duration <= 0.0f || !fx_enabled()) return;
        _stops.push_back(gd::ticks() + duration / battle_speed);
        set_time_scale(0.05f * battle_speed);
    }

    // 1x / 2x battle speed (scales every animation, tween and timer in the battle).
    void set_battle_speed(float v, bool update_hud = true)
    {
        battle_speed = v >= 1.5f ? 2.0f : 1.0f;
        if (_stops.empty()) set_time_scale(battle_speed);
        if (update_hud) hud->set_speed(battle_speed);
    }

    // ------------------------------------------------------------------ auto battle
    bool _auto_pending = false;
    bool _warned_charge = false;

    bool popup_open()
    {
        for (auto ch : hud->children())
            if (dynamic_cast<FantasyPopup*>(ch)) return true;
        return false;
    }

    // Auto Battle: Bursts when useful, Guards against charged attacks, element-advantage targets.
    void auto_step()
    {
        if (!hud->auto_on || state != PLAYER || _auto_pending) return;
        _auto_pending = true;
        gd::after(this, 0.3f, [this] {
            _auto_pending = false;
            if (!hud->auto_on || state != PLAYER || popup_open())
            {
                if (hud->auto_on && state == PLAYER) gd::after(this, 0.5f, [this] { auto_step(); });
                return;
            }
            auto u = model.first_ready_player();
            if (!u) return;
            bool charging = false;
            for (auto& e : model.alive(model.enemies)) charging = charging || !e->charging_skill.empty();
            double lowest = 1.0;
            for (auto& p : model.alive(model.players)) lowest = std::min(lowest, p->hp_ratio());
            bool support = S(DB.skill(u->burst_skill), "target") == "ally_all";
            CombatantPtr best;
            double best_score = -INFINITY;
            for (auto& f : model.alive(model.enemies))
            {
                double score = DB.element_multiplier(u->element, f->element) * 1000.0 - f->hp_ratio() * 300.0;
                if (f->is_boss) score -= 150.0;
                if (score > best_score)
                {
                    best_score = score;
                    best = f;
                }
            }
            if (best) set_target(best);
            if (u->burst_ready() && (!support || lowest < 0.65 || charging)) request_action("burst", u);
            else if (charging && u->hp_ratio() < 0.5) request_action("guard", u);
            else request_action("attack", u);
        });
    }

    // Quick colour pulse on a hero's battle card (heals, buffs, recovery).
    void pulse_card(const CombatantPtr& c, const Col& color)
    {
        auto it = hud->cards.find(c.get());
        if (it == hud->cards.end()) return;
        auto card = it->second;
        auto tw = gd::tween(card);
        tw->modulate(card->frame, color.lightened(0.4f), 0.1f);
        tw->modulate(card->frame, Col::WHITE, 0.3f);
    }

    void set_dim(bool on)
    {
        dim->setVisible(true);
        tween_dim(on ? 0.45f : 0.0f, 0.2f, on ? Next() : Next([this] { dim->setVisible(false); }));
    }

    void refresh_hud()
    {
        bool can_input = state == PLAYER;
        hud->refresh(can_input, selected);
        for (auto& [c, v] : views)
            if (c->is_player) v->set_selected(can_input && c == selected);
    }

    void on_field_input(gd::InputEvent& e)
    {
        if (state != PLAYER || e.type != gd::Ev::PRESS) return;
        Vec2 world_pos = (e.local - vp() / 2) / camera.zoom + camera.position + camera.offset;
        for (auto& [c, v] : views)
            if (!c->is_player && c->is_alive() && v->hit_rect().has_point(world_pos))
            {
                set_target(c);
                AudioManager::play_sfx("target", 0.05f, -4.0f);
                coach_progress("target");
                e.accept();
                return;
            }
    }

    bool on_key(int key) override
    {
        using K = ax::EventKeyboard::KeyCode;
        K k = (K)key;
        if (_result && (k == K::KEY_ENTER || k == K::KEY_KP_ENTER)) return _result->handle_enter();
        if (state != PLAYER) return false;
        switch (k)
        {
        case K::KEY_A: request_action("attack"); return true;
        case K::KEY_B: request_action("burst"); return true;
        case K::KEY_G: request_action("guard"); return true;
        case K::KEY_TAB:
        case K::KEY_RIGHT_ARROW: cycle_target(1); return true;
        case K::KEY_LEFT_ARROW: cycle_target(-1); return true;
        default: break;
        }
        int idx = key - (int)K::KEY_1;
        if (idx >= 0 && idx < 5)
        {
            if (idx < (int)model.players.size()) on_unit_selected(model.players[idx]);
            return true;
        }
        return false;
    }

    void cycle_target(int dir)
    {
        Units living = model.alive(model.enemies);
        if (living.empty()) return;
        int n = (int)living.size();
        int i = int(std::find(living.begin(), living.end(), target) - living.begin());
        if (i >= n) i = -1;   // Godot find() returns -1
        set_target(living[((i + dir) % n + n) % n]);
    }
};
REGISTER_SCREEN("battle", BattleScreen)

// ================================================================== SkillExecutor
// Plays a planned action: anticipation, movement, animation, hit timing, impact (flash, particles,
// numbers, hit-stop, tiered shake), sounds and the per-hero Burst presentation.
static const float SHAKE_TINY[2] = {3.0f, 0.08f}, SHAKE_STRONG[2] = {8.0f, 0.14f}, SHAKE_BURST[2] = {15.0f, 0.22f},
                   SHAKE_BOSS[2] = {20.0f, 0.3f};

BattleModel& SkillExecutor::model() { return battle->model; }
BattleUnitView* SkillExecutor::view(const CombatantPtr& c) { return battle->view_of(c); }
void SkillExecutor::wait(float t, Next f) { BattleFx::wait(battle, t, std::move(f)); }

static int hit_count_of(const Plan& p)
{
    int n = 0;
    for (auto& t : p.targets) n = std::max(n, (int)t.hits.size());
    return n;
}

void SkillExecutor::execute(Plan plan, Next done)
{
    auto p = std::make_shared<Plan>(std::move(plan));
    auto user = p->user;
    auto uview = view(user);
    battle->hud->add_log(user->display_name + " uses " + S(p->skill, "name", "?") + "!",
                         p->is_burst ? UIKit::GOLD : (user->is_player ? UIKit::TEXT : Col("#ffb0a0")));
    Next motion = [this, p, uview, done] {
        Next after_motion = [this, p, done] {
            auto events = model().finish_action(*p);
            show_events(events, [this, p, done] {
                if (p->is_burst) burst_outro(p->user, done);
                else done();
            });
        };
        std::string m = S(p->skill, "motion", "melee");
        if (m == "melee") melee(p, uview, after_motion);
        else if (m == "ranged") ranged(p, uview, after_motion);
        else self_cast(p, uview, after_motion);
    };
    if (p->is_burst) burst_intro(user, p->skill, motion);
    else if (!user->is_player && S(p->skill, "kind") == "skill") enemy_special_windup(user, p->skill, motion);
    else motion();
}

// ------------------------------------------------------------------ anticipation
void SkillExecutor::enemy_special_windup(const CombatantPtr& user, const Json& skill, Next done)
{
    auto v = view(user);
    if (!v) return done();
    Col col(DB.element_color(user->element));
    v->anticipate(col.lightened(0.3f), 0.35f);
    battle->effects.floating_text(v->impact_point() + Vec2(0, -v->visual_height() * 0.7f), upper(S(skill, "name")), col.lightened(0.5f), 40);
    battle->effects.particles(user->element, v->impact_point(), 10);
    AudioManager::play_sfx("burst_ready", 0.1f, -8.0f);
    wait(0.35f, done);
}

// ------------------------------------------------------------------ motions
void SkillExecutor::melee(PlanPtr p, BattleUnitView* uview, Next done)
{
    if (p->targets.empty()) return done();
    bool is_player = p->user->is_player;
    Vec2 anchor;
    if (p->targets.size() == 1) anchor = view(p->targets[0].unit)->melee_anchor(is_player);
    else
    {
        Vec2 sum;
        for (auto& t : p->targets) sum += view(t.unit)->home_pos;
        anchor = sum / (float)p->targets.size() + Vec2(is_player ? 260.0f : -260.0f, 0);
    }
    if (!p->is_burst) battle->camera.focus(anchor, 1.04f, 0.25f);
    uview->z_index = 12;
    // anticipation: a short crouch before the lunge
    uview->anticipate(Col(1, 1, 1), 0.1f);
    wait(0.08f, [this, p, uview, anchor, done] {
        uview->move_to(anchor, DASH_TIME)->on_finished([this, p, uview, done] {
            std::string anim = uview->resolve_anim(S(p->skill, "anim", "attack"));
            float total = uview->play_anim(anim);
            run_hits(p, uview, anim, [this, p, uview, total, done](float elapsed) {
                wait(std::max(total - elapsed, 0.0f) + 0.05f, [this, p, uview, done] {
                    uview->return_home(RETURN_TIME)->on_finished([this, p, uview, done] {
                        uview->z_index = 0;
                        uview->play_idle();
                        if (!p->is_burst) battle->camera.reset(0.25f);
                        done();
                    });
                });
            });
        });
    });
}

// Applies hits at the animation frames listed in the skill. Reports the time spent.
void SkillExecutor::run_hits(PlanPtr p, BattleUnitView* uview, const std::string& anim, std::function<void(float)> done)
{
    int hit_count = hit_count_of(*p);
    const Json& frames_list = A(p->skill, "hit_frames");
    std::vector<float> times;
    int last_frame = -1, dupes = 0;
    for (int i = 0; i < hit_count; ++i)
    {
        int f = i < (int)frames_list.size() ? I(frames_list[i]) : (!frames_list.empty() ? I(frames_list.back()) : 2);
        dupes = f == last_frame ? dupes + 1 : 0;
        last_frame = f;
        times.push_back(SpriteFactory::frame_time(uview->sprite_def, anim, f) + dupes * MULTI_HIT_GAP);
    }
    auto elapsed = std::make_shared<float>(0.0f);
    std::vector<Step> steps;
    for (int i = 0; i < hit_count; ++i)
        steps.push_back([this, p, times, elapsed, i, hit_count](Next next) {
            wait(times[i] - *elapsed, [this, p, times, elapsed, i, hit_count, next] {
                *elapsed = std::max(*elapsed, times[i]);
                for (int ti = 0; ti < (int)p->targets.size(); ++ti) hit(p, ti, i, i == hit_count - 1);
                next();
            });
        });
    Chain::run(std::move(steps), [elapsed, done] { done(*elapsed); });
}

void SkillExecutor::ranged(PlanPtr p, BattleUnitView* uview, Next done)
{
    std::string anim = uview->resolve_anim(S(p->skill, "anim", "attack"));
    float total = uview->play_anim(anim);
    float release = SpriteFactory::frame_time(uview->sprite_def, anim, I(p->skill, "release_frame", 2));
    bool is_player = p->user->is_player;
    // cast glow gathers while the staff / fins rise
    battle->effects.particles(p->user->element, uview->impact_point() + Vec2(is_player ? -60.0f : 60.0f, -20), 8, 360.0f);
    wait(release, [this, p, uview, total, release, is_player, done] {
        AudioManager::play_sfx(S(p->skill, "sfx_cast", "water"));
        Vec2 from = uview->impact_point() + Vec2(is_player ? -70.0f : 70.0f, -10);
        std::string proj = S(p->skill, "projectile");
        gd::TweenRef last_tween;
        for (auto& t : p->targets) last_tween = battle->effects.projectile(proj, from, view(t.unit)->impact_point(), PROJECTILE_TIME, is_player);
        Next after = [this, p, uview, total, release, is_player, from, proj, done] {
            int hit_count = hit_count_of(*p);
            std::vector<Step> steps;
            for (int i = 0; i < hit_count; ++i)
                steps.push_back([this, p, i, hit_count, from, proj, is_player](Next next) {
                    for (int ti = 0; ti < (int)p->targets.size(); ++ti) hit(p, ti, i, i == hit_count - 1);
                    if (i >= hit_count - 1) return next();
                    // the stream keeps pouring: extra small projectiles for follow-up hits
                    for (auto& t : p->targets) battle->effects.projectile(proj, from, view(t.unit)->impact_point(), 0.12f, is_player);
                    wait(0.12f, next);
                });
            Chain::run(std::move(steps), [this, uview, total, release, hit_count, done] {
                float spent = release + PROJECTILE_TIME + 0.12f * (hit_count - 1);
                wait(std::max(total - spent, 0.0f) + 0.1f, [uview, done] {
                    uview->play_idle();
                    done();
                });
            });
        };
        if (last_tween) last_tween->on_finished(after);
        else after();
    });
}

void SkillExecutor::self_cast(PlanPtr p, BattleUnitView* uview, Next done)
{
    auto& fx = battle->effects;
    std::string anim = uview->resolve_anim(S(p->skill, "anim", "burst"));
    float total = uview->play_anim(anim);
    float release = SpriteFactory::frame_time(uview->sprite_def, anim, I(p->skill, "release_frame", 4));
    auto user = p->user;
    std::string style = S(p->skill, "burst_fx");
    Col col(DB.element_color(user->element));
    if (style == "tide_ring")
    {
        // water gathers around Mira before the wave breaks
        fx.ring(uview->position(), Col("#5ac8ff"), 160, release, 10, 0.4f);
        fx.particles("water", uview->impact_point(), 12, 360.0f);
    }
    else if (style == "hearth_hymn" || style == "bloom" || style == "litany" || style == "bulwark")
    {
        fx.ring(uview->position(), col.lightened(0.3f), 150, release, 10, 0.4f);
        fx.particles(user->element, uview->impact_point(), 12, 360.0f);
    }
    wait(release, [this, p, uview, total, release, style, user, done] {
        auto& fx = battle->effects;
        AudioManager::play_sfx(S(p->skill, "sfx_cast", "burst"));
        std::string field = S(p->skill, "field_effect");
        // skills that hit foes (e.g. a whirlpool or a curse on every enemy) play on the targets
        Units field_units;
        for (auto& t : p->targets) field_units.push_back(t.unit);
        if (field_units.empty() || S(p->skill, "target") == "ally_all") field_units = model().alive(model().allies_of(*user));
        for (auto& ally : field_units)
        {
            auto v = view(ally);
            if (!v) continue;
            if (field == "roots") fx.spawn(field, v->position() + Vec2(user->is_player ? -40.0f : 40.0f, -110), user->is_player, 1.0f, 5);
            else if (!field.empty()) fx.spawn(field, v->position() + Vec2(0, -10), false, 1.0f, -1);
            if (style == "tide_ring")
            {
                fx.ring(v->position(), Col("#8ae0ff"), 200, 0.5f, 12, 0.4f);
                fx.particles("heal", v->impact_point(), 14, 360.0f);
            }
            else if (style == "grove_bastion")
            {
                fx.shield_dome(v->position(), Col("#8ae05a"), v->visual_height() * 0.62f, 0.7f);
                fx.particles("earth", v->position() + Vec2(0, -10), 16, 70.0f);
                fx.ring(v->position(), Col("#8ae05a"), 220, 0.55f, 12, 0.4f);
            }
            else if (style == "bulwark")
            {
                fx.shield_dome(v->position(), Col("#8ad8ff"), v->visual_height() * 0.62f, 0.7f);
                fx.ring(v->position(), Col("#8ad8ff"), 220, 0.55f, 12, 0.4f);
            }
            else if (style == "hearth_hymn")
            {
                fx.ring(v->position(), Col("#ffcf6a"), 210, 0.5f, 12, 0.4f);
                fx.particles("fire", v->impact_point(), 12, 360.0f);
            }
            else if (style == "bloom")
            {
                fx.spawn("petal_burst", v->impact_point(), false, 1.0f, -1);
                fx.particles("heal", v->impact_point(), 14, 360.0f);
            }
            else if (style == "litany")
                fx.ring(v->position(), Col("#b08aff"), 200, 0.5f, 12, 0.4f);
        }
        if (style == "litany")
            for (auto& f : model().alive(model().foes_of(*user)))
                if (auto fv = view(f)) fx.spawn("hex_cloud", fv->impact_point(), false, 1.0f, -1);
        float shake = (float)F(p->skill, "shake", 0.0);
        if (shake > 0.0f) battle->camera.shake(6.0f + 10.0f * shake, 0.25f);
        if (style == "grove_bastion" || style == "bloom") battle->hud->flash_screen(Col("#8ae05a"), 0.2f, 0.18f);
        else if (style == "tide_ring" || style == "bulwark") battle->hud->flash_screen(Col("#8ae0ff"), 0.2f, 0.18f);
        else if (style == "hearth_hymn") battle->hud->flash_screen(Col("#ffcf6a"), 0.2f, 0.18f);
        else if (style == "litany") battle->hud->flash_screen(Col("#b08aff"), 0.2f, 0.18f);
        // damage part (all-target casts)
        int hit_count = hit_count_of(*p);
        auto spent = std::make_shared<float>(0.0f);
        std::vector<Step> steps;
        for (int i = 0; i < hit_count; ++i)
            steps.push_back([this, p, i, hit_count, spent](Next next) {
                for (int ti = 0; ti < (int)p->targets.size(); ++ti) hit(p, ti, i, i == hit_count - 1);
                if (i >= hit_count - 1) return next();
                *spent += 0.12f;
                wait(0.12f, next);
            });
        Chain::run(std::move(steps), [this, uview, total, release, spent, done] {
            wait(std::max(total - release - *spent, 0.2f), [uview, done] {
                uview->play_idle();
                done();
            });
        });
    });
}

// ------------------------------------------------------------------ hits
void SkillExecutor::hit(const PlanPtr& p, int ti, int hi, bool is_final)
{
    auto& fx = battle->effects;
    PlanTarget& entry = p->targets[ti];
    CombatantPtr target = entry.unit;
    HitResult result = model().apply_hit(*p, ti, hi);
    if (result.skipped) return;
    const Json& skill = p->skill;
    auto user = p->user;
    bool is_burst = p->is_burst;
    std::string style = S(skill, "burst_fx");
    auto tv = view(target);
    Vec2 point = tv->impact_point();
    bool flip = user->is_player;   // effects drawn facing right; mirror for player attacks
    std::string slash = S(skill, "hit_effect");
    bool finisher = is_final && is_burst;
    if (finisher && skill.contains("final_effect")) slash = S(skill, "final_effect");
    fx.spawn(slash, point + Vec2(randf_range(-12, 12), randf_range(-16, 16)), flip, finisher ? 1.3f : 1.0f);
    fx.spawn(S(skill, "impact_effect", "hit_spark"), point + Vec2(randf_range(-30, 30), randf_range(-30, 30)), flip, finisher ? 1.5f : 0.8f);
    fx.particles(user->element, point, finisher ? 18 : (entry.crit ? 10 : 6));
    if (is_burst)
    {
        if (style == "ember_rush") fx.streaks(point, Col("#ff9a3a"), finisher ? 7 : 3);
        else if (style == "frost_waltz") fx.streaks(point, Col("#bff4ff"), finisher ? 7 : 3);
        else if (style == "volley") fx.streaks(point, Col("#aef07a"), finisher ? 5 : 2);
    }

    // ---- number
    std::string kind = target->is_player ? "player" : "normal", icon;
    if (entry.tag == "WEAK")
    {
        kind = "advantage";
        icon = "assets/icons/orb_" + user->element + ".png";
    }
    else if (entry.tag == "RESIST")
        kind = "resist";
    if (entry.crit) kind = "crit";
    if (finisher && p->targets.size() == 1) kind = "finisher";
    Vec2 stagger(float((hi % 3 - 1) * 70), float(-(hi % 3) * 30));
    if (result.absorbed > 0)
    {
        fx.floating_text(point + Vec2(0, -90) + stagger, UIKit::fmt("ABSORB %d", result.absorbed), Col("#8ad8ff"), 28);
        fx.shield_dome(tv->position(), Col("#8ad8ff"), tv->visual_height() * 0.6f, 0.25f);
    }
    if (result.dealt > 0 || result.absorbed == 0)
        fx.damage_number(point + Vec2(0, -30) + stagger, result.dealt, kind, hi == 0 ? entry.tag : "", icon);
    AudioManager::play_sfx(S(skill, "sfx_hit", "hit"), 0.08f);

    // ---- impact: flash frame, hit-stop and tiered shake
    bool user_boss = B(user->def, "boss", false);
    bool boss_hit = user_boss || (B(target->def, "boss", false) && is_final);
    const float* tier = nullptr;
    if (finisher)
    {
        tier = SHAKE_BURST;
        battle->hud->flash_screen(Col(DB.element_color(user->element)).lightened(0.5f), 0.35f, 0.14f);
        fx.ring(tv->position(), Col(DB.element_color(user->element)).lightened(0.3f), 260, 0.4f, 12, 0.35f);
        battle->hit_stop(0.1f);
    }
    else if (entry.crit)
    {
        tier = SHAKE_STRONG;
        battle->hud->flash_screen(Col::WHITE, 0.18f, 0.08f);
        battle->hit_stop(0.06f);
    }
    else if (F(skill, "shake", 0.0) > 0.0 && (is_final || !is_burst))
        tier = SHAKE_STRONG;
    else if (is_final && !is_burst)
    {
        tier = SHAKE_TINY;
        battle->hit_stop(0.03f);
    }
    if (user_boss && is_final)
    {
        tier = SHAKE_BOSS;
        battle->hit_stop(0.07f);
    }
    else if (boss_hit && !tier)
        tier = SHAKE_TINY;
    if (tier) battle->camera.shake(tier[0], tier[1]);

    if (hi == 0 && entry.tag == "WEAK") battle->hud->add_log("  Elemental advantage!", Col("#ff9a5a"));
    else if (hi == 0 && entry.tag == "RESIST") battle->hud->add_log("  The attack is resisted...", Col("#9ab4d0"));
    if (result.killed)
    {
        battle->hud->add_log(target->display_name + " was defeated!", target->is_player ? UIKit::DANGER : UIKit::MUTED);
        tv->play_defeat();
        fx.particles(target->element, point, 20);
        AudioManager::play_sfx(target->is_player ? "ko" : "enemy_die");
        if (!target->is_player) battle->hit_stop(0.05f);
        battle->on_unit_defeated(target);
    }
    else
        tv->hit_react(finisher || entry.crit ? 26.0f : 14.0f);
}

void SkillExecutor::show_events(const std::vector<BattleEvent>& events, Next done)
{
    auto healed = std::make_shared<bool>(false);
    std::vector<Step> steps;
    for (auto& e : events)
        steps.push_back([this, e, healed](Next next) {
            auto v = view(e.unit);
            if (!v) return next();
            auto& fx = battle->effects;
            if (e.type == "heal")
            {
                fx.damage_number(v->impact_point() + Vec2(0, -40), e.amount, "heal");
                battle->hud->add_log(UIKit::fmt("  %s recovers %d HP.", e.unit->display_name.c_str(), e.amount), UIKit::GOOD);
                v->flash(Col("#8ae05a"), 0.3f);
                battle->pulse_card(e.unit, Col("#8ae05a"));
                if (!*healed)
                {
                    AudioManager::play_sfx("heal");
                    *healed = true;
                }
            }
            else if (e.type == "status")
            {
                const Json& sdef = DB.status(e.status);
                Col c(S(sdef, "color", "#ffffff"));
                fx.floating_text(v->impact_point() + Vec2(0, -120), upper(S(sdef, "name")), c, 30);
                battle->hud->add_log("  " + e.unit->display_name + ": " + S(sdef, "name"), c);
                if (!B(sdef, "negative", false)) battle->pulse_card(e.unit, c);
            }
            else if (e.type == "cleanse")
                fx.floating_text(v->impact_point() + Vec2(0, -160), "CLEANSED", Col("#bff4ff"), 30);
            else if (e.type == "shield")
            {
                fx.shield_dome(v->position(), Col("#8ad8ff"), v->visual_height() * 0.62f, 0.6f);
                fx.floating_text(v->impact_point() + Vec2(0, -120), UIKit::fmt("SHIELD %d", e.amount), Col("#8ad8ff"), 30);
                battle->hud->add_log(UIKit::fmt("  %s gains a %d-point Shield.", e.unit->display_name.c_str(), e.amount), Col("#8ad8ff"));
                battle->pulse_card(e.unit, Col("#8ad8ff"));
            }
            else if (e.type == "burst")
            {
                fx.floating_text(v->impact_point() + Vec2(0, -150), UIKit::fmt("BURST +%d", e.amount), UIKit::GOLD, 28);
                battle->pulse_card(e.unit, UIKit::GOLD);
            }
            wait(0.06f, next);
        });
    Chain::run(std::move(steps), done);
}

// ------------------------------------------------------------------ burst presentation
// darken -> cut-in (hero + burst name) -> charge-up effect -> restore light.
void SkillExecutor::burst_intro(const CombatantPtr& user, const Json& skill, Next done)
{
    AudioManager::play_sfx("burst");
    auto uview = view(user);
    uview->z_index = 12;
    battle->set_dim(true);
    battle->camera.focus(uview->position(), 1.07f, 0.3f);
    std::string style = S(skill, "burst_fx");
    battle->hud->play_burst_cutin(user, skill, [this, user, uview, style, done] {
        // charge: element aura gathers on the hero
        auto& fx = battle->effects;
        Col col(DB.element_color(user->element));
        uview->flash(col.lightened(0.4f), 0.3f);
        fx.ring(uview->position(), col.lightened(0.3f), 170, 0.3f, 10, 0.4f);
        fx.particles(user->element, uview->impact_point(), 20, 360.0f);
        if (style == "ember_rush") fx.streaks(uview->impact_point(), Col("#ffb03a"), 4);
        else if (style == "frost_waltz") fx.streaks(uview->impact_point(), Col("#bff4ff"), 4);
        wait(0.18f, [this, done] {
            battle->set_dim(false);
            done();
        });
    });
}

void SkillExecutor::burst_outro(const CombatantPtr& user, Next done)
{
    if (auto uview = view(user)) uview->z_index = 0;
    battle->camera.reset(0.3f)->on_finished(done);
}
