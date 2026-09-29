// Battle interface: battle_hud.gd, party_card.gd, components/enemy_plate.gd, components/cutin_decor.gd.
#include "battle/BattleScene.h"
#include <cmath>

using gd::Control;
static std::string first_word(const std::string& s) { return s.substr(0, s.find(' ')); }
static Vec2 vp() { return gd::Root::get()->size(); }

// ================================================================== BattleHUD
BattleHUD* BattleHUD::create()
{
    auto h = gd::make<BattleHUD>();
    h->set_name("HUD");
    h->set_anchors_preset(gd::PRESET_FULL_RECT);
    h->set_mouse_filter(gd::MOUSE_IGNORE);
    h->flash_rect = gd::ColorRect::create(Col(1, 1, 1, 0));
    h->flash_rect->set_anchors_preset(gd::PRESET_FULL_RECT);
    h->flash_rect->set_mouse_filter(gd::MOUSE_IGNORE);
    h->add(h->flash_rect);
    h->build_top();
    h->build_enemy_row();
    h->build_bottom();
    for (auto layer : {&h->banner_layer, &h->cutin})
    {
        *layer = Control::create();
        (*layer)->set_anchors_preset(gd::PRESET_FULL_RECT);
        (*layer)->set_mouse_filter(gd::MOUSE_IGNORE);
        h->add(*layer);
    }
    h->cutin->setVisible(false);
    return h;
}

float BattleHUD::field_bottom() const { return vp().y - bottom_block; }
float BattleHUD::field_top() const { return UIKit::safe_top() + TOP_H + 160; }

void BattleHUD::build_top()
{
    auto top = PanelFrame::make("plank", 10);
    top->set_name("TopBar");
    top->set_anchors_preset(gd::PRESET_TOP_WIDE);
    top->set_offsets(6, 4 + UIKit::safe_top(), -6, TOP_H + UIKit::safe_top());
    add(top);
    auto row = UIKit::hbox(12);
    top->add(row);
    auto badge = PanelFrame::make("slot", 6);
    badge->set_custom_min(Vec2(84, 84));
    stage_num = UIKit::label("", UIKit::T_NAME, UIKit::GOLD, gd::ALIGN_CENTER, 8);
    stage_num->set_align(gd::ALIGN_CENTER, gd::VALIGN_CENTER);
    badge->add(stage_num);
    row->add(badge);
    auto mid = UIKit::vbox(2);
    mid->set_h_flags(gd::SIZE_EXPAND_FILL);
    row->add(mid);
    stage_label = UIKit::label("", UIKit::T_BODY, Col("#fff0c0"), gd::ALIGN_LEFT, 6);
    stage_label->set_clip_text(true);
    mid->add(stage_label);
    auto wrow = UIKit::hbox(8);
    wave_label = UIKit::label("", UIKit::T_SMALL, UIKit::SKY, gd::ALIGN_LEFT, 5);
    wave_label->set_name("WaveLabel");
    wrow->add(wave_label);
    wave_pips = UIKit::hbox(6);
    wave_pips->set_v_flags(gd::SIZE_SHRINK_CENTER);
    wrow->add(wave_pips);
    mid->add(wrow);
    auto loot = UIKit::vbox(0);
    auto g = UIKit::hbox(6);
    g->add(UIKit::icon("assets/icons/gold.png", 32));
    gold_label = UIKit::label("0", UIKit::T_SMALL, UIKit::GOLD, gd::ALIGN_LEFT, 5);
    gold_label->set_min_w(90);
    g->add(gold_label);
    loot->add(g);
    auto d = UIKit::hbox(6);
    d->add(UIKit::icon("assets/icons/nav_bag.png", 32));
    drops_label = UIKit::label("0", UIKit::T_SMALL, UIKit::TEXT, gd::ALIGN_LEFT, 5);
    d->add(drops_label);
    loot->add(d);
    row->add(loot);
    btn_speed = FantasyButton::make("1x", "steel", Vec2(96, 88));
    btn_speed->set_name("SpeedButton");
    btn_speed->set_font_size(30);
    btn_speed->pressed.connect([this] { set_speed(speed < 1.5f ? 2.0f : 1.0f, true); });
    row->add(btn_speed);
    btn_auto = FantasyButton::make("AUTO", "stone", Vec2(150, 88));
    btn_auto->set_name("AutoButton");
    btn_auto->set_font_size(28);
    btn_auto->pressed.connect([this] {
        if (auto_available) set_auto(!auto_on, true);
        else add_log("Auto Battle unlocks after clearing Stage 1-4.", UIKit::MUTED);
    });
    row->add(btn_auto);
    btn_menu = FantasyButton::make("MENU", "stone", Vec2(128, 88));
    btn_menu->set_name("BattleMenu");
    btn_menu->set_font_size(28);
    btn_menu->pressed.connect([this] { menu_requested.emit(); });
    row->add(btn_menu);
}

void BattleHUD::build_enemy_row()
{
    enemy_row = UIKit::hbox(6);
    enemy_row->set_name("EnemyRow");
    enemy_row->set_anchors_preset(gd::PRESET_TOP_WIDE);
    enemy_row->set_offsets(8, TOP_H + 8 + UIKit::safe_top(), -8, TOP_H + 158 + UIKit::safe_top());
    enemy_row->set_mouse_filter(gd::MOUSE_IGNORE);
    add(enemy_row);
}

void BattleHUD::build_bottom()
{
    _block = Control::create();
    _block->set_name("BottomBlock");
    _block->set_anchors_preset(gd::PRESET_BOTTOM_WIDE);
    _block->set_offset(gd::SIDE_TOP, -bottom_block);
    _block->set_mouse_filter(gd::MOUSE_IGNORE);
    add(_block);
    auto base = PanelFrame::make("panel", 0);
    base->set_anchors_preset(gd::PRESET_FULL_RECT);
    base->set_offsets(-12, 0, 12, 30);
    base->set_mouse_filter(gd::MOUSE_IGNORE);
    _block->add(base);

    auto v = UIKit::vbox(8);
    v->set_anchors_preset(gd::PRESET_FULL_RECT);
    v->set_offsets(10, 14, -10, -8 - UIKit::safe_bottom());
    _block->add(v);

    cards_grid = gd::GridContainer::create(2);
    cards_grid->h_separation = 8;
    cards_grid->v_separation = 8;
    v->add(cards_grid);

    auto log_panel = PanelFrame::make("inset", 12);
    log_panel->set_v_flags(gd::SIZE_EXPAND_FILL);
    log_panel->set_mouse_filter(gd::MOUSE_IGNORE);
    v->add(log_panel);
    auto lh = UIKit::hbox(10);
    log_panel->add(lh);
    log_box = UIKit::vbox(0);
    log_box->alignment = gd::ALIGNMENT_END;
    log_box->set_h_flags(gd::SIZE_EXPAND_FILL);
    lh->add(log_box);
    auto hint = UIKit::vbox(0);
    hint->set_name("GestureHint");
    for (auto pair : {std::pair{"assets/icons/hand.png", "TAP  ATTACK"}, std::pair{"assets/icons/gesture_up.png", "UP  BURST"},
                      std::pair{"assets/icons/gesture_down.png", "DOWN  GUARD"}})
    {
        auto r = UIKit::hbox(4);
        r->add(UIKit::icon(pair.first, 16));
        r->add(UIKit::label(pair.second, UIKit::T_SMALL, UIKit::MUTED, gd::ALIGN_LEFT, 4));
        hint->add(r);
    }
    lh->add(hint);
}

