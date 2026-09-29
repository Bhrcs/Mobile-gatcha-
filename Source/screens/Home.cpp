// Home hub (scripts/ui/home.gd): camp with the squad around the fire, the big QUEST plate,
// UNITS / SUMMON, then TOWER / MISSIONS / SQUAD. On arrival it shows, one at a time: save-update
// notes, the daily login reward and announcements for newly unlocked features.
#include "screens/Screens.h"
#include <cstdlib>

using namespace gd;

namespace
{
constexpr int CAMP_MIN_H = 560;
struct Feature { std::string title, icon, text, scene; };
const std::map<std::string, Feature> FEATURE_INFO{
    {"auto", {"AUTO BATTLE", "assets/icons/auto.png", "Tap AUTO in battle and your heroes fight on their own - they Burst when it matters and Guard against charged attacks. Tap 1x/2x to speed battles up.", ""}},
    {"units", {"UNITS & SQUAD", "assets/icons/nav_units.png", "Your squad can now hold up to 5 heroes. Open UNITS to inspect heroes and SQUAD to choose who fights and who leads - the leader's Leader Skill boosts the team.", "squad"}},
    {"training", {"TRAINING", "assets/icons/radiant_wisp.png", "Feed Wisps and Gold to a hero to level them up. Wisps of the hero's own element give +50% EXP.", "units"}},
    {"tower", {"ELEMENTAL TOWERS", "assets/icons/tower.png", "Three towers - Ember, Tide and Verdant - wait to be climbed. Each floor is harder than the last and each tower is the best source of its element's evolution materials.", "tower"}},
    {"evolution", {"EVOLUTION", "assets/icons/star.png", "Heroes at max level can evolve into a stronger form with Fragments, Cores and Gold. Tap EVOLVE on a hero; WHERE TO FIND shows where materials drop.", "units"}},
    {"summon", {"THE EMBERGATE", "assets/icons/nav_summon.png", "The Embergate is open! Spend Gems to summon new heroes. Heroes you already own become Soul Shards for Burst training.", "summon"}},
    {"missions", {"MISSIONS", "assets/icons/missions.png", "Daily and weekly missions now give Gems, Gold and Wisps. Claim 4 daily missions to open the daily chest.", "missions"}},
    {"world2", {"SALTGLASS REACH", "assets/icons/world.png", "A new region beyond the Wilds: a glittering coast of salt-glass, drowned ruins and something enormous sleeping in the spire.", "world_select"}},
};
// Short camp lines when a focused hero is tapped again (by element).
const std::map<std::string, std::vector<std::string>> LINES{
    {"fire", {"The fire's warm. Let's move!", "Point me at the next fight.", "Ready when you are."}},
    {"water", {"The tide is turning our way.", "Calm first, then strike.", "Ready when you are."}},
    {"nature", {"The forest is listening.", "Roots hold, branches strike.", "Ready when you are."}},
    {"light", {"Our path is bright.", "Stand behind me.", "Ready when you are."}},
    {"dark", {"The night hides us well.", "Quietly now.", "Ready when you are."}},
};
constexpr float BG_SCALE = 5;
const Vec2 FIRE(240, 205);   // campfire position in bg_camp pixels
// member feet relative to the campfire: leader in front, others around the fire
const Vec2 SLOTS[] = {Vec2(0, 150), Vec2(-280, 60), Vec2(280, 60), Vec2(-420, 170), Vec2(420, 170)};

Feature info_of(const std::string& f)
{
    auto it = FEATURE_INFO.find(f);
    return it != FEATURE_INFO.end() ? it->second : Feature{upper(f), "assets/icons/star.png", "", ""};
}
}  // namespace

