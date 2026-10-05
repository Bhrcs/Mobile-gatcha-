// World-side battle presentation: battle_camera.gd, battle_stage.gd, battle_unit_view.gd, effects_layer.gd.
#include "battle/BattleScene.h"
#include <cmath>

using namespace BattleFx;
static constexpr float PI_F = 3.14159265f;
static float deg(float rad) { return rad * 180.0f / PI_F; }
static uint8_t u8(float v) { return (uint8_t)std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f); }

static ax::Sprite* spr(ax::Texture2D* t)
{
    return t ? ax::Sprite::createWithTexture(t) : ax::Sprite::create();
}

namespace BattleFx
{
float randf_range(float a, float b)
{
    static Rng rng;
    return (float)rng.randf_range(a, b);
}
bool fx_enabled() { return B(GM.settings, "battle_effects", true); }
void wait(ax::Node* owner, float t, Next f)
{
    if (t > 0.0f) gd::after(owner, t, std::move(f));
    else f();
}
void free_later(ax::Node* n)
{
    n->retain();
    gd::defer([n] {
        n->removeFromParent();
        n->release();
    });
}
}  // namespace BattleFx

// ================================================================== BattleCamera
void BattleCamera::process(float dt)
{
    if (_shake_time > 0.0f)
    {
        _shake_time -= dt;
        float k = _shake_time / std::max(_shake_duration, 0.001f);
        offset = Vec2(randf_range(-1, 1), randf_range(-1, 1)) * _shake_strength * k;
        if (_shake_time <= 0.0f) offset = Vec2::ZERO;
    }
}

void BattleCamera::shake(float strength, float duration)
{
    if (!B(GM.settings, "screen_shake", true)) return;
    _shake_strength = std::min(strength, 24.0f);
    _shake_duration = duration;
    _shake_time = duration;
}

gd::TweenRef BattleCamera::move(Vec2 to, float z, float time)
{
    auto tw = _move_tween.start(owner);
    tw->set_parallel();
    tw->prop([this] { return zoom; }, [this](float v) { zoom = v; }, z, time).trans(gd::TRANS_SINE).ease(gd::EASE_IN_OUT);
    tw->prop2([this] { return position; }, [this](Vec2 v) { position = v; }, to, time).trans(gd::TRANS_SINE).ease(gd::EASE_IN_OUT);
    return tw;
}

gd::TweenRef BattleCamera::focus(Vec2 point, float zoom_amount, float time)
{
    float z = std::clamp(zoom_amount, 1.0f, MAX_ZOOM);
    Vec2 d = point - base_position;
    if (d.length() > MAX_OFFSET) d = d.getNormalized() * MAX_OFFSET;
    return move(base_position + d * (z - 1.0f) * 2.5f, z, time);
}

gd::TweenRef BattleCamera::reset(float time) { return move(base_position, 1.0f, time); }

// ================================================================== BattleStage
void BattleStage::setup(gd::Node2D* world, const std::string& bg_name, bool is_boss, BattleCamera* cam)
{
    _world = world;
    env = bg_name.rfind("bg_", 0) == 0 ? bg_name.substr(3) : bg_name;
    const std::string dir = "assets/environments/battle/";
    if (!gd::exists(dir + env + "_ground.png")) env = "forest";
    boss = is_boss;
    _camera = cam;
    // sky fill above the art so very tall screens never show a gap
    Col sky = Col::BLACK;
    auto img = new ax::Image();
    if (img->initWithImageFile(dir + env + "_far.png") && img->getBitPerPixel() >= 24)
    {
        auto d = img->getData();
        sky = Col(d[0] / 255.0f, d[1] / 255.0f, d[2] / 255.0f, img->getBitPerPixel() == 32 ? d[3] / 255.0f : 1.0f);
    }
    img->release();
    _sky = ax::DrawNode::create();
    _sky->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);
    ax::Vec2 poly[4] = {gd::p2(-600, -4000), gd::p2(1800, -4000), gd::p2(1800, 40), gd::p2(-600, 40)};
    _sky->drawSolidPoly(poly, 4, sky.c4f());
    world->addChild(_sky, -23 * ZK);
    struct Layer { const char* name; float factor; int z; };
    for (auto l : {Layer{"far", 0.45f, -12}, Layer{"mid", 0.3f, -11}, Layer{"ground", 0.0f, -10}, Layer{"fore", -0.22f, 30}})
    {
        auto s = spr(gd::texture(dir + env + "_" + l.name + ".png"));
        s->setScale(PX);
        world->addChild(s, (l.z - 10) * ZK);   // the stage node itself sits at z -10
        _sprites.push_back(s);
        _factors.push_back(l.factor);
    }
    add_ambient();
}

void BattleStage::fit(Vec2 view_size, float field_bottom)
{
    bottom_y = field_bottom + 60.0f;
    _view = view_size;
    _base_cam = _camera ? _camera->position : view_size / 2;
    _homes.clear();
    for (auto s : _sprites)
    {
        Vec2 home(view_size.x / 2, bottom_y - IMG_H * PX / 2);
        s->setPosition(gd::p2(home));
        _homes.push_back(home);
    }
    _sky->setPosition(gd::p2(0, bottom_y - IMG_H * PX));
    place_ambient(view_size);
}