// ------------------------------------------------------------------ auto / speed
void BattleHUD::set_auto(bool on, bool emit)
{
    auto_on = on && auto_available;
    btn_auto->apply_style(auto_on ? "ember" : "stone");
    btn_auto->set_text(auto_on ? "AUTO ON" : "AUTO");
    btn_auto->set_modulate(auto_available ? Col::WHITE : Col(0.6f, 0.6f, 0.6f));
    update_auto_band();
    if (emit) auto_toggled.emit(auto_on);
}

// Pulsing "AUTO BATTLE" plate just above the hero cards while auto is on. Tapping it turns auto off.
void BattleHUD::update_auto_band()
{
    if (!_auto_band && !auto_on) return;
    if (!_auto_band)
    {
        _auto_band = PanelFrame::make("boss", 8);
        _auto_band->set_name("AutoBand");
        auto h = UIKit::hbox(UIKit::SP_S);
        h->set_mouse_filter(gd::MOUSE_IGNORE);
        h->add(UIKit::icon("assets/icons/auto.png", 32));
        h->add(UIKit::label("AUTO BATTLE  -  tap to take control", UIKit::T_SMALL, UIKit::GOLD, gd::ALIGN_LEFT, 5));
        _auto_band->add(h);
        _auto_band->set_anchors_preset(gd::PRESET_BOTTOM_RIGHT);
        add(_auto_band);
        UIKit::on_tap(_auto_band, [this] { set_auto(false, true); });
        auto tw = gd::tween(_auto_band);
        tw->loops();
        tw->alpha(_auto_band, 0.65f, 0.6f).trans(gd::TRANS_SINE);
        tw->alpha(_auto_band, 1.0f, 0.6f).trans(gd::TRANS_SINE);
    }
    _auto_band->setVisible(auto_on);
    Vec2 sz = _auto_band->combined_min();
    _auto_band->set_offsets(-12 - sz.x, -bottom_block - 8 - sz.y, -12, -bottom_block - 8);
}

void BattleHUD::set_auto_available(bool on)
{
    auto_available = on;
    set_auto(auto_on && on);
}

void BattleHUD::set_speed(float v, bool emit)
{
    speed = v >= 1.5f ? 2.0f : 1.0f;
    btn_speed->set_text(speed > 1.0f ? "2x" : "1x");
    btn_speed->apply_style(speed > 1.0f ? "ember" : "steel");
    if (emit) speed_toggled.emit(speed);
}

// Red warning band for telegraphed enemy attacks.
void BattleHUD::show_warning(const std::string& text, const std::string& sub, Next done)
{
    AudioManager::play_sfx("warning");
    flash_screen(Col("#ff3a2a"), 0.25f, 0.25f);
    show_banner(text, Col("#ff7a5a"), 0.9f, "boss", sub, std::move(done));
}

// ------------------------------------------------------------------ enemies
void BattleHUD::set_enemies(const Units& enemies)
{
    for (auto ch : enemy_row->children()) ch->queue_free();
    plates.clear();
    bool any_boss = false, any_break = false;
    for (auto& e : enemies)
    {
        auto p = EnemyPlate::create(e);
        enemy_row->add(p);
        p->tapped.connect([this](CombatantPtr c) { target_requested.emit(c); });
        plates[e.get()] = p;
        any_boss = any_boss || B(e->def, "boss", false);   // boss plates take more room
        any_break = any_break || e->break_max > 0;
    }
    enemy_row->set_offset(gd::SIDE_BOTTOM, enemy_row->offset(gd::SIDE_TOP) + (any_break ? 200 : any_boss ? 170 : 130));
}

// ------------------------------------------------------------------ party
void BattleHUD::set_party(const Units& players)
{
    for (auto ch : cards_grid->children()) ch->queue_free();
    cards.clear();
    for (auto& c : players)
    {
        auto card = PartyCard::make(c);
        cards_grid->add(card);
        card->pressed_unit.connect([this](CombatantPtr cc) { unit_selected.emit(cc); });
        card->action.connect([this](CombatantPtr cc, std::string a) { card_action.emit(cc, a); });
        cards[c.get()] = card;
    }
    // one wide card for a solo hero, otherwise two columns (grows to 3 rows for 5-6 heroes)
    cards_grid->columns = players.size() <= 1 ? 1 : 2;
    int rows = std::max(1, (int)std::ceil(players.size() / float(cards_grid->columns)));
    bottom_block = 22 + rows * (CARD_H + 8) + LOG_H + 16 + UIKit::safe_bottom();
    _block->set_offset(gd::SIDE_TOP, -bottom_block);
    if (_auto_band) update_auto_band();
}

void BattleHUD::set_header(const Json& stage, int wave, int wave_total, int /*turn*/)
{
    stage_num->set_text(std::to_string(I(stage, "number", 0)));
    stage_label->set_text(S(stage, "name"));
    wave_label->set_text(UIKit::fmt("WAVE %d/%d", wave + 1, wave_total));
    for (auto ch : wave_pips->children()) ch->queue_free();
    for (int i = 0; i < wave_total; ++i)
    {
        auto pip = gd::ColorRect::create(i < wave ? UIKit::GOLD : (i == wave ? UIKit::EMBER : Col(0.2f, 0.18f, 0.22f)));
        pip->set_custom_min(Vec2(24, 16));
        pip->set_mouse_filter(gd::MOUSE_IGNORE);
        wave_pips->add(pip);
    }
}

