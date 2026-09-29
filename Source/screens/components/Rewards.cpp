// Reward & stage components: RewardItem, RewardPopup, EnergyPopup, StageNode, StageInfo, RankUpOverlay
// (scripts/ui/components/reward_item.gd, reward_popup.gd, energy_popup.gd, stage_node.gd, stage_info.gd,
// rank_up_overlay.gd).
#include "screens/Screens.h"

using namespace gd;

static std::string first_word(const std::string& s) { return s.substr(0, s.find(' ')); }
static bool has(const Json& arr, const std::string& v) { return contains(arr, Json(v)); }

// ================================================================== RewardItem
RewardItem* RewardItem::make(const std::string& icon_p, const std::string& qty, const std::string& cap, int slot_px)
{
    auto r = gd::make<RewardItem>();
    r->icon_path = icon_p;
    r->qty_text = qty;
    r->caption = cap;
    r->px = slot_px;
    float px = (float)slot_px;
    r->set_custom_min(Vec2(px, px + (cap.empty() ? 0 : 40)));
    auto slot = PanelFrame::make("slot", 12);
    slot->set_size(Vec2(px, px));
    slot->set_mouse_filter(MOUSE_IGNORE);
    r->add(slot);
    int isz = UIKit::snap_icon(int(px * 0.62f));
    auto ic = UIKit::icon(icon_p, isz);
    ic->set_position(Vec2((px - isz) / 2.0f, px * 0.1f));
    ic->set_size(Vec2((float)isz, (float)isz));
    r->add(ic);
    int fs = slot_px >= 130 ? 30 : 20;
    auto q = UIKit::label(qty, fs, Col::WHITE, ALIGN_RIGHT, 6);
    q->set_position(Vec2(0, px - fs - 14));
    q->set_size(Vec2(px - 10, (float)fs + 8));
    r->add(q);
    if (!cap.empty())
    {
        auto c = UIKit::label(cap, 20, UIKit::MUTED, ALIGN_CENTER);
        c->set_position(Vec2(-20, px + 2));
        c->set_size(Vec2(px + 40, 36));
        r->add(c);
    }
    r->set_pivot(Vec2(px / 2, px / 2));
    // Godot _ready: callers may flip hidden_start after make()
    r->setOnEnterCallback([r] { r->set_alpha(r->hidden_start ? 0.0f : 1.0f); });
    return r;
}

void RewardItem::pop(float delay, bool silent)
{
    setScale(0.3f);
    auto tw = gd::tween(this);
    tw->interval(delay);
    if (!silent) tw->callback([] { AudioManager::play_sfx("reward", 0.05f, -4.0f); });
    tw->set_parallel(true);
    tw->alpha(this, 1.0f, 0.12f);
    tw->scale(this, Vec2(1.15f, 1.15f), 0.12f).trans(TRANS_BACK);
    tw->chain().scale(this, Vec2(1, 1), 0.08f);
}

// ================================================================== RewardPopup
FantasyPopup* RewardPopup::open(Control* parent, const std::string& title, const Json& r, const std::string& sub)
{
    auto p = FantasyPopup::open(parent, title, 900, "boss");
    p->set_name("RewardPopup");
    if (!sub.empty())
    {
        auto s = UIKit::wrap_label(sub, UIKit::T_BODY, Col("#fff0c0"));
        s->set_align(ALIGN_CENTER);
        s->set_min_w(820);
        p->content->add(s);
    }
    auto row = FlowContainer::create();
    row->alignment = ALIGNMENT_CENTER;
    row->h_separation = 14;
    row->set_min_w(820);
    p->content->add(row);
    std::vector<RewardItem*> slots;
    if (I(r, "gems", 0) > 0)
        slots.push_back(RewardItem::make("assets/icons/gem.png", std::to_string(I(r, "gems", 0)), "GEMS", 120));
    if (I(r, "gold", 0) > 0)
        slots.push_back(RewardItem::make("assets/icons/gold.png", UIKit::format_number(I(r, "gold", 0)), "GOLD", 120));
    if (I(r, "soul_shards", 0) > 0)
        slots.push_back(RewardItem::make("assets/icons/soul_shard.png", std::to_string(I(r, "soul_shards", 0)), "SHARDS", 120));
    for (auto& [item_id, q] : O(r, "items").items())
        slots.push_back(RewardItem::make(S(DB.item(item_id), "icon"), "x" + std::to_string(I(q)),
                                         upper(first_word(DB.item_name(item_id))), 120));
    int k = 0;
    for (auto s : slots)
    {
        row->add(s);
        s->pop(0.08f * k++);
    }
    UIKit::sparkle(p->panel, Rect2{Vec2(0, 0), Vec2(900, 400)}, UIKit::GOLD, 10);
    auto ok = FantasyButton::make("OK", "ember", Vec2(300, 110));
    ok->set_name("RewardOK");
    ok->set_h_flags(SIZE_SHRINK_CENTER);
    ok->pressed.connect([p] { p->close(); });
    p->content->add(ok);
    return p;
}

