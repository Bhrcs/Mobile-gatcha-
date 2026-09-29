// Starter selection (scripts/ui/starter_select.gd): three hero tiles on top, large detail card below.
#include "screens/Screens.h"

using namespace gd;

class StarterSelect : public ScreenBase
{
public:
    std::vector<std::string> starters;
    std::string selected_id;
    std::map<std::string, PanelFrame*> cards;
    BoxContainer* detail_box = nullptr;

    void on_back() override {}   // plain Control in Godot: Esc does nothing

    void ready() override
    {
        UIKit::screen_background(this, "bg_camp", 0.3f);
        ScreenHeader::attach(this, "CHOOSE YOUR HERO", [] { SceneRouter::go("main_menu"); }, 10 + UIKit::safe_top());
        starters = DB.starter_ids();

        auto body = UIKit::vbox(18);
        body->set_anchors_preset(PRESET_FULL_RECT);
        body->set_offsets(20, 144 + UIKit::safe_top(), -20, -24);
        add(body);

        auto row = UIKit::hbox(16);
        row->alignment = ALIGNMENT_CENTER;
        body->add(row);
        for (auto& id : starters) cards[id] = row->add(make_card(id));

        auto detail = UIKit::panel();
        detail->set_v_flags(SIZE_EXPAND_FILL);
        body->add(detail);
        detail_box = UIKit::vbox(14);
        detail->add(detail_box);

        auto buttons = UIKit::hbox(16);
        buttons->alignment = ALIGNMENT_CENTER;
        auto b_select = UIKit::button("SELECT", "", Vec2(330, 120), "ember");
        auto b_skills = UIKit::button("SKILLS", "", Vec2(330, 120));
        auto b_back = UIKit::button("BACK", "", Vec2(300, 120), "stone");
        b_select->pressed.connect([this] { on_select_pressed(); });
        b_skills->pressed.connect([this] { show_skills(DB.character(selected_id)); });
        b_back->pressed.connect([] { SceneRouter::go("main_menu"); });
        for (auto b : {b_select, b_skills, b_back})
        {
            b->set_font_size(40);
            buttons->add(b);
        }
        body->add(buttons);
        AudioManager::play_music("menu");
        if (!starters.empty()) select(starters[0]);
    }

    PanelFrame* make_card(const std::string& id)
    {
        const Json& def = DB.character(id);
        auto card = PanelFrame::make("card_" + S(def, "element", "neutral"));
        card->set_name("Starter_" + id);
        card->set_custom_min(Vec2(330, 0));
        auto v = UIKit::vbox(6);
        v->alignment = ALIGNMENT_CENTER;
        card->add(v);
        auto pf = UIKit::portrait_frame(def, 220);
        pf->set_h_flags(SIZE_SHRINK_CENTER);
        v->add(pf);
        std::string name = S(def, "name");
        v->add(UIKit::label(name.substr(0, name.find(' ')), 40, UIKit::TEXT, ALIGN_CENTER, 6));
        v->add(UIKit::label(S(def, "role"), 20, UIKit::MUTED, ALIGN_CENTER));
        UIKit::on_tap(card, [this, id] { select(id); });
        return card;
    }

    void select(const std::string& id)
    {
        selected_id = id;
        for (auto& [cid, c] : cards)
        {
            std::string el = S(DB.character(cid), "element", "neutral");
            c->set_variant("card_" + el + (cid == id ? "_lit" : ""));
            c->set_modulate(cid == id ? Col::WHITE : Col(0.66f, 0.66f, 0.72f));
        }
        if (!cards.empty()) AudioManager::play_sfx("unit_select", 0.03f, -4.0f);
        build_detail(DB.character(id));
    }

    void build_detail(const Json& def)
    {
        detail_box->clear_children();
        auto title = UIKit::hbox(14);
        title->add(UIKit::orb(S(def, "element"), 60));
        auto nm = UIKit::label(S(def, "name"), 50, UIKit::GOLD, ALIGN_LEFT, 8);
        nm->set_h_flags(SIZE_EXPAND_FILL);
        title->add(nm);
        title->add(UIKit::stars(I(def, "rarity", 3), 48));
        detail_box->add(title);

        // hero on an element-coloured stage
        auto stage = PanelFrame::make("inset", 6);
        stage->set_custom_min(Vec2(0, 432));
        detail_box->add(stage);
        auto holder = Control::create();
        holder->set_mouse_filter(MOUSE_IGNORE);
        stage->add(holder);
        auto portrait = UIKit::portrait_art(def, Vec2(420, 420));
        portrait->set_position(Vec2(0, 0));
        portrait->set_size(Vec2(420, 420));
        holder->add(portrait);
        auto sprite = UnitSpriteDisplay::make(O(def, "sprite"), 10.0f, true, "victory");
        Vec2 m = sprite->custom_min();
        sprite->set_position(Vec2(540, 410 - m.y));
        sprite->set_size(m);
        holder->add(sprite);

        auto info = UIKit::hbox(30);
        info->add(UIKit::element_badge(S(def, "element"), 30));
        info->add(UIKit::label(S(def, "role"), 30, UIKit::TEXT));
        detail_box->add(info);
        const Json& stats = O(def, "base_stats");
        auto grid = GridContainer::create(2);
        grid->h_separation = 80;
        grid->v_separation = 6;
        for (auto key : {"hp", "atk", "def", "rec"})
            grid->add(UIKit::stat_row(upper(key), std::to_string(I(stats, key, 0)), 40));
        detail_box->add(grid);
        auto desc = UIKit::wrap_label(S(def, "description"), 30);
        desc->set_min_w(900);
        detail_box->add(desc);
        struct Pair { const char* title; std::string skill; Col color; };
        for (auto& pr : {Pair{"NORMAL", S(def, "normal_attack"), Col("#d06a1e")}, Pair{"BURST", S(def, "burst"), Col("#2a6ad0")}})
        {
            const Json& sk = DB.skill(pr.skill);
            detail_box->add(UIKit::strip(pr.title, S(sk, "name"), pr.color));
            auto d = UIKit::wrap_label(S(sk, "description"), 30, Col("#e0d6c6"));
            d->set_min_w(900);
            detail_box->add(d);
        }
    }

    void show_skills(const Json& def)
    {
        auto m = UIKit::modal(this, "SKILLS", 1000);
        auto v = m->content;
        struct Pair { const char* title; std::string skill; Col color; };
        for (auto& pr : {Pair{"NORMAL", S(def, "normal_attack"), UIKit::EMBER}, Pair{"BURST", S(def, "burst"), Col("#3a78d8")}})
        {
            const Json& sk = DB.skill(pr.skill);
            v->add(UIKit::strip(pr.title, S(sk, "name"), pr.color));
            auto d = UIKit::wrap_label(S(sk, "description"), 30);
            d->set_min_w(920);
            v->add(d);
        }
        auto ok = UIKit::button("CLOSE", "", Vec2(320, 110), "stone");
        ok->set_h_flags(SIZE_SHRINK_CENTER);
        v->add(ok);
        ok->pressed.connect([m] { m->close(); });
    }

    void on_select_pressed()
    {
        const Json& def = DB.character(selected_id);
        std::string id = selected_id;
        UIKit::confirm(this, "Begin your journey with " + S(def, "name") + "?", [id] {
            GM.new_game(id);
            AudioManager::play_sfx("level_up");
            SceneRouter::go("intro");
        });
    }
};
REGISTER_SCREEN("starter_select", StarterSelect)