void BattleStage::process(float dt)
{
    _t += dt;
    if (_camera)
    {
        Vec2 d = _camera->position - _base_cam;
        for (size_t i = 0; i < _sprites.size() && i < _homes.size(); ++i) _sprites[i]->setPosition(gd::p2(_homes[i] + d * _factors[i]));
    }
    if (_fog)
    {
        _fog->setOpacity(u8(0.5f + 0.25f * std::sin(_t * 0.6f)));
        _fog->setPositionX(std::sin(_t * 0.15f) * 60.0f + _view.x / 2);
    }
    if (boss && !_sprites.empty())
    {
        float k = 0.92f + 0.08f * std::sin(_t * 1.6f);
        _sprites[0]->setColor(Col(k, k * 1.02f, k).c3b());
    }
}

void BattleStage::add_ambient()
{
    float dense = boss ? 1.6f : 1.0f;
    auto add = [this](gd::ParticleCfg c, const char* kind) { _ambient.push_back({c, kind}); };
    if (env == "forest")
    {
        add(particles(int(14 * dense), Col("#8ac050"), Col("#4a7e30"), Vec2(20, 50), 7.0f, 6, 9), "sky");
        add_rays(Col(1.0f, 0.95f, 0.7f, 0.10f));
    }
    else if (env == "ruins")
        add(particles(int(18 * dense), Col("#f0e8d0"), Col(0.9f, 0.85f, 0.7f, 0), Vec2(8, -6), 6.0f, 4, 6), "field");
    else if (env == "scorched")
    {
        add(particles(int(30 * dense), Col("#ffd35a"), Col(1, 0.3f, 0.1f, 0), Vec2(6, -60), 4.0f, 4, 8), "ground");
        add_fog(Col(0.35f, 0.18f, 0.14f, 0.45f));
    }
    else if (env == "flooded")
    {
        add(particles(int(22 * dense), Col("#e0f8ff"), Col(0.6f, 0.9f, 1, 0), Vec2(0, 0), 1.6f, 3, 6), "water");
        add_fog(Col(0.75f, 0.85f, 0.9f, 0.35f));
    }
    else if (env == "heart")
    {
        add(particles(int(24 * dense), Col("#c8ff9a"), Col(0.4f, 0.9f, 0.3f, 0), Vec2(4, -24), 5.0f, 4, 8), "field");
        add_rays(Col(0.7f, 1.0f, 0.6f, boss ? 0.12f : 0.08f));
        if (boss) add_fog(Col(0.2f, 0.4f, 0.2f, 0.35f));
    }
}

// Particles are (re)created in place_ambient, once their emission area is known.
gd::ParticleCfg BattleStage::particles(int amount, const Col& c0, const Col& c1, Vec2 gravity, float life, float smin, float smax)
{
    if (!fx_enabled()) amount = std::max(4, amount / 3);
    gd::ParticleCfg p;
    p.amount = amount;
    p.lifetime = life;
    p.preprocess = life;
    p.gravity = gravity;
    p.vel_min = 5;
    p.vel_max = 25;
    p.direction = Vec2(0.3f, 1);
    p.spread = 60;
    p.scale_min = smin;
    p.scale_max = smax;
    p.ramp = {c0, c1};
    return p;
}

void BattleStage::add_rays(const Col& col)
{
    for (int i = 0; i < 3; ++i)
    {
        auto r = ax::DrawNode::create();
        r->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);   // plain (non-premultiplied) colours
        float x = 260.0f + i * 260.0f;
        ax::Vec2 poly[4] = {gd::p2(x - 40, 0), gd::p2(x + 30, 0), gd::p2(x + 260, 1400), gd::p2(x + 90, 1400)};
        r->drawSolidPoly(poly, 4, col.c4f());
        r->setBlendFunc(ax::BlendFunc::ADDITIVE);
        _world->addChild(r, -19 * ZK);
        _rays.push_back(r);
        auto tw = gd::tween(r);
        tw->loops();
        tw->opacity(r, 0.4f, 2.0f + i * 0.7f).trans(gd::TRANS_SINE);
        tw->opacity(r, 1.0f, 2.0f + i * 0.7f).trans(gd::TRANS_SINE);
    }
}

void BattleStage::add_fog(const Col& col)
{
    auto gt = gd::gradient_texture({{0.0f, col.with_alpha(0)}, {0.5f, col}, {1.0f, col.with_alpha(0)}}, 8, 64);
    _fog = spr(gt);
    _fog->setScale(190, 5);
    _world->addChild(_fog, -19 * ZK);
}