// ================================================================== EnergyPopup
FantasyPopup* EnergyPopup::open(Control* parent, const std::string& stage_id)
{
    int need = GM.stage_energy(stage_id);
    auto p = FantasyPopup::open(parent, "NOT ENOUGH ENERGY", 900);
    auto row = UIKit::hbox(14);
    row->alignment = ALIGNMENT_CENTER;
    row->add(UIKit::icon("assets/icons/energy.png", 64));
    auto amount = UIKit::label("", UIKit::T_NAME, UIKit::GOLD, ALIGN_LEFT, 6);
    row->add(amount);
    p->content->add(row);
    auto timer = UIKit::label("", UIKit::T_BODY, UIKit::TEXT, ALIGN_CENTER, 5);
    p->content->add(timer);
    auto tip = UIKit::wrap_label("Energy recovers by itself, even while the game is closed, and refills completely whenever your Rank goes up.",
                                 UIKit::T_SMALL);
    tip->set_min_w(820);
    tip->set_color(UIKit::MUTED);
    p->content->add(tip);
    auto ok = FantasyButton::make("OK", "ember", Vec2(320, 110));
    ok->set_h_flags(SIZE_SHRINK_CENTER);
    p->content->add(ok);
    ok->pressed.connect([p] { p->close(); });
    auto refresh = [amount, timer, need] {
        amount->set_text(UIKit::fmt("%d / %d   (need %d)", GM.energy(), GM.max_energy(), need));
        int secs = GM.energy_seconds_to_next();
        int missing = std::max(need - GM.energy(), 0);
        if (missing <= 0)
            timer->set_text("You have enough Energy now!");
        else
        {
            int total = secs + (missing - 1) * I(DB.balance("energy", "regen_seconds"), 180);
            timer->set_text("Next +1 in " + UIKit::format_time(secs) + "  -  ready in " + UIKit::format_time(total));
        }
    };
    refresh();
    p->schedule([refresh](float) { refresh(); }, 1.0f, "energy_refresh");
    return p;
}

// ================================================================== StageNode
StageNode* StageNode::make(const std::string& sid, const std::string& st, int px)
{
    auto n = gd::make<StageNode>();
    n->stage_id = sid;
    n->state = st;
    auto t = TextureRect::create(UIKit::UI_DIR + "v2_node_" + st + ".png");
    t->ignore_size = true;
    t->stretch = STRETCH_KEEP_ASPECT_CENTERED;
    t->set_anchors_preset(PRESET_FULL_RECT);
    t->set_mouse_filter(MOUSE_IGNORE);
    n->add(t);
    Vec2 s((float)px, (float)px);
    n->set_custom_min(s);
    n->set_size(s);
    n->set_pivot(s / 2);
    n->set_name("Node_" + sid);
    // TextureButton button_down / button_up
    n->gui_input.connect([n](InputEvent& e) {
        if (e.pressed())
        {
            n->setScale(0.9f);
            e.accept();
        }
        else if (e.released() || e.type == Ev::CANCEL)
            n->setScale(1.0f);
    });
    if (st == "locked") n->set_modulate(Col(0.8f, 0.8f, 0.85f));
    return n;
}

