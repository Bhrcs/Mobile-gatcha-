// Short story introduction shown after choosing a starter (scripts/ui/intro.gd).
#include "screens/Screens.h"

using namespace gd;

class Intro : public ScreenBase
{
public:
    std::vector<std::string> pages;
    size_t page = 0;
    Label* text_label = nullptr;
    Label* page_label = nullptr;
    FantasyButton* btn_next = nullptr;

    void on_back() override {}   // plain Control in Godot: Esc does nothing

    void ready() override
    {
        UIKit::screen_background(this, "bg_forest", 0.45f);
        const Json& starter = DB.character(S(GM.profile, "starter_id"));
        std::string name_s = S(starter, "name", "The hero");
        pages = {
            "The Ashroot Wilds were once the quietest forest in the realm - old trees, cold streams and broken stones from a forgotten age.",
            "Then the ground began to smoulder. Streams boiled. Beasts grew restless, and something ancient stirred at the Heart of the forest.",
            name_s + " has come to the edge of the Wilds to find out why.\n\n" + S(starter, "lore"),
            "Fight through ten stages, grow stronger with every victory, and reach the Heart of Ashroot.\n\nYour first battle awaits.",
        };
        auto col = UIKit::vbox(24);
        col->set_anchors_preset(PRESET_FULL_RECT);
        col->set_offsets(30, 90, -30, -60);
        add(col);
        col->add(UIKit::title_plate("ASHROOT WILDS"));
        auto pf = UIKit::portrait_frame(starter, 480);
        pf->set_h_flags(SIZE_SHRINK_CENTER);
        col->add(pf);
        auto p = UIKit::panel();
        p->set_v_flags(SIZE_EXPAND_FILL);
        col->add(p);
        auto v = UIKit::vbox(20);
        p->add(v);
        text_label = UIKit::wrap_label("", 40);
        text_label->set_v_flags(SIZE_EXPAND_FILL);
        v->add(text_label);
        page_label = UIKit::label("", 30, UIKit::MUTED, ALIGN_CENTER);
        v->add(page_label);
        auto bottom = UIKit::hbox(24);
        bottom->alignment = ALIGNMENT_CENTER;
        auto skip = UIKit::button("SKIP", "", Vec2(320, 120), "stone");
        btn_next = UIKit::button("NEXT", "", Vec2(420, 120), "ember");
        for (auto b : {skip, btn_next}) b->set_font_size(40);
        bottom->add(skip);
        bottom->add(btn_next);
        col->add(bottom);
        skip->pressed.connect([this] { finish(); });
        btn_next->pressed.connect([this] { next(); });
        AudioManager::play_music("world");
        show_page();
    }

    void show_page()
    {
        text_label->set_text(pages[page]);
        text_label->set_visible_ratio(0);
        auto l = text_label;
        gd::tween(this)->method([l](float r) { l->set_visible_ratio(r); }, 0.0f, 1.0f, 0.6f);
        page_label->set_text(UIKit::fmt("%d / %d", int(page + 1), int(pages.size())));
        btn_next->set_text(page == pages.size() - 1 ? "BEGIN" : "NEXT");
    }

    void next()
    {
        if (page < pages.size() - 1)
        {
            ++page;
            show_page();
        }
        else
            finish();
    }

    void finish()
    {
        GM.mark_intro_seen();
        SceneRouter::go("stage_select", {{"highlight", DB.stage_order[0]}});
    }
};
REGISTER_SCREEN("intro", Intro)