void BattleStage::place_ambient(Vec2 vs)
{
    float hz = horizon_y();
    for (auto& a : _ambient)
    {
        Vec2 pos;
        if (a.kind == "sky")
        {
            pos = Vec2(vs.x / 2, hz - 500);
            a.cfg.emission_rect = Vec2(vs.x / 2, 60);
        }
        else if (a.kind == "ground")
        {
            pos = Vec2(vs.x / 2, bottom_y - 200);
            a.cfg.emission_rect = Vec2(vs.x / 2, 180);
            a.cfg.direction = Vec2(0, -1);
        }
        else if (a.kind == "water")
        {
            pos = Vec2(vs.x / 2, (hz + bottom_y) / 2);
            a.cfg.emission_rect = Vec2(vs.x / 2, (bottom_y - hz) / 2);
            a.cfg.vel_max = 2;
        }
        else
        {
            pos = Vec2(vs.x / 2, (hz + bottom_y) / 2 - 150);
            a.cfg.emission_rect = Vec2(vs.x / 2, (bottom_y - hz) / 2 + 150);
        }
        if (a.node) a.node->removeFromParent();
        a.node = gd::Particles::create(a.cfg);
        a.node->set_position(pos);
        _world->addChild(a.node, 15 * ZK);
    }
    if (_fog) _fog->setPosition(gd::p2(vs.x / 2, hz + 40));
    for (auto r : _rays) r->setPosition(gd::p2(-200, hz - 1300));
}

// ================================================================== BattleUnitView
static ax::Texture2D* make_tex(int w, int h, const std::function<bool(float, float)>& inside, const Col& c)
{
    std::vector<uint8_t> px(size_t(w) * h * 4, 0);
    auto col = c.c4b();
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
            if (inside((x - (w - 1) / 2.0f) / ((w - 1) / 2.0f), (y - (h - 1) / 2.0f) / ((h - 1) / 2.0f)))
            {
                uint8_t* p = &px[(size_t(y) * w + x) * 4];
                p[0] = col.r; p[1] = col.g; p[2] = col.b; p[3] = col.a;
            }
    auto t = new ax::Texture2D();   // kept for the whole run (like Godot's static cache)
    t->initWithData(px.data(), px.size(), ax::backend::PixelFormat::RGBA8, w, h);
    t->setAliasTexParameters();
    return t;
}
static ax::Texture2D* shadow_tex()
{
    static auto t = make_tex(28, 8, [](float dx, float dy) { return dx * dx + dy * dy <= 1.0f; }, Col::WHITE);
    return t;
}
static ax::Texture2D* ring_tex()
{
    static auto t = make_tex(30, 10, [](float dx, float dy) { float d = dx * dx + dy * dy; return d <= 1.0f && d >= 0.55f; }, Col("#ffc14a"));
    return t;
}
static ax::Texture2D* target_frame(int i) { return gd::texture("assets/ui/v2_target_" + std::to_string(i) + ".png"); }

BattleUnitView* BattleUnitView::make(const CombatantPtr& c, Vec2 pos, float scale_mult)
{
    auto v = gd::make<BattleUnitView>();
    v->combatant = c;
    v->home_pos = pos;
    v->set_position(pos);
    v->sprite_def = O(c->def, "sprite");
    v->unit_scale = (float)F(v->sprite_def, "scale", 5) * scale_mult;
    v->frame_size = SpriteFactory::frame_size(v->sprite_def);
    v->build();
    gd::listen(v, c->statuses_changed, [v] { v->refresh_statuses(); });
    v->play_idle();
    v->scheduleUpdate();
    return v;
}

void BattleUnitView::build()
{
    float k = frame_size.x / 48.0f;
    _shadow = spr(shadow_tex());
    _shadow->setScale(unit_scale * k);
    _shadow->setColor(ax::Color3B::BLACK);
    _shadow->setOpacity(u8(0.35f));
    addChild(_shadow);

    _select_ring = spr(ring_tex());
    _select_ring->setScale(unit_scale * k);
    _select_ring->setVisible(false);
    addChild(_select_ring);

    // animated ember sigil on the ground under the current target
    _target_ring = spr(target_frame(0));
    _target_ring->setScale(6.0f * k, 2.4f * k);
    _target_ring->setPosition(gd::p2(0, 2));
    _target_ring->setVisible(false);
    addChild(_target_ring);

    sprite = SpriteFactory::unit(sprite_def);
    sprite->setScale(unit_scale);
    sprite->setFlippedX(combatant->is_player);   // heroes are drawn facing right; players face left
    if (combatant->def.contains("tint"))
    {
        Col tint(S(combatant->def, "tint"));
        // elites keep most of their colours (gold sheen); tower guardians take the full tint
        _tint = combatant->is_elite ? Col::WHITE.lerp(tint, 0.45f) : tint;
    }
    sprite->animation_finished.connect([this] {
        if (_dead_visual) return;
        const std::string& a = sprite->animation();
        if (a == "attack" || a == "hit" || a == "burst" || a == "special") play_idle();
    });
    addChild(sprite);
    // shader stand-in: the flash colour is added on top by an additive copy of the frame
    _overlay = ax::Sprite::create();
    _overlay->setBlendFunc(ax::BlendFunc::ADDITIVE);
    _overlay->setVisible(false);
    addChild(_overlay);
    apply_color();

    _guard_icon = spr(gd::texture("assets/icons/shield.png"));
    _guard_icon->setScale(4);
    _guard_icon->setPosition(gd::p2(combatant->is_player ? -60 : 60, -visual_height() * 0.55f));
    _guard_icon->setVisible(false);
    addChild(_guard_icon);

    _cursor = spr(gd::texture("assets/ui/v2_chevron.png"));
    _cursor->setScale(5);
    _cursor->setPosition(gd::p2(0, -visual_height() - 100));
    _cursor->setVisible(false);
    addChild(_cursor);
    // names, HP and statuses live in the HUD plates / cards (the Godot overhead bar is always hidden)
    if (is_boss()) add_boss_aura();
    else if (combatant->is_elite) add_boss_aura(Col("#ffe07a"), Col("#ffb03a"), 8);
    else if (combatant->is_player)   // heroes breathe their element: a few motes, more with each evolution
        add_boss_aura(Col(DB.element_color(combatant->element)).lightened(0.35f), Col::WHITE,
                      2 + 2 * std::max(0, I(combatant->def, "rarity", 3) - 2));
}