void StageNode::set_selected(bool on)
{
    // the pulse tween is owned by a helper child: removing it kills the tween
    if (auto old = getChildByName("__pulse")) old->removeFromParent();
    setScale(1.0f);
    if (!on) return;
    auto holder = ax::Node::create();
    holder->setName("__pulse");
    addChild(holder);
    auto tw = gd::tween(holder);
    tw->loops();
    tw->scale(this, Vec2(1.22f, 1.22f), 0.45f).trans(TRANS_SINE);
    tw->scale(this, Vec2(1, 1), 0.45f).trans(TRANS_SINE);
}

// ================================================================== StageInfo
namespace StageInfo
{
Json species(const Json& stage)
{
    Json out = Json::array();
    std::string leader_el = "fire";
    Json party = GM.party_units();
    if (!party.empty()) leader_el = S(DB.character(S(party[0], "char_id")), "element", "fire");
    for (auto& wave : A(stage, "waves"))
        for (auto& spawn : wave)
        {
            std::string eid = S(spawn, "enemy");
            if (spawn.contains("enemy_by_leader_element")) eid = S(O(spawn, "enemy_by_leader_element"), leader_el, eid);
            if (!eid.empty() && !has(out, eid)) out.push_back(eid);
            const Json& sm = O(O(DB.enemy(eid), "ai"), "summon");
            if (!sm.empty() && !has(out, S(sm, "enemy"))) out.push_back(S(sm, "enemy"));
        }
    return out;
}

Json elements(const Json& stage)
{
    Json out = Json::array();
    for (auto& eid : species(stage))
    {
        std::string el = S(DB.enemy(S(eid)), "element");
        if (!el.empty() && !has(out, el)) out.push_back(el);
    }
    return out;
}

Json possible_drops(const Json& stage)
{
    std::vector<std::string> out;
    auto push = [&out](const std::string& id) {
        if (std::find(out.begin(), out.end(), id) == out.end()) out.push_back(id);
    };
    for (auto& d : A(stage, "drops")) push(S(d, "item"));
    for (auto& eid : species(stage))
        for (auto& item_id : Progression::table_items(A(DB.enemy(S(eid)), "drop_table"))) push(item_id);
    std::stable_sort(out.begin(), out.end(), [](const std::string& a, const std::string& b) {
        return I(DB.item(a), "sort", 99) < I(DB.item(b), "sort", 99);
    });
    return Json(out);
}

Control* chip(const std::string& label_text, const std::string& value, const Col& color, const std::string& icon_path)
{
    auto h = UIKit::hbox(6);
    if (!icon_path.empty()) h->add(UIKit::icon(icon_path, 40));
    h->add(UIKit::label(label_text, UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 5));
    h->add(UIKit::label(value, UIKit::T_BODY, color, ALIGN_LEFT, 6));
    return h;
}

Control* info_row(const Json& stage)
{
    auto info = UIKit::hbox(22);
    info->set_name("StageInfoRow");
    int cost = I(stage, "energy", 0);
    info->add(chip("", std::to_string(cost), GM.energy() >= cost ? Col("#ffe07a") : UIKit::DANGER, "assets/icons/energy.png"));
    int rec = I(stage, "recommended_power", 0);
    int sp = GM.squad_power();
    info->add(chip("POWER", UIKit::format_number(sp) + " / " + UIKit::format_number(rec),
                   sp >= rec ? UIKit::GOOD : (sp >= rec * 0.8 ? UIKit::EMBER : UIKit::DANGER)));
    info->add(chip("WAVES", std::to_string(A(stage, "waves").size())));
    auto foes = UIKit::hbox(4);
    for (auto& el : elements(stage)) foes->add(UIKit::orb(S(el), 40));
    info->add(foes);
    return info;
}

Control* stars_row(const Json& stage)
{
    auto col = UIKit::vbox(2);
    col->set_name("StarObjectives");
    Json got = GM.stage_stars(S(stage, "id"));
    const Json& objs = A(stage, "stars");
    for (size_t i = 0; i < objs.size(); ++i)
    {
        auto h = UIKit::hbox(8);
        bool on = i < got.size() && B(got[i]);
        h->add(UIKit::icon(on ? "assets/icons/star_obj.png" : "assets/icons/star_obj_empty.png", 36));
        h->add(UIKit::label(S(objs[i], "text"), UIKit::T_SMALL, on ? UIKit::TEXT : UIKit::MUTED, ALIGN_LEFT, 5));
        col->add(h);
    }
    return col;
}

Control* rewards_row(const Json& stage, int px)
{
    auto col = UIKit::vbox(6);
    bool cleared = GM.is_stage_cleared(S(stage, "id"));
    auto h = UIKit::hbox(10);
    h->set_name("PossibleDrops");
    h->add(UIKit::label("POSSIBLE\nDROPS", UIKit::T_SMALL, UIKit::GOLD, ALIGN_LEFT, 5));
    const Json& rewards = O(stage, "rewards");
    int xp = I(rewards, "xp", 0), gold = I(rewards, "gold", 0);
    auto xp_i = RewardItem::make("assets/icons/xp.png", std::to_string(xp), "", px);
    UIManager::attach_tooltip(xp_i, UIKit::fmt("EXP  %d", xp), "Shared by the heroes in your squad.", "assets/icons/xp.png");
    auto gold_i = RewardItem::make("assets/icons/gold.png", std::to_string(gold), "", px);
    UIManager::attach_tooltip(gold_i, UIKit::fmt("Gold  %d", gold), "Base Gold for a clear.", "assets/icons/gold.png");
    std::vector<RewardItem*> items{xp_i, gold_i};
    Json drops = possible_drops(stage);
    for (size_t i = 0; i < drops.size() && i < 7; ++i)
    {
        std::string item_id = S(drops[i]);
        const Json& def = DB.item(item_id);
        auto ri = RewardItem::make(S(def, "icon"), "", "", px);
        ri->set_name("Drop_" + item_id);
        UIManager::attach_tooltip(ri, DB.item_name(item_id), S(def, "description"), S(def, "icon"));
        items.push_back(ri);
    }
    for (auto it : items)
    {
        it->hidden_start = false;
        h->add(it);
    }
    col->add(h);
    const Json& fc = O(stage, "first_clear");
    if (!cleared && (I(fc, "gems", 0) > 0 || !O(fc, "items").empty()))
    {
        auto f = UIKit::hbox(10);
        f->set_name("FirstClearRewards");
        f->add(UIKit::label("FIRST CLEAR", UIKit::T_SMALL, UIKit::EMBER, ALIGN_LEFT, 5));
        if (I(fc, "gems", 0) > 0)
        {
            f->add(UIKit::icon("assets/icons/gem.png", 40));
            f->add(UIKit::label(UIKit::fmt("+%d", I(fc, "gems", 0)), UIKit::T_BODY, Col("#9ae8ff"), ALIGN_LEFT, 6));
        }
        if (I(rewards, "first_clear_gold", 0) > 0)
        {
            f->add(UIKit::icon("assets/icons/gold.png", 40));
            f->add(UIKit::label(UIKit::fmt("+%d", I(rewards, "first_clear_gold", 0)), UIKit::T_BODY, UIKit::GOLD, ALIGN_LEFT, 6));
        }
        for (auto& [item_id, q] : O(fc, "items").items())
        {
            f->add(UIKit::icon(S(DB.item(item_id), "icon"), 40));
            f->add(UIKit::label("x" + std::to_string(I(q)), UIKit::T_SMALL, UIKit::TEXT, ALIGN_LEFT, 5));
        }
        col->add(f);
    }
    return col;
}

// ------------------------------------------------------------------ element matchup
Control* matchup_row(const Json& party, const Json& stage, Control* host)
{
    Json foes = elements(stage);
    Json mine = Json::array();
    for (auto& u : party)
    {
        std::string el = S(DB.character(S(u, "char_id")), "element");
        if (!has(mine, el)) mine.push_back(el);
    }
    auto box = PanelFrame::make("inset", 12);
    box->set_name("ElementMatchup");
    auto v = UIKit::vbox(UIKit::SP_S);
    box->add(v);
    auto h = UIKit::hbox(UIKit::SP_M);
    h->alignment = ALIGNMENT_CENTER;
    h->add(UIKit::label("SQUAD", UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 5));
    for (auto& el : mine) h->add(UIKit::orb(S(el), 44));
    h->add(UIKit::label("VS", UIKit::T_BODY, UIKit::MUTED, ALIGN_CENTER, 6));
    h->add(UIKit::label("FOES", UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 5));
    for (auto& el : foes) h->add(UIKit::orb(S(el), 44));
    auto chart = UIKit::btn("", "quiet", Vec2(88, 88), "assets/icons/element_chart.png");
    chart->set_name("MatchupChart");
    chart->tooltip_text = "Element chart";
    chart->pressed.connect([host] { ElementChart::popup(host); });
    h->add(chart);
    v->add(h);
    auto advice = matchup_advice(mine, foes);
    bool warn = !advice[1].empty();
    auto line = UIKit::hbox(UIKit::SP_S);
    line->alignment = ALIGNMENT_CENTER;
    line->add(UIKit::icon(warn ? "assets/icons/warning.png" : "assets/icons/check.png", 36));
    auto l = UIKit::wrap_label(advice[0], UIKit::T_SMALL, warn ? UIKit::EMBER : UIKit::GOOD);
    l->set_name("MatchupAdvice");
    l->set_min_w(780);
    line->add(l);
    v->add(line);
    return box;
}

// Returns {text, is_warning}: is_warning is "1" or "" (test with !empty()).
std::vector<std::string> matchup_advice(const Json& mine, const Json& foes)
{
    std::vector<std::string> uncovered, threatened;
    for (auto& f : foes)
    {
        bool covered = false;
        for (auto& m : mine)
            if (DB.element_multiplier(S(m), S(f)) > 1.0) covered = true;
        if (!covered) uncovered.push_back(S(f));
    }
    for (auto& m : mine)
        for (auto& f : foes)
            if (DB.element_multiplier(S(f), S(m)) > 1.0 &&
                std::find(threatened.begin(), threatened.end(), S(m)) == threatened.end())
                threatened.push_back(S(m));
    if (!uncovered.empty())
    {
        const std::string& f = uncovered[0];
        std::string counter;
        for (auto& [el, _] : DB.elements.items())
            if (DB.element_multiplier(el, f) > 1.0) counter = DB.element_name(el);
        return {"No hero in your squad beats " + DB.element_name(f) + " foes. " + counter + " heroes deal extra damage to them.", "1"};
    }
    if (!threatened.empty() && threatened.size() == mine.size())
        return {"Every hero in your squad is weak to a foe here. Consider mixing elements.", "1"};
    return {"Good matchup: your squad has an advantage against these foes.", ""};
}

// ------------------------------------------------------------------ prepare
FantasyPopup* open_prepare(Control* parent, const std::string& stage_id, const std::string& back_scene)
{
    const Json& stage = DB.stage(stage_id);
    auto p = FantasyPopup::open(parent, "PREPARE", 1000);
    p->set_name("PreparePopup");
    std::string sname = S(stage, "name");
    std::string lbl = GM.stage_label(stage_id);
    p->content->add(UIKit::label(sname.rfind("Floor", 0) == 0 ? lbl : lbl + "  -  " + sname, UIKit::T_BODY, Col("#fff0c0"), ALIGN_CENTER, 6));
    auto slots = UIKit::hbox(8);
    slots->alignment = ALIGNMENT_CENTER;
    slots->set_name("PrepareSquad");
    Json party = GM.party_units();
    for (int i = 0; i < GM.max_party_size(); ++i)
    {
        auto cell = PanelFrame::make("slot", 6);
        cell->set_custom_min(Vec2(176, 200));
        auto v = UIKit::vbox(2);
        v->set_mouse_filter(MOUSE_IGNORE);
        cell->add(v);
        if (i < (int)party.size())
        {
            const Json& def = DB.character(S(party[i], "char_id"));
            auto art = UIKit::portrait_art(def, Vec2(160, 140));
            v->add(art);
            v->add(UIKit::label(UIKit::fmt("Lv.%d", I(party[i], "level", 1)), UIKit::T_SMALL, UIKit::GOLD, ALIGN_CENTER, 5));
            if (i == 0)
            {
                auto em = UIKit::icon("assets/icons/leader.png", 40);
                em->set_position(Vec2(2, 2));
                art->add(em);
            }
        }
        else
        {
            auto l = UIKit::label("EMPTY", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER);
            l->v_align = VALIGN_CENTER;
            l->set_v_flags(SIZE_EXPAND_FILL);
            v->add(l);
        }
        slots->add(cell);
    }
    p->content->add(slots);
    Json ls = GM.leader_skill();
    if (!ls.empty())
    {
        auto lr = UIKit::hbox(10);
        lr->add(UIKit::icon("assets/icons/leader.png", 40));
        auto lt = UIKit::wrap_label("LEADER: " + S(ls, "name") + " - " + S(ls, "description"), UIKit::T_SMALL, UIKit::GOLD);
        lt->set_min_w(860);
        lr->add(lt);
        p->content->add(lr);
    }
    int rec = I(stage, "recommended_power", 0);
    int sp = GM.squad_power();
    auto pw = UIKit::hbox(14);
    pw->alignment = ALIGNMENT_CENTER;
    pw->add(UIKit::label("SQUAD POWER " + UIKit::format_number(sp), UIKit::T_BODY, sp >= rec ? UIKit::GOOD : UIKit::EMBER, ALIGN_CENTER, 6));
    pw->add(UIKit::label("RECOMMENDED " + UIKit::format_number(rec), UIKit::T_BODY, UIKit::MUTED, ALIGN_CENTER, 6));
    p->content->add(pw);
    if (sp < rec)
    {
        auto warn = UIKit::wrap_label("Your squad is below the recommended power. You can still depart - training, evolving or adding heroes will help.",
                                      UIKit::T_SMALL, UIKit::EMBER);
        warn->set_name("PowerWarning");
        warn->set_align(ALIGN_CENTER);
        warn->set_min_w(900);
        p->content->add(warn);
    }
    p->content->add(matchup_row(party, stage, p));
    int cost = I(stage, "energy", 0);
    p->content->add(UIKit::label(UIKit::fmt("Energy: %d / %d   (cost %d)", GM.energy(), GM.max_energy(), cost), UIKit::T_BODY,
                                 GM.energy() >= cost ? Col("#ffe07a") : UIKit::DANGER, ALIGN_CENTER, 6));
    auto row = UIKit::hbox(16);
    row->alignment = ALIGNMENT_CENTER;
    auto edit = FantasyButton::make("EDIT SQUAD", "steel", Vec2(320, 116));
    edit->set_name("EditSquad");
    if (GM.feature_unlocked("squad"))
        edit->pressed.connect([p, stage_id, back_scene] {
            p->close();
            SceneRouter::remember({{"highlight", stage_id}, {"prepare", true}});
            SceneRouter::go("squad", {{"return_to", back_scene}, {"stage_id", stage_id}});
        });
    else
    {
        edit->set_modulate(Col(0.55f, 0.53f, 0.58f));
        edit->pressed.connect([parent] {
            UIKit::toast(parent, "Squad unlocks after clearing " + GM.feature_unlock_label("squad") + ".", UIKit::MUTED);
        });
    }
    row->add(edit);
    auto depart = FantasyButton::make("DEPART", "ember", Vec2(360, 130));
    depart->set_name("DepartButton");
    depart->set_font_size(UIKit::T_NAME);
    depart->add_shine();
    depart->pressed.connect([p, parent, stage_id] {
        Json r = GM.try_start_stage(stage_id);
        if (B(r, "ok", false))
        {
            p->close();
            AudioManager::play_sfx("energy", 0.02f, -4.0f);
            SceneRouter::go("battle", {{"stage_id", stage_id}});
        }
        else if (S(r, "reason") == "energy")
            EnergyPopup::open(parent, stage_id);
        else
            UIKit::toast(parent, "This stage is locked.", UIKit::DANGER);
    });
    row->add(depart);
    p->content->add(row);
    auto cancel = FantasyButton::make("CANCEL", "stone", Vec2(280, 96));
    cancel->set_name("CancelPrepare");
    cancel->set_h_flags(SIZE_SHRINK_CENTER);
    cancel->pressed.connect([p] { p->close(); });
    p->content->add(cancel);
    return p;
}
}  // namespace StageInfo

