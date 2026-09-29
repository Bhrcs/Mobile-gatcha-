// Victory / defeat screen (scripts/ui/battle_result.gd).
// Victory: a sequenced reveal - stars -> party cards -> EXP counts up and bars fill (LEVEL UP)
// -> gold -> reward items -> first-clear bonus -> unlocks / rank -> CONTINUE. Tap anywhere to fast-forward.
// Defeat: DEFEAT, one useful tip, then RETRY / EDIT SQUAD / STAGE SELECT.
#include "battle/BattleScene.h"
#include <cmath>

using gd::Control;

static const std::map<std::string, std::string> FEATURE_NAMES{
    {"auto", "Auto Battle"}, {"units", "Units"}, {"squad", "Squad (5 heroes)"}, {"training", "Training"},
    {"tower", "Elemental Towers"}, {"evolution", "Evolution"}, {"summon", "Embergate Summoning"}, {"missions", "Missions"},
    {"world2", "World 2: Saltglass Reach"}};

BattleResult* BattleResult::create()
{
    auto r = gd::make<BattleResult>();
    r->set_anchors_preset(gd::PRESET_FULL_RECT);
    r->set_mouse_filter(gd::MOUSE_STOP);
    r->gui_input.connect([r](gd::InputEvent& e) {
        if (e.type == gd::Ev::PRESS) r->skip_now();
    });
    return r;
}

void BattleResult::skip_now()
{
    _fast = true;
    if (_skip) _skip->setVisible(false);
}

bool BattleResult::handle_enter()
{
    if (!sequence_done)
    {
        skip_now();
        return true;
    }
    if (_default && !_default->disabled() && !UIManager::top_popup())
    {
        _default->pressed.emit();
        return true;
    }
    return false;
}

void BattleResult::add_skip()
{
    _skip = UIKit::btn("SKIP", "quiet", Vec2(200, 88));
    _skip->set_name("SkipResults");
    Vec2 vs = gd::Root::get()->size();
    _skip->set_position(Vec2(vs.x - 230, vs.y - 140 - UIKit::safe_bottom()));
    _skip->pressed.connect([this] { skip_now(); });
    add(_skip);
}

Step BattleResult::step(float t)
{
    return [this, t](Next n) { gd::after(this, t * (_fast ? 0.15f : 1.0f), n); };
}

void BattleResult::frame(const std::string& title, const Col& color, const std::string& variant)
{
    auto dim = gd::ColorRect::create(Col(0.03f, 0.02f, 0.05f, 0.7f));
    dim->set_anchors_preset(gd::PRESET_FULL_RECT);
    dim->set_mouse_filter(gd::MOUSE_IGNORE);
    add(dim);
    auto center = gd::CenterContainer::create();
    center->set_anchors_preset(gd::PRESET_FULL_RECT);
    center->set_mouse_filter(gd::MOUSE_IGNORE);
    add(center);
    _panel = PanelFrame::make(variant, 30);
    _panel->set_min_w(1030);
    center->add(_panel);
    _content = UIKit::vbox(16);
    _panel->add(_content);
    auto t = UIKit::heading(title, 120, color);
    t->set_outline(20, Col("#2a0a04"));
    t->set_name("ResultTitle");
    _content->add(t);
    _panel->set_alpha(0.0f);
    _panel->set_pivot(Vec2(515, 300));
    _panel->setScale(0.9f);
    auto tw = gd::tween(this);
    tw->set_parallel();
    tw->alpha(_panel, 1.0f, 0.2f);
    tw->scale(_panel, Vec2(1, 1), 0.2f).trans(gd::TRANS_BACK);
    // (the Godot title shine tweens modulate above 1, which clamps to white here)
}