// Slow drifting spores and embers around an Ancient foe.
void BattleUnitView::add_boss_aura(const Col& c0, const Col& /*c1 mid stop: the toolkit ramp uses first/last*/, int amount)
{
    gd::ParticleCfg c;
    c.amount = amount;
    c.lifetime = 2.4f;
    c.preprocess = 2.4f;
    c.emission_radius = visual_height() * 0.6f;
    c.gravity = Vec2(0, -24);
    c.vel_max = 10;
    c.scale_min = 5;
    c.scale_max = 9;
    c.ramp = {c0, Col(0.4f, 0.8f, 0.3f, 0)};
    _aura = gd::Particles::create(c);
    _aura->set_position(Vec2(0, -visual_height() * 0.5f));
    addChild(_aura, 1);
}

void BattleUnitView::update(float dt)
{
    if (_cursor->isVisible())
    {
        _cursor_time += dt;
        _cursor->setPosition(gd::p2(0, -visual_height() - 100 + std::sin(_cursor_time * 6.0f) * 8.0f));
    }
    if (_guard_icon->isVisible()) _guard_icon->setOpacity(u8(0.7f + 0.3f * std::sin(float(gd::ticks() * 1000.0 * 0.008))));
    if (_target_ring->isVisible())
    {
        _ring_t += dt;
        if (auto t = target_frame(int(_ring_t * 12) % 8)) _target_ring->setTexture(t);
    }
    _overlay->setVisible(_flash_amt > 0.001f && sprite->getSpriteFrame());
    if (_overlay->isVisible())
    {
        _overlay->setSpriteFrame(sprite->getSpriteFrame());
        _overlay->setBlendFunc(ax::BlendFunc::ADDITIVE);   // setSpriteFrame resets the blend mode
        _overlay->setAnchorPoint(sprite->getAnchorPoint());
        _overlay->setPosition(sprite->getPosition());
        _overlay->setScale(sprite->getScaleX(), sprite->getScaleY());
        _overlay->setFlippedX(sprite->isFlippedX());
    }
}

gd::Rect2 BattleUnitView::hit_rect() const
{
    float w = frame_size.x * 0.6f * unit_scale, h = visual_height() + 20;
    return {Vec2(position().x - w / 2, position().y - h), Vec2(w, h + 20)};
}

Vec2 BattleUnitView::melee_anchor(bool attacker_is_player) const
{
    float gap = frame_size.x * 0.5f * unit_scale * 0.62f + 70;
    return position() + Vec2(attacker_is_player ? gap : -gap, 6);
}

void BattleUnitView::play_idle()
{
    if (!_dead_visual) play("idle");
}

float BattleUnitView::play_anim(const std::string& anim, float speed)
{
    if (_dead_visual) return 0.0f;
    play(anim, speed);
    return SpriteFactory::anim_length(sprite_def, resolve_anim(anim)) / speed;
}

std::string BattleUnitView::resolve_anim(const std::string& anim) const
{
    if (sprite->has_animation(anim)) return anim;
    static const std::map<std::string, std::string> alt{{"special", "attack"}, {"guard", "hit"}, {"death", "ko"}, {"ko", "death"}};
    auto it = alt.find(anim);
    std::string a = it == alt.end() ? "idle" : it->second;
    return sprite->has_animation(a) ? a : "idle";
}

void BattleUnitView::play(const std::string& anim, float speed)
{
    sprite->speed_scale = speed;
    sprite->play(resolve_anim(anim));
    sprite->set_frame(0);
}

void BattleUnitView::hit_react(float knock)
{
    if (!combatant->is_alive() || _dead_visual) return;
    play("hit");
    flash(Col::WHITE, 0.12f);
    // knockback away from the attacker, then settle
    float dir = combatant->is_player ? 1.0f : -1.0f;
    auto s = sprite;
    auto tw = gd::tween(this);
    auto get = [s] { return s->getPositionX(); };
    auto set = [s](float v) { s->setPositionX(v); };
    tw->prop(get, set, dir * knock, 0.05f).trans(gd::TRANS_QUAD);
    tw->prop(get, set, 0.0f, 0.16f).trans(gd::TRANS_QUAD);
}

void BattleUnitView::play_guard()
{
    if (_dead_visual) return;
    if (sprite->has_animation("guard")) play("guard");
    flash(Col("#a8d0ff"), 0.3f);
    set_guarding(true);
}