class Home : public ScreenBase
{
public:
    Control* camp = nullptr;
    PanelFrame* focus_plate = nullptr;
    std::string focus_uid;
    std::map<std::string, UnitSpriteDisplay*> sprites;
    TextureRect *camp_bg = nullptr, *glow = nullptr;
    Particles* embers = nullptr;
    Label* hint = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        auto area = build_frame("bg_camp", "", "home", nullptr, 0.55f);
        auto col = UIKit::vbox(12);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);
        col->add(camp_view());
        col->add(quest_plate());
        // feature hierarchy: QUEST (above) > UNITS / SUMMON > TOWER / MISSIONS / SQUAD
        auto grid = GridContainer::create(2);
        grid->set_name("FeatureGrid");
        grid->h_separation = grid->v_separation = UIKit::SP_M;
        col->add(grid);
        grid->add(tile("UNITS", "assets/icons/nav_units.png", "units", "UnitsButton", "units", GM.units_badge()));
        grid->add(tile("SUMMON", "assets/icons/nav_summon.png", "summon", "SummonButton", "summon", GM.summon_badge()));
        auto small_grid = GridContainer::create(3);
        small_grid->set_name("SmallGrid");
        small_grid->h_separation = small_grid->v_separation = UIKit::SP_M;
        col->add(small_grid);
        small_grid->add(tile("TOWER", "assets/icons/nav_tower.png", "tower", "TowerButton", "tower", false, "!", 116));
        int mc = GM.missions_claimable();
        small_grid->add(tile("MISSIONS", "assets/icons/nav_missions.png", "missions", "MissionsButton", "missions",
                        mc > 0 || GM.login_available(), mc > 0 ? std::to_string(mc) : "!", 116));
        small_grid->add(tile("SQUAD", "assets/icons/leader.png", "squad", "SquadTile", "squad", false, "!", 116));
        AudioManager::play_music("world");
        gd::after(this, 0.35f, [this] { arrival_popups(); });
    }

    // ------------------------------------------------------------------ camp
    Control* camp_view()
    {
        auto frame = PanelFrame::make("panel", 10);
        frame->set_min_h(CAMP_MIN_H);
        frame->set_v_flags(SIZE_EXPAND_FILL);
        camp = Control::create();
        camp->set_clip(true);
        camp->set_mouse_filter(MOUSE_IGNORE);
        frame->add(camp);
        camp->resized.connect([this] { layout_camp(); });
        camp_bg = TextureRect::create("assets/environments/bg_camp.png");
        camp_bg->set_name("CampBG");
        camp_bg->ignore_size = true;
        camp_bg->stretch = STRETCH_SCALE;
        camp_bg->set_size(camp_bg->texture_size() * BG_SCALE);
        camp_bg->set_mouse_filter(MOUSE_IGNORE);
        camp->add(camp_bg);
        glow = fire_glow();
        camp->add(glow);
        ParticleCfg c;
        c.amount = 22;
        c.lifetime = 1.8f;
        c.preprocess = 2.0f;
        c.emission_rect = Vec2(20, 6);
        c.direction = Vec2(0, -1);
        c.spread = 20;
        c.gravity = Vec2(6, -40);
        c.vel_min = 40;
        c.vel_max = 90;
        c.scale_min = 4;
        c.scale_max = 8;
        c.ramp = {Col("#fff0a0"), Col(0.8f, 0.2f, 0.1f, 0)};   // ponytail: mid stop #ff8a2a dropped (ramp is 2-stop)
        embers = Particles::create(c);
        embers->set_name("FireEmbers");
        camp->add(embers);

        Json party = GM.party_units();
        for (size_t i = 0; i < party.size(); ++i) add_member(party[i], (int)i);
        if (!party.empty()) focus_uid = S(party[0], "uid");

        focus_plate = PanelFrame::make("plank", 12);
        focus_plate->set_name("FocusPlate");
        camp->add(focus_plate);
        hint = UIKit::label("TAP YOUR HEROES", UIKit::T_SMALL, Col(1, 1, 1, 0.6f), ALIGN_RIGHT, 5);
        hint->set_name("CampHint");
        camp->add(hint);
        refresh_focus();
        return frame;
    }

    TextureRect* fire_glow()
    {
        auto g = TextureRect::create();
        g->set_name("FireGlow");
        g->set_texture(gradient_texture({{0.0f, Col(1.0f, 0.6f, 0.2f, 0.35f)}, {1.0f, Col(1.0f, 0.4f, 0.1f, 0.0f)}}, 64, 32, true,
                                        Vec2(0.5f, 0.5f), Vec2(1.0f, 0.5f)));
        g->ignore_size = true;
        g->set_size(Vec2(900, 360));
        g->set_mouse_filter(MOUSE_IGNORE);
        g->additive = true;
        auto tw = gd::tween(g);
        tw->loops();
        tw->alpha(g, 0.7f, 0.35f).trans(TRANS_SINE);
        tw->alpha(g, 1.0f, 0.25f).trans(TRANS_SINE);
        tw->alpha(g, 0.82f, 0.3f).trans(TRANS_SINE);
        tw->alpha(g, 1.0f, 0.4f).trans(TRANS_SINE);
        return g;
    }

    void add_member(const Json& u, int slot)
    {
        const Json& def = DB.character(S(u, "char_id"));
        std::string uid = S(u, "uid");
        auto holder = Control::create();
        holder->set_name("Member_" + uid);
        holder->meta["slot"] = slot;
        camp->add(holder);
        auto shadow = ColorRect::create(Col(0, 0, 0, 0.35f));
        shadow->set_size(Vec2(150, 18));
        shadow->set_position(Vec2(-75, -10));
        shadow->set_mouse_filter(MOUSE_IGNORE);
        holder->add(shadow);
        auto sp = UnitSpriteDisplay::make(O(def, "sprite"), slot == 0 ? 8.0f : 7.0f, slot == 2 || slot == 4);
        Vec2 ss = sp->custom_min();
        sp->set_size(ss);
        sp->set_position(Vec2(-ss.x / 2, -ss.y));
        holder->add(sp);
        sprites[uid] = sp;
        // stagger idle so they don't bob in sync
        if (sp->sprite) sp->sprite->set_frame(slot % 3);
        auto hit = Control::create();
        hit->set_name("Tap_" + uid);
        Vec2 hs(ss.x * 0.7f, ss.y * 0.85f);
        hit->set_size(hs);
        hit->set_position(Vec2(-hs.x / 2, -hs.y));
        holder->add(hit);
        UIKit::on_tap(hit, [this, uid] { on_member_tapped(uid); });
        if (slot == 0)
        {
            auto em = UIKit::icon("assets/icons/leader.png", 64);
            em->set_name("LeaderEmblem");
            float y = -ss.y * 0.8f - 56;
            em->set_position(Vec2(-32, y));
            holder->add(em);
            auto tw = gd::tween(em);
            tw->loops();
            tw->position_y(em, y - 10, 0.7f).trans(TRANS_SINE);
            tw->position_y(em, y, 0.7f).trans(TRANS_SINE);
        }
    }

    void layout_camp()
    {
        float w = camp->size().x;
        // campfire sits in the lower third of the view; the starry sky fills the rest
        float fire_y = camp->size().y - 290.0f;
        Vec2 off(w / 2.0f - FIRE.x * BG_SCALE, fire_y - FIRE.y * BG_SCALE);
        camp_bg->set_position(off);
        Vec2 fire = FIRE * BG_SCALE + off;
        glow->set_position(fire - glow->size() / 2.0f);
        embers->set_position(fire + Vec2(0, -20));
        for (auto ch : camp->children())
            if (ch->meta.contains("slot"))
            {
                ch->set_position(fire + SLOTS[I(ch->meta["slot"]) % 5]);
                ch->set_z(int(ch->position().y / 10.0f) - 60);   // draw back members first
            }
        focus_plate->set_position(Vec2(12, 12));
        focus_plate->set_size(Vec2(w - 24, 0));
        hint->set_position(Vec2(w - 420, camp->size().y - 44));
        hint->set_size(Vec2(400, 34));
    }

    void on_member_tapped(const std::string& uid)
    {
        auto it = sprites.find(uid);
        if (it == sprites.end()) return;
        UnitSpriteDisplay* sp = it->second;
        if (uid != focus_uid)
        {
            focus_uid = uid;
            AudioManager::play_sfx("unit_select", 0.03f, -3.0f);
            refresh_focus();
            return;
        }
        // flourish: victory pose (leader) or attack swing
        sp->play(uid == GM.leader_uid() ? "victory" : "attack");
        AudioManager::play_sfx("unit_select", 0.05f);
        if (sp->sprite && !sp->meta.contains("idle_hooked"))
        {
            sp->meta["idle_hooked"] = true;
            sp->sprite->animation_finished.connect([sp] { sp->play("idle"); });
        }
        Control* holder = sp->parent_control();
        if (holder->meta.contains("hopping")) return;
        holder->meta["hopping"] = true;
        float base_y = holder->position().y;
        auto tw = gd::tween(holder);
        tw->position_y(holder, base_y - 24, 0.12f).trans(TRANS_QUAD).ease(EASE_OUT);
        tw->position_y(holder, base_y, 0.14f).trans(TRANS_QUAD).ease(EASE_IN);
        tw->callback([holder] { holder->meta.erase("hopping"); });
        const Json& def = DB.character(S(GM.unit(uid), "char_id"));
        auto li = LINES.find(S(def, "element", "fire"));
        const auto& pool = li != LINES.end() ? li->second : LINES.at("fire");
        speech(holder, sp, pool[std::rand() % pool.size()]);
    }

    // Small speech bubble above a camp hero (one at a time, fades by itself).
    void speech(Control* holder, UnitSpriteDisplay* sp, const std::string& text)
    {
        if (auto old = camp->find("Speech")) old->removeFromParent();
        auto b = PanelFrame::make("inset", 10);
        b->set_name("Speech");
        b->set_mouse_filter(MOUSE_IGNORE);
        b->add(UIKit::label(text, UIKit::T_SMALL, UIKit::TEXT, ALIGN_CENTER, 5));
        camp->add(b);
        b->set_z(40);
        b->set_size(b->combined_min());
        float x = std::clamp(holder->position().x - b->size().x / 2.0f, 8.0f, camp->size().x - b->size().x - 8.0f);
        b->set_position(Vec2(x, holder->position().y - sp->size().y * 0.9f - b->size().y - 30));
        b->set_alpha(0);
        auto tw = gd::tween(b);
        tw->alpha(b, 1.0f, 0.12f);
        tw->interval(1.6f);
        tw->alpha(b, 0.0f, 0.25f);
        tw->callback([b] { b->queue_free(); });
    }

    void refresh_focus()
    {
        for (auto& [uid, sp] : sprites) sp->set_modulate(uid == focus_uid ? Col::WHITE : Col(0.72f, 0.72f, 0.8f));
        focus_plate->clear_children();
        Json u = GM.unit(focus_uid);
        if (u.is_null() || u.empty())
        {
            focus_plate->setVisible(false);
            return;
        }
        focus_plate->setVisible(true);
        const Json& def = DB.character(S(u, "char_id"));
        auto row = UIKit::hbox(12);
        focus_plate->add(row);
        row->add(UIKit::orb(S(def, "element"), 64));
        auto v = UIKit::vbox(0);
        v->set_h_flags(SIZE_EXPAND_FILL);
        auto nm = UIKit::label(S(def, "name"), UIKit::T_NAME, Col("#fff0c0"), ALIGN_LEFT, 8);
        nm->set_name("FocusName");
        v->add(nm);
        std::string lead = focus_uid == GM.leader_uid() ? " - LEADER" : "";
        v->add(UIKit::label(UIKit::fmt("Lv.%d  ", I(u, "level", 1)) + S(def, "class") + lead, UIKit::T_SMALL, UIKit::GOLD, ALIGN_LEFT, 5));
        row->add(v);
        auto b = FantasyButton::make("DETAILS", "steel", Vec2(230, 96));
        b->set_font_size(30);
        std::string uid = focus_uid;
        b->pressed.connect([uid] { SceneRouter::go("unit_detail", {{"uid", uid}}); });
        row->add(b);
    }

    // ------------------------------------------------------------------ plates
    const Json& next_stage()
    {
        std::string last = DB.stage_order[0];
        for (auto& sid : DB.stage_order)
            if (GM.is_stage_unlocked(sid)) last = sid;
        return DB.stage(last);
    }

    Control* quest_plate()
    {
        auto b = FantasyButton::make("", "ember", Vec2(0, 230));
        b->set_name("QuestButton");
        b->set_h_flags(SIZE_EXPAND_FILL);
        auto v = UIKit::vbox(0);
        v->set_anchors_preset(PRESET_FULL_RECT);
        v->alignment = ALIGNMENT_CENTER;
        v->set_mouse_filter(MOUSE_IGNORE);
        b->add(v);
        auto h = UIKit::hbox(20);
        h->alignment = ALIGNMENT_CENTER;
        h->set_mouse_filter(MOUSE_IGNORE);
        h->add(UIKit::icon("assets/icons/nav_quest.png", 112));
        auto title = UIKit::label("QUEST", 120, Col("#ffe08a"), ALIGN_CENTER, 20);
        title->set_outline_color(Col("#3a0e08"));
        h->add(title);
        v->add(h);
        const Json& st = next_stage();
        std::string sid = S(st, "id");
        bool cleared = GM.is_stage_cleared(sid);
        std::string sub = std::string(cleared ? "Replay" : "Next") + "  -  " + GM.stage_label(sid) + ": " + S(st, "name");
        auto sl = UIKit::label(sub, UIKit::T_BODY, Col("#fff0d0"), ALIGN_CENTER, 6);
        sl->set_name("QuestNext");
        v->add(sl);
        b->pressed.connect([sid] { SceneRouter::go("stage_select", {{"highlight", sid}}); });
        b->add_shine();
        // ember sparks drift over the main action
        UIKit::sparkle(b, Rect2{Vec2(40, 30), Vec2(960, 190)}, Col("#ffb04a"), 8);
        return b;
    }

    // Feature tile: opens its screen, or explains where it unlocks.
    Control* tile(const std::string& text, const std::string& icon_path, const std::string& scene, const std::string& node_name,
                  const std::string& feature, bool badge, const std::string& badge_text = "!", int height = 150)
    {
        auto b = FantasyButton::make(text, "steel", Vec2(0, (float)height), icon_path);
        b->set_name(node_name);
        b->set_h_flags(SIZE_EXPAND_FILL);
        b->set_font_size(height >= 140 ? UIKit::T_NAME : UIKit::T_BODY);
        b->icon_max_width = height >= 140 ? 72 : 56;
        bool locked = !feature.empty() && !GM.feature_unlocked(feature);
        if (locked)
        {
            b->set_modulate(Col(0.55f, 0.53f, 0.58f));
            auto lk = UIKit::icon("assets/icons/lock.png", 40);
            lk->set_position(Vec2(10, 10));
            b->add(lk);
            std::string req = GM.feature_unlock_label(feature);
            b->tooltip_text = "Unlocks after clearing " + req;
            std::string lower = text;
            for (auto& ch : lower) ch = (char)tolower(ch);
            std::string msg = capitalize(lower) + " unlocks after clearing " + req + ".";
            b->pressed.connect([msg] { UIManager::toast(msg, "info"); });
        }
        else
        {
            b->pressed.connect([scene] { SceneRouter::go(scene); });
            if (badge) UIKit::badge(b, badge_text);
        }
        return b;
    }

    // ------------------------------------------------------------------ arrival popups
    void arrival_popups()
    {
        if (!GM.pending_migration_notes.empty())
        {
            std::string text;
            for (auto& n : GM.pending_migration_notes) text += (text.empty() ? "" : "\n\n") + n;
            GM.pending_migration_notes.clear();
            auto p = UIKit::message(this, "YOUR SAVE WAS UPDATED", text + "\n\nAll your progress was kept.");
            p->closed.connect([this] { after_migration(); });
        }
        else
            after_migration();
    }

    void after_migration()
    {
        if (GM.login_available() && B(O(GM.profile, "tutorial"), "intro_seen", false) && GM.stages_cleared_count() > 0)
            login_popup([this] { announce_features(); });
        else
            announce_features();
    }

    void announce_features()
    {
        gd::after(this, 0.3f, [this] { guides(); });
        std::vector<std::string> fresh;
        for (auto f : {"auto", "units", "training", "tower", "evolution", "summon", "missions", "world2"})
            if (GM.feature_unlocked(f) && !GM.feature_announced(f) && !S(O(DB.progression, "unlocks"), f).empty())
                fresh.push_back(f);
        if (fresh.size() > 2)
            announce_many(fresh);
        else
            announce_from(fresh, 0);
    }

    void announce_from(std::vector<std::string> list, size_t i)
    {
        if (i >= list.size()) return;
        announce(list[i])->closed.connect([this, list, i] { announce_from(list, i + 1); });
    }

    // First-time guides, one at a time, most important first. Shown only when no
    // popup is open, so they never cover an announcement.
    void guides()
    {
        if (UIManager::top_popup())
        {
            gd::after(this, 0.25f, [this] { guides(); });
            return;
        }
        if (!GM.coach_done("home_quest"))
            UIManager::guide("home_quest", find("QuestButton"), "Tap QUEST to continue your journey.");
        else if (GM.feature_unlocked("units") && !GM.coach_done("home_units"))
            UIManager::guide("home_units", find("UnitsButton"), "New heroes and upgrades live in UNITS.");
        else if (GM.feature_unlocked("summon") && !GM.coach_done("home_summon"))
            UIManager::guide("home_summon", find("SummonButton"), "The Embergate is open - summon new heroes here.");
    }

    void login_popup(std::function<void()> then)
    {
        const Json& cycle = A(DB.login_rewards, "cycle");
        if (cycle.empty())
        {
            then();
            return;
        }
        int idx = GM.login_day_index();
        auto p = FantasyPopup::open(this, "DAILY LOGIN", 960, "boss");
        p->set_name("LoginPopup");
        p->content->add(UIKit::label(UIKit::fmt("DAY %d REWARD", idx + 1), UIKit::T_NAME, UIKit::GOLD, ALIGN_CENTER, 8));
        auto row = UIKit::hbox(8);
        row->alignment = ALIGNMENT_CENTER;
        for (int i = 0; i < (int)cycle.size(); ++i)
        {
            auto c = PanelFrame::make(i != idx ? "slot" : "boss", 4);
            c->set_custom_min(Vec2(118, 118));
            auto l = UIKit::label(UIKit::fmt("D%d", i + 1), UIKit::T_SMALL, i == idx ? UIKit::GOLD : (i < idx ? UIKit::MUTED : UIKit::TEXT),
                                  ALIGN_CENTER, 5);
            l->v_align = VALIGN_CENTER;
            c->add(l);
            if (i < idx) c->set_modulate(Col(0.6f, 0.6f, 0.65f));
            row->add(c);
        }
        p->content->add(row);
        auto claim = FantasyButton::make("CLAIM", "gold", Vec2(360, 120));
        claim->set_name("ClaimLoginPopup");
        claim->set_h_flags(SIZE_SHRINK_CENTER);
        claim->add_shine();
        p->content->add(claim);
        auto chosen = std::make_shared<bool>(false);
        claim->pressed.connect([chosen, p] {
            *chosen = true;
            p->close();
        });
        p->cancel_action = [claim] { claim->pressed.emit(); };
        p->default_action = p->cancel_action;
        p->closed.connect([this, chosen, then] {
            if (!*chosen)
            {
                then();
                return;
            }
            Json r = GM.claim_login();
            AudioManager::play_sfx("claim");
            auto rp = RewardPopup::open(this, "LOGIN REWARD", r,
                                        UIKit::fmt("Day %d of 7 - come back tomorrow for the next reward!", I(r, "day", 1)));
            rp->closed.connect(then);   // currencies are live in the status bar; badges refresh on the next visit
        });
    }

    FantasyPopup* announce(const std::string& f)
    {
        Feature info = info_of(f);
        GM.mark_feature_announced(f);
        auto p = FantasyPopup::open(this, "NEW: " + info.title, 940, "boss");
        p->set_name("FeaturePopup");
        auto ic = UIKit::icon(info.icon, 128);
        ic->set_h_flags(SIZE_SHRINK_CENTER);
        p->content->add(ic);
        auto w = UIKit::wrap_label(info.text, UIKit::T_BODY);
        w->set_min_w(860);
        w->set_align(ALIGN_CENTER);
        p->content->add(w);
        if (f == "units")
        {
            Json gift = gift_unit();
            if (!gift.empty())
            {
                const Json& d = DB.character(S(gift, "char_id"));
                std::string guid = S(gift, "uid");
                auto g = UIKit::hbox(14);
                g->alignment = ALIGNMENT_CENTER;
                auto fr = PanelFrame::make(UIKit::fmt("rarity_%d", I(d, "rarity", 3)), 6);
                fr->add(UIKit::portrait_art(d, Vec2(180, 180)));
                g->add(fr);
                auto gw = UIKit::wrap_label(S(d, "name") + " has joined you and is already in your squad!", UIKit::T_BODY, UIKit::GOLD);
                gw->set_min_w(560);
                g->add(gw);
                p->content->add(g);
                if (!GM.is_in_party(guid) && (int)GM.party_uids().size() < GM.max_party_size()) GM.toggle_party(guid);
                if (!GM.is_in_party(guid)) gw->set_text(S(d, "name") + " has joined you! Add them to your squad from SQUAD.");
            }
        }
        auto row = UIKit::hbox(14);
        row->alignment = ALIGNMENT_CENTER;
        if (!info.scene.empty())
        {
            auto go = FantasyButton::make("TAKE ME THERE", "ember", Vec2(420, 116));
            go->set_name("FeatureGo");
            std::string scene = info.scene;
            go->pressed.connect([p, scene] {
                p->close();
                SceneRouter::go(scene);
            });
            row->add(go);
        }
        auto later = FantasyButton::make("OK", "stone", Vec2(260, 116));
        later->set_name("FeatureOK");
        later->pressed.connect([p] { p->close(); });
        row->add(later);
        p->content->add(row);
        AudioManager::play_sfx("level_up", 0.0f, -4.0f);
        return p;
    }

    void announce_many(const std::vector<std::string>& features)
    {
        auto p = FantasyPopup::open(this, "NEW FEATURES", 940, "boss");
        p->set_name("FeaturePopup");
        for (auto& f : features)
        {
            GM.mark_feature_announced(f);
            Feature info = info_of(f);
            auto h = UIKit::hbox(12);
            h->add(UIKit::icon(info.icon, 56));
            h->add(UIKit::label(info.title, UIKit::T_BODY, UIKit::GOLD, ALIGN_LEFT, 6));
            p->content->add(h);
        }
        auto w = UIKit::wrap_label("Explore them from the Home screen and the MENU.", UIKit::T_SMALL, UIKit::MUTED);
        w->set_min_w(860);
        p->content->add(w);
        auto ok = FantasyButton::make("OK", "ember", Vec2(300, 116));
        ok->set_name("FeatureOK");
        ok->set_h_flags(SIZE_SHRINK_CENTER);
        ok->pressed.connect([p] { p->close(); });
        p->content->add(ok);
    }

    // GameManager.unit_of_family has no C++ equivalent: looked up here.
    Json gift_unit()
    {
        const Json& prog = DB.progression;
        const Json& gifts = O(O(prog, "unlock_gifts"), S(O(prog, "unlocks"), "units"));
        std::string hero = S(O(gifts, "hero_by_starter"), S(GM.profile, "starter_id"));
        if (hero.empty()) return Json::object();
        std::string family = S(DB.character(hero), "family");
        for (auto& u : GM.units())
            if (S(DB.character(S(u, "char_id")), "family") == family) return u;
        return Json::object();
    }
};
REGISTER_SCREEN("home", Home)