// ------------------------------------------------------------------ victory
void BattleResult::show_victory(const Json& summary, bool has_next)
{
    frame("VICTORY", UIKit::GOLD);
    UIKit::sparkle(this, gd::Rect2{Vec2(40, 200), Vec2(1000, 400)}, Col("#ffe08a"), 16);

    // star objectives
    const Json& stage = DB.stage(GM.current_stage_id);
    auto stars_box = UIKit::hbox(18);
    stars_box->alignment = gd::ALIGNMENT_CENTER;
    stars_box->set_name("StarRow");
    _content->add(stars_box);
    std::vector<std::pair<gd::TextureRect*, bool>> star_nodes;
    const Json& objs = A(stage, "stars");
    const Json& run = A(summary, "stars_this_run");
    for (size_t i = 0; i < objs.size(); ++i)
    {
        auto col = UIKit::vbox(2);
        col->set_min_w(320);
        bool got = i < run.size() && B(run[i], false);
        auto ic = UIKit::icon(got ? "assets/icons/star_obj.png" : "assets/icons/star_obj_empty.png", 72);
        ic->set_h_flags(gd::SIZE_SHRINK_CENTER);
        ic->set_alpha(0.0f);
        col->add(ic);
        auto tl = UIKit::wrap_label(S(objs[i], "text"), UIKit::T_SMALL, got ? UIKit::TEXT : UIKit::MUTED);
        tl->h_align = gd::ALIGN_CENTER;
        tl->set_min_w(300);
        col->add(tl);
        stars_box->add(col);
        star_nodes.push_back({ic, got});
    }

    // party with EXP bars
    auto party_box = UIKit::vbox(8);
    _content->add(party_box);
    std::vector<Row> rows;
    const Json& units = A(summary, "units");
    for (auto& u : units)
    {
        Row row = unit_row(u, units.size() > 3);
        row.node->set_alpha(0.0f);
        party_box->add(row.node);
        rows.push_back(row);
    }

    // counters
    auto counters = UIKit::hbox(40);
    counters->alignment = gd::ALIGNMENT_CENTER;
    auto xp_l = counter(counters, "assets/icons/xp.png", Col("#c0a8ff"));
    auto gold_l = counter(counters, "assets/icons/gold.png", UIKit::GOLD);
    counters->set_alpha(0.0f);
    _content->add(counters);

    // reward slots
    auto reward_row = gd::FlowContainer::create();
    reward_row->set_name("RewardRow");
    reward_row->alignment = gd::ALIGNMENT_CENTER;
    reward_row->h_separation = 14;
    reward_row->v_separation = 10;
    reward_row->set_custom_min(Vec2(960, 150));
    _content->add(reward_row);

    auto extra = UIKit::vbox(6);
    _content->add(extra);

    auto buttons = UIKit::hbox(20);
    buttons->alignment = gd::ALIGNMENT_CENTER;
    auto b_next = FantasyButton::make("CONTINUE", "ember", Vec2(480, 130));
    b_next->set_name("ContinueButton");
    b_next->set_font_size(50);
    auto b_retry = FantasyButton::make("RETRY", "stone", Vec2(260, 110));
    b_next->pressed.connect([this] { next_pressed.emit(); });
    b_next->add_shine(2.0f);
    b_retry->pressed.connect([this] { retry_pressed.emit(); });
    buttons->add(b_next);
    buttons->add(b_retry);
    buttons->set_alpha(0.0f);
    b_next->set_disabled(true);
    b_retry->set_disabled(true);
    _content->add(buttons);
    _default = b_next;
    add_skip();

    // ---- sequence
    std::vector<Step> steps;
    auto then = [&steps](std::function<void()> f) { steps.push_back([f](Next n) { f(); n(); }); };
    steps.push_back(step(0.3f));
    for (auto [ic, got] : star_nodes)
    {
        then([this, ic = ic, got = got] {
            ic->set_alpha(1.0f);
            pop(ic);
            if (got) AudioManager::play_sfx("reward", 0.05f, -8.0f);
        });
        steps.push_back(step(0.14f));
    }
    steps.push_back(step(0.1f));
    for (auto& r : rows)
    {
        auto node = r.node;
        then([this, node] {
            gd::tween(this)->alpha(node, 1.0f, 0.18f);
            AudioManager::play_sfx("unit_select", 0.03f, -6.0f);
        });
        steps.push_back(step(0.12f));
    }
    int xp = I(summary, "xp", 0), gold = I(summary, "gold", 0);
    steps.push_back([this, counters, xp_l, xp](Next n) {
        gd::tween(this)->alpha(counters, 1.0f, 0.15f);
        count(xp_l, xp, "+%s EXP", n);
    });
    then([this, rows] {
        for (auto& r : rows) animate_xp(r);
    });
    steps.push_back(step(0.2f));
    steps.push_back([this, gold_l, gold](Next n) { count(gold_l, gold, "+%s G", n); });
    then([] { AudioManager::play_sfx("reward", 0.02f, -3.0f); });
    steps.push_back(step(0.2f));
    // items physically drop into slots
    auto drop = [&](const Json& items, const std::string& caption) {
        for (auto& [item_id, qty] : items.items())
        {
            std::string icon = S(DB.item(item_id), "icon");
            std::string q = UIKit::fmt("x%d", I(qty));
            then([reward_row, icon, q, caption] {
                auto ri = RewardItem::make(icon, q, caption, 130);
                reward_row->add(ri);
                ri->pop(0.0f);
            });
            steps.push_back(step(0.16f));
        }
    };
    const Json& items = O(summary, "items");
    const Json& fcr = O(summary, "first_clear_reward");
    drop(items, "");
    drop(O(fcr, "items"), "FIRST");
    bool first_clear = B(summary, "first_clear", false);
    then([reward_row, empty = items.empty() && O(fcr, "items").empty()] {
        if (empty) reward_row->add(UIKit::label("No items dropped this time.", UIKit::T_BODY, UIKit::MUTED, gd::ALIGN_CENTER));
    });
    if (first_clear)
    {
        steps.push_back(step(0.15f));
        then([this, extra, fcr, summary] {
            int gems = I(fcr, "gems", 0);
            auto fc = UIKit::hbox(12);
            fc->alignment = gd::ALIGNMENT_CENTER;
            fc->add(UIKit::title_plate("FIRST CLEAR  +" + UIKit::format_number(I(summary, "first_clear_gold", 0)) + " G", 40));
            if (gems > 0)
            {
                auto gh = UIKit::hbox(6);
                gh->add(UIKit::icon("assets/icons/gem.png", 56));
                gh->add(UIKit::label(UIKit::fmt("+%d", gems), UIKit::T_NAME, Col("#9ae8ff"), gd::ALIGN_LEFT, 8));
                fc->add(gh);
            }
            fc->set_name("FirstClear");
            extra->add(fc);
            pop(fc);
            AudioManager::play_sfx("level_up", 0.0f, -6.0f);
        });
    }
    then([this, extra, summary, has_next, first_clear, stage] {
        auto line = [extra](const std::string& text, int size, const Col& c, int outline = 6) {
            auto l = UIKit::label(text, size, c, gd::ALIGN_CENTER, outline);
            extra->add(l);
            return l;
        };
        int new_stars = I(summary, "new_stars", 0);
        if (new_stars > 0 && !first_clear)
            line(UIKit::fmt("NEW STAR%s EARNED!", new_stars > 1 ? "S" : ""), UIKit::T_BODY, UIKit::GOLD);
        for (auto& u : A(summary, "units"))
            if (B(u, "burst_up", false))
                line(UIKit::fmt("%s's Burst reached Lv.%d!", S(DB.character(S(u, "char_id")), "name").c_str(), I(O(u, "after"), "burst_level", 1)),
                     UIKit::T_BODY, UIKit::EMBER);
        for (auto& sid : A(summary, "unlocked"))
            line("NEW: " + upper(GM.stage_label(S(sid))) + "  " + upper(S(DB.stage(S(sid)), "name", S(sid))), UIKit::T_BODY, UIKit::GOOD);
        for (auto& f : A(summary, "features"))
        {
            auto it = FEATURE_NAMES.find(S(f));
            pop(line("UNLOCKED: " + upper(it != FEATURE_NAMES.end() ? it->second : S(f)), UIKit::T_BODY, Col("#ffe08a")));
        }
        const Json& gift = O(summary, "gift");
        if (gift.contains("hero"))
            line(S(DB.character(S(gift, "hero")), "name") + " joins you!", UIKit::T_NAME, UIKit::GOLD, 8);
        if (I(gift, "gems", 0) > 0) line(UIKit::fmt("Gift: +%d Gems", I(gift, "gems", 0)), UIKit::T_BODY, Col("#9ae8ff"));
        if (first_clear && !has_next && !B(summary, "tower", false))
        {
            line(upper(S(O(DB.worlds, S(stage, "world_id")), "name")) + " CLEARED!", UIKit::T_NAME, UIKit::GOLD, 8);
            std::string nxt;
            for (auto& w : DB.world_order)
                if (S(O(DB.worlds, w), "requires") == GM.current_stage_id) nxt = S(O(DB.worlds, w), "name");
            extra->add(UIKit::label(!nxt.empty() ? "New region open: " + nxt : "More regions will open in a future update.", UIKit::T_SMALL,
                                    UIKit::MUTED, gd::ALIGN_CENTER));
        }
    });
    steps.push_back(step(0.25f));
    const Json& ups = A(summary, "rank_ups");
    if (!ups.empty())
        steps.push_back([this, ups](Next n) {
            if (auto o = RankUpOverlay::play(this, ups)) o->closed.connect(n);
            else n();
        });
    then([this, buttons, b_next, b_retry] {
        gd::tween(this)->alpha(buttons, 1.0f, 0.2f);
        b_next->set_disabled(false);
        b_retry->set_disabled(false);
        sequence_done = true;
        if (_skip) _skip->queue_free();
        _skip = nullptr;
    });
    Chain::run(std::move(steps));
}