void BattleHUD::set_loot(int gold, int drops)
{
    std::string old = gold_label->text();
    gold_label->set_text(UIKit::format_number(gold));
    drops_label->set_text(std::to_string(drops));
    if (old != gold_label->text() && gold > 0)
    {
        gold_label->set_pivot(Vec2(0, 15));
        auto tw = gd::tween(this);
        tw->scale(gold_label, Vec2(1.3f, 1.3f), 0.06f);
        tw->scale(gold_label, Vec2(1, 1), 0.12f);
    }
}

void BattleHUD::set_target_text(const CombatantPtr& target)
{
    _target = target;
    for (auto& [c, p] : plates) p->set_targeted(c == target.get());
}

// Enables/disables the cards according to the battle state.
void BattleHUD::refresh(bool can_input, const CombatantPtr& selected)
{
    for (auto& [c, card] : cards)
    {
        card->set_enabled(can_input);
        card->set_selected(c == selected.get());
    }
    btn_menu->set_disabled(!can_input);
}

// Adds a line to the action log (older lines fade).
void BattleHUD::add_log(const std::string& text, const Col& color)
{
    auto l = UIKit::label(text, UIKit::T_SMALL, color, gd::ALIGN_LEFT, 5);
    l->set_clip_text(true);
    l->set_h_flags(gd::SIZE_EXPAND_FILL);
    log_box->add(l);
    auto kids = log_box->children();
    while ((int)kids.size() > LOG_LINES)
    {
        log_box->remove_child(kids.front());
        kids.erase(kids.begin());
    }
    for (size_t i = 0; i < kids.size(); ++i) kids[i]->set_alpha(0.5f + 0.5f * float(i + 1) / kids.size());
}

// ------------------------------------------------------------------ presentation
// Brief full-screen flash (impact frame). Respects the Battle Effects setting.
void BattleHUD::flash_screen(const Col& color, float strength, float time)
{
    if (!BattleFx::fx_enabled()) strength *= 0.4f;
    flash_rect->set_color(color.with_alpha(strength));
    auto fr = flash_rect;
    gd::tween(this)->prop([fr] { return fr->color().a; }, [fr](float a) { fr->set_color(fr->color().with_alpha(a)); }, 0.0f, time);
}

// Centered banner that sweeps in, holds and sweeps out. style: "wave" (iron plank) or "boss" (crimson frame).
void BattleHUD::show_banner(const std::string& text, const Col& color, float hold, const std::string& style, const std::string& sub,
                            Next done)
{
    Vec2 v = vp();
    auto p = PanelFrame::make(style == "boss" ? "boss" : "plank", 18);
    p->set_name("Banner");
    p->set_custom_min(Vec2(v.x + 40, 0));
    p->set_position(Vec2(-v.x - 40, -1000));   // off screen until measured
    banner_layer->add(p);
    auto box = UIKit::vbox(0);
    box->alignment = gd::ALIGNMENT_CENTER;
    p->add(box);
    auto big = UIKit::label(text, style != "victory" ? UIKit::T_TITLE : 120, color, gd::ALIGN_CENTER, 14);
    big->set_outline_color(Col("#1a0806"));
    box->add(big);
    if (!sub.empty())
    {
        auto sl = UIKit::wrap_label(sub, UIKit::T_BODY, Col("#fff0c0"));   // long boss hints wrap
        sl->set_align(gd::ALIGN_CENTER);
        sl->set_min_w(940);
        box->add(sl);
    }
    ax::RefPtr<PanelFrame> keep(p);
    gd::defer([this, keep, big, color, hold, v, done] {
        auto p = keep.get();
        if (!p->is_inside_tree()) return;   // the screen went away
        float y = (field_top() + field_bottom()) * 0.5f - p->size().y * 0.5f - 80;
        p->set_position(Vec2(-v.x - 40, y));
        auto sparks = UIKit::sparkle(banner_layer, gd::Rect2{Vec2(0, y), Vec2(v.x, p->size().y)}, color.lightened(0.3f), 14);
        big->set_pivot(Vec2(v.x / 2, 50));
        auto tw = gd::tween(this);
        tw->position_x(p, -20.0f, 0.18f).trans(gd::TRANS_CUBIC).ease(gd::EASE_OUT);
        tw->scale(big, Vec2(1.06f, 1.06f), 0.08f);
        tw->scale(big, Vec2(1, 1), 0.08f);
        tw->interval(hold);
        tw->position_x(p, v.x + 40, 0.18f).trans(gd::TRANS_CUBIC).ease(gd::EASE_IN);
        tw->on_finished([this, p, sparks, done] {
            p->queue_free();
            sparks->set_emitting(false);
            gd::after(this, 1.5f, [sparks] { sparks->queue_free(); });
            if (done) done();
        });
    });
}

// Burst cut-in: the field darkens, an element-themed band sweeps in with the hero portrait,
// the hero name and the Burst name, then fades (about 1 second).
void BattleHUD::play_burst_cutin(const CombatantPtr& c, const Json& skill, Next done)
{
    cutin->clear_children();
    cutin->setVisible(true);
    cutin->set_alpha(1.0f);
    Vec2 v = vp();
    Col col(DB.element_color(c->element));
    float y0 = (field_top() + field_bottom()) * 0.5f - 220;
    auto band = Control::create();
    band->set_position(Vec2(0, y0));
    band->set_size(Vec2(v.x, 360));
    band->set_clip(true);
    band->set_mouse_filter(gd::MOUSE_IGNORE);
    cutin->add(band);
    auto rect = [band](const Col& color, Vec2 pos, Vec2 size) {
        auto r = gd::ColorRect::create(color);
        r->set_mouse_filter(gd::MOUSE_IGNORE);
        r->set_position(pos);
        r->set_size(size);
        band->add(r);
    };
    rect(Col(0.03f, 0.02f, 0.05f, 0.92f), Vec2::ZERO, band->size());
    rect(col.with_alpha(0.22f), Vec2::ZERO, band->size());
    CutinDecor::add(band, c->element);
    for (float yy : {0.0f, 352.0f}) rect(col.lightened(0.2f), Vec2(0, yy), Vec2(v.x, 8));
    auto art = UIKit::portrait_art(c->def, Vec2(384, 344));
    art->set_position(Vec2(v.x + 40, 8));
    art->set_size(Vec2(384, 344));
    band->add(art);
    auto place = [band](gd::Label* l, Vec2 pos, Vec2 size) {
        l->set_position(pos);
        l->set_size(size);
        band->add(l);
        return l;
    };
    auto name_l = place(UIKit::label(upper(c->display_name), UIKit::T_NAME, col.lightened(0.45f), gd::ALIGN_LEFT, 8), Vec2(-760, 70),
                        Vec2(700, 50));
    auto burst_l = place(UIKit::label(upper(S(skill, "name")), UIKit::T_TITLE, UIKit::GOLD, gd::ALIGN_LEFT, 14), Vec2(-900, 150),
                         Vec2(900, 100));
    burst_l->set_outline_color(Col("#2a0a04"));
    auto tag = place(UIKit::label("BURST", UIKit::T_BODY, Col("#fff0c0"), gd::ALIGN_LEFT, 6), Vec2(-300, 262), Vec2(300, 40));
    band->setScale(1, 0.1f);
    band->set_pivot(Vec2(v.x / 2, 180));
    // Godot runs these in one parallel tween with per-step delays
    gd::tween(this)->scale(band, Vec2(1, 1), 0.12f).trans(gd::TRANS_CUBIC).ease(gd::EASE_OUT);
    auto slide = [this](Control* n, float x, float t, float delay) {
        auto tw = gd::tween(this);
        tw->interval(delay);
        tw->position_x(n, x, t).trans(gd::TRANS_CUBIC).ease(gd::EASE_OUT);
    };
    slide(art, v.x - 420, 0.24f, 0.05f);
    slide(name_l, 40.0f, 0.22f, 0.08f);
    slide(burst_l, 40.0f, 0.26f, 0.14f);
    slide(tag, 44.0f, 0.26f, 0.2f);
    auto tw = gd::tween(this);
    tw->interval(0.46f);   // longest parallel step (0.2 + 0.26)
    tw->interval(0.5f);
    tw->alpha(cutin, 0.0f, 0.16f).trans(gd::TRANS_CUBIC).ease(gd::EASE_OUT);
    tw->on_finished([this, done] {
        cutin->setVisible(false);
        for (auto ch : cutin->children()) ch->queue_free();
        if (done) done();
    });
}

