// Unit detail (scripts/ui/unit_detail.gd): showcase, identity (lock / favourite), stats +
// power, passive, leader skill, Burst (level, EXP, training), normal attack, evolution
// path, TRAIN / EVOLVE / SQUAD, a full-screen VIEW of the hero, and lore.
#include "screens/Screens.h"

using namespace UIKit;
using gd::Rect2;

class UnitDetail : public ScreenBase
{
public:
    std::string uid;
    Json unit;
    gd::BoxContainer* body = nullptr;
    gd::ScrollContainer* scroll = nullptr;
    UnitSpriteDisplay* sprite = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        uid = S(params(), "uid");
        if (GM.unit(uid).is_null() && !GM.units().empty()) uid = S(GM.units()[0], "uid");
        back_fallback = S(params(), "back", GM.feature_unlocked("units") ? "units" : "home");
        auto area = build_frame("bg_camp", "UNIT DETAILS", "units", nullptr, 0.6f);
        scroll = gd::ScrollContainer::create();
        scroll->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(scroll);
        body = vbox(14);
        body->set_h_flags(gd::SIZE_EXPAND_FILL);
        scroll->add(body);
        GM.mark_unit_seen(uid);
        build();
    }

    // Stat bar reference: best value any unit reaches at its level cap (+15%).
    static int stat_reference(const std::string& key)
    {
        int best = 1;
        for (auto& [id, def] : DB.characters.items())
            best = std::max(best, I(Progression::unit_stats(def, I(def, "max_level", 20)), key, 0));
        return (int)(best * 1.15);
    }

    static FantasyButton* dim_locked(FantasyButton* b)
    {
        b->set_modulate(Col(0.55f, 0.53f, 0.58f));
        return b;
    }

    void build()
    {
        float keep_scroll = scroll->scroll_vertical();
        body->clear_children();
        unit = GM.unit(uid);
        const Json& def = DB.character(S(unit, "char_id"));
        std::string el = S(def, "element", "neutral");
        Json stats = GM.unit_stats(unit);
        int max_level = I(def, "max_level", 20), level = I(unit, "level", 1);

        // ---- showcase: portrait + animated sprite on element-lit card
        auto show = PanelFrame::make("card_" + el + "_lit", 12);
        show->set_custom_min(Vec2(0, 500));
        body->add(show);
        auto stage = gd::Control::create();
        stage->set_mouse_filter(gd::MOUSE_IGNORE);
        show->add(stage);
        auto art = portrait_art(def, Vec2(460, 460));
        art->set_position(Vec2(4, 4));
        art->set_size(Vec2(460, 460));
        stage->add(art);
        sprite = UnitSpriteDisplay::make(O(def, "sprite"), 8.0f, true);
        Vec2 m = sprite->custom_min();
        sprite->set_position(Vec2(740 - m.x / 2, 450 - m.y));
        sprite->set_size(m);
        sprite->set_name("ShowcaseSprite");
        stage->add(sprite);
        on_tap(sprite, [this] { poke_sprite(); });
        auto tap_hint = label("TAP TO ANIMATE", T_SMALL, MUTED, gd::ALIGN_CENTER, 5);
        tap_hint->set_position(Vec2(540, 452));
        tap_hint->set_size(Vec2(400, 30));
        stage->add(tap_hint);
        auto flags = hbox(8);
        flags->set_position(Vec2(720, 8));
        flags->add(flag_button("locked", "assets/icons/lock.png", "LOCK"));
        flags->add(flag_button("favorite", "assets/icons/fav.png", "FAV"));
        stage->add(flags);
        auto view = btn("VIEW", "quiet", Vec2(160, 72));
        view->set_name("ViewButton");
        view->set_font_size(T_SMALL);
        view->set_position(Vec2(12, 380));
        view->pressed.connect([this] { open_viewer(); });
        stage->add(view);
        if (I(def, "rarity", 3) >= 5) sparkle(stage, Rect2{Vec2(0, 0), Vec2(1000, 460)});
        sparkle(stage, Rect2{Vec2(560, 120), Vec2(400, 320)}, Col(DB.element_color(el)).lightened(0.4f), 5);

        // ---- identity plate
        auto plate = PanelFrame::make("plank", 14);
        body->add(plate);
        auto pv = vbox(8);
        plate->add(pv);
        auto r1 = hbox(14);
        r1->add(orb(el, 64));
        auto nm = label(S(def, "name"), T_HEAD, Col("#fff0c0"), gd::ALIGN_LEFT, 10);
        nm->set_name("UnitName");
        nm->set_h_flags(gd::SIZE_EXPAND_FILL);
        nm->set_clip_text(true);
        r1->add(nm);
        r1->add(stars(I(def, "rarity", 3), 48));
        pv->add(r1);
        auto r2 = hbox(16);
        static const std::map<std::string, Col> CLASS_COLORS = {{"ATTACKER", Col("#b8401e")}, {"HEALER", Col("#2a6ab0")},
                                                                {"GUARDIAN", Col("#3a7a2a")}, {"SUPPORT", Col("#9a6a1a")},
                                                                {"BREAKER", Col("#6a2a8a")}};
        std::string cls = S(def, "class", "ATTACKER");
        r2->add(tag(cls, CLASS_COLORS.count(cls) ? CLASS_COLORS.at(cls) : Col("#5a4a6a")));
        r2->add(label(DB.element_name(el), T_BODY, Col(DB.element_color(el)).lightened(0.3f), gd::ALIGN_LEFT, 6));
        r2->add(label("POWER " + format_number(GM.unit_power(unit)), T_BODY, SKY, gd::ALIGN_LEFT, 6));
        r2->add(spacer());
        auto lvl_l = label(level >= max_level ? UIKit::fmt("Lv.MAX (%d)", max_level) : UIKit::fmt("Lv.%d / %d", level, max_level),
                           T_NAME, GOLD, gd::ALIGN_RIGHT, 8);
        lvl_l->set_name("LevelLabel");
        r2->add(lvl_l);
        pv->add(r2);
        auto r3 = hbox(12);
        r3->add(label("EXP", T_SMALL, EMBER, gd::ALIGN_LEFT, 5));
        auto xb = ResourceBar::make("xp", 30);
        xb->set_h_flags(gd::SIZE_EXPAND_FILL);
        xb->set_v_flags(gd::SIZE_SHRINK_CENTER);
        int exp_now = I(unit, "exp", 0);
        int exp_need = level < max_level ? Progression::xp_to_next(level) : 1;
        xb->set_values(level < max_level ? (float)exp_now : 1.0f, (float)exp_need, false);
        r3->add(xb);
        r3->add(label(level < max_level ? UIKit::fmt("NEXT %d", exp_need - exp_now) : "MAX", T_SMALL, TEXT, gd::ALIGN_RIGHT, 5));
        pv->add(r3);

        // ---- actions
        auto buttons = hbox(12);
        buttons->alignment = gd::ALIGNMENT_CENTER;
        body->add(buttons);
        auto b_train = FantasyButton::make(level < max_level ? "TRAIN" : "MAX LEVEL", "gold", Vec2(330, 120),
                                           "assets/icons/radiant_wisp.png");
        b_train->set_name("TrainButton");
        if (!GM.feature_unlocked("training"))
        {
            dim_locked(b_train)->pressed.connect([this] {
                toast(this, "Training unlocks after clearing " + GM.feature_unlock_label("training") + ".", MUTED);
            });
        }
        else
        {
            b_train->set_disabled(level >= max_level);
            b_train->pressed.connect([this] { SceneRouter::go("train", {{"uid", uid}}); });
        }
        buttons->add(b_train);
        bool has_evo = at(def, "evolution").is_object();
        auto b_evo = FantasyButton::make(has_evo ? "EVOLVE" : "FINAL FORM", "ember", Vec2(330, 120));
        b_evo->set_name("EvolveButton");
        if (!has_evo)
            b_evo->set_disabled(true);
        else if (!GM.feature_unlocked("evolution"))
            dim_locked(b_evo)->pressed.connect([this] {
                toast(this, "Evolution unlocks after clearing " + GM.feature_unlock_label("evolution") + ".", MUTED);
            });
        else
        {
            b_evo->pressed.connect([this] { SceneRouter::go("evolve", {{"uid", uid}}); });
            if (GM.can_evolve(uid))
            {
                badge(b_evo);
                b_evo->add_shine();
            }
        }
        buttons->add(b_evo);
        auto b_squad = FantasyButton::make("SQUAD", "steel", Vec2(280, 120));
        b_squad->set_name("SquadButton");
        if (GM.feature_unlocked("squad"))
            b_squad->pressed.connect([this] { SceneRouter::go("squad", {{"from_uid", uid}}); });
        else
            dim_locked(b_squad)->pressed.connect([this] {
                toast(this, "Squad unlocks after clearing " + GM.feature_unlock_label("squad") + ".", MUTED);
            });
        buttons->add(b_squad);
        if (level >= max_level && has_evo)
            body->add(label("Max level reached - evolve to grow stronger!", T_SMALL, EMBER, gd::ALIGN_CENTER, 5));

        // ---- stats
        auto sp = PanelFrame::make("panel", 24);
        body->add(sp);
        auto sv = vbox(10);
        sp->add(sv);
        sv->add(label("STATS", T_BODY, GOLD, gd::ALIGN_LEFT, 6));
        // the hero's strongest stat (relative to the best in the game) is highlighted
        static const char* STAT_KEYS[] = {"hp", "atk", "def", "rec"};
        std::string best_key;
        float best_ratio = -1;
        for (auto key : STAT_KEYS)
        {
            float ratio = (float)I(stats, key, 0) / (float)stat_reference(key);
            if (ratio > best_ratio) best_ratio = ratio, best_key = key;
        }
        for (std::string key : STAT_KEYS)
        {
            auto row = StatRow::make(upper(key), I(stats, key, 0), stat_reference(key), key == best_key ? GOLD : SKY);
            row->set_name("Stat_" + key);
            if (key == best_key) row->add(tag("BEST", Col("#8a5a10")));
            sv->add(row);
        }

        // ---- passive + leader skill
        body->add(ability_panel("PASSIVE", O(def, "passive"), "assets/icons/star_obj.png", SKY));
        body->add(ability_panel("LEADER SKILL", O(def, "leader_skill"), "assets/icons/leader.png", GOLD));

        // ---- skills
        body->add(burst_panel(def));
        body->add(skill_panel("ATTACK", S(def, "normal_attack"), false));

        // ---- evolution path
        body->add(evolution_path(def));

        // ---- lore
        auto lp = PanelFrame::make("inset", 22);
        body->add(lp);
        auto lv = vbox(8);
        lp->add(lv);
        lv->add(label("LORE", T_BODY, GOLD, gd::ALIGN_LEFT, 6));
        auto lore = wrap_label(S(def, "lore"), T_BODY, Col("#e0d6c6"));
        lore->set_min_w(960);
        lv->add(lore);
        body->add(spacer(false, false));
        ax::RefPtr<gd::ScrollContainer> sc(scroll);
        gd::defer([sc, keep_scroll] {
            if (sc->is_inside_tree()) sc->set_scroll_vertical(keep_scroll);
        });
    }

    gd::Control* flag_button(const std::string& flag, const std::string& icon_path, const std::string& text)
    {
        bool on = B(unit, flag, false);
        auto b = FantasyButton::make(text, on ? "gold" : "stone", Vec2(130, 72), icon_path);
        b->set_name("Flag_" + flag);
        b->set_font_size(22);
        b->icon_max_width = 32;
        b->tooltip_text = flag == "locked" ? "Locked heroes are protected from future selling/fusing." : "Favourites sort first.";
        b->pressed.connect([this, flag] {
            GM.set_unit_flag(uid, flag, !B(GM.unit(uid), flag, false));
            build();
        });
        return b;
    }

    gd::Control* ability_panel(const std::string& kind, const Json& data, const std::string& icon_path, const Col& color)
    {
        auto p = PanelFrame::make("inset", 18);
        std::string n = kind;
        n.erase(std::remove(n.begin(), n.end(), ' '), n.end());
        p->set_name(n);
        auto v = vbox(6);
        p->add(v);
        auto head = hbox(12);
        head->add(icon(icon_path, 40));
        head->add(label(kind, T_SMALL, color, gd::ALIGN_LEFT, 5));
        auto nl = label(S(data, "name", "-"), T_BODY, TEXT, gd::ALIGN_LEFT, 6);
        nl->set_h_flags(gd::SIZE_EXPAND_FILL);
        head->add(nl);
        v->add(head);
        auto d = wrap_label(S(data, "description"), T_BODY, Col("#e8dece"));
        d->set_min_w(960);
        v->add(d);
        return p;
    }

    gd::Control* burst_panel(const Json& def)
    {
        gd::BoxContainer* v = nullptr;
        auto p = skill_panel("BURST", S(def, "burst"), true, &v);
        const Json& sk = DB.skill(S(def, "burst"));
        int bl = I(unit, "burst_level", 1);
        int bmax = I(DB.balance("burst_levels", "max"), 5);
        int bxp = I(unit, "burst_xp", 0);
        auto row = hbox(12);
        row->set_name("BurstLevel");
        row->add(label(UIKit::fmt("BURST Lv.%d%s", bl, bl >= bmax ? " (MAX)" : ""), T_BODY, EMBER, gd::ALIGN_LEFT, 6));
        auto bar = ResourceBar::make("burst", 24);
        bar->set_h_flags(gd::SIZE_EXPAND_FILL);
        bar->set_v_flags(gd::SIZE_SHRINK_CENTER);
        int lo = Progression::burst_xp_for_level(bl);
        int hi = Progression::burst_xp_for_level(std::min(bl + 1, bmax));
        bar->set_values(bl < bmax ? (float)(bxp - lo) : 1.0f, bl < bmax ? (float)std::max(hi - lo, 1) : 1.0f, false);
        row->add(bar);
        row->add(label(bl < bmax ? UIKit::fmt("%d/%d", bxp - lo, hi - lo) : "MAX", T_SMALL, TEXT, gd::ALIGN_RIGHT, 5));
        v->add(row);
        double cost = Progression::burst_cost(sk, bl);
        auto il = wrap_label(UIKit::fmt("Gauge cost %d.  %s", (int)cost, Progression::burst_level_text(sk).c_str()), T_SMALL, MUTED);
        il->set_min_w(960);
        v->add(il);
        v->add(label("Burst EXP: +1 each time this hero uses Burst in a won battle.", T_SMALL, MUTED, gd::ALIGN_LEFT, 4));
        if (bl < bmax)
        {
            auto br = hbox(12);
            int sig = GM.item_count("spark_sigil");
            auto b1 = FantasyButton::make(UIKit::fmt("SPARK SIGIL (%d)", sig), "steel", Vec2(420, 90), "assets/icons/spark_sigil.png");
            b1->set_name("BurstSigil");
            b1->set_font_size(26);
            b1->set_disabled(sig <= 0);
            b1->pressed.connect([this] { burst_train("sigil"); });
            br->add(b1);
            int cost_s = I(DB.balance("burst_levels", "shards_per_step"), 20);
            auto b2 = FantasyButton::make(UIKit::fmt("%d SOUL SHARDS", cost_s), "steel", Vec2(420, 90), "assets/icons/soul_shard.png");
            b2->set_name("BurstShards");
            b2->set_font_size(26);
            b2->set_disabled(GM.soul_shards() < cost_s);
            b2->pressed.connect([this] { burst_train("shards"); });
            br->add(b2);
            v->add(br);
            v->add(label(UIKit::fmt("You have %d Soul Shards (earned from duplicate summons).", GM.soul_shards()), T_SMALL, MUTED,
                         gd::ALIGN_LEFT, 4));
        }
        return p;
    }

    void burst_train(const std::string& method)
    {
        Json r = GM.train_burst(uid, method);
        if (!B(r, "ok", false))
        {
            UIManager::toast(S(r, "reason", "Cannot train."), "error");
            return;
        }
        bool up = I(r, "after", 0) > I(r, "before", 0);
        AudioManager::play_sfx(up ? "level_up" : "reward");
        toast(this, up ? UIKit::fmt("BURST LEVEL UP! Lv.%d", I(r, "after", 0)) : UIKit::fmt("+%d Burst EXP", I(r, "xp", 0)), GOLD);
        build();
    }

    PanelFrame* skill_panel(const std::string& kind, const std::string& skill_id, bool is_burst, gd::BoxContainer** out_v = nullptr)
    {
        const Json& sk = DB.skill(skill_id);
        auto p = PanelFrame::make(is_burst ? "panel" : "inset", is_burst ? 24 : 20);
        p->set_name("Skill_" + kind);
        auto v = vbox(8);
        p->add(v);
        if (out_v) *out_v = v;
        auto head = hbox(14);
        head->add(icon(is_burst ? "assets/icons/burst.png" : "assets/icons/sword.png", 48));
        head->add(label(kind, T_BODY, is_burst ? SKY : EMBER, gd::ALIGN_LEFT, 6));
        auto n = label(S(sk, "name"), T_NAME, is_burst ? GOLD : TEXT, gd::ALIGN_LEFT, 8);
        n->set_h_flags(gd::SIZE_EXPAND_FILL);
        head->add(n);
        v->add(head);
        v->add(SkillText::chips(sk, is_burst ? SKY : EMBER));
        auto d = wrap_label(S(sk, "description"), T_SMALL, Col("#d8cebe"));
        d->set_min_w(960);
        v->add(d);
        std::vector<Json> granted;
        for (auto& eff : A(sk, "effects"))
            if (S(eff, "type") == "status") granted.push_back(eff);
        if (!granted.empty())
        {
            auto row = gd::FlowContainer::create();
            row->h_separation = 12;
            row->add(label("EFFECTS", T_SMALL, MUTED, gd::ALIGN_LEFT, 5));
            for (auto& eff : granted)
            {
                std::string sid = S(eff, "status");
                row->add(StatusIcon::make(sid, 0, (float)F(eff, "value", 0.0), 48));
                const Json& sdef = DB.status(sid);
                std::string txt = UIKit::fmt("%s %dT", S(sdef, "name", sid).c_str(), I(eff, "duration", 0));
                if (F(eff, "chance", 1.0) < 1.0) txt += UIKit::fmt(" (%d%%)", (int)std::round(F(eff, "chance", 1.0) * 100));
                row->add(label(txt, T_SMALL, Col(S(sdef, "color", "#ffffff")), gd::ALIGN_LEFT, 5));
            }
            v->add(row);
        }
        return p;
    }

    gd::Control* evolution_path(const Json& def)
    {
        auto p = PanelFrame::make("inset", 18);
        p->set_name("EvolutionPath");
        auto v = vbox(8);
        p->add(v);
        v->add(label("EVOLUTION PATH", T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
        auto row = hbox(8);
        row->alignment = gd::ALIGNMENT_CENTER;
        Json forms = DB.family_forms(S(def, "family"));
        for (size_t i = 0; i < forms.size(); i++)
        {
            std::string fid = S(forms[i]);
            const Json& fd = DB.character(fid);
            bool current = fid == S(def, "id");
            auto cell = vbox(2);
            auto frame = PanelFrame::make("rarity_" + std::to_string(std::clamp(I(fd, "rarity", 3), 3, 6)), 6);
            frame->add(portrait_art(fd, Vec2(180, 180)));
            if (!current) frame->set_modulate(Col(0.7f, 0.7f, 0.75f));
            cell->add(frame);
            std::string name = S(fd, "name");
            size_t sp = name.find(' ');
            if (sp != std::string::npos)
            {
                name = name.substr(sp + 1);
                name = name.substr(0, name.find(' '));   // get_slice(" ", 1)
            }
            cell->add(label(name, T_SMALL, current ? GOLD : MUTED, gd::ALIGN_CENTER, 5));
            cell->add(stars(I(fd, "rarity", 3), 20));
            row->add(cell);
            if (i < forms.size() - 1) row->add(label(">", T_HEAD, EMBER, gd::ALIGN_CENTER, 6));
        }
        v->add(row);
        return p;
    }

    // Full-screen character viewer: big sprite on the element backdrop with
    // animation buttons, portrait and description.
    void open_viewer()
    {
        if (UIManager::has_popup("CharacterViewer")) return;
        const Json& def = DB.character(S(unit, "char_id"));
        auto p = FantasyPopup::open(this, "", 1040, "card_" + S(def, "element", "fire") + "_lit");
        p->set_name("CharacterViewer");
        p->tap_outside_closes = true;
        auto holder = gd::Control::create();
        holder->set_custom_min(Vec2(980, 820));
        holder->set_mouse_filter(gd::MOUSE_IGNORE);
        p->content->add(holder);
        auto big = UnitSpriteDisplay::make(O(def, "sprite"), 14.0f, true);
        Vec2 s = big->custom_min();
        big->set_size(s);
        big->set_position(Vec2(490 - s.x / 2, 800 - s.y));
        holder->add(big);
        // one-shot animations return to idle (idle loops, so it never "finishes")
        if (big->sprite) big->sprite->animation_finished.connect([big] { big->play("idle"); });
        p->content->add(label(S(def, "name"), T_HEAD, Col("#fff0c0"), gd::ALIGN_CENTER, 10));
        auto d = wrap_label(S(def, "description"), T_BODY);
        d->set_align(gd::ALIGN_CENTER);
        d->set_min_w(960);
        p->content->add(d);
        auto row = hbox(SP_S);
        row->alignment = gd::ALIGNMENT_CENTER;
        for (std::string a : {"idle", "attack", "burst", "victory"})
        {
            auto b = btn(upper(a), "secondary", Vec2(220, 96));
            b->set_name("Anim_" + a);
            b->set_font_size(T_BODY);
            b->pressed.connect([big, a] { big->play(a); });
            row->add(b);
        }
        p->content->add(row);
        auto close = btn("CLOSE", "quiet", Vec2(300, 100));
        close->set_name("ViewerClose");
        close->set_h_flags(gd::SIZE_SHRINK_CENTER);
        close->pressed.connect([p] { p->close(); });
        p->content->add(close);
        p->default_action = [p] { p->close(); };
    }

    void poke_sprite()
    {
        if (!sprite || !sprite->sprite) return;
        sprite->play(GM.rng.randf() < 0.6 ? "attack" : "victory");
        AudioManager::play_sfx("unit_select", 0.05f, -4.0f);
        if (!B(sprite->meta, "idle_hooked", false))
        {
            sprite->meta["idle_hooked"] = true;
            auto sd = sprite;
            sd->sprite->animation_finished.connect([sd] { sd->play("idle"); });
        }
    }
};
REGISTER_SCREEN("unit_detail", UnitDetail)