void BattleUnitView::set_flash(const Col& c, float amount)
{
    _flash_col = c;
    _flash_amt = amount;
    apply_color();
}

// mix(base, flash, amount) approximated: the base tint moves toward the flash colour
// (dark silhouettes) and an additive copy adds it (bright flashes).
void BattleUnitView::apply_color()
{
    sprite->setColor((_tint * _mod).lerp(_flash_col, _flash_amt).c3b());
    _overlay->setColor(_flash_col.c3b());
    _overlay->setOpacity(u8(_flash_amt));
}

void BattleUnitView::set_silhouette(bool on, float time)
{
    _flash_tween.cancel();
    Col c(0.04f, 0.02f, 0.06f);
    if (time <= 0.0f)
    {
        set_flash(c, on ? 1.0f : 0.0f);
        return;
    }
    _flash_col = c;
    _flash_tween.start(this)->method([this, c](float v) { set_flash(c, v); }, on ? 0.0f : 1.0f, on ? 1.0f : 0.0f, time);
}

void BattleUnitView::set_guarding(bool on)
{
    _guard_icon->setVisible(on && !_dead_visual);
    if (!on && sprite->animation() == "guard") play_idle();
}

void BattleUnitView::anticipate(const Col& color, float time)
{
    if (_dead_visual) return;
    flash(color, time);
    auto tw = gd::tween(this);
    tw->scale(sprite, Vec2(unit_scale * 1.08f, unit_scale * 0.92f), time * 0.6f);
    tw->scale(sprite, Vec2(unit_scale, unit_scale), time * 0.4f);
}

void BattleUnitView::flash(const Col& color, float time)
{
    set_flash(color, 0.85f);
    _flash_tween.start(this)->method([this, color](float v) { set_flash(color, v); }, 0.85f, 0.0f, time);
}

void BattleUnitView::play_defeat()
{
    if (_dead_visual) return;
    _dead_visual = true;
    set_targeted(false);
    set_selected(false);
    _guard_icon->setVisible(false);
    if (_aura) _aura->set_emitting(false);
    std::string anim = combatant->is_player ? "ko" : "death";
    sprite->speed_scale = 1.0f;
    sprite->play(anim);
    flash(Col("#ff5a4a"), 0.25f);
    auto tw = gd::tween(this);
    if (combatant->is_player)
    {
        tw->interval(0.4f);
        tw->method([this](float k) { _mod = Col::WHITE.lerp(Col(0.6f, 0.55f, 0.6f), k); apply_color(); }, 0.0f, 1.0f, 0.3f);
    }
    else
    {
        tw->interval(SpriteFactory::anim_length(sprite_def, anim));
        tw->alpha(this, 0.0f, 0.3f);
        tw->callback([this] { setVisible(false); });
    }
}

void BattleUnitView::play_victory()
{
    if (combatant->is_alive()) play("victory");
}

gd::TweenRef BattleUnitView::move_to(Vec2 target, float time)
{
    auto tw = gd::tween(this);
    tw->position(this, target, time).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
    // small hop so movement reads as a dash, not a slide
    auto s = sprite;
    auto get = [s] { return -s->getPositionY(); };
    auto set = [s](float v) { s->setPositionY(-v); };
    auto hop = gd::tween(this);
    hop->prop(get, set, -18.0f, time * 0.5f).ease(gd::EASE_OUT);
    hop->prop(get, set, 0.0f, time * 0.5f).ease(gd::EASE_IN);
    return tw;
}

void BattleUnitView::set_targeted(bool on)
{
    bool show = on && !_dead_visual;
    _cursor->setVisible(show);
    if (show && !_target_ring->isVisible()) _ring_t = 0;
    _target_ring->setVisible(show);
}

void BattleUnitView::set_selected(bool on) { _select_ring->setVisible(on && !_dead_visual); }

// Pulsing glow + rising sparks while an enemy charges a telegraphed attack.
void BattleUnitView::set_charging(bool on)
{
    if (on == (_charge_fx != nullptr)) return;
    if (on)
    {
        gd::ParticleCfg c;
        c.amount = 24;
        c.lifetime = 0.9f;
        c.emission_radius = visual_height() * 0.5f;
        c.gravity = Vec2(0, -160);
        c.scale_min = 5;
        c.scale_max = 10;
        c.ramp = {Col("#fff4a0"), Col(1.0f, 0.3f, 0.1f, 0.0f)};
        _charge_fx = gd::Particles::create(c);
        _charge_fx->set_position(Vec2(0, -visual_height() * 0.4f));
        addChild(_charge_fx, 2);
        Col fc("#ffcf4a");
        _charge_tw = gd::tween(this);
        _charge_tw->loops();
        _charge_tw->method([this, fc](float v) { set_flash(fc, v); }, 0.0f, 0.45f, 0.35f);
        _charge_tw->method([this, fc](float v) { set_flash(fc, v); }, 0.45f, 0.0f, 0.35f);
    }
    else
    {
        _charge_fx->set_emitting(false);
        auto fx = _charge_fx;
        gd::after(this, 1.0f, [fx] { fx->queue_free(); });
        _charge_fx = nullptr;
        if (_charge_tw) _charge_tw->kill();
        _charge_tw = nullptr;
        set_flash(_flash_col, 0.0f);
    }
}

