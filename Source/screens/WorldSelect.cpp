// QUEST hub (scripts/ui/world_select.gd): one card per story world with its scenery, completion,
// stars and boss state, plus the Elemental Towers. Tapping a world opens its stage map.
#include "screens/Screens.h"
#include <cmath>

using namespace gd;

class WorldSelect : public ScreenBase
{
public:
    static constexpr float ART_SCALE = 5;
    static constexpr int CARD_H = 330;
    BoxContainer* list = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        auto area = build_frame("bg_camp", "QUEST", "world_select", nullptr, 0.6f, true, {{"help", "progress"}});
        auto scroll = ScrollContainer::create();
        scroll->set_name("WorldScroll");
        scroll->set_anchors_preset(PRESET_FULL_RECT);
        area->add(scroll);
        list = UIKit::vbox(UIKit::SP_L);
        list->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(list);
        for (auto& wid : DB.world_order) list->add(world_card(wid));
        list->add(tower_card());
        AudioManager::play_music("world");
    }

    Control* world_card(const std::string& wid)
    {
        const Json& w = at(DB.worlds, wid);
        bool open = GM.world_unlocked(wid);
        const Json& stages = A(w, "stages");
        int cleared = 0;
        std::string boss_id;
        for (auto& st : stages)
        {
            if (GM.is_stage_cleared(S(st, "id"))) ++cleared;
            if (B(st, "boss", false)) boss_id = S(st, "id");
        }
        int stars = GM.total_stars(wid);
        std::string bg_name = "forest";
        if (!stages.empty())
        {
            bg_name = S(stages[0], "background", "bg_forest");
            if (bg_name.rfind("bg_", 0) == 0) bg_name = bg_name.substr(3);
        }
        BoxContainer* v = nullptr;
        auto card = make_card("World_" + wid, bg_name, open, v);
        auto top = UIKit::hbox(UIKit::SP_M);
        top->set_mouse_filter(MOUSE_IGNORE);
        top->add(UIKit::label(UIKit::fmt("WORLD %d", I(w, "number", 1)), UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 6));
        top->add(UIKit::spacer());
        if (open)
        {
            top->add(UIKit::icon("assets/icons/star.png", 32));
            top->add(UIKit::label(UIKit::fmt("%d / %d", stars, int(stages.size()) * 3), UIKit::T_BODY, UIKit::GOLD, ALIGN_LEFT, 6));
        }
        v->add(top);
        v->add(UIKit::label(upper(S(w, "name", wid)), open ? UIKit::T_TITLE : UIKit::T_HEAD, open ? Col("#fff0c0") : UIKit::MUTED,
                            ALIGN_LEFT, 12));
        auto sub = UIKit::label(S(w, "subtitle"), UIKit::T_SMALL, UIKit::TEXT, ALIGN_LEFT, 6);
        sub->set_autowrap(true);
        v->add(sub);
        v->add(UIKit::spacer(false, true));
        auto bottom = UIKit::hbox(UIKit::SP_M);
        bottom->set_mouse_filter(MOUSE_IGNORE);
        std::string wname = S(w, "name");
        if (open)
        {
            int pct = (int)std::lround(100.0 * cleared / std::max<size_t>(1, stages.size()));
            auto bar = ResourceBar::make("xp", 28);
            bar->set_min_w(360);
            bar->set_v_flags(SIZE_SHRINK_CENTER);
            bar->set_values((float)cleared, (float)stages.size(), false);
            bottom->add(bar);
            auto pl = UIKit::label(UIKit::fmt("%d%% CLEARED", pct), UIKit::T_BODY, pct >= 100 ? UIKit::GOOD : UIKit::TEXT, ALIGN_LEFT, 6);
            pl->set_name("Completion");
            bottom->add(pl);
            bottom->add(UIKit::spacer());
            bool boss_done = !boss_id.empty() && GM.is_stage_cleared(boss_id);
            bottom->add(UIKit::tag(boss_done ? "BOSS DEFEATED" : "BOSS AWAITS", boss_done ? Col("#2a5a1a") : Col("#7a1a14")));
        }
        else
        {
            bottom->add(UIKit::icon("assets/icons/lock.png", 40));
            auto why = UIKit::label("Clear " + GM.stage_label(S(w, "requires")) + " to open", UIKit::T_BODY, UIKit::EMBER, ALIGN_LEFT, 6);
            why->set_name("LockReason");
            bottom->add(why);
        }
        v->add(bottom);
        if (open)
            UIKit::on_tap(card, [wid] { SceneRouter::go("stage_select", {{"world", wid}}); });
        else
        {
            std::string msg = "Clear " + GM.stage_label(S(w, "requires")) + " to reach " + wname + ".";
            UIKit::on_tap(card, [msg] { UIManager::toast(msg, "info"); });
        }
        return card;
    }

    Control* tower_card()
    {
        bool open = GM.feature_unlocked("tower");
        BoxContainer* v = nullptr;
        auto card = make_card("World_towers", "", open, v);
        v->add(UIKit::label("CHALLENGE", UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 6));
        v->add(UIKit::label("ELEMENTAL TOWERS", UIKit::T_HEAD, open ? Col("#fff0c0") : UIKit::MUTED, ALIGN_LEFT, 12));
        v->add(UIKit::spacer(false, true));
        auto row = UIKit::hbox(UIKit::SP_L);
        row->set_mouse_filter(MOUSE_IGNORE);
        if (open)
        {
            for (auto& t : DB.tower_order)
            {
                const Json& td = at(DB.towers, t);
                auto h = UIKit::hbox(UIKit::SP_S);
                h->set_mouse_filter(MOUSE_IGNORE);
                h->add(UIKit::orb(S(td, "element", "fire"), 40));
                h->add(UIKit::label(UIKit::fmt("%d/%d", GM.tower_highest_floor(t), int(A(td, "stages").size())), UIKit::T_BODY, UIKit::TEXT,
                                    ALIGN_LEFT, 6));
                row->add(h);
            }
            row->add(UIKit::spacer());
            row->add(UIKit::label("Evolution materials", UIKit::T_SMALL, UIKit::MUTED, ALIGN_RIGHT, 5));
            UIKit::on_tap(card, [] { SceneRouter::go("tower"); });
        }
        else
        {
            std::string req = GM.feature_unlock_label("tower");
            row->add(UIKit::icon("assets/icons/lock.png", 40));
            row->add(UIKit::label("Clear " + req + " to open", UIKit::T_BODY, UIKit::EMBER, ALIGN_LEFT, 6));
            UIKit::on_tap(card, [req] { UIManager::toast("The towers open after clearing " + req + ".", "info"); });
        }
        v->add(row);
        return card;
    }

    // Card shell: layered scenery (or the tower backdrop), a dark gradient for text
    // contrast, and a frame. `body` receives the card's text column.
    PanelFrame* make_card(const std::string& node_name, const std::string& bg, bool open, BoxContainer*& body)
    {
        auto card = PanelFrame::make("panel", 8);
        card->set_name(node_name);
        card->set_custom_min(Vec2(0, CARD_H));
        auto clip = Control::create();
        clip->set_clip(true);
        clip->set_mouse_filter(MOUSE_IGNORE);
        card->add(clip);
        auto art = Control::create();
        art->set_mouse_filter(MOUSE_IGNORE);
        clip->add(art);
        Vec2 src(200, 270);
        if (bg.empty())
        {
            auto t = UIKit::tex_rect(gd::texture("assets/environments/bg_tower.png"), Vec2::ZERO);
            t->set_size(t->texture_size() * 6);
            art->add(t);
            src = t->texture_size() * 6.0f / ART_SCALE;
        }
        else
            for (auto layer : {"far", "mid", "ground"})
            {
                std::string path = "assets/environments/battle/" + bg + "_" + layer + ".png";
                if (!gd::exists(path)) continue;
                auto t = UIKit::tex_rect(gd::texture(path), Vec2::ZERO);
                t->set_size(t->texture_size() * ART_SCALE);
                art->add(t);
                src = t->texture_size();
            }
        if (!open) art->set_modulate(Col(0.35f, 0.33f, 0.4f));
        clip->resized.connect([clip, art, src] {
            // centre the art horizontally and show the band just above the ground line
            art->set_position(Vec2((clip->size().x - src.x * ART_SCALE) / 2.0f, clip->size().y - src.y * ART_SCALE * 0.72f));
        });
        auto shade = TextureRect::create();
        shade->set_texture(gradient_texture({{0.0f, Col(0.03f, 0.02f, 0.05f, 0.85f)}, {1.0f, Col(0.03f, 0.02f, 0.05f, 0.1f)}}, 64, 64,
                                            false, Vec2(0, 0.5f), Vec2(1, 0.5f)));
        shade->ignore_size = true;
        shade->set_anchors_preset(PRESET_FULL_RECT);
        shade->set_mouse_filter(MOUSE_IGNORE);
        clip->add(shade);
        auto margin = MarginContainer::create(UIKit::SP_XL, UIKit::SP_XL, UIKit::SP_XL, UIKit::SP_XL);
        margin->set_mouse_filter(MOUSE_IGNORE);
        clip->add(margin);
        margin->set_anchors_preset(PRESET_FULL_RECT);
        body = UIKit::vbox(UIKit::SP_XS);
        body->set_mouse_filter(MOUSE_IGNORE);
        margin->add(body);
        return card;
    }
};
REGISTER_SCREEN("world_select", WorldSelect)