// Boss entrance title: darkened band, ANCIENT FOE and the boss name.
void BattleHUD::play_boss_title(const std::string& boss_name) { show_banner("ANCIENT FOE", Col("#ff6a4a"), 1.0f, "boss", upper(boss_name)); }

// Tutorial popup. Resolves when the player presses GOT IT.
void BattleHUD::show_hint(const Json& hint, Next done)
{
    auto p = FantasyPopup::open(this, S(hint, "title", "Tip"), 980);
    for (auto& line : A(hint, "lines"))
    {
        auto l = UIKit::wrap_label(S(line), UIKit::T_BODY);
        l->set_min_w(900);
        p->content->add(l);
    }
    auto ok = FantasyButton::make("GOT IT", "ember", Vec2(340, 110));
    ok->set_h_flags(gd::SIZE_SHRINK_CENTER);
    p->content->add(ok);
    p->set_name("HintPopup");
    ok->pressed.connect([p] { p->close(); });
    p->default_action = [p] { p->close(); };
    p->closed.connect([done] { if (done) done(); });
}

void BattleHUD::show_menu(std::function<void()> on_retreat)
{
    if (UIManager::has_popup("PauseMenu")) return;
    auto p = FantasyPopup::open(this, "PAUSED", 820);
    p->set_name("PauseMenu");
    auto resume = UIKit::btn("RESUME", "primary", Vec2(520, 116));
    resume->set_name("ResumeButton");
    auto elements = UIKit::btn("ELEMENTS", "secondary", Vec2(520, 110), "assets/icons/element_chart.png");
    elements->set_name("PauseElements");
    auto settings = UIKit::btn("SETTINGS", "secondary", Vec2(520, 110));
    settings->set_name("PauseSettings");
    auto retreat = UIKit::btn("RETREAT", "danger", Vec2(520, 110));
    retreat->set_name("RetreatButton");
    elements->pressed.connect([this] { ElementChart::popup(this); });
    for (auto b : {resume, elements, settings, retreat})
    {
        b->set_h_flags(gd::SIZE_SHRINK_CENTER);
        p->content->add(b);
    }
    p->content->add(UIKit::label("Retreating ends the battle without rewards (Energy is not refunded).", UIKit::T_SMALL, UIKit::MUTED,
                                 gd::ALIGN_CENTER));
    resume->pressed.connect([p] { p->close(); });
    settings->pressed.connect([this] { SettingsPanel::open(this); });
    p->default_action = [p] { p->close(); };
    // retreating costs the run, so it asks once
    retreat->pressed.connect([this, p, on_retreat] {
        ConfirmOpts o;
        o.danger = true;
        o.parent = this;
        UIManager::confirm("RETREAT?", "The battle ends without rewards and the Energy is not refunded.", "RETREAT",
                           [p, on_retreat] {
                               p->close();
                               on_retreat();
                           },
                           o);
    });
}

// ================================================================== PartyCard
PartyCard* PartyCard::make(const CombatantPtr& c)
{
    auto card = gd::make<PartyCard>();
    card->setup(c);
    return card;
}