void BattleUnitView::refresh_statuses()
{
    if (!combatant->is_player && is_inside_tree()) set_charging(combatant->has_status("charging") && combatant->is_alive());
}

// ================================================================== EffectsLayer
struct NumberStyle { int size; const char* color; const char* icon; float pop; };
static const std::map<std::string, NumberStyle>& number_styles()
{
    static const std::map<std::string, NumberStyle> S{
        {"normal", {50, "#fff6e8", "", 1.15f}},
        {"player", {50, "#ff8a7a", "", 1.15f}},
        {"crit", {70, "#ffd35a", "assets/icons/star.png", 1.5f}},
        {"advantage", {60, "#ff9a4a", "", 1.3f}},
        {"resist", {40, "#9ab4d0", "assets/icons/shield.png", 1.0f}},
        {"heal", {50, "#8ae05a", "assets/icons/herb.png", 1.2f}},
        {"dot", {40, "#ffa04a", "assets/icons/status_burn.png", 1.0f}},
        {"finisher", {80, "#fff0a0", "assets/icons/burst.png", 1.7f}}};
    return S;
}
struct ParticleStyle { const char *c0, *c1; Vec2 gravity; float speed; };
static const std::map<std::string, ParticleStyle>& particle_styles()
{
    static const std::map<std::string, ParticleStyle> S{
        {"fire", {"#fff0a0", "#ff5a1e", Vec2(0, -260), 340.0f}},
        {"water", {"#dff6ff", "#3a8ad8", Vec2(0, 700), 380.0f}},
        {"nature", {"#c8ff9a", "#4a8a2a", Vec2(0, 240), 300.0f}},
        {"neutral", {"#ffffff", "#a8a0b0", Vec2(0, 300), 300.0f}},
        {"earth", {"#c8a878", "#5a4026", Vec2(0, 900), 520.0f}},
        {"heal", {"#e0ffd0", "#5ae05a", Vec2(0, -160), 120.0f}}};
    return S;
}

gd::AnimatedSprite* EffectsLayer::spawn(const std::string& effect_name, Vec2 pos, bool flip, float scale_mult, int z)
{
    if (effect_name.empty()) return nullptr;
    auto fx = take_effect(effect_name);
    if (!fx) return nullptr;
    fx->setPosition(gd::p2(pos));
    fx->setFlippedX(flip);
    fx->setScale(EFFECT_SCALE * scale_mult);
    world->reorderChild(fx, z * ZK);
    fx->setColor(ax::Color3B::WHITE);
    fx->setOpacity(255);
    fx->setVisible(true);
    fx->play("default");
    fx->set_frame(0);
    return fx;
}

gd::AnimatedSprite* EffectsLayer::take_effect(const std::string& effect_name)
{
    auto& pool = _effect_pools[effect_name];
    for (auto fx : pool)
        if (!fx->isVisible()) return fx;
    if ((int)pool.size() >= MAX_PER_EFFECT) return pool[0];   // recycle the oldest instead of growing
    auto node = SpriteFactory::effect(effect_name);
    if (node->frame_count("default") == 0) return nullptr;
    node->setVisible(false);
    node->animation_finished.connect([this, node, effect_name] {
        if (_looping.count(effect_name)) node->play("default");
        else node->setVisible(false);
    });
    world->addChild(node);
    pool.push_back(node);
    return node;
}

gd::TweenRef EffectsLayer::projectile(const std::string& effect_name, Vec2 from, Vec2 to, float time, bool flip)
{
    auto fx = spawn(effect_name, from, flip, 1.0f, 25);
    auto tw = gd::tween(world);
    if (!fx)
    {
        tw->interval(time);
        return tw;
    }
    _looping.insert(effect_name);
    fx->play("default");
    tw->node_pos(fx, to, time).trans(gd::TRANS_SINE);
    tw->callback([fx] {
        fx->setVisible(false);
        fx->stop();
    });
    return tw;
}

void EffectsLayer::particles(const std::string& kind, Vec2 pos, int amount, float spread_deg)
{
    if (!fx_enabled()) amount = std::max(3, amount / 3);
    auto it = particle_styles().find(kind);
    const ParticleStyle& st = it != particle_styles().end() ? it->second : particle_styles().at("neutral");
    gd::ParticleCfg c;
    c.one_shot = true;
    c.explosiveness = 0.9f;
    c.lifetime = 0.7f;
    c.direction = Vec2(0, -1);
    c.scale_min = 5;
    c.scale_max = 10;
    c.amount = std::clamp(amount, 2, 40);
    c.spread = spread_deg;
    c.gravity = st.gravity;
    c.vel_min = st.speed * 0.4f;
    c.vel_max = st.speed;
    c.ramp = {Col(st.c0), Col(st.c1).with_alpha(0)};
    auto p = gd::Particles::create(c);
    p->set_position(pos);
    if ((int)_bursts.size() < MAX_BURSTS) _bursts.push_back(p);
    else
    {
        _bursts[_burst_index]->removeFromParent();
        _bursts[_burst_index] = p;
        _burst_index = (_burst_index + 1) % (int)_bursts.size();
    }
    world->addChild(p, 30 * ZK);
}

