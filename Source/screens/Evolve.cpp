// EVOLVE (scripts/ui/evolve.gd): current form -> next form, stat changes, required
// materials (each with WHERE TO FIND), gold cost and the level requirement. Confirming
// plays the evolution ceremony and shows the new form.
#include "screens/Screens.h"

using namespace UIKit;
using gd::Rect2;

class EvolveScreen : public ScreenBase
{
public:
    std::string uid;
    gd::BoxContainer* body = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        uid = S(params(), "uid", GM.leader_uid());
        auto area = build_frame("bg_camp", "EVOLUTION", "units", nullptr, 0.65f);
        auto scroll = gd::ScrollContainer::create();
        scroll->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(scroll);
        body = vbox(14);
        body->set_h_flags(gd::SIZE_EXPAND_FILL);
        scroll->add(body);
        build();
    }

    void build()
    {
        body->clear_children();
        Json unit = GM.unit(uid);
        const Json& def = DB.character(S(unit, "char_id"));
        Json st = GM.evolution_status(uid);
        if (B(st, "final", false) || !st.contains("into"))
        {
            body->add(heading("FINAL FORM", T_HEAD));
            body->add(label(S(def, "name") + " has reached their final form.", T_BODY, MUTED, gd::ALIGN_CENTER));
            return;
        }
        const Json& nxt = DB.character(S(st, "into"));

        // ---- forms
        auto forms = PanelFrame::make("card_" + S(def, "element", "neutral") + "_lit", 16);
        forms->set_name("EvolutionForms");
        body->add(forms);
        auto fr = hbox(10);
        fr->alignment = gd::ALIGNMENT_CENTER;
        forms->add(fr);
        fr->add(form_card(def, UIKit::fmt("Lv.%d / %d", I(unit, "level", 1), I(def, "max_level", 15))));
        auto arrow = vbox(4);
        arrow->alignment = gd::ALIGNMENT_CENTER;
        arrow->add(label(">>", T_TITLE, EMBER, gd::ALIGN_CENTER, 12));
        fr->add(arrow);
        fr->add(form_card(nxt, UIKit::fmt("Lv.1 / %d", I(nxt, "max_level", 25))));

        // ---- stats
        auto sp = PanelFrame::make("panel", 20);
        sp->set_name("EvolutionStats");
        body->add(sp);
        auto sv = vbox(6);
        sp->add(sv);
        sv->add(label("STATS  (now  >  new form Lv.1  /  new max)", T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
        Json now = GM.unit_stats(unit);
        Json at1 = Progression::unit_stats(nxt, 1);
        Json atmax = Progression::unit_stats(nxt, I(nxt, "max_level", 25));
        for (std::string k : {"hp", "atk", "def", "rec"})
        {
            auto r = hbox(12);
            auto n = label(upper(k), T_BODY, SKY, gd::ALIGN_LEFT, 6);
            n->set_min_w(110);
            r->add(n);
            r->add(label(std::to_string(I(now, k, 0)), T_BODY, TEXT, gd::ALIGN_LEFT, 6));
            r->add(label(">", T_BODY, EMBER, gd::ALIGN_LEFT, 6));
            int diff = I(at1, k, 0) - I(now, k, 0);
            r->add(label(UIKit::fmt("%d (%s%d)", I(at1, k, 0), diff >= 0 ? "+" : "", diff), T_BODY, diff >= 0 ? GOOD : EMBER,
                         gd::ALIGN_LEFT, 6));
            r->add(spacer());
            r->add(label(UIKit::fmt("MAX %d", I(atmax, k, 0)), T_BODY, GOLD, gd::ALIGN_RIGHT, 6));
            sv->add(r);
        }
        std::vector<std::string> changes;
        if (S(nxt, "burst") != S(def, "burst")) changes.push_back("New Burst: " + S(DB.skill(S(nxt, "burst")), "name"));
        changes.push_back("Passive: " + S(O(nxt, "passive"), "description"));
        changes.push_back("Leader Skill: " + S(O(nxt, "leader_skill"), "description"));
        changes.push_back("Level resets to 1 with a higher cap. Burst level is kept.");
        for (auto& ctext : changes)
        {
            auto cl = wrap_label(ctext, T_SMALL, Col("#e8dece"));
            cl->set_min_w(960);
            sv->add(cl);
        }

        // ---- requirements
        auto rp = PanelFrame::make("panel", 20);
        rp->set_name("EvolutionRequirements");
        body->add(rp);
        auto rv = vbox(8);
        rp->add(rv);
        rv->add(label("REQUIREMENTS", T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
        int max_l = I(def, "max_level", 15);
        bool max_ok = I(unit, "level", 1) >= max_l;
        auto lr = hbox(10);
        lr->add(icon(max_ok ? "assets/icons/check.png" : "assets/icons/lock.png", 40));
        lr->add(label(UIKit::fmt("Reach Lv.%d (max level)", max_l), T_BODY, max_ok ? GOOD : DANGER, gd::ALIGN_LEFT, 6));
        if (!max_ok && GM.feature_unlocked("training"))
        {
            lr->add(spacer());
            auto tb = FantasyButton::make("TRAIN", "gold", Vec2(200, 80));
            tb->set_font_size(28);
            tb->pressed.connect([this] { SceneRouter::go("train", {{"uid", uid}}); });
            lr->add(tb);
        }
        rv->add(lr);
        for (auto& [m, q] : O(st, "materials").items()) rv->add(material_row(m, I(q)));
        int gold_need = I(st, "gold", 0);
        auto gr = hbox(10);
        gr->add(icon("assets/icons/gold.png", 56));
        gr->add(label(format_number(gold_need) + " Gold  (you have " + format_number(GM.gold()) + ")", T_BODY,
                      GM.gold() >= gold_need ? GOOD : DANGER, gd::ALIGN_LEFT, 6));
        rv->add(gr);

        // ---- action
        bool ok = B(st, "ok", false);
        auto b = FantasyButton::make("EVOLVE", "ember", Vec2(560, 140));
        b->set_name("ConfirmEvolve");
        b->set_h_flags(gd::SIZE_SHRINK_CENTER);
        b->set_font_size(T_HEAD);
        b->set_disabled(!ok);
        if (ok) b->add_shine();
        std::string def_id = S(unit, "char_id"), nxt_id = S(st, "into");
        b->pressed.connect([this, def_id, nxt_id, st] { confirm(DB.character(def_id), DB.character(nxt_id), st); });
        body->add(b);
        for (auto& reason : A(st, "reasons")) body->add(label(S(reason), T_SMALL, MUTED, gd::ALIGN_CENTER, 5));
    }

    gd::Control* form_card(const Json& d, const std::string& sub)
    {
        auto v = vbox(4);
        auto frame = PanelFrame::make("rarity_" + std::to_string(std::clamp(I(d, "rarity", 3), 3, 6)), 8);
        frame->add(portrait_art(d, Vec2(380, 380)));
        v->add(frame);
        auto n = label(S(d, "name"), T_BODY, Col("#fff0c0"), gd::ALIGN_CENTER, 6);
        n->set_min_w(400);
        n->set_clip_text(true);
        v->add(n);
        auto s = stars(I(d, "rarity", 3), 32);
        s->alignment = gd::ALIGNMENT_CENTER;
        v->add(s);
        v->add(label(sub, T_SMALL, GOLD, gd::ALIGN_CENTER, 5));
        return v;
    }

    gd::Control* material_row(const std::string& item_id, int need)
    {
        int have = GM.item_count(item_id);
        auto row = PanelFrame::make("plank", 8);
        row->set_name("Material_" + item_id);
        auto h = hbox(12);
        row->add(h);
        h->add(icon(S(DB.item(item_id), "icon"), 64));
        auto v = vbox(0);
        v->set_h_flags(gd::SIZE_EXPAND_FILL);
        v->add(label(DB.item_name(item_id), T_BODY, TEXT, gd::ALIGN_LEFT, 6));
        v->add(label(UIKit::fmt("%d / %d", have, need), T_BODY, have >= need ? GOOD : DANGER, gd::ALIGN_LEFT, 6));
        h->add(v);
        auto src = btn("WHERE TO FIND", have < need ? "secondary" : "quiet", Vec2(300, 80));
        src->set_name("Source_" + item_id);
        src->set_font_size(T_SMALL);
        src->pressed.connect([this, item_id] { ItemSources::open(this, item_id); });
        h->add(src);
        return row;
    }

    // The one confirmation: what will be spent, then the ceremony.
    void confirm(const Json& def, const Json& nxt, const Json& st)
    {
        ConfirmOpts o;
        for (auto& [m, q] : O(st, "materials").items())
            o.lines.push_back({S(DB.item(m), "icon"), DB.item_name(m) + "  x" + std::to_string(I(q)), TEXT});
        o.lines.push_back({"assets/icons/gold.png", format_number(I(st, "gold", 0)) + " Gold", GOLD});
        o.name = "EvolveConfirm";
        UIManager::confirm("EVOLVE?", S(def, "name") + " becomes " + S(nxt, "name") + ". These will be used:", "EVOLVE",
                           [this] { do_evolve(); }, o);
    }

    // Evolution ceremony: light gathers, the old form dissolves, the new form bursts out.
    void do_evolve()
    {
        prev = DB.character(S(GM.unit(uid), "char_id"));
        const Json& before = prev;
        Json r = GM.evolve(uid);
        if (!B(r, "ok", false))
        {
            std::string reasons;
            for (auto& x : A(r, "reasons")) reasons += (reasons.empty() ? "" : ", ") + S(x);
            UIManager::toast("Cannot evolve: " + reasons, "error");
            return;
        }
        const Json& after = DB.character(S(r, "into"));
        auto o = gd::Control::create();
        o->set_name("EvolveCeremony");
        o->set_anchors_preset(gd::PRESET_FULL_RECT);
        o->set_mouse_filter(gd::MOUSE_STOP);
        o->set_z(70);
        add(o);
        auto dim = gd::ColorRect::create(Col(0.02f, 0.01f, 0.04f));
        dim->set_alpha(0);
        dim->set_anchors_preset(gd::PRESET_FULL_RECT);
        o->add(dim);
        Vec2 vp = size();
        Col col(DB.element_color(S(after, "element")));
        auto sp_old = UnitSpriteDisplay::make(O(before, "sprite"), 12.0f, false);
        sp_old->set_size(sp_old->custom_min());
        sp_old->set_position(Vec2(vp.x / 2 - sp_old->size().x / 2, vp.y * 0.55f - sp_old->size().y));
        o->add(sp_old);
        AudioManager::play_sfx("evolve");
        auto tw = gd::tween(this);
        tw->alpha(dim, 0.9f, 0.4f);
        tw->on_finished([this, o, sp_old, vp, col, after] {
            sparkle(o, Rect2{Vec2(vp.x / 2 - 300, vp.y * 0.25f), Vec2(600, 700)}, col.lightened(0.4f), 30);
            for (int i = 0; i < 3; i++)
            {
                auto rr = gd::ColorRect::create(Col(col.r, col.g, col.b, 0.35f));
                rr->set_size(Vec2(40, 40));
                rr->set_position(Vec2(vp.x / 2 - 20, vp.y * 0.45f - 20));
                rr->set_pivot(Vec2(20, 20));
                o->add(rr);
                auto t2 = gd::tween(rr);
                t2->interval(i * 0.25f);
                t2->scale(rr, Vec2(30, 30), 0.6f).parallel().alpha(rr, 0.0f, 0.6f);
                t2->callback([rr] { rr->queue_free(); });
            }
            // ponytail: Godot flashes the sprite over-bright (modulate 3x); no over-bright here, so it just holds then fades
            auto t3 = gd::tween(this);
            t3->interval(0.6f);
            t3->alpha(sp_old, 0.0f, 0.25f);
            t3->on_finished([this, o, vp, after] { reveal(o, vp, after); });
        });
    }

    void reveal(gd::Control* o, Vec2 vp, const Json& after)
    {
        auto flash = gd::ColorRect::create(Col::WHITE);
        flash->set_alpha(0.9f);
        flash->set_anchors_preset(gd::PRESET_FULL_RECT);
        o->add(flash);
        auto sp_new = UnitSpriteDisplay::make(O(after, "sprite"), 12.0f, false, "victory");
        sp_new->set_size(sp_new->custom_min());
        sp_new->set_position(Vec2(vp.x / 2 - sp_new->size().x / 2, vp.y * 0.55f - sp_new->size().y));
        o->add(sp_new);
        AudioManager::play_sfx("summon_rare");
        gd::tween(this)->alpha(flash, 0.0f, 0.5f);
        auto title = heading("EVOLUTION COMPLETE", T_TITLE, GOLD);
        title->set_position(Vec2(0, vp.y * 0.12f));
        title->set_size(Vec2(vp.x, 140));
        o->add(title);
        auto nm = label(S(after, "name"), T_HEAD, Col("#fff0c0"), gd::ALIGN_CENTER, 10);
        nm->set_position(Vec2(0, vp.y * 0.6f));
        nm->set_size(Vec2(vp.x, 70));
        o->add(nm);
        int rarity = I(after, "rarity", 4);
        auto st = stars(rarity, 64);
        st->set_position(Vec2(vp.x / 2 - rarity * 32, vp.y * 0.6f + 80));
        o->add(st);
        // what changed, in one line
        std::string summary_text = UIKit::fmt("Max Lv.%d", I(after, "max_level", 25));
        if (S(after, "burst") != S(prev, "burst")) summary_text += "   -   New Burst: " + S(DB.skill(S(after, "burst")), "name");
        if (S(O(after, "passive"), "name") != S(O(prev, "passive"), "name"))
            summary_text += "   -   New Passive: " + S(O(after, "passive"), "name");
        auto summary = wrap_label(summary_text, T_BODY, TEXT);
        summary->set_name("EvolveSummary");
        summary->set_align(gd::ALIGN_CENTER);
        summary->set_position(Vec2(60, vp.y * 0.6f + 160));
        summary->set_size(Vec2(vp.x - 120, 90));
        o->add(summary);
        UIManager::haptic("evolve");
        auto ok = btn("CONTINUE", "primary", Vec2(420, 130));
        ok->set_name("EvolveContinue");
        ok->set_position(Vec2(vp.x / 2 - 210, vp.y * 0.6f + 280));
        o->add(ok);
        ok->pressed.connect([this] { SceneRouter::go("unit_detail", {{"uid", uid}}); });
    }

    Json prev;   // pre-evolution character def (for the summary)
};
REGISTER_SCREEN("evolve", EvolveScreen)