void PartyCard::setup(const CombatantPtr& c)
{
    combatant = c;
    set_name("PartyCard_" + std::to_string(c->slot));
    _el = (c->element == "fire" || c->element == "water" || c->element == "nature") ? c->element : "neutral";
    set_custom_min(Vec2(500, H));
    set_h_flags(gd::SIZE_EXPAND_FILL);
    set_mouse_filter(gd::MOUSE_STOP);
    resized.connect([this] { set_pivot(size() / 2); });

    frame = PanelFrame::make("card_" + _el, 14);
    frame->set_anchors_preset(gd::PRESET_FULL_RECT);
    frame->set_mouse_filter(gd::MOUSE_IGNORE);
    add(frame);
    auto row = UIKit::hbox(12);
    row->set_mouse_filter(gd::MOUSE_IGNORE);
    frame->add(row);
    content = row;

    portrait = UIKit::portrait_art(c->def, Vec2(150, 176));
    row->add(portrait);
    ko_stamp = UIKit::label("KO", UIKit::T_TITLE, UIKit::DANGER, gd::ALIGN_CENTER, 14);
    ko_stamp->set_align(gd::ALIGN_CENTER, gd::VALIGN_CENTER);
    ko_stamp->set_anchors_preset(gd::PRESET_FULL_RECT);
    ko_stamp->setRotation(-0.2f * 180.0f / 3.14159265f);
    ko_stamp->set_pivot(Vec2(75, 88));
    ko_stamp->setVisible(false);
    portrait->add(ko_stamp);

    auto col = UIKit::vbox(3);
    col->set_h_flags(gd::SIZE_EXPAND_FILL);
    col->set_mouse_filter(gd::MOUSE_IGNORE);
    row->add(col);
    auto top = UIKit::hbox(6);
    top->add(UIKit::orb(c->element, 32));
    auto nm = UIKit::label(first_word(c->display_name), UIKit::T_BODY, Col::WHITE, gd::ALIGN_LEFT, 7);
    nm->set_clip_text(true);
    nm->set_h_flags(gd::SIZE_EXPAND_FILL);
    top->add(nm);
    status_row = UIKit::hbox(2);
    top->add(status_row);
    col->add(top);
    auto hp_row = UIKit::hbox(6);
    hp_row->add(UIKit::label("HP", UIKit::T_SMALL, UIKit::GOOD, gd::ALIGN_LEFT, 5));
    hp_text = UIKit::label("", UIKit::T_BODY, Col::WHITE, gd::ALIGN_RIGHT, 6);
    hp_text->set_h_flags(gd::SIZE_EXPAND_FILL);
    hp_row->add(hp_text);
    col->add(hp_row);
    hp_bar = ResourceBar::make("hp", 28);
    col->add(hp_bar);
    auto b_row = UIKit::hbox(6);
    burst_label = UIKit::label("BURST", UIKit::T_SMALL, UIKit::SKY, gd::ALIGN_LEFT, 5);
    burst_label->set_h_flags(gd::SIZE_EXPAND_FILL);
    b_row->add(burst_label);
    burst_pct = UIKit::label("", UIKit::T_SMALL, UIKit::SKY, gd::ALIGN_RIGHT, 5);
    b_row->add(burst_pct);
    col->add(b_row);
    burst_bar = ResourceBar::make("burst", 24);
    col->add(burst_bar);
    burst_bar->filled.connect([this] { on_burst_filled(); });

    build_gesture_overlay();

    gd::listen(this, c->hp_changed, [this](int cur, int mx) { on_hp(cur, mx); });
    gd::listen(this, c->burst_changed, [this](double cur, double mx) { on_burst(cur, mx); });
    gd::listen(this, c->statuses_changed, [this] { on_statuses(); });
    hp_bar->set_values((float)c->hp, (float)c->max_hp, false);
    burst_bar->set_values((float)c->burst, (float)c->burst_max, false);
    on_hp(c->hp, c->max_hp);
    on_burst(c->burst, c->burst_max);
    gui_input.connect([this](gd::InputEvent& e) { on_input(e); });
}

void PartyCard::build_gesture_overlay()
{
    gesture = Control::create();
    gesture->set_anchors_preset(gd::PRESET_FULL_RECT);
    gesture->set_mouse_filter(gd::MOUSE_IGNORE);
    gesture->setVisible(false);
    gesture->set_z(5);
    add(gesture);
    auto shade = gd::ColorRect::create(Col(0.02f, 0.01f, 0.04f, 0.55f));
    shade->set_anchors_preset(gd::PRESET_FULL_RECT);
    shade->set_mouse_filter(gd::MOUSE_IGNORE);
    gesture->add(shade);
    auto h = UIKit::hbox(12);
    h->set_anchors_preset(gd::PRESET_CENTER);   // grows both ways: stays centred like the Godot resized handler
    h->alignment = gd::ALIGNMENT_CENTER;
    h->set_mouse_filter(gd::MOUSE_IGNORE);
    gesture->add(h);
    gesture_icon = UIKit::icon("assets/icons/gesture_up.png", 96);
    h->add(gesture_icon);
    gesture_label = UIKit::label("", UIKit::T_HEAD, UIKit::GOLD, gd::ALIGN_LEFT, 10);
    h->add(gesture_label);
}

// ------------------------------------------------------------------ gestures
void PartyCard::on_input(gd::InputEvent& e)
{
    if (e.type == gd::Ev::PRESS)
    {
        _pressing = true;
        _press_pos = e.local;
        pressed_unit.emit(combatant);
        if (_enabled && combatant->can_act()) gd::tween(this)->scale(this, Vec2(1.03f, 1.03f), 0.06f);
        e.accept();
    }
    else if ((e.type == gd::Ev::RELEASE || e.type == gd::Ev::CANCEL) && _pressing)
    {
        _pressing = false;
        // a cancelled touch resets the card without acting (a long sideways delta matches no gesture)
        release(e.type == gd::Ev::CANCEL ? Vec2(1000, 0) : e.local - _press_pos);
        e.accept();
    }
    else if (e.type == gd::Ev::MOVE && _pressing)
    {
        float dy = e.local.y - _press_pos.y;
        content->set_shift(Vec2(0, std::clamp(dy, -40.0f, 40.0f) * 0.5f));
        update_gesture(dy);
        e.accept();
    }
}

// Direction indicator: up = Burst, down = Guard; brightens past the threshold.
void PartyCard::update_gesture(float dy)
{
    if (!_enabled || !combatant->can_act() || std::abs(dy) < 16.0f)
    {
        gesture->setVisible(false);
        return;
    }
    gesture->setVisible(true);
    bool up = dy < 0.0f;
    float k = std::clamp(std::abs(dy) / SWIPE_DIST, 0.0f, 1.0f);
    bool armed = k >= 1.0f;
    gesture_icon->set_texture(up ? "assets/icons/gesture_up.png" : "assets/icons/gesture_down.png");
    if (up && !combatant->burst_ready())
    {
        gesture_label->set_text("NOT READY");
        gesture_label->set_color(UIKit::MUTED);
        gesture->set_modulate(Col(1, 1, 1, 0.4f + 0.4f * k));
        return;
    }
    gesture_label->set_text(armed ? (up ? "BURST!" : "GUARD") : (up ? "BURST" : "GUARD"));
    gesture_label->set_color(up ? UIKit::GOLD : Col("#a8d0ff"));
    gesture->set_modulate(armed ? Col(1.3f, 1.2f, 1.0f) : Col(1, 1, 1, 0.35f + 0.55f * k));
    gesture_icon->set_pivot(gesture_icon->size() / 2);
    gesture_icon->setScale(armed ? 1.2f : 0.8f + 0.2f * k);
}

void PartyCard::release(Vec2 delta)
{
    gesture->setVisible(false);
    auto tw = gd::tween(this);
    tw->set_parallel();
    tw->shift(content, Vec2::ZERO, 0.1f);
    tw->scale(this, Vec2(1, 1), 0.08f);
    if (!_enabled) return;
    if (delta.y < -SWIPE_DIST && std::abs(delta.y) > std::abs(delta.x)) action.emit(combatant, "burst");
    else if (delta.y > SWIPE_DIST && std::abs(delta.y) > std::abs(delta.x)) action.emit(combatant, "guard");
    else if (delta.length() < SWIPE_DIST) action.emit(combatant, "attack");
}