gd::Label* BattleResult::counter(Control* parent, const std::string& icon_path, const Col& color)
{
    auto h = UIKit::hbox(10);
    h->add(UIKit::icon(icon_path, 64));
    auto l = UIKit::label("+0", UIKit::T_HEAD, color, gd::ALIGN_LEFT, 10);
    l->set_min_w(300);
    h->add(l);
    parent->add(h);
    return l;
}

void BattleResult::count(gd::Label* l, int total, const std::string& fmt, Next done)
{
    float t = 0.5f * (_fast ? 0.2f : 1.0f);
    auto tw = gd::tween(this);
    tw->method([l, fmt](float v) { l->set_text(UIKit::fmt(fmt.c_str(), UIKit::format_number((long long)v).c_str())); }, 0.0f, (float)total, t);
    tw->on_finished([this, l, total, fmt, done] {
        l->set_text(UIKit::fmt(fmt.c_str(), UIKit::format_number(total).c_str()));
        pop(l);
        done();
    });
}

BattleResult::Row BattleResult::unit_row(const Json& u, bool compact)
{
    const Json& def = DB.character(S(u, "char_id"));
    auto panel = PanelFrame::make("card_" + S(def, "element", "neutral"), compact ? 8 : 12);
    panel->set_name("ResultUnit_" + S(u, "uid"));
    auto h = UIKit::hbox(16);
    panel->add(h);
    h->add(UIKit::portrait_art(def, compact ? Vec2(88, 88) : Vec2(128, 128)));
    auto v = UIKit::vbox(6);
    v->set_h_flags(gd::SIZE_EXPAND_FILL);
    h->add(v);
    auto name_row = UIKit::hbox(16);
    auto nm = UIKit::label(S(def, "name"), UIKit::T_BODY, Col::WHITE, gd::ALIGN_LEFT, 6);
    nm->set_h_flags(gd::SIZE_EXPAND_FILL);
    name_row->add(nm);
    int before_level = I(O(u, "before"), "level", 1);
    auto lvl = UIKit::label(UIKit::fmt("Lv.%d", before_level), UIKit::T_NAME, UIKit::GOLD, gd::ALIGN_RIGHT, 8);
    name_row->add(lvl);
    v->add(name_row);
    auto bar = ResourceBar::make("xp", 30);
    bar->set_values((float)I(O(u, "before"), "exp", 0), (float)Progression::xp_to_next(before_level), false);
    v->add(bar);
    auto gains = UIKit::label("", UIKit::T_SMALL, UIKit::GOOD, gd::ALIGN_LEFT, 5);
    v->add(gains);
    auto stamp = UIKit::label("LEVEL UP!", UIKit::T_HEAD, Col("#fff0a0"), gd::ALIGN_CENTER, 10);
    stamp->setVisible(false);
    stamp->setRotation(-0.1f * 180.0f / 3.14159265f);
    stamp->set_size(Vec2(360, 60));
    stamp->set_pivot(Vec2(180, 30));
    stamp->set_outline_color(Col("#6a2a08"));
    auto holder = Control::create();   // overlay so the stamp can sit on the card corner
    holder->set_mouse_filter(gd::MOUSE_IGNORE);
    panel->add(holder);
    holder->add(stamp);
    panel->resized.connect([panel, stamp] { stamp->set_position(Vec2(panel->size().x - 400, -40)); });
    return {panel, u, bar, lvl, gains, stamp};
}

