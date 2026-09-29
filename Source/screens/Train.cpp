// TRAINING (scripts/ui/train.gd): feed Wisps (+ Gold) to one hero. Each material card has
// -1 / +1 / +5 / MAX; the preview (level, EXP bar, stat gains, Gold cost) updates live.
// Same-element Wisps give +50% EXP. Nothing is spent until TRAIN is pressed.
#include "screens/Screens.h"

using namespace UIKit;
using gd::Rect2;

static const std::vector<std::string> WISPS = {"ember_wisp", "tide_wisp", "verdant_wisp", "radiant_wisp"};
static const char* STAT_KEYS[] = {"hp", "atk", "def", "rec"};

class TrainScreen : public ScreenBase
{
public:
    std::string uid;
    Json unit, def;
    Json sel = Json::object();   // wisp id -> amount chosen
    gd::BoxContainer* hero_box = nullptr;
    gd::GridContainer* cards = nullptr;
    gd::BoxContainer* footer = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        uid = S(params(), "uid");
        if (GM.unit(uid).is_null()) uid = GM.leader_uid();
        back_fallback = "units";
        auto area = build_frame("bg_camp", "TRAINING", "units", nullptr, 0.6f, true, {{"help", "units"}});
        auto col = vbox(SP_M);
        col->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(col);
        auto hp = PanelFrame::make("panel", 18);
        hp->set_name("TrainPreview");
        col->add(hp);
        hero_box = vbox(SP_S);
        hp->add(hero_box);
        col->add(label("WISPS", T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
        auto scroll = gd::ScrollContainer::create();
        scroll->set_v_flags(gd::SIZE_EXPAND_FILL);
        col->add(scroll);
        cards = gd::GridContainer::create(2);
        cards->set_h_flags(gd::SIZE_EXPAND_FILL);
        cards->h_separation = SP_M;
        cards->v_separation = SP_M;
        scroll->add(cards);
        auto fp = PanelFrame::make("plank", 14);
        col->add(fp);
        footer = vbox(SP_S);
        fp->add(footer);
        render();
    }

    void render()
    {
        unit = GM.unit(uid);
        def = DB.character(S(unit, "char_id"));
        Json pv = GM.preview_training(uid, sel);
        render_hero(pv);
        render_cards(pv);
        render_footer(pv);
    }

    void render_hero(const Json& pv)
    {
        hero_box->clear_children();
        auto h = hbox(SP_L);
        hero_box->add(h);
        auto fr = PanelFrame::make("rarity_" + std::to_string(std::clamp(I(def, "rarity", 3), 3, 6)), 6);
        fr->add(portrait_art(def, Vec2(200, 200)));
        h->add(fr);
        auto v = vbox(SP_XS);
        v->set_h_flags(gd::SIZE_EXPAND_FILL);
        h->add(v);
        auto nh = hbox(SP_S);
        nh->add(orb(S(def, "element"), 40));
        auto nm = label(S(def, "name"), T_NAME, Col("#fff0c0"), gd::ALIGN_LEFT, 8);
        nm->set_h_flags(gd::SIZE_EXPAND_FILL);
        nh->add(nm);
        v->add(nh);
        int lb = I(pv, "level_before", I(unit, "level", 1));
        int la = I(pv, "level_after", lb);
        int max_l = I(def, "max_level", 20);
        std::string lt = UIKit::fmt("Lv.%d", lb) + (la > lb ? UIKit::fmt("  >  Lv.%d", la) : "") +
                         (la >= max_l ? UIKit::fmt("  (MAX %d)", max_l) : UIKit::fmt("  / %d", max_l));
        auto lv = label(lt, la > lb ? T_HEAD : T_NAME, la > lb ? GOLD : TEXT, gd::ALIGN_LEFT, 8);
        lv->set_name("PreviewLevel");
        v->add(lv);
        // EXP bar: where the hero will end up after training
        auto xb = ResourceBar::make("xp", 28);
        xb->set_h_flags(gd::SIZE_EXPAND_FILL);
        int exp_after = I(pv, "exp_after", I(unit, "exp", 0));
        int need = la < max_l ? Progression::xp_to_next(la) : 1;
        xb->set_values(la < max_l ? (float)exp_after : 1.0f, (float)need, false);
        v->add(xb);
        const Json& g = O(pv, "gains");
        Json stats = GM.unit_stats(unit);
        auto sg = gd::GridContainer::create(4);
        sg->h_separation = SP_XL;
        for (std::string key : STAT_KEYS)
        {
            auto cell = vbox(0);
            cell->add(label(upper(key), T_SMALL, SKY, gd::ALIGN_LEFT, 5));
            int gain = I(g, key, 0);
            auto val = label(std::to_string(I(stats, key, 0)) + (gain > 0 ? UIKit::fmt("  +%d", gain) : ""), T_BODY,
                             gain > 0 ? GOOD : TEXT, gd::ALIGN_LEFT, 6);
            val->set_name("Gain_" + key);
            cell->add(val);
            sg->add(cell);
        }
        v->add(sg);
        if (I(pv, "wasted_xp", 0) > 0)
            hero_box->add(label("Reaches the level cap - extra EXP would be wasted.", T_SMALL, EMBER, gd::ALIGN_CENTER, 5));
        if (B(pv, "at_cap", false))
        {
            std::string cap = std::string("Max level reached.") + (at(def, "evolution").is_object() ? " Evolve to raise the cap." : "");
            hero_box->add(label(cap, T_BODY, EMBER, gd::ALIGN_CENTER, 6));
        }
    }

    void render_cards(const Json& pv)
    {
        cards->clear_children();
        bool full = B(pv, "at_cap", false) || I(pv, "wasted_xp", 0) > 0 || I(pv, "used_xp", 0) >= Progression::xp_to_cap(unit);
        for (auto& w : WISPS)
        {
            int have = GM.item_count(w);
            int n = I(sel, w, 0);
            auto card = PanelFrame::make(n == 0 ? "inset" : "boss", 12);
            card->set_name("Wisp_" + w);
            card->set_h_flags(gd::SIZE_EXPAND_FILL);
            auto v = vbox(SP_XS);
            card->add(v);
            auto h = hbox(SP_S);
            const Json& item = DB.item(w);
            h->add(icon(S(item, "icon"), 64));
            auto tv = vbox(0);
            tv->set_h_flags(gd::SIZE_EXPAND_FILL);
            auto nm = label(DB.item_name(w), T_BODY, TEXT, gd::ALIGN_LEFT, 6);
            fit_label(nm, 300);
            tv->add(nm);
            bool bonus = S(item, "element") == S(def, "element", "-");
            tv->add(label(UIKit::fmt("+%d EXP%s", Progression::item_xp(w, def), bonus ? "  x1.5" : ""), T_SMALL, bonus ? GOOD : MUTED,
                          gd::ALIGN_LEFT, 4));
            h->add(tv);
            auto cnt = label(UIKit::fmt("%d / %d", n, have), T_NAME, n > 0 ? GOLD : MUTED, gd::ALIGN_RIGHT, 8);
            cnt->set_name("Count");
            h->add(cnt);
            v->add(h);
            auto row = hbox(SP_S);
            struct Step { const char* text; const char* name; int d; };
            for (auto st : {Step{"-1", "m1", -1}, Step{"+1", "p1", 1}, Step{"+5", "p5", 5}, Step{"MAX", "MAX", 999}})
            {
                auto b = btn(st.text, st.d < 0 ? "quiet" : "secondary", Vec2(0, TOUCH_MIN));
                b->set_name(std::string("Step_") + st.name);
                b->press_cooldown = 0.0f;
                b->set_h_flags(gd::SIZE_EXPAND_FILL);
                b->set_font_size(T_BODY);
                b->set_disabled(st.d < 0 ? n <= 0 : (n >= have || full));
                int d = st.d;
                std::string wid = w;
                b->pressed.connect([this, wid, d] { change(wid, d); });
                row->add(b);
            }
            v->add(row);
            if (have <= 0)
            {
                card->set_modulate(Col(0.6f, 0.6f, 0.65f));
                auto src = btn("WHERE TO FIND", "quiet", Vec2(0, 72));
                src->set_name("Source_" + w);
                src->set_h_flags(gd::SIZE_EXPAND_FILL);
                src->set_font_size(T_SMALL);
                std::string wid = w;
                src->pressed.connect([this, wid] { ItemSources::open(this, wid); });
                v->add(src);
            }
            cards->add(card);
        }
    }

    void render_footer(const Json& pv)
    {
        footer->clear_children();
        int cost = I(pv, "gold", 0);
        bool enough = GM.gold() >= cost;
        auto cl = hbox(SP_S);
        cl->alignment = gd::ALIGNMENT_CENTER;
        cl->add(label("+" + format_number(I(pv, "used_xp", 0)) + " EXP", T_BODY, TEXT, gd::ALIGN_LEFT, 6));
        cl->add(label("   COST", T_SMALL, SKY, gd::ALIGN_LEFT, 5));
        cl->add(icon("assets/icons/gold.png", 40));
        auto cost_l = label(format_number(cost) + "  (you have " + format_compact(GM.gold()) + ")", T_BODY, enough ? GOLD : DANGER,
                            gd::ALIGN_LEFT, 6);
        cost_l->set_name("TrainCost");
        cl->add(cost_l);
        footer->add(cl);
        auto row = hbox(SP_M);
        row->alignment = gd::ALIGNMENT_CENTER;
        auto autob = btn("AUTO", "secondary", Vec2(240, 110));
        autob->set_name("AutoSelect");
        autob->tooltip_text = "Pick wisps up to the next level cap (best match first)";
        autob->pressed.connect([this] { auto_select(); });
        row->add(autob);
        auto clear = btn("CLEAR", "quiet", Vec2(220, 110));
        clear->set_name("ClearSelection");
        clear->set_disabled(sel.empty());
        clear->pressed.connect([this] {
            sel = Json::object();
            render();
        });
        row->add(clear);
        auto ok = btn("TRAIN", "primary", Vec2(340, 120));
        ok->set_name("ConfirmTrain");
        ok->set_disabled(sel.empty() || B(pv, "at_cap", false));
        ok->pressed.connect([this, enough, cost] {
            if (!enough)
            {
                UIManager::not_enough("Gold", cost, GM.gold(), "Remove some wisps or earn Gold from stages.");
                return;
            }
            confirm();
        });
        row->add(ok);
        footer->add(row);
    }

    void change(const std::string& w, int d)
    {
        int have = GM.item_count(w);
        int n = I(sel, w, 0);
        if (d >= 999)
        {
            // MAX: as many as needed to reach the level cap (or all owned)
            int target = n;
            while (target < have)
            {
                Json trial = sel;
                trial[w] = target + 1;
                Json pv = GM.preview_training(uid, trial);
                target++;
                if (I(pv, "wasted_xp", 0) > 0 || I(pv, "used_xp", 0) >= Progression::xp_to_cap(unit)) break;
            }
            n = target;
        }
        else
        {
            n = std::clamp(n + d, 0, have);
            // never step past the cap
            while (n > I(sel, w, 0) && n > 0)
            {
                Json trial = sel;
                trial[w] = n - 1;
                if (I(GM.preview_training(uid, trial), "used_xp", 0) < Progression::xp_to_cap(unit)) break;
                n--;
            }
        }
        if (n <= 0)
            sel.erase(w);
        else
            sel[w] = n;
        UIManager::sfx("press", -6.0f);
        render();
    }

    // Picks wisps (best element match first) until the next level cap or Gold runs out.
    void auto_select()
    {
        sel = Json::object();
        std::vector<std::string> order = WISPS;
        // same-element wisps first (they give +50%), then the smallest to waste least
        std::string el = S(def, "element");
        std::sort(order.begin(), order.end(), [this, &el](const std::string& a, const std::string& b) {
            bool ma = S(DB.item(a), "element") == el, mb = S(DB.item(b), "element") == el;
            if (ma != mb) return ma;
            return Progression::item_xp(a, def) < Progression::item_xp(b, def);
        });
        int need = Progression::xp_to_cap(unit);
        int got = 0;
        for (auto& w : order)
        {
            int have = GM.item_count(w);
            int xp = Progression::item_xp(w, def);
            while (have > 0 && got < need)
            {
                if (Progression::training_gold(std::min(got + xp, need)) > GM.gold()) break;
                sel[w] = I(sel, w, 0) + 1;
                got += xp;
                have--;
            }
        }
        if (sel.empty())
            UIManager::toast(Progression::xp_to_cap(unit) > 0 ? "No wisps to use, or not enough Gold." : "This hero is at max level.", "info");
        render();
    }

    void confirm()
    {
        Json r = GM.train_unit_with(uid, sel);
        if (!B(r, "ok", false))
        {
            UIManager::toast(S(r, "reason", "Cannot train."), "error");
            return;
        }
        sel = Json::object();
        UIManager::sfx("level_up");
        UIManager::haptic("confirm");
        render();
        int before = I(r, "level_before", 1), after = I(r, "level_after", 1);
        bool up = after > before;
        auto p = FantasyPopup::open(this, up ? "LEVEL UP!" : "TRAINED", 760, "boss");
        p->set_name("TrainResult");
        p->content->add(heading(UIKit::fmt("Lv.%d  >  Lv.%d", before, after), T_TITLE, TEXT));
        const Json& g = O(r, "gains");
        for (std::string key : STAT_KEYS)
            p->content->add(label(upper(key) + "  +" + std::to_string(I(g, key, 0)), T_NAME, GOOD, gd::ALIGN_CENTER, 8));
        if (up) sparkle(p->panel, Rect2{Vec2(0, 0), Vec2(760, 400)}, GOLD, 12);
        auto ok = btn("OK", "primary", Vec2(300, 110));
        ok->set_name("TrainResultOK");
        ok->set_h_flags(gd::SIZE_SHRINK_CENTER);
        p->content->add(ok);
        ok->pressed.connect([p] { p->close(); });
        p->default_action = [p] { p->close(); };
    }
};
REGISTER_SCREEN("train", TrainScreen)