// ------------------------------------------------------------------ state
void PartyCard::set_enabled(bool on)
{
    _enabled = on;
    refresh_state();
}

void PartyCard::set_selected(bool on)
{
    _selected = on;
    refresh_state();
}

void PartyCard::refresh_state()
{
    bool alive = combatant->is_alive();
    ko_stamp->setVisible(!alive);
    if (!alive)
    {
        frame->set_variant("card_neutral", 14);
        set_modulate(Col(0.5f, 0.42f, 0.44f));
        portrait->set_modulate(Col(0.55f, 0.5f, 0.55f));
        set_sparkle(false);
        return;
    }
    portrait->set_modulate(Col::WHITE);
    bool can = combatant->can_act() && _enabled;
    frame->set_variant("card_" + _el + ((_ready_state || (can && _selected)) ? "_lit" : ""), 14);
    if (can) set_modulate(Col::WHITE);
    else if (!combatant->can_act()) set_modulate(Col(0.6f, 0.6f, 0.68f));   // already acted this turn
    else set_modulate(Col(0.82f, 0.82f, 0.88f));                            // enemy phase / animating
    set_sparkle(_ready_state && can);
}

void PartyCard::on_hp(int current, int maximum)
{
    hp_text->set_text(UIKit::fmt("%d/%d", current, maximum));
    float r = float(current) / std::max((float)maximum, 1.0f);
    hp_text->set_color(r > 0.5f ? Col::WHITE : (r > 0.25f ? Col("#ffe06a") : Col("#ff7a6a")));
    hp_bar->set_values((float)current, (float)maximum);
    refresh_state();
}

void PartyCard::on_burst(double current, double maximum)
{
    burst_bar->set_values((float)current, (float)maximum);
    bool full = current >= maximum;
    int pct = (int)std::floor(current / std::max(maximum, 1.0) * 100.0);
    _ready_state = full;
    if (full)
    {
        burst_label->set_text("READY! SWIPE UP");
        burst_label->set_color(UIKit::GOLD);
        burst_pct->set_text("");
        if (!_glow_tween || !_glow_tween->is_running())
        {
            // self_modulate glow; values above 1 clamp in this toolkit
            _glow_tween = gd::tween(this);
            _glow_tween->loops();
            _glow_tween->modulate(frame, Col(1.35f, 1.2f, 0.9f), 0.35f).trans(gd::TRANS_SINE);
            _glow_tween->modulate(frame, Col::WHITE, 0.35f).trans(gd::TRANS_SINE);
        }
    }
    else
    {
        burst_label->set_text(current <= 0.0 ? "BURST" : "CHARGING");
        burst_label->set_color(current <= 0.0 ? UIKit::MUTED : UIKit::SKY);
        burst_pct->set_text(current <= 0.0 ? "EMPTY" : UIKit::fmt("%d%%", pct));
        if (_glow_tween) _glow_tween->kill();
        _glow_tween = nullptr;
        frame->set_modulate(Col::WHITE);
    }
    refresh_state();
}

void PartyCard::on_burst_filled()
{
    if (!combatant->is_alive()) return;
    AudioManager::play_sfx("burst_ready", 0.02f, -2.0f);
    auto tw = gd::tween(this);
    tw->scale(this, Vec2(1.05f, 1.05f), 0.08f);
    tw->scale(this, Vec2(1, 1), 0.12f);
}

void PartyCard::set_sparkle(bool on)
{
    if (!BattleFx::fx_enabled()) on = false;
    if (on && !_sparkle)
    {
        _sparkle = UIKit::sparkle(this, gd::Rect2{Vec2(10, 10), Vec2(std::max(size().x, 480.0f) - 20, H - 20)}, Col("#ffe08a"), 10);
        _sparkle->set_z(4);
    }
    else if (!on && _sparkle)
    {
        _sparkle->queue_free();
        _sparkle = nullptr;
    }
}

void PartyCard::on_statuses()
{
    status_row->clear_children();
    for (auto& s : combatant->statuses)
        status_row->add(StatusIcon::make(S(s, "id"), I(s, "turns", 0), (float)F(s, "value", 0.0), 32));
}

// ================================================================== EnemyPlate
EnemyPlate* EnemyPlate::create(const CombatantPtr& c)
{
    auto p = gd::make<EnemyPlate>();
    p->combatant = c;
    p->is_boss = B(c->def, "boss", false);
    p->set_name("EnemyPlate_" + std::to_string(c->slot));
    p->build();
    return p;
}