// Fills the XP bar, rolling over once per level gained (LEVEL UP stamp + sound).
void BattleResult::animate_xp(const Row& row)
{
    const Json& u = row.data;
    std::string char_id = S(u, "char_id");
    int start_level = I(O(u, "before"), "level", 1);
    auto level = std::make_shared<int>(start_level);
    const Json& level_ups = A(u, "level_ups");
    int n_ups = (int)level_ups.size();
    std::vector<Step> steps;
    for (auto& up : level_ups)
    {
        int new_level = I(up, "level", start_level);
        steps.push_back([row](Next n) {
            row.bar->set_values(row.bar->max_value, row.bar->max_value);
            n();
        });
        steps.push_back(step(0.35f));
        steps.push_back([this, row, level, new_level, start_level, n_ups, char_id](Next n) {
            *level = new_level;
            row.level->set_text(UIKit::fmt("Lv.%d > %d", start_level, new_level));
            // gains are shown as the total since the battle started (several levels add up)
            Json total = GM.unit_stats({{"char_id", char_id}, {"level", new_level}});
            Json base = GM.unit_stats({{"char_id", char_id}, {"level", start_level}});
            row.gains->set_text(UIKit::fmt("HP +%d  ATK +%d  DEF +%d  REC +%d", I(total, "hp", 0) - I(base, "hp", 0),
                                           I(total, "atk", 0) - I(base, "atk", 0), I(total, "def", 0) - I(base, "def", 0),
                                           I(total, "rec", 0) - I(base, "rec", 0)));
            AudioManager::play_sfx("level_up", 0.02f, new_level - start_level == 1 ? -2.0f : -6.0f);
            row.stamp->set_text(n_ups <= 1 ? "LEVEL UP!" : UIKit::fmt("LEVEL UP x%d", new_level - start_level));
            row.stamp->setVisible(true);
            pop(row.stamp);
            pop(row.level);
            // (the Godot card flash tweens modulate above 1, which clamps to white here)
            row.bar->set_values(0, (float)Progression::xp_to_next(new_level), false);
            n();
        });
    }
    Chain::run(std::move(steps), [row, level, char_id] {
        const Json& def = DB.character(char_id);
        if (*level >= I(def, "max_level", 20))
        {
            row.bar->set_values(1, 1, false);
            row.gains->set_text(row.gains->text() + "   MAX LEVEL" + (at(def, "evolution").is_object() ? "  -  ready to Evolve!" : ""));
            return;
        }
        row.bar->set_values((float)I(O(row.data, "after"), "exp", 0), (float)Progression::xp_to_next(*level));
    });
}