void EffectsLayer::ring(Vec2 pos, const Col& color, float radius, float time, float thickness, float squash)
{
    auto r = ax::DrawNode::create();
    r->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);   // plain (non-premultiplied) colours
    r->setPosition(gd::p2(pos));
    world->addChild(r, 22 * ZK);
    auto draw = [r, color, thickness, squash](float rad) {
        // chunky pixel ring: small squares around an ellipse
        r->clear();
        int steps = (int)std::clamp(rad * 0.35f, 16.0f, 96.0f);
        for (int i = 0; i < steps; ++i)
        {
            float a = 2 * PI_F * i / steps;
            Vec2 p(std::floor(std::cos(a) * rad / 4.0f) * 4.0f, std::floor(std::sin(a) * rad * squash / 4.0f) * 4.0f);
            r->drawSolidRect(gd::p2(p - Vec2(thickness, thickness) / 2), gd::p2(p + Vec2(thickness, thickness) / 2), color.c4f());
        }
    };
    draw(radius * 0.15f);
    auto tw = gd::tween(r);
    tw->set_parallel();
    tw->method(draw, radius * 0.15f, radius, time).trans(gd::TRANS_QUAD).ease(gd::EASE_OUT);
    tw->opacity(r, 0.0f, time).ease(gd::EASE_IN);
    tw->chain().callback([r] { free_later(r); });
}

void EffectsLayer::shield_dome(Vec2 pos, const Col& color, float radius, float hold)
{
    auto d = ax::DrawNode::create();
    d->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);   // plain (non-premultiplied) colours
    d->setPosition(gd::p2(pos));
    d->setScale(0.2f);
    world->addChild(d, 21 * ZK);
    d->drawSolidCircle(gd::p2(0, -radius * 0.55f), radius, 0, 48, color.with_alpha(0.18f).c4f());
    const int steps = 40;
    for (int i = 0; i <= steps; ++i)
    {
        float a = PI_F + PI_F * i / steps;
        Vec2 p(std::floor(std::cos(a) * radius / 6.0f) * 6.0f, std::floor((-radius * 0.55f + std::sin(a) * radius) / 6.0f) * 6.0f);
        d->drawSolidRect(gd::p2(p - Vec2(5, 5)), gd::p2(p + Vec2(5, 5)), color.with_alpha(0.85f).c4f());
    }
    // hex facets
    for (int k = 0; k < 3; ++k)
    {
        float y = -radius * 0.55f - radius * 0.3f * k;
        d->drawSegment(gd::p2(-radius * 0.6f + k * 20, y), gd::p2(radius * 0.6f - k * 20, y), 2, Col(1, 1, 1, 0.25f).c4f());
    }
    auto tw = gd::tween(d);
    tw->scale(d, Vec2(1.1f, 1.1f), 0.18f).trans(gd::TRANS_BACK);
    tw->scale(d, Vec2(1, 1), 0.08f);
    tw->interval(hold);
    tw->opacity(d, 0.0f, 0.3f);
    tw->callback([d] { free_later(d); });
}

void EffectsLayer::streaks(Vec2 pos, const Col& color, int count, float length)
{
    if (!fx_enabled()) count = 2;
    for (int i = 0; i < count; ++i)
    {
        auto s = ax::DrawNode::create();
        s->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);   // plain (non-premultiplied) colours
        Col col = i % 2 == 0 ? color : color.lightened(0.4f);
        float len = length * randf_range(0.6f, 1.1f);
        s->setPosition(gd::p2(pos + Vec2(randf_range(-60, 60), randf_range(-60, 60))));
        s->setRotation(deg(i % 2 == 0 ? randf_range(-0.9f, -0.5f) : randf_range(0.5f, 0.9f)));
        world->addChild(s, 24 * ZK);
        auto draw = [s, col, len](float progress) {
            s->clear();
            Vec2 a(-len / 2, 0), b(len / 2, 0);
            Vec2 head = a.lerp(b, progress), tail = a.lerp(b, std::max(progress - 0.5f, 0.0f));
            s->drawSegment(gd::p2(tail), gd::p2(head), 4, col.c4f());
            s->drawSegment(gd::p2(tail.lerp(head, 0.5f)), gd::p2(head), 2, Col(1, 1, 1, 0.9f).c4f());
        };
        gd::tween(s)->method(draw, 0.0f, 1.0f, 0.16f);
        auto fade = gd::tween(s);
        fade->interval(0.12f);
        fade->opacity(s, 0.0f, 0.12f);
        fade->callback([s] { free_later(s); });
    }
}