void EnemyPlate::build()
{
    set_variant(is_boss ? "boss" : "enemy", is_boss ? 14 : 10);
    set_h_flags(gd::SIZE_EXPAND_FILL);
    set_custom_min(Vec2(200, is_boss ? 150 : 120));
    set_mouse_filter(gd::MOUSE_STOP);
    auto row = UIKit::hbox(10);
    row->set_mouse_filter(gd::MOUSE_IGNORE);
    add(row);
    auto left = Control::create();
    left->set_custom_min(Vec2(is_boss ? 64 : 48, 48));
    left->set_mouse_filter(gd::MOUSE_IGNORE);
    row->add(left);
    auto orb = UIKit::orb(combatant->element, is_boss ? 64 : 48);
    orb->set_position(Vec2(0, is_boss ? 8 : 4));
    left->add(orb);
    marker = UIKit::icon("assets/ui/v2_chevron.png", 32);
    marker->set_position(Vec2(is_boss ? 16 : 8, -26));
    marker->setVisible(false);
    left->add(marker);
    auto col = UIKit::vbox(4);
    col->set_h_flags(gd::SIZE_EXPAND_FILL);
    col->set_mouse_filter(gd::MOUSE_IGNORE);
    row->add(col);
    auto top = UIKit::hbox(8);
    top->set_mouse_filter(gd::MOUSE_IGNORE);
    name_label = UIKit::label(combatant->display_name, is_boss ? UIKit::T_NAME : UIKit::T_BODY,
                              Col(DB.element_color(combatant->element)).lightened(0.5f), gd::ALIGN_LEFT, 7);
    name_label->set_clip_text(true);
    name_label->set_h_flags(gd::SIZE_EXPAND_FILL);
    top->add(name_label);
    top->add(UIKit::label(UIKit::fmt("Lv%d", combatant->level), UIKit::T_SMALL, UIKit::GOLD, gd::ALIGN_RIGHT, 5));
    col->add(top);
    bar = ResourceBar::make(is_boss ? "boss" : "enemy", is_boss ? 36 : 26);
    bar->set_h_flags(gd::SIZE_EXPAND_FILL);
    col->add(bar);
    if (combatant->break_max > 0)   // BREAK gauge under the HP bar
    {
        auto br = UIKit::hbox(6);
        br->set_mouse_filter(gd::MOUSE_IGNORE);
        break_label = UIKit::label("BREAK", UIKit::T_SMALL, Col("#ffe070"), gd::ALIGN_LEFT, 5);
        br->add(break_label);
        break_bar = ResourceBar::make("break", 22);
        break_bar->set_name("BreakBar");
        break_bar->set_h_flags(gd::SIZE_EXPAND_FILL);
        break_bar->set_v_flags(gd::SIZE_SHRINK_CENTER);
        br->add(break_bar);
        col->add(br);
        break_bar->set_values((float)combatant->break_value, (float)combatant->break_max, false);
        gd::listen(this, combatant->break_changed, [this] { on_break(); });
    }
    auto bottom = UIKit::hbox(6);
    bottom->set_mouse_filter(gd::MOUSE_IGNORE);
    if (is_boss)
    {
        phase_tag = UIKit::tag(phase_text(), Col("#7a1a14"));
        phase_tag->set_name("PhaseTag");
        bottom->add(phase_tag);
        add_phase_tick();
    }
    else if (combatant->is_elite)
        bottom->add(UIKit::tag("ELITE", Col("#8a6a10")));
    status_row = UIKit::hbox(4);
    status_row->set_h_flags(gd::SIZE_EXPAND_FILL);
    bottom->add(status_row);
    pct = UIKit::label("", UIKit::T_SMALL, UIKit::TEXT, gd::ALIGN_RIGHT, 5);
    bottom->add(pct);
    col->add(bottom);
    gd::listen(this, combatant->hp_changed, [this](int cur, int mx) { on_hp(cur, mx); });
    gd::listen(this, combatant->statuses_changed, [this] {
        on_statuses();
        if (break_bar) on_break();
    });
    bar->set_values((float)combatant->hp, (float)combatant->max_hp, false);
    _last_hp = combatant->hp;
    on_hp(combatant->hp, combatant->max_hp);
    gui_input.connect([this](gd::InputEvent& e) {
        if (e.type == gd::Ev::PRESS) e.accept();   // keep the release on this plate
        else if (e.type == gd::Ev::RELEASE && combatant->is_alive())
        {
            tapped.emit(combatant);
            e.accept();
        }
    });
    set_targeted(false);
}

void EnemyPlate::on_hp(int current, int maximum)
{
    bar->set_values((float)current, (float)maximum);
    pct->set_text(UIKit::fmt("%d%%", (int)std::ceil(float(current) / std::max(maximum, 1) * 100.0f)));
    if (current <= 0)
    {
        set_targeted(false);
        auto tw = gd::tween(this);
        tw->interval(0.4f);
        tw->modulate(this, Col(0.45f, 0.4f, 0.45f, 0.55f), 0.3f);
        pct->set_text("DOWN");
    }
    else if (current < _last_hp)
    {
        // brief hit blink (self_modulate above 1 clamps in this toolkit)
        auto tw = gd::tween(this);
        tw->modulate(this, Col(1.8f, 1.5f, 1.5f), 0.04f);
        tw->modulate(this, _targeted ? Col::WHITE : Col(0.78f, 0.76f, 0.82f), 0.12f);
    }
    _last_hp = current;
}

void EnemyPlate::on_break()
{
    bool broken = combatant->is_broken();
    break_bar->set_values(broken ? 0.0f : (float)combatant->break_value, (float)combatant->break_max);
    break_label->set_text(broken ? "BROKEN" : "BREAK");
    break_label->set_modulate(broken ? Col("#ff8a5a") : Col::WHITE);
}

void EnemyPlate::on_statuses()
{
    status_row->clear_children();
    bool charging = false;
    for (auto& s : combatant->statuses)
    {
        status_row->add(StatusIcon::make(S(s, "id"), I(s, "turns", 0), (float)F(s, "value", 0.0), 32));
        charging = charging || S(s, "id") == "charging";
    }
    set_danger(charging);
}

static Json phase_list(const Json& def)
{
    const Json& ai = O(def, "ai");
    if (ai.contains("phases")) return ai["phases"];
    return ai.contains("phase2") ? Json::array({ai["phase2"]}) : Json::array();
}

// "PHASE 1 / n" for bosses with phases, otherwise ANCIENT FOE.
std::string EnemyPlate::phase_text() const
{
    int n = (int)phase_list(combatant->def).size();
    if (n == 0) return "ANCIENT FOE";
    return UIKit::fmt("PHASE %d / %d", combatant->phase_index + 1, n + 1);
}

// Small marks on the HP bar where each phase begins.
void EnemyPlate::add_phase_tick()
{
    for (auto& ph : phase_list(combatant->def))
    {
        auto tick = gd::ColorRect::create(Col("#ffd35a"));
        tick->set_name("PhaseTick");
        tick->set_mouse_filter(gd::MOUSE_IGNORE);
        bar->add(tick);
        _ticks.push_back(tick);
        float ratio = (float)F(ph, "below", 0.5);
        auto b = bar;
        bar->resized.connect([tick, b, ratio] {
            tick->set_size(Vec2(6, b->size().y));
            tick->set_position(Vec2(6 + (b->size().x - 12) * ratio - 3, 0));
        });
    }
}

void EnemyPlate::refresh_phase()
{
    if (!phase_tag) return;
    if (auto l = dynamic_cast<gd::Label*>(phase_tag->children().front())) l->set_text(phase_text());
    phase_tag->set_style(UIKit::flat(Col("#b8281e"), Col("#ffd35a"), 3).content(10, 2, 10, 2));
    for (int i = 0; i < (int)_ticks.size(); ++i) _ticks[i]->setVisible(i >= combatant->phase_index);
}

// DANGER: the foe is charging a big attack (guard!). Pulses until it fires.
void EnemyPlate::set_danger(bool on)
{
    if (on && !_danger)
    {
        _danger = UIKit::tag("DANGER - GUARD!", Col("#c8281e"));
        _danger->set_name("DangerTag");
        auto parent = status_row->parent_control();
        parent->add(_danger);
        parent->move_child(_danger, 0);
        auto tw = gd::tween(_danger);
        tw->loops();
        tw->modulate(_danger, Col(1.6f, 1.2f, 1.2f), 0.3f);
        tw->modulate(_danger, Col::WHITE, 0.3f);
    }
    else if (!on && _danger)
    {
        _danger->queue_free();
        _danger = nullptr;
    }
}