void BattleResult::pop(Control* c)
{
    c->set_pivot(c->size() / 2);
    c->setScale(1.4f);
    gd::tween(this)->scale(c, Vec2(1, 1), 0.2f).trans(gd::TRANS_BACK);
}

// ------------------------------------------------------------------ defeat
void BattleResult::show_defeat()
{
    frame("DEFEAT", UIKit::DANGER, "boss");
    auto msg = UIKit::wrap_label("Your squad has fallen. Nothing is lost.", UIKit::T_BODY);
    msg->h_align = gd::ALIGN_CENTER;
    msg->set_min_w(940);
    _content->add(msg);
    auto tip = PanelFrame::make("inset", 16);
    tip->set_name("DefeatTip");
    auto th = UIKit::hbox(UIKit::SP_M);
    tip->add(th);
    th->add(UIKit::icon("assets/icons/info.png", 48));
    auto tl = UIKit::wrap_label(defeat_tip(), UIKit::T_BODY, Col("#fff0c0"));
    tl->set_min_w(820);
    th->add(tl);
    _content->add(tip);
    auto buttons = UIKit::hbox(16);
    buttons->alignment = gd::ALIGNMENT_CENTER;
    auto b_retry = UIKit::btn("RETRY", "primary", Vec2(300, 120));
    b_retry->set_name("RetryButton");
    auto b_party = UIKit::btn("EDIT SQUAD", "secondary", Vec2(320, 120));
    b_party->set_name("EditSquadButton");
    auto b_stage = UIKit::btn("STAGE SELECT", "quiet", Vec2(320, 120));
    b_stage->set_name("StageSelectButton");
    b_stage->set_font_size(UIKit::T_BODY);
    b_retry->pressed.connect([this] { retry_pressed.emit(); });
    b_party->pressed.connect([this] { party_pressed.emit(); });
    b_stage->pressed.connect([this] { stage_select_pressed.emit(); });
    for (auto b : {b_retry, b_party, b_stage}) buttons->add(b);
    _content->add(buttons);
    int cost = I(DB.stage(GM.current_stage_id), "energy", 0);
    _content->add(UIKit::label(UIKit::fmt("Retry costs %d Energy (you have %d).", cost, GM.energy()), UIKit::T_SMALL, UIKit::MUTED,
                               gd::ALIGN_CENTER, 5));
    _default = b_retry;
    sequence_done = true;
}