// ================================================================== RankUpOverlay
RankUpOverlay* RankUpOverlay::play(Control* parent, const Json& ups)
{
    if (!ups.is_array() || ups.empty()) return nullptr;
    auto o = gd::make<RankUpOverlay>();
    o->set_name("RankUpOverlay");
    parent->add(o);
    o->set_anchors_preset(PRESET_FULL_RECT);
    o->set_mouse_filter(MOUSE_STOP);
    o->set_z(60);
    auto close = [o] {
        if (B(o->meta, "closing", false)) return;
        o->meta["closing"] = true;
        o->closed.emit();
        o->queue_free();
    };
    o->gui_input.connect([close](InputEvent& e) {
        if (e.pressed()) close();
    });
    auto dim = ColorRect::create(Col(0.02f, 0.01f, 0.05f, 0.82f));
    dim->set_anchors_preset(PRESET_FULL_RECT);
    dim->set_mouse_filter(MOUSE_PASS);
    o->add(dim);
    auto center = CenterContainer::create();
    center->set_anchors_preset(PRESET_FULL_RECT);
    center->set_mouse_filter(MOUSE_PASS);
    o->add(center);
    auto col = UIKit::vbox(18);
    col->alignment = ALIGNMENT_CENTER;
    col->set_min_w(900);
    col->set_mouse_filter(MOUSE_PASS);
    center->add(col);
    auto title = UIKit::heading("RANK UP!", 130, UIKit::GOLD);
    title->set_outline(20, Col("#3a1404"));
    col->add(title);
    const Json& last = ups.back();
    auto badge = PanelFrame::make("slot", 20);
    badge->set_custom_min(Vec2(260, 220));
    badge->set_h_flags(SIZE_SHRINK_CENTER);
    auto bv = UIKit::vbox(0);
    bv->alignment = ALIGNMENT_CENTER;
    badge->add(bv);
    auto ic = UIKit::icon("assets/icons/rank.png", 80);
    ic->set_h_flags(SIZE_SHRINK_CENTER);
    bv->add(ic);
    auto num = UIKit::label(UIKit::fmt("RANK %d", I(last, "rank", 1)), UIKit::T_HEAD, Col::WHITE, ALIGN_CENTER, 10);
    num->set_name("RankNumber");
    bv->add(num);
    col->add(badge);
    int energy_up = 0, gems = 0;
    for (auto& u : ups)
    {
        energy_up += I(u, "energy_max_up", 0);
        gems += I(u, "gems", 0);
    }
    std::vector<std::pair<std::string, std::string>> lines{
        {"assets/icons/energy.png", UIKit::fmt("Energy fully restored! (%d / %d)", GM.energy(), GM.max_energy())}};
    if (energy_up > 0) lines.push_back({"assets/icons/energy.png", UIKit::fmt("Max Energy +%d", energy_up)});
    if (gems > 0) lines.push_back({"assets/icons/gem.png", UIKit::fmt("Rank reward: +%d Gems", gems)});
    std::vector<Control*> line_nodes;
    for (auto& [icon, text] : lines)
    {
        auto h = UIKit::hbox(12);
        h->alignment = ALIGNMENT_CENTER;
        h->add(UIKit::icon(icon, 48));
        h->add(UIKit::label(text, UIKit::T_BODY, Col("#fff0c0"), ALIGN_LEFT, 6));
        h->set_alpha(0);
        col->add(h);
        line_nodes.push_back(h);
    }
    auto ok = FantasyButton::make("OK", "ember", Vec2(320, 116));
    ok->set_name("RankUpOK");
    ok->set_h_flags(SIZE_SHRINK_CENTER);
    ok->set_alpha(0);
    col->add(ok);
    ok->pressed.connect(close);
    UIKit::sparkle(o, Rect2{Vec2(80, 500), Vec2(920, 600)}, Col("#ffe08a"), 20);
    AudioManager::play_sfx("rank_up");
    // animate
    title->set_pivot(Vec2(450, 70));
    title->setScale(2.2f);
    title->set_alpha(0);
    badge->set_pivot(badge->custom_min() / 2);
    badge->setScale(0.3f);
    auto tw = gd::tween(o);
    tw->alpha(title, 1.0f, 0.12f);
    tw->parallel().scale(title, Vec2(1, 1), 0.25f).trans(TRANS_BACK);
    tw->scale(badge, Vec2(1, 1), 0.25f).trans(TRANS_BACK);
    for (auto n : line_nodes) tw->alpha(n, 1.0f, 0.18f);
    tw->alpha(ok, 1.0f, 0.15f);
    return o;
}