void EnemyPlate::set_targeted(bool on)
{
    _targeted = on && combatant->is_alive();
    marker->setVisible(_targeted);
    if (_pulse) _pulse->kill();
    _pulse = nullptr;
    if (!combatant->is_alive()) return;
    set_modulate(_targeted ? Col::WHITE : Col(0.78f, 0.76f, 0.82f));
    if (_targeted)
    {
        _pulse = gd::tween(this);
        _pulse->loops();
        _pulse->modulate(marker, Col(1.6f, 1.3f, 0.8f), 0.35f);
        _pulse->modulate(marker, Col::WHITE, 0.35f);
    }
}

// ================================================================== CutinDecor
// Element-themed motion inside the Burst cut-in band.
//   fire: racing ember streaks + rising sparks   water: flowing twin ribbon + bubbles   nature: roots + earth bits
namespace
{
// Two flowing sine ribbons drawn with chunky pixel steps.
class Ribbon : public gd::Node2D
{
public:
    Vec2 area;
    float t = 0;
    ax::DrawNode* dn = nullptr;
    void update(float dt) override
    {
        t += dt;
        dn->clear();
        for (int k = 0; k < 2; ++k)
        {
            float amp = 40.0f - k * 12.0f, yb = area.y * (0.45f + k * 0.2f);
            Col col = k == 0 ? Col("#5ac8ff") : Col("#bff0ff");
            for (float x = 0; x < area.x; x += 12.0f)
            {
                float y = yb + std::sin(x * 0.012f + t * (6.0f + k * 2.0f)) * amp;
                dn->drawSolidRect(gd::p2(x, y), gd::p2(x + 12, y + 12 - k * 4), col.c4f());
                dn->drawSolidRect(gd::p2(x, y + 12), gd::p2(x + 12, y + 18), Col(0.2f, 0.5f, 0.8f, 0.6f).c4f());
            }
        }
    }
};

// Roots that grow inward from both bottom corners and the band edges.
class Roots : public gd::Node2D
{
public:
    float t = 0;
    std::vector<std::vector<Vec2>> branches;
    ax::DrawNode* dn = nullptr;
    void grow(Vec2 area)
    {
        Rng rng;
        rng.seed(7);
        for (int i = 0; i < 7; ++i)
        {
            bool from_left = i % 2 == 0;
            Vec2 p(from_left ? 0 : area.x, area.y - (float)rng.randf_range(0, area.y * 0.8f));
            std::vector<Vec2> pts{p};
            for (int s = 0; s < 14; ++s)
            {
                p += Vec2((from_left ? 1 : -1) * (float)rng.randf_range(24, 44), (float)rng.randf_range(-22, 22));
                pts.push_back(p);
            }
            branches.push_back(pts);
        }
    }
    void update(float dt) override
    {
        t = std::min(t + dt * 1.6f, 1.0f);
        dn->clear();
        for (auto& pts : branches)
        {
            int n = (int)std::floor((pts.size() - 1) * t);
            for (int i = 0; i < n; ++i)
            {
                float w = 14.0f - i * 0.8f;
                dn->drawSegment(gd::p2(pts[i]), gd::p2(pts[i + 1]), std::max(w + 4, 4.0f) / 2, Col("#3a2616").c4f());
                dn->drawSegment(gd::p2(pts[i]), gd::p2(pts[i + 1]), std::max(w, 2.0f) / 2,
                                (i % 3 == 0 ? Col("#6a8a3a") : Col("#5a4026")).c4f());
            }
        }
    }
};

void streaks(Control* band, bool fx_on)
{
    int n = fx_on ? 14 : 6;
    Vec2 bs = band->size();
    for (int i = 0; i < n; ++i)
    {
        static const Col cols[3] = {Col("#ffb03a"), Col("#ff6a1e"), Col("#fff0a0")};
        auto s = gd::ColorRect::create(cols[i % 3]);
        s->set_mouse_filter(gd::MOUSE_IGNORE);
        float h = 4.0f + (i % 3) * 4;
        s->set_size(Vec2(160.0f + (i * 53) % 260, h));
        s->set_position(Vec2(bs.x + (i * 97) % 600, 20.0f + (i * 71) % int(bs.y - 40)));
        band->add(s);
        auto tw = gd::tween(s);
        tw->loops();
        tw->method([s](float x) { s->set_position_x(x); }, bs.x + 20, -s->size().x - 20, 0.35f + (i % 4) * 0.08f);
    }
}

void particles(Control* band, const Col& c0, const Col& c1, Vec2 gravity, int amount, float smin, float smax, bool burst = false)
{
    Vec2 bs = band->size();
    gd::ParticleCfg p;
    p.amount = amount;
    p.lifetime = 1.0f;
    p.preprocess = 0.3f;
    p.explosiveness = burst ? 0.6f : 0.0f;
    p.emission_rect = Vec2(bs.x * 0.5f, 20);
    p.direction = Vec2(0, -1);
    p.spread = 30;
    p.gravity = gravity;
    p.vel_min = burst ? 200.0f : 60.0f;
    p.vel_max = burst ? 420.0f : 160.0f;
    p.scale_min = smin;
    p.scale_max = smax;
    p.ramp = {c0, c1};
    auto n = gd::Particles::create(p);
    n->set_position(Vec2(bs.x * 0.5f, bs.y * (gravity.y < 0 ? 0.95f : 0.6f)));
    band->add(n);
}

template <class T>
T* drawn(Control* band)
{
    auto d = gd::make<T>();
    d->dn = ax::DrawNode::create();
    d->dn->setBlendFunc(ax::BlendFunc::ALPHA_NON_PREMULTIPLIED);
    d->addChild(d->dn);
    d->scheduleUpdate();
    band->add(d);
    return d;
}
}  // namespace

void CutinDecor::add(Control* band, const std::string& element)
{
    bool fx_on = BattleFx::fx_enabled();
    if (element == "fire")
    {
        streaks(band, fx_on);
        particles(band, Col("#ffd35a"), Col(1, 0.3f, 0.1f, 0), Vec2(0, -80), fx_on ? 30 : 10, 4, 10);
    }
    else if (element == "water")
    {
        drawn<Ribbon>(band)->area = band->size();
        particles(band, Col("#dff6ff"), Col(0.5f, 0.8f, 1, 0), Vec2(0, -120), fx_on ? 24 : 8, 6, 12);
    }
    else if (element == "nature")
    {
        drawn<Roots>(band)->grow(band->size());
        particles(band, Col("#b08a5a"), Col(0.3f, 0.2f, 0.1f, 0), Vec2(0, 260), fx_on ? 22 : 8, 6, 12, true);
    }
}