// The most useful advice for this defeat: power first, then elements, then a general tip.
std::string BattleResult::defeat_tip()
{
    const Json& stage = DB.stage(GM.current_stage_id);
    int rec = I(stage, "recommended_power", 0);
    int sp = GM.squad_power();
    if (rec > 0 && sp < rec)
        return "Squad power " + UIKit::format_number(sp) + " is below the recommended " + UIKit::format_number(rec) +
               ". Train heroes with Wisps or evolve them, then try again.";
    Json mine = Json::array();
    for (auto& u : GM.party_units())
    {
        std::string el = S(DB.character(S(u, "char_id")), "element");
        if (!contains(mine, el)) mine.push_back(el);
    }
    auto advice = StageInfo::matchup_advice(mine, StageInfo::elements(stage));
    // [text, flag] - the flag marks a real problem worth showing
    if (advice.size() > 1 && !advice[1].empty() && advice[1] != "false" && advice[1] != "0") return advice[0];
    static const char* general[] = {"Swipe DOWN on a card to Guard when a foe shows DANGER - it halves the damage.",
                                    "Save Bursts for the last wave or the boss: swipe UP on a full card.",
                                    "A healer in the squad keeps everyone standing through long fights.",
                                    "Your leader's Leader Skill boosts the whole squad - pick a leader that matches your team."};
    return general[std::rand() % 4];
}