void EffectsLayer::damage_number(Vec2 pos, int value, const std::string& kind, const std::string& tag, const std::string& icon_path)
{
    if (!B(GM.settings, "damage_numbers", true) && kind != "heal") return;
    auto it = number_styles().find(kind);
    const NumberStyle& st = it != number_styles().end() ? it->second : number_styles().at("normal");
    Number& n = take_number();
    n.main->set_text((kind == "heal" ? "+" : "") + std::to_string(value));
    n.main->set_font_size(st.size);
    n.main->set_color(Col(st.color));
    n.main->set_outline(st.size / 5);
    std::string ipath = !icon_path.empty() ? icon_path : st.icon;
    n.ic->setVisible(!ipath.empty());
    if (!ipath.empty())
    {
        n.ic->set_texture(res(ipath));
        float isz = st.size >= 60 ? 48.0f : 32.0f;
        n.ic->set_custom_min(Vec2(isz, isz));
    }
    std::vector<std::string> tags;
    if (kind == "crit") tags.push_back("CRITICAL");
    else if (kind == "finisher") tags.push_back("FINISH");
    if (tag == "WEAK") tags.push_back("ADVANTAGE");
    else if (tag == "RESIST") tags.push_back("RESIST");
    else if (!tag.empty() && std::find(tags.begin(), tags.end(), tag) == tags.end()) tags.push_back(tag);
    std::string joined;
    for (auto& t : tags) joined += (joined.empty() ? "" : "  ") + t;
    n.sub->set_text(joined);
    n.sub->setVisible(!tags.empty());
    n.sub->set_color(tag == "WEAK" ? Col("#ff7a3a") : tag == "RESIST" ? Col("#9ab4d0") : Col("#ffd35a"));
    Vec2 m = n.row->combined_min();
    n.row->set_size(m);
    n.row->set_position(-m / 2);
    launch(n, pos, st.pop, kind == "resist" || kind == "dot");
}

void EffectsLayer::floating_text(Vec2 pos, const std::string& text, const Col& color, int size)
{
    Number& n = take_number();
    n.ic->setVisible(false);
    n.main->set_text(text);
    n.main->set_font_size(UIKit::snap_text(size));
    n.main->set_color(color);
    n.main->set_outline(8);
    n.sub->setVisible(false);
    Vec2 m = n.row->combined_min();
    n.row->set_size(m);
    n.row->set_position(-m / 2);
    launch(n, pos, 1.1f, true);
}

// Pop (scale overshoot) -> rise -> fade. Softer drift for small numbers.
void EffectsLayer::launch(Number& n, Vec2 pos, float pop, bool soft)
{
    // numbers landing on the same spot at the same time stack upwards instead of overlapping
    double now = gd::ticks() * 1000.0;
    int stack = 0;
    for (auto& r : _recent)
        if (now - r.second < 450 && r.first.distance(pos) < 90.0f) ++stack;
    _recent.erase(std::remove_if(_recent.begin(), _recent.end(), [now](auto& r) { return now - r.second >= 450; }), _recent.end());
    _recent.push_back({pos, now});
    auto node = n.n;
    node->set_position(pos + Vec2(randf_range(-10, 10) + (stack % 2) * 30 - 15 * std::min(stack, 1), -52.0f * std::min(stack, 4)));
    node->setVisible(true);
    node->set_alpha(1.0f);
    node->setScale(pop);
    float rise = soft ? 60.0f : 100.0f;
    auto tw = n.tw.start(node);
    tw->set_parallel();
    tw->scale(node, Vec2(1, 1), 0.14f).trans(gd::TRANS_BACK);
    tw->position_y(node, node->position().y - rise, 0.85f).ease(gd::EASE_OUT).trans(gd::TRANS_CUBIC);
    if (pop >= 1.5f)
    {
        node->setRotation(deg(randf_range(-0.12f, 0.12f)));
        tw->rotation(node, 0.0f, 0.2f);
    }
    tw->chain().alpha(node, 0.0f, 0.25f);
    tw->chain().callback([node] { node->setVisible(false); });
}

EffectsLayer::Number& EffectsLayer::take_number()
{
    if ((int)_number_pool.size() < MAX_NUMBERS)
    {
        Number n;
        n.n = gd::Node2D::create();
        n.row = UIKit::hbox(6);
        n.row->set_mouse_filter(gd::MOUSE_IGNORE);
        n.ic = gd::TextureRect::create();
        n.ic->ignore_size = true;
        n.ic->stretch = gd::STRETCH_KEEP_ASPECT_CENTERED;
        n.ic->set_v_flags(gd::SIZE_SHRINK_CENTER);
        n.ic->set_mouse_filter(gd::MOUSE_IGNORE);
        n.row->add(n.ic);
        n.main = UIKit::label("", 50, Col::WHITE, gd::ALIGN_CENTER, 10);
        n.main->set_shadow(UIKit::SHADOW, 5);
        n.row->add(n.main);
        n.sub = UIKit::label("", 30, Col::WHITE, gd::ALIGN_CENTER, 7);
        n.sub->set_size(Vec2(400, 40));
        n.sub->set_position(Vec2(-200, -84));
        n.n->add(n.row);
        n.n->add(n.sub);
        world->addChild(n.n, 40 * ZK);
        _number_pool.push_back(n);
        return _number_pool.back();
    }
    // recycle round-robin
    Number& reuse = _number_pool[_number_index];
    _number_index = (_number_index + 1) % (int)_number_pool.size();
    reuse.tw.cancel();
    reuse.n->setRotation(0);
    return reuse;
}
